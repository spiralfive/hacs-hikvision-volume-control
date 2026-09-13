"""Constants for HikVision Audio Control."""

DOMAIN = "hikvision_audio"
DEFAULT_NAME = "HikVision Audio Control"

# Configuration keys
CONF_IP = "ip"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_CHANNEL = "channel"
CONF_NAME = "name"
CONF_UPDATE_INTERVAL = "update_interval"

# Services
SERVICE_SET_SPEAKER_VOLUME = "set_speaker_volume"
SERVICE_SET_MICROPHONE_VOLUME = "set_microphone_volume"
SERVICE_SET_BOTH_VOLUMES = "set_both_volumes"
SERVICE_GET_SETTINGS = "get_settings"

# Attributes
ATTR_SPEAKER_VOLUME = "speaker_volume"
ATTR_MICROPHONE_VOLUME = "microphone_volume"
ATTR_ENABLED = "enabled"
ATTR_CHANNEL = "channel"

# Defaults
DEFAULT_CHANNEL = 1
DEFAULT_UPDATE_INTERVAL = 30