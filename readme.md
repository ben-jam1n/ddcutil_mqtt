# ddcutil MQTT
V0.2

**Remotely control a display/monitor (input selection, KVM settings, volume, brightness, etc.) from Home Assistant (or other automation systems) via ddcutil and MQTT with auto discovery.**

Control a ddcutil-compatible monitor/display via MQTT. 
Designed for use with Home Assistant and tested with a Dell U4323QE

Especially useful for monitors with built-in KVM functionality, allowing to change inputs, PIP/PbP modes, etc. through Home Assistant (or another automation platform).

My primary usage is an Aqara Zigbee pushbutton switch next to my keyboard that allows for quick input toggling, enabling or disabling PiP/PbP, and swapping the USB connections between inputs. 

## Features
Remotely control monitor settings over the network via MQTT using ddcutil. 

Available Controls:
* Input Source
* Sub Input Source*
* Picture in Picture/Picture By Picture Modes*
* Brightness
* Volume
* USB Uplink*
* Input Preset
* Service Restart (diagnostic button)

 *Known to work on Dell monitor with built-in KVM features

---
## About ddcutil

ddcutil is a command-line utility for querying and changing monitor settings using the DDC/CI protocol. It allows you to control features such as brightness, contrast, input source, and more, directly from your computer.

- **Official Documentation:** [https://www.ddcutil.com/](https://www.ddcutil.com/)
- **GitHub Repository:** [https://github.com/rockowitz/ddcutil](https://github.com/rockowitz/ddcutil)

## Tested Environment & Notes

- This script has been created and tested only on a Raspberry Pi connected to the monitor via HDMI.
- For Raspberry Pi, you must enable I2C in system settings (use `raspi-config` > Interface Options > I2C).
- Created and tested only on a Dell U4323QE monitor.

---

## Installation & Setup
This script must run on a computer connected to the monitor via a display connection (HDMI tested; DisplayPort should also work but is unverified) that can reach your MQTT broker.

The script can be installed as a systemd service on low-power devices like a Raspberry Pi Zero W for wireless network control. 

---

### Semi-Automated Installation
The `install.sh` script will clone the repository to a local directory, install dependencies, and set up the script as a systemd service.

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/ben-jam1n/ddcutil_mqtt/main/install.sh)"
```


After running the script, you'll need to:
1. Update `config.yaml` with your specific monitor and MQTT broker settings
* See `Configuration_help.md` for more information about configuration options. 
2. Restart the systemd service for changes to take effect

---

### Manual Installation Steps

1. Install System Dependencies
```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv ddcutil git
```

2. Clone the Project Files
```bash
git clone https://github.com/ben-jam1n/ddcutil_mqtt.git /opt/ddcutil_MQTT
cd /opt/ddcutil_MQTT
```

3. Create and Activate Python Virtual Environment
```bash
python3 -m venv /opt/ddcutil_MQTT/venv
source /opt/ddcutil_MQTT/venv/bin/activate
```

4. Install Python Dependencies
```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
deactivate
```

5. Configure the Script
Edit `config.yaml` to match your monitor and MQTT broker setup. See the included example `example_config.yaml` for details.

---

### Running the Script

**Manual Test**
```bash
cd /opt/ddcutil_MQTT
source venv/bin/activate
python3 ddcutil_MQTT.py
```

---

**Setting Up as a Systemd Service**

1. Create the Service File
Run the following command to create `/etc/systemd/system/ddcutil_MQTT.service`:
```bash
sudo tee /etc/systemd/system/ddcutil_MQTT.service > /dev/null <<EOF
[Unit]
Description=DDCutil MQTT Monitor Control
After=network.target

[Service]
Type=simple
ExecStart=/opt/ddcutil_MQTT/venv/bin/python /opt/ddcutil_MQTT/ddcutil_MQTT.py /opt/ddcutil_MQTT/config.yaml
WorkingDirectory=/opt/ddcutil_MQTT
Restart=always
RestartSec=10
User=root
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

2. Enable and Start the Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable ddcutil_MQTT.service
sudo systemctl start ddcutil_MQTT.service
```

3. Check Service Status
```bash
sudo systemctl status ddcutil_MQTT.service
sudo journalctl -u ddcutil_MQTT.service -f  # Follow logs
```

---

## Updating or Changing the Config
- To add new controls or change settings: Edit `config.yaml` and restart the service with `sudo systemctl restart ddcutil_MQTT.service`
- To update the code: Replace the `.py` files and restart the service
- To view the current configuration: `cat /opt/ddcutil_MQTT/config.yaml`

---
## Home Assistant Integration
- The script uses MQTT Discovery, so Home Assistant will automatically detect and add your monitor controls as entities.
- You can customize which controls appear as configuration or diagnostic items using the `entity_category` field in your config.

---

## Troubleshooting
- **Configuration:** See `Configuration_help.md` for more information about finding controls available for your monitor
- **Monitor not responding:** Ensure ddcutil works from the command line (`ddcutil capabilities`) and verify your monitor supports DDC/CI on the current input.
- **MQTT connection errors:** Double-check your broker address, credentials, and network connectivity in `config.yaml`.
- **Permissions:** If you get I2C permission errors, ensure the service user (root by default) has access. For non-root users, you may need to add them to the `i2c` group: `sudo usermod -aG i2c $USER`
- **Service won't start:** Check the logs with:
  ```bash
  sudo systemctl status ddcutil_MQTT.service
  sudo journalctl -u ddcutil_MQTT.service -f
  ```
- **Logs:** View real-time logs with `sudo journalctl -u ddcutil_MQTT.service -f`
- **Manual testing:** Run the script manually with increased log level (set `log_level` to `DEBUG` in `config.yaml`):
  ```bash
  cd /opt/ddcutil_MQTT
  python3 ddcutil_MQTT.py config.yaml
  ```
- **Multiple monitors:** You can use the script with different config files for different monitors/devices by specifying the config path as an argument.

---

## Credits

ddcutil: 
* https://www.ddcutil.com/
* https://github.com/rockowitz/ddcutil

For reference of the DDC/VPC configurations available, and interpreting outputs, many thanks to the work done by others: 
https://gist.github.com/lainosantos/06d233f6c586305cde67489c2e4a764d
https://github.com/rockowitz/ddcutil/issues/268
https://github.com/ScriptGod1337/kvm/blob/d81776dbbd821176195b0b2afe866ee814cdf234/src/kvmutil/kvmutil.py#L7
https://github.com/moimart/ddc-mqtt/
https://github.com/Penpal1278/ddcutil2MQTT/blob/main/ddcutil2MQTT.py