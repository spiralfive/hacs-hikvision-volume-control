"""HikVision Audio Control integration for Home Assistant."""

import logging
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_IP, CONF_USERNAME, CONF_PASSWORD, CONF_NAME
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import (
    DOMAIN, 
    CONF_CHANNEL, 
    CONF_UPDATE_INTERVAL,
    DEFAULT_CHANNEL,
    SERVICE_SET_SPEAKER_VOLUME,
    SERVICE_SET_MICROPHONE_VOLUME,
    SERVICE_SET_BOTH_VOLUMES,
    SERVICE_GET_SETTINGS,
    ATTR_SPEAKER_VOLUME,
    ATTR_MICROPHONE_VOLUME,
    ATTR_CHANNEL
)
from .audio_controller import HikVisionAudioController

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_IP): cv.string,
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(CONF_CHANNEL, default=DEFAULT_CHANNEL): cv.positive_int,
                vol.Optional(CONF_NAME, default="HikVision Audio"): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

# Service schemas
SET_SPEAKER_VOLUME_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_SPEAKER_VOLUME): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
        vol.Optional(ATTR_CHANNEL): cv.positive_int,
    }
)

SET_MICROPHONE_VOLUME_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MICROPHONE_VOLUME): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
        vol.Optional(ATTR_CHANNEL): cv.positive_int,
    }
)

SET_BOTH_VOLUMES_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_SPEAKER_VOLUME): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
        vol.Required(ATTR_MICROPHONE_VOLUME): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
        vol.Optional(ATTR_CHANNEL): cv.positive_int,
    }
)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the HikVision Audio Control component."""
    hass.data.setdefault(DOMAIN, {})
    
    if DOMAIN not in config:
        return True
    
    conf = config[DOMAIN]
    
    # Create controller instance
    controller = HikVisionAudioController(
        ip=conf[CONF_IP],
        username=conf[CONF_USERNAME],
        password=conf[CONF_PASSWORD],
        channel=conf.get(CONF_CHANNEL, DEFAULT_CHANNEL)
    )
    
    hass.data[DOMAIN]["controller"] = controller
    
    # Register services
    async def handle_set_speaker_volume(call: ServiceCall):
        """Handle set speaker volume service call."""
        volume = call.data[ATTR_SPEAKER_VOLUME]
        channel = call.data.get(ATTR_CHANNEL, conf.get(CONF_CHANNEL, DEFAULT_CHANNEL))
        
        if channel != controller.channel:
            # Create temporary controller for different channel
            temp_controller = HikVisionAudioController(
                ip=conf[CONF_IP],
                username=conf[CONF_USERNAME],
                password=conf[CONF_PASSWORD],
                channel=channel
            )
            success = await hass.async_add_executor_job(
                temp_controller.set_speaker_volume, volume
            )
        else:
            success = await hass.async_add_executor_job(
                controller.set_speaker_volume, volume
            )
        
        if success:
            _LOGGER.info(f"Set speaker volume to {volume} on channel {channel}")
        else:
            _LOGGER.error(f"Failed to set speaker volume to {volume}")
    
    async def handle_set_microphone_volume(call: ServiceCall):
        """Handle set microphone volume service call."""
        volume = call.data[ATTR_MICROPHONE_VOLUME]
        channel = call.data.get(ATTR_CHANNEL, conf.get(CONF_CHANNEL, DEFAULT_CHANNEL))
        
        if channel != controller.channel:
            temp_controller = HikVisionAudioController(
                ip=conf[CONF_IP],
                username=conf[CONF_USERNAME],
                password=conf[CONF_PASSWORD],
                channel=channel
            )
            success = await hass.async_add_executor_job(
                temp_controller.set_microphone_volume, volume
            )
        else:
            success = await hass.async_add_executor_job(
                controller.set_microphone_volume, volume
            )
        
        if success:
            _LOGGER.info(f"Set microphone volume to {volume} on channel {channel}")
        else:
            _LOGGER.error(f"Failed to set microphone volume to {volume}")
    
    async def handle_set_both_volumes(call: ServiceCall):
        """Handle set both volumes service call."""
        speaker_vol = call.data[ATTR_SPEAKER_VOLUME]
        mic_vol = call.data[ATTR_MICROPHONE_VOLUME]
        channel = call.data.get(ATTR_CHANNEL, conf.get(CONF_CHANNEL, DEFAULT_CHANNEL))
        
        if channel != controller.channel:
            temp_controller = HikVisionAudioController(
                ip=conf[CONF_IP],
                username=conf[CONF_USERNAME],
                password=conf[CONF_PASSWORD],
                channel=channel
            )
            success = await hass.async_add_executor_job(
                temp_controller.set_volumes, speaker_vol, mic_vol
            )
        else:
            success = await hass.async_add_executor_job(
                controller.set_volumes, speaker_vol, mic_vol
            )
        
        if success:
            _LOGGER.info(
                f"Set volumes - Speaker: {speaker_vol}, Mic: {mic_vol} on channel {channel}"
            )
        else:
            _LOGGER.error(f"Failed to set volumes")
    
    async def handle_get_settings(call: ServiceCall):
        """Handle get settings service call."""
        settings = await hass.async_add_executor_job(controller.get_current_settings)
        if settings:
            _LOGGER.info(f"Current settings: {settings}")
            # Fire an event with the settings
            hass.bus.async_fire(f"{DOMAIN}_settings", settings)
        else:
            _LOGGER.error("Failed to get settings")
    
    # Register services
    hass.services.async_register(
        DOMAIN, SERVICE_SET_SPEAKER_VOLUME, handle_set_speaker_volume,
        schema=SET_SPEAKER_VOLUME_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SET_MICROPHONE_VOLUME, handle_set_microphone_volume,
        schema=SET_MICROPHONE_VOLUME_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SET_BOTH_VOLUMES, handle_set_both_volumes,
        schema=SET_BOTH_VOLUMES_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_GET_SETTINGS, handle_get_settings
    )
    
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up from a config entry."""
    # For future configuration flow support
    hass.data[DOMAIN][entry.entry_id] = entry.data
    
    controller = HikVisionAudioController(
        ip=entry.data[CONF_IP],
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        channel=entry.data.get(CONF_CHANNEL, DEFAULT_CHANNEL)
    )
    
    hass.data[DOMAIN]["controller"] = controller
    
    # Register services here as well
    # (same service registration as above)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    return True