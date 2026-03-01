# Details for setting up and configuring ddcutil MQTT

## **About ddcutil**

ddcutil is a command-line utility for querying and changing monitor settings using the DDC/CI protocol. It allows you to control features such as brightness, contrast, input source, and more, directly from your computer.

- **Official Documentation:** [https://www.ddcutil.com/](https://www.ddcutil.com/)
- **GitHub Repository:** [https://github.com/rockowitz/ddcutil](https://github.com/rockowitz/ddcutil)

### **Basic Usage**

1. **List Connected Monitors:**
   ```bash
   ddcutil detect
   ```
   This command shows all monitors detected by ddcutil.

2. **List Supported Controls (VCP Codes):**
   ```bash
   ddcutil capabilities
   ```
   This displays the VCP (Virtual Control Panel) codes your monitor supports, such as brightness (0x10), input source (0x60), etc.

3. **Get Current Value of a Control:**
   ```bash
   ddcutil getvcp 10
   ```
   Replace `10` with the VCP code you want to query (e.g., `10` for brightness).

4. **Set a Value:**
   ```bash
   ddcutil setvcp 10 50
   ```
   This sets the brightness (VCP code 10) to 50. Replace `10` and `50` as needed.

For more advanced usage and troubleshooting, refer to the [ddcutil documentation](https://www.ddcutil.com/documentation/).

---

## **New Features & Updates**

- **Home Assistant Button Entities:** The script now supports MQTT button entities via discovery. Actions like "Favorite" and "Return to Single Display" appear as true buttons in Home Assistant, not switches.
- **YAML Config for Buttons:** Button actions are defined in the YAML config with `type: button` and an `actions` list. See the example config for details.
- **Improved Select Handling:** Select controls always publish a valid string state, never `False`, ensuring correct Home Assistant operation.
- **Momentary Button Behavior:** Button entities in Home Assistant immediately return to the "off" state after being pressed, providing a responsive UI.
- **PbP/PiP & Multi-Input Support:** The config and script support advanced monitor modes, including PbP/PiP, and can be extended for tertiary input selection as you map more VCP codes.

---

## **YAML Configuration File**

The script now uses `config.yaml` as the default configuration file.

- **YAML Example:** See `example_config.yaml` for a commented example.
- **YAML Syntax:** Indentation matters. Use spaces, not tabs.
- **Shared Options:** Use YAML anchors (&) and aliases (*) to avoid duplication.
- **PyYAML Required:** Install with `pip install pyyaml` if using YAML configs.

See `example_config.yaml` for a full sample configuration with known VCP codes and options from a Dell U4323QE

### Required Configuration Options

```yaml
log_level: INFO
mqtt_broker: YOUR_MQTT_BROKER_IP
mqtt_port: 1883
mqtt_username: your_mqtt_username
mqtt_password: your_mqtt_password
device_name: Monitor_Name
polling_interval: 30
debounce_delay: 0.5
```
### Monitor Specific Options

```yaml
input_source_options: &input_source_options
  - name: USB C
    vcp_value: "0x1b"
  - name: DP 1
    vcp_value: "0x13"

controls:
  - name: Primary Input Source
    key: primary_input
    type: select
    vcp_code: "60"
    options: *input_source_options
  - name: Picture-by-Picture
    key: pbp
    type: switch
    vcp_code: E9
    on_value: "0x24"
    off_value: "0x00"
  - name: Monitor Brightness
    key: brightness
    type: number
    vcp_code: "10"
    min: 0
    max: 100
    step: 1
  - name: Monitor Volume
    key: volume
    type: number
    vcp_code: "62"
    min: 0
    max: 100
    step: 1
  # PbP/PiP Mode selector
  - name: PbP/PiP Mode
    key: pbp_pip_mode
    type: select
    vcp_code: E9
    options:
      - name: Off
        vcp_value: "0x00"
      - name: PbP Left/Right
        vcp_value: "0x24"
      - name: PbP Top/Bottom
        vcp_value: "0x21"
      - name: PiP Top-Left
        vcp_value: "0x31"
      - name: PiP Top-Right
        vcp_value: "0x32"
      - name: PiP Bottom-Left
        vcp_value: "0x33"
      - name: PiP Bottom-Right
        vcp_value: "0x34"
      # Add more as you map them


  # Custom 'Preset' button - Can set multiple VCP codes in sequence to restore a specific setup
  - name: Custom Preset 1
    key: main_preset1
    type: button  # Home Assistant button entity
    actions:
      - vcp_code: 60  # Primary input VCP code
        vcp_value: "0x1b"         # Example: USB-C
      - vcp_code: E9              # PbP/PiP Mode VCP code 
        vcp_value: "0x00"         # Example: Return to single display (no PbP/PiP)
    entity_category: diagnostic   # Optional: config, diagnostic, or omit for none
```

---

## **Integration with Home Assistant**
The script supports MQTT discovery, allowing Home Assistant to automatically detect and configure entities for monitor control.

### **Discovery Entities**
- **Switches**: For toggling inputs and enabling/disabling PBP.
- **Selects**: For choosing input sources or other options.
- **Numbers**: For adjusting brightness and volume.
- **Buttons**: For actions like "Favorite" and "Return to Single Display". These appear as true button entities in Home Assistant and trigger the defined actions when pressed.

---