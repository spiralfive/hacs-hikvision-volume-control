"""HikVision Audio Control integration for Home Assistant."""

import logging
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.core import HomeAssistant, ServiceCall

from .audio_controller import HikVisionAudioController

_LOGGER = logging.getLogger(__name__)

DOMAIN = "hikvision_audio"

# Configuration keys
CONF_IP = "ip"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_CHANNEL = "channel"

# Configuration schema
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_IP): cv.string,
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(CONF_CHANNEL, default=1): cv.positive_int,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

# Service schemas
SET_SPEAKER_VOLUME_SCHEMA = vol.Schema(
    {
        vol.Required("volume"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
    }
)

SET_MICROPHONE_VOLUME_SCHEMA = vol.Schema(
    {
        vol.Required("volume"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
    }
)

SET_BOTH_VOLUMES_SCHEMA = vol.Schema(
    {
        vol.Required("speaker_volume"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
        vol.Required("microphone_volume"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
    }
)


def setup(hass: HomeAssistant, config):
    """Set up the HikVision Audio Control component."""
    
    if DOMAIN not in config:
        return True
    
    conf = config[DOMAIN]
    
    # Create controller instance
    controller = HikVisionAudioController(
        ip=conf[CONF_IP],
        username=conf[CONF_USERNAME],
        password=conf[CONF_PASSWORD],
        channel=conf.get(CONF_CHANNEL, 1)
    )
    
    # Store controller in hass data
    hass.data[DOMAIN] = controller
    
    def set_speaker_volume(call: ServiceCall):
        """Set speaker volume."""
        volume = call.data["volume"]
        if controller.set_speaker_volume(volume):
            _LOGGER.info(f"Speaker volume set to {volume}")
        else:
            _LOGGER.error(f"Failed to set speaker volume to {volume}")
    
    def set_microphone_volume(call: ServiceCall):
        """Set microphone volume."""
        volume = call.data["volume"]
        if controller.set_microphone_volume(volume):
            _LOGGER.info(f"Microphone volume set to {volume}")
        else:
            _LOGGER.error(f"Failed to set microphone volume to {volume}")
    
    def set_both_volumes(call: ServiceCall):
        """Set both volumes."""
        speaker_vol = call.data["speaker_volume"]
        mic_vol = call.data["microphone_volume"]
        if controller.set_volumes(speaker_volume=speaker_vol, microphone_volume=mic_vol):
            _LOGGER.info(f"Volumes set - Speaker: {speaker_vol}, Mic: {mic_vol}")
        else:
            _LOGGER.error(f"Failed to set volumes")
    
    # Register services
    hass.services.register(DOMAIN, "set_speaker_volume", set_speaker_volume, schema=SET_SPEAKER_VOLUME_SCHEMA)
    hass.services.register(DOMAIN, "set_microphone_volume", set_microphone_volume, schema=SET_MICROPHONE_VOLUME_SCHEMA)
    hass.services.register(DOMAIN, "set_both_volumes", set_both_volumes, schema=SET_BOTH_VOLUMES_SCHEMA)
    
    _LOGGER.info("HikVision Audio Control integration loaded successfully")
    _LOGGER.info(f"Configured for camera at {conf[CONF_IP]} on channel {conf.get(CONF_CHANNEL, 1)}")
    
    return True