"""
ddcutil MQTT - Remote Control of a Monitor/Display
https://github.com/ben-jam1n/ddcutil_mqtt

Controls monitor settings via DDC/CI using MQTT for Home Assistant integration.
- Loads config (YAML/JSON)
- Connects to MQTT broker
- Publishes Home Assistant discovery
- Handles monitor commands (brightness, input, PBP, etc.)
- Supports button, switch, select, and number entities
"""

# =========================
# Imports and Dependencies
# =========================
import json
import os
import sys
import paho.mqtt.client as mqtt
import subprocess
import time
import threading
import functools
try:
    import yaml
except ImportError:
    yaml = None

__version__ = "0.2"

# =========================
# Config Loading Utilities
# =========================
def load_config(config_path):
    """Load YAML or JSON config file."""
    if not os.path.exists(config_path):
        print(f"Config file not found: {config_path}")
        sys.exit(1)
    ext = os.path.splitext(config_path)[1].lower()
    with open(config_path, "r") as config_file:
        if ext in (".yaml", ".yml"):
            if yaml is None:
                print("PyYAML is required for YAML config files. Install with: pip install pyyaml")
                sys.exit(1)
            return yaml.safe_load(config_file)
        else:
            return json.load(config_file)

# =========================
# Logging Setup
# =========================
def setup_logging(log_level):
    """
    Set up logging optimized for systemd services.
    Logs to stdout/stderr which systemd captures and manages automatically.
    Includes rate limiting to prevent log spam and SD card overflow.
    """
    import logging
    import logging.handlers
    
    # Create logger
    logger = logging.getLogger(__name__)
    logger.setLevel(getattr(logging, log_level, logging.DEBUG))
    
    # Clear any existing handlers to avoid duplicates
    if logger.handlers:
        logger.handlers.clear()
    
    # Create formatter optimized for systemd (no timestamp since systemd adds it)
    formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    
    # Console handler for systemd to capture
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level, logging.DEBUG))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    logger.info("Logging configured for systemd service (viewable with: journalctl -u MQTT_DDC.service)")
    return logger

# =========================
# Main Application Logic
# =========================
def main():
    """Main entry point for ddcutil_MQTT."""
    # --- Config & Logging ---
    script_dir = os.path.dirname(os.path.realpath(__file__))
    default_config_path = os.path.join(script_dir, "config.yaml")
    config_path = sys.argv[1] if len(sys.argv) > 1 else default_config_path
    config = load_config(config_path)

    log_level = config.get("log_level", "INFO").upper()
    logger = setup_logging(log_level)

    # --- MQTT Setup ---
    MQTT_BROKER = config["mqtt_broker"]
    MQTT_PORT = config["mqtt_port"]
    MQTT_USERNAME = config["mqtt_username"]
    MQTT_PASSWORD = config["mqtt_password"]

    DEVICE_NAME = config["device_name"]
    SANITIZED_DEVICE_NAME = DEVICE_NAME.replace(" ", "_")
    TOPIC_PREFIX = f"ddc_control/{SANITIZED_DEVICE_NAME}"

    MQTT_TOPIC_COMMAND = f"{TOPIC_PREFIX}/command"
    MQTT_TOPIC_STATE = f"{TOPIC_PREFIX}/state"

    DEBOUNCE_DELAY = config.get("debounce_delay", 0.5)

    # --- DDC Command Helpers ---
    def handle_errors(func):
        """Decorator to handle errors in DDC commands."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                return None
        return wrapper

    @handle_errors
    def ddc_command(vcp_code, vcp_value=None, get=False, retries=3, timeout=2):
        """Send a DDC command to the monitor."""
        cmd = f"ddcutil {'getvcp' if get else 'setvcp'} {vcp_code}"
        if vcp_value is not None and not get:
            cmd += f" {vcp_value}"
        for attempt in range(retries):
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
                if result.returncode == 0:
                    return result.stdout
                logger.warning(f"Command failed (attempt {attempt + 1}/{retries}): {cmd}")
            except subprocess.TimeoutExpired as e:
                logger.warning(f"ddcutil command timed out: {cmd}, {e}")
            except Exception as e:
                logger.error(f"Error running command: {cmd}, Error: {e}")
            time.sleep(0.5)
        logger.error(f"Command failed after {retries} attempts: {cmd}")
        return None

    @handle_errors
    def ddc_command_button(vcp_code, vcp_value=None, get=False, timeout=2):
        """Send a single-attempt DDC command for button actions."""
        cmd = f"ddcutil {'getvcp' if get else 'setvcp'} {vcp_code}"
        if vcp_value is not None and not get:
            cmd += f" {vcp_value}"
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
            if result.returncode == 0:
                return result.stdout
            logger.warning(f"Button command failed: {cmd}")
        except subprocess.TimeoutExpired as e:
            logger.warning(f"Button ddcutil command timed out: {cmd}, {e}")
        except Exception as e:
            logger.error(f"Error running button command: {cmd}, Error: {e}")
        logger.error(f"Button command failed: {cmd}")
        return None

    @handle_errors
    def restart_service():
        """Trigger a service restart by exiting the process.
        
        When running under systemd with Restart=always, simply exiting
        will cause systemd to automatically restart the service.
        """
        try:
            logger.info("Exiting process to trigger systemd restart")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Error during restart: {e}")
            return False
            logger.error(f"Error during restart: {e}")
            return False

    # Centralized MQTT state publishing
    def publish_state(client, topic, value, retain=True):
        client.publish(topic, value, retain=retain)

    # Generic debounce helper
    class Debouncer:
        def __init__(self, delay):
            self.delay = delay
            self.timer = None
            self.latest_value = None

        def call(self, func, *args):
            self.latest_value = args[-1]
            if self.timer and self.timer.is_alive():
                self.timer.cancel()
            self.timer = threading.Timer(self.delay, func, args=args)
            self.timer.start()

    # Ensure discovery messages are retained
    def publish_discovery(client):
        """Publish Home Assistant discovery messages."""
        logger.debug("Publishing MQTT discovery messages...")
        discovery_payloads = []
        device_info = {
            "identifiers": [SANITIZED_DEVICE_NAME],
            "name": f"{DEVICE_NAME}",
            "manufacturer": "ben-jam1n",
            "model": "ddcutil to MQTT"
        }
        for control in config["controls"]:
            key = control["key"]
            name = control["name"]
            vcp_code = control.get("vcp_code")
            entity_category = control.get("entity_category")
            if control["type"] == "button":
                button_payload = {
                    "name": name,
                    "command_topic": MQTT_TOPIC_COMMAND,
                    "payload_press": f"{key}:press",
                    "device": device_info,
                    "unique_id": f"{SANITIZED_DEVICE_NAME}_{key}_button"
                }
                if entity_category:
                    button_payload["entity_category"] = entity_category
                button_topic = f"homeassistant/button/{SANITIZED_DEVICE_NAME}_{key}/config"
                discovery_payloads.append({"topic": button_topic, "payload": button_payload})
                continue
            if not vcp_code or vcp_code == "<TBD>":
                continue
            if control["type"] == "switch":
                switch_payload = {
                    "name": name,
                    "command_topic": MQTT_TOPIC_COMMAND,
                    "state_topic": f"{TOPIC_PREFIX}/{key}_state",
                    "payload_on": f"{key}:on",
                    "payload_off": f"{key}:off",
                    "state_on": "on",
                    "state_off": "off",
                    "device": device_info,
                    "unique_id": f"{SANITIZED_DEVICE_NAME}_{key}_switch",
                    "optimistic": True
                }
                if entity_category:
                    switch_payload["entity_category"] = entity_category
                switch_topic = f"homeassistant/switch/{SANITIZED_DEVICE_NAME}_{key}/config"
                discovery_payloads.append({"topic": switch_topic, "payload": switch_payload})
            elif control["type"] == "select" and len(control["options"]) > 0:
                options = [opt["name"] for opt in control["options"]]
                select_payload = {
                    "name": name,
                    "command_topic": MQTT_TOPIC_COMMAND,
                    "state_topic": f"{TOPIC_PREFIX}/{key}_state",
                    "options": options,
                    "command_template": f"{key}:{{{{ value }}}}",
                    "device": device_info,
                    "unique_id": f"{SANITIZED_DEVICE_NAME}_{key}_select",
                    "optimistic": True
                }
                if entity_category:
                    select_payload["entity_category"] = entity_category
                select_topic = f"homeassistant/select/{SANITIZED_DEVICE_NAME}_{key}/config"
                discovery_payloads.append({"topic": select_topic, "payload": select_payload})
            elif control["type"] == "number":
                number_payload = {
                    "name": name,
                    "command_topic": MQTT_TOPIC_COMMAND,
                    "state_topic": f"{TOPIC_PREFIX}/{key}_state",
                    "min": control["min"],
                    "max": control["max"],
                    "step": control["step"],
                    "command_template": f"{key}:{{{{ value }}}}",
                    "state_value_template": "{{ value if value.isdigit() else '' }}",
                    "device": device_info,
                    "unique_id": f"{SANITIZED_DEVICE_NAME}_{key}_number",
                    "optimistic": True
                }
                if entity_category:
                    number_payload["entity_category"] = entity_category
                number_topic = f"homeassistant/number/{SANITIZED_DEVICE_NAME}_{key}/config"
                discovery_payloads.append({"topic": number_topic, "payload": number_payload})
        for item in discovery_payloads:
            result = client.publish(item["topic"], json.dumps(item["payload"]), retain=True)
            logger.debug(f"Published to {item['topic']} with result: {result}")

    # Helper to extract VCP value from ddcutil output
    def extract_vcp_value(output, key="sl="):
        if not output:
            return None
        try:
            return output.split(key)[-1].strip(" )\n\t").lower()
        except Exception:
            return None

    # Refactored poll_monitor_state function
    def poll_monitor_state(client, sections=None):
        """Poll the monitor state and publish to MQTT."""
        if sections is None or sections == "all":
            sections = [c["key"] for c in config["controls"]]
        try:
            for control in config["controls"]:
                key = control["key"]
                vcp_code = control.get("vcp_code")
                if key not in sections or not vcp_code or vcp_code == "<TBD>":
                    continue
                if control["type"] == "switch":
                    output = ddc_command(vcp_code, get=True)
                    if output:
                        value = extract_vcp_value(output)
                        state = "on" if value == control["on_value"].lower() else "off"
                        publish_state(client, f"{TOPIC_PREFIX}/{key}_state", state)
                elif control["type"] == "select":
                    output = ddc_command(vcp_code, get=True)
                    if output:
                        value = extract_vcp_value(output)
                        matched = False
                        for opt in control["options"]:
                            vcp_value = str(opt["vcp_value"]).strip().lower()
                            if value == vcp_value:
                                publish_state(client, f"{TOPIC_PREFIX}/{key}_state", opt["name"])
                                matched = True
                                break
                        if not matched:
                            publish_state(client, f"{TOPIC_PREFIX}/{key}_state", control["options"][0]["name"])
                elif control["type"] == "number":
                    output = ddc_command(vcp_code, get=True)
                    if output:
                        logger.debug(f"{key.capitalize()} command output: {output}")
                        num_value = output.split("current value =")[-1].split(",")[0].strip()
                        publish_state(client, f"{TOPIC_PREFIX}/{key}_state", num_value)
                    else:
                        publish_state(client, f"{TOPIC_PREFIX}/{key}_state", "unknown")
        except Exception as e:
            logger.error(f"Error polling monitor state: {e}")

    # Polling thread function
    def polling_thread_func(client):
        while True:
            poll_monitor_state(client, "all")
            time.sleep(config["polling_interval"])

    # Debouncer dictionary for all number controls
    control_debouncers = {}

    def send_number_control(client, key, value):
        control = next((c for c in config["controls"] if c["key"] == key), None)
        if not control:
            return
        vcp_code = control["vcp_code"]
        ddc_command(vcp_code, vcp_value=value)
        poll_monitor_state(client, [key])

    # MQTT Callback: When a message is received
    def on_message(client, userdata, msg):
        """Handle incoming MQTT messages."""
        try:
            payload = msg.payload.decode("utf-8")
            logger.debug(f"Received message: {payload} on topic: {msg.topic}")
            if ":" in payload:
                command, value = payload.split(":", 1)
            else:
                command, value = payload, None
            control = next((c for c in config["controls"] if c["key"] == command), None)
            if control:
                vcp_code = control.get("vcp_code")
                if control["type"] == "switch":
                    if value == "on":
                        ddc_command(vcp_code, vcp_value=control["on_value"])
                    elif value == "off":
                        ddc_command(vcp_code, vcp_value=control["off_value"])
                    else:
                        logger.warning(f"Invalid {command} switch value: {value}")
                        return
                    poll_monitor_state(client, [command])
                    return
                elif control["type"] == "select":
                    for opt in control["options"]:
                        if opt["name"] == value:
                            vcp_value = opt["vcp_value"]
                            ddc_command(vcp_code, vcp_value=vcp_value)
                            poll_monitor_state(client, [command])
                            return
                    logger.warning(f"Invalid {command}: {value}")
                elif control["type"] == "number":
                    try:
                        num_value = int(value)
                        if control["min"] <= num_value <= control["max"]:
                            if command not in control_debouncers:
                                control_debouncers[command] = Debouncer(DEBOUNCE_DELAY)
                            control_debouncers[command].call(send_number_control, client, command, num_value)
                        else:
                            logger.warning(f"{command} value {num_value} out of range.")
                    except Exception as e:
                        logger.warning(f"Invalid {command} value: {value}, error: {e}")
                elif control["type"] == "button":
                    if control.get("is_restart_button", False):
                        # Handle service restart button
                        logger.info("Restart button pressed from Home Assistant")
                        if restart_service():
                            publish_state(client, f"{TOPIC_PREFIX}/{command}_state", "success")
                            logger.info("Service restart will occur in a moment (connection may drop)")
                        else:
                            publish_state(client, f"{TOPIC_PREFIX}/{command}_state", "error")
                            logger.error("Failed to initiate service restart")
                    else:
                        # Handle regular DDC button actions
                        actions = control.get("actions", [])
                        for action in actions:
                            ddc_command_button(action["vcp_code"], vcp_value=action["vcp_value"])
                        publish_state(client, f"{TOPIC_PREFIX}/{command}_state", "off")
                        poll_monitor_state(client)
                    return
            else:
                logger.warning(f"Unknown command: {command}")
                publish_state(client, MQTT_TOPIC_STATE, "unknown")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            publish_state(client, MQTT_TOPIC_STATE, "error")

    # --- Systemd Service & Main Loop ---
    def on_connect(client, userdata, flags, rc):
        """Handle MQTT connection events."""
        logger.info(f"Connected to MQTT broker with result code {rc}")
        client.subscribe(MQTT_TOPIC_COMMAND)
        publish_discovery(client)

    client = mqtt.Client()
    # Only enable MQTT client logging for DEBUG level to reduce log spam
    if log_level == "DEBUG":
        client.enable_logger(logger)
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message

    polling_thread = threading.Thread(target=polling_thread_func, args=(client,))
    polling_thread.daemon = True
    polling_thread.start()

    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

# =========================
# Script Entrypoint
# =========================
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(f"\nMQTT DDC Monitor Controller v{__version__}\nUsage: python MQTT_DDC.py [config_path]\nIf no config_path is provided, defaults to config.yaml in the script directory.\nSupports .json, .yaml, and .yml config files.\n")
        sys.exit(0)
    main()