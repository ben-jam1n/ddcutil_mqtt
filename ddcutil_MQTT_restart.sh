#!/bin/bash
# ddcutil_MQTT_restart.sh - Helper script to restart the ddcutil_MQTT service
# This script is called by the ddcutil_MQTT_restart.service systemd unit

INSTALL_DIR="/opt/ddcutil_MQTT"

# Restart the main service
sudo systemctl restart ddcutil_MQTT.service

exit $?
