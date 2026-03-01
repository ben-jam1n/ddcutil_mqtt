#!/bin/bash
# install.sh - Install ddcutil MQTT Utility
# https://github.com/ben-jam1n/ddcutil_mqtt
# This script automates setup on Linux systems (Raspberry Pi, Debian, Ubuntu, etc.)
# Requires: sudo access

set -e

INSTALL_DIR="/opt/ddcutil_MQTT"
SERVICE_FILE="/etc/systemd/system/ddcutil_MQTT.service"
GITHUB_URL="https://github.com/ben-jam1n/ddcutil_mqtt.git"

# 1. Install system dependencies
echo "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y python3 python3-venv ddcutil git

# 2. Create install directory
echo "Creating installation directory..."
sudo mkdir -p "$INSTALL_DIR"
sudo chown $USER:$USER "$INSTALL_DIR"

# 3. Clone repository
echo "Cloning repository..."
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "Repository already exists, pulling latest changes..."
    cd "$INSTALL_DIR" && git pull
else
    git clone "$GITHUB_URL" "$INSTALL_DIR"
fi

# 4. Create and activate Python virtual environment
echo "Creating Python virtual environment..."
python3 -m venv "$INSTALL_DIR/venv"
source "$INSTALL_DIR/venv/bin/activate"

# 5. Install required Python packages in venv
echo "Installing Python dependencies..."
pip install --upgrade pip setuptools wheel
pip install -r "$INSTALL_DIR/requirements.txt"
deactivate

# 5. Set script permissions
echo "Setting permissions..."
chmod +x "$INSTALL_DIR/ddcutil_MQTT.py"

# 6. Create systemd service file
echo "Creating systemd service..."
sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=DDCutil MQTT https://github.com/ben-jam1n/ddcutil_mqtt
After=network.target

[Service]
Type=simple
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/ddcutil_MQTT.py $INSTALL_DIR/config.yaml
WorkingDirectory=$INSTALL_DIR
Restart=always
RestartSec=10
User=root
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 7. Create restart service file
echo "Creating systemd restart service..."
sudo tee /etc/systemd/system/ddcutil_MQTT_restart.service > /dev/null <<EOF
[Unit]
Description=DDCutil MQTT Service Restart Handler https://github.com/ben-jam1n/ddcutil_mqtt
After=ddcutil_MQTT.service
PartOf=ddcutil_MQTT.service

[Service]
Type=oneshot
ExecStart=$INSTALL_DIR/ddcutil_MQTT_restart.sh
User=root
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 8. Enable and start the service
echo "Enabling and starting systemd services..."
sudo systemctl daemon-reload
sudo systemctl enable ddcutil_MQTT.service
sudo systemctl enable ddcutil_MQTT_restart.service

# 9. Final instructions
echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit the configuration file:"
echo "   sudo nano $INSTALL_DIR/config.yaml"
echo "2. Update MQTT broker settings and monitor controls"
echo "3. Start the service:"
echo "   sudo systemctl start ddcutil_MQTT.service"
echo "4. Check service status:"
echo "   sudo systemctl status ddcutil_MQTT.service"
echo "5. View logs in real-time:"
echo "   sudo journalctl -u ddcutil_MQTT.service -f"
echo ""
echo "For more information, see README.md on https://github.com/ben-jam1n/ddcutil_mqtt"
echo "=========================================="
