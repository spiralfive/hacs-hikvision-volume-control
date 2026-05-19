"""HikVision Audio Controller for Home Assistant."""

import requests
from requests.auth import HTTPDigestAuth
import xml.etree.ElementTree as ET
import logging
from typing import Optional, Dict, Any

_LOGGER = logging.getLogger(__name__)


class HikVisionAudioController:
    """Controller for HikVision camera audio settings."""

    def __init__(self, ip: str, username: str, password: str, channel: int = 1):
        """Initialize the controller."""
        self.ip = ip
        self.username = username
        self.password = password
        self.channel = channel
        self.base_url = f"http://{ip}"
        self.auth = HTTPDigestAuth(username, password)
        self.session = requests.Session()
        
        self.headers = {
            'Accept': '*/*',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'User-Agent': 'HomeAssistant/1.0'
        }

    def get_current_settings(self) -> Optional[Dict[str, Any]]:
        """Get current audio channel settings."""
        url = f"{self.base_url}/ISAPI/System/TwoWayAudio/channels/{self.channel}"
        
        try:
            response = self.session.get(
                url,
                auth=self.auth,
                headers=self.headers,
                timeout=10,
                verify=False
            )
            
            if response.status_code == 200:
                return self._parse_settings_xml(response.text)
            else:
                _LOGGER.error(
                    f"Failed to get settings from {self.ip}: HTTP {response.status_code}"
                )
                return None
                
        except requests.exceptions.RequestException as e:
            _LOGGER.error(f"Error getting settings from {self.ip}: {e}")
            return None

    def _parse_settings_xml(self, xml_content: str) -> Optional[Dict[str, Any]]:
        """Parse XML response into dictionary."""
        try:
            root = ET.fromstring(xml_content)
            
            # Handle namespaces
            ns = {'hik': 'http://www.hikvision.com/ver20/XMLSchema'}
            
            settings = {
                'id': self._get_xml_text(root, './/id'),
                'enabled': self._get_xml_text(root, './/enabled', 'false') == 'true',
                'audio_compression': self._get_xml_text(root, './/audioCompressionType'),
                'audio_input_type': self._get_xml_text(root, './/audioInputType'),
                'speaker_volume': int(self._get_xml_text(root, './/speakerVolume', '0')),
                'microphone_volume': int(self._get_xml_text(root, './/microphoneVolume', '0')),
                'noise_reduce': self._get_xml_text(root, './/noisereduce', 'false') == 'true'
            }
            
            return settings
            
        except ET.ParseError as e:
            _LOGGER.error(f"Failed to parse XML response: {e}")
            return None

    def _get_xml_text(self, root: ET.Element, path: str, default: str = "") -> str:
        """Helper to extract text from XML element."""
        element = root.find(path)
        return element.text if element is not None else default

    def set_volumes(self, speaker_volume: Optional[int] = None, 
                   microphone_volume: Optional[int] = None,
                   enabled: bool = True) -> bool:
        """Set speaker and/or microphone volume."""
        # Get current settings first
        current = self.get_current_settings()
        
        if current:
            speaker_vol = speaker_volume if speaker_volume is not None else current.get('speaker_volume', 80)
            mic_vol = microphone_volume if microphone_volume is not None else current.get('microphone_volume', 45)
            current_enabled = current.get('enabled', True)
        else:
            speaker_vol = speaker_volume if speaker_volume is not None else 80
            mic_vol = microphone_volume if microphone_volume is not None else 45
            current_enabled = enabled

        # Validate volumes
        speaker_vol = max(0, min(100, speaker_vol))
        mic_vol = max(0, min(100, mic_vol))

        # Build XML request
        xml_request = self._build_xml_request(speaker_vol, mic_vol, current_enabled)
        
        # Send PUT request
        url = f"{self.base_url}/ISAPI/System/TwoWayAudio/channels/{self.channel}"
        
        try:
            response = self.session.put(
                url,
                auth=self.auth,
                headers=self.headers,
                data=xml_request,
                timeout=10,
                verify=False
            )
            
            if response.status_code in [200, 201]:
                _LOGGER.info(
                    f"Successfully set volumes for {self.ip}: "
                    f"Speaker={speaker_vol}, Mic={mic_vol}"
                )
                return True
            else:
                _LOGGER.error(
                    f"Failed to set volumes for {self.ip}: HTTP {response.status_code} - {response.text}"
                )
                return False
                
        except requests.exceptions.RequestException as e:
            _LOGGER.error(f"Error setting volumes for {self.ip}: {e}")
            return False

    def _build_xml_request(self, speaker_volume: int, microphone_volume: int, enabled: bool) -> str:
        """Build XML request string."""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<TwoWayAudioChannel>
    <id>{self.channel}</id>
    <enabled>{str(enabled).lower()}</enabled>
    <audioCompressionType>G.711ulaw</audioCompressionType>
    <audioInputType>MicIn</audioInputType>
    <speakerVolume>{speaker_volume}</speakerVolume>
    <microphoneVolume>{microphone_volume}</microphoneVolume>
    <noisereduce>false</noisereduce>
</TwoWayAudioChannel>"""

    def set_speaker_volume(self, volume: int) -> bool:
        """Set speaker volume only."""
        volume = max(0, min(100, volume))
        return self.set_volumes(speaker_volume=volume)

    def set_microphone_volume(self, volume: int) -> bool:
        """Set microphone volume only."""
        volume = max(0, min(100, volume))
        return self.set_volumes(microphone_volume=volume)