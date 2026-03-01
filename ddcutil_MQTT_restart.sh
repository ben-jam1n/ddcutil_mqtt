#!/bin/bash
# ddcutil_MQTT_restart.sh - Helper script to restart the ddcutil_MQTT service
# This script is called by the ddcutil_MQTT_restart.service systemd unit

# Restart the main service (already running as root, no sudo needed)
systemctl restart ddcutil_MQTT.service

exit $?
