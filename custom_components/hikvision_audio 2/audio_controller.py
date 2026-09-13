"""HikVision Audio Controller for Home Assistant."""

import requests
from requests.auth import HTTPDigestAuth
import xml.etree.ElementTree as ET
import logging

_LOGGER = logging.getLogger(__name__)


class HikVisionAudioController:
    """Controller for HikVision camera audio settings."""

    def __init__(self, ip, username, password, channel=1):
        """Initialize the controller."""
        self.ip = ip
        self.username = username
        self.password = password
        self.channel = channel
        self.base_url = f"http://{ip}"
        self.auth = HTTPDigestAuth(username, password)
        
        self.headers = {
            'Accept': '*/*',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'User-Agent': 'HomeAssistant/1.0'
        }

    def set_volumes(self, speaker_volume=None, microphone_volume=None):
        """Set speaker and/or microphone volume."""
        # First get current settings
        current = self.get_current_settings()
        
        if current:
            speaker_vol = speaker_volume if speaker_volume is not None else current.get('speaker_volume', 80)
            mic_vol = microphone_volume if microphone_volume is not None else current.get('microphone_volume', 45)
        else:
            speaker_vol = speaker_volume if speaker_volume is not None else 80
            mic_vol = microphone_volume if microphone_volume is not None else 45

        # Validate volumes
        speaker_vol = max(0, min(100, speaker_vol))
        mic_vol = max(0, min(100, mic_vol))

        # Build XML request
        xml_request = f'''<?xml version="1.0" encoding="UTF-8"?>
<TwoWayAudioChannel>
    <id>{self.channel}</id>
    <enabled>true</enabled>
    <audioCompressionType>G.711ulaw</audioCompressionType>
    <audioInputType>MicIn</audioInputType>
    <speakerVolume>{speaker_vol}</speakerVolume>
    <microphoneVolume>{mic_vol}</microphoneVolume>
    <noisereduce>false</noisereduce>
</TwoWayAudioChannel>'''
        
        # Send PUT request
        url = f"{self.base_url}/ISAPI/System/TwoWayAudio/channels/{self.channel}"
        
        try:
            response = requests.put(
                url,
                auth=self.auth,
                headers=self.headers,
                data=xml_request,
                timeout=10,
                verify=False
            )
            
            if response.status_code in [200, 201]:
                _LOGGER.info(f"Successfully set volumes for {self.ip}: Speaker={speaker_vol}, Mic={mic_vol}")
                return True
            else:
                _LOGGER.error(f"Failed to set volumes: HTTP {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            _LOGGER.error(f"Error setting volumes: {e}")
            return False

    def set_speaker_volume(self, volume):
        """Set only speaker volume."""
        return self.set_volumes(speaker_volume=volume)

    def set_microphone_volume(self, volume):
        """Set only microphone volume."""
        return self.set_volumes(microphone_volume=volume)

    def get_current_settings(self):
        """Get current audio channel settings."""
        url = f"{self.base_url}/ISAPI/System/TwoWayAudio/channels/{self.channel}"
        
        try:
            response = requests.get(
                url,
                auth=self.auth,
                headers=self.headers,
                timeout=10,
                verify=False
            )
            
            if response.status_code == 200:
                try:
                    root = ET.fromstring(response.text)
                    settings = {
                        'speaker_volume': int(root.find('.//speakerVolume').text) if root.find('.//speakerVolume') is not None else 80,
                        'microphone_volume': int(root.find('.//microphoneVolume').text) if root.find('.//microphoneVolume') is not None else 45,
                    }
                    return settings
                except:
                    return None
            else:
                return None
                
        except requests.exceptions.RequestException as e:
            _LOGGER.error(f"Error getting settings: {e}")
            return None