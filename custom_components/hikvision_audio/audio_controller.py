"""HikVision Audio & PTZ Controller for Home Assistant."""

import requests
from requests.auth import HTTPDigestAuth
import xml.etree.ElementTree as ET
import logging

_LOGGER = logging.getLogger(__name__)


class HikVisionAudioController:
    """Controller for HikVision camera audio and PTZ settings."""

    def __init__(self, ip, username, password, channel=1):
        """Initialize the controller."""
        self.ip = ip
        self.username = username
        self.password = password
        self.channel = channel
        self.base_url = f"http://{ip}"
        self.auth = HTTPDigestAuth(username, password)

        self.headers = {
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "HomeAssistant/1.0",
        }

    # ------------------------------------------------------------------ #
    # Audio volume methods
    # ------------------------------------------------------------------ #
    def set_volumes(self, speaker_volume=None, microphone_volume=None):
        """Set speaker and/or microphone volume."""
        current = self.get_current_settings()

        if current:
            speaker_vol = (
                speaker_volume
                if speaker_volume is not None
                else current.get("speaker_volume", 80)
            )
            mic_vol = (
                microphone_volume
                if microphone_volume is not None
                else current.get("microphone_volume", 45)
            )
        else:
            speaker_vol = speaker_volume if speaker_volume is not None else 80
            mic_vol = microphone_volume if microphone_volume is not None else 45

        speaker_vol = max(0, min(100, speaker_vol))
        mic_vol = max(0, min(100, mic_vol))

        xml_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<TwoWayAudioChannel>
    <id>{self.channel}</id>
    <enabled>true</enabled>
    <audioCompressionType>G.711ulaw</audioCompressionType>
    <audioInputType>MicIn</audioInputType>
    <speakerVolume>{speaker_vol}</speakerVolume>
    <microphoneVolume>{mic_vol}</microphoneVolume>
    <noisereduce>false</noisereduce>
</TwoWayAudioChannel>"""

        url = f"{self.base_url}/ISAPI/System/TwoWayAudio/channels/{self.channel}"

        try:
            response = requests.put(
                url,
                auth=self.auth,
                headers=self.headers,
                data=xml_request,
                timeout=10,
                verify=False,
            )

            if response.status_code in [200, 201]:
                _LOGGER.info(
                    f"Successfully set volumes for {self.ip}: "
                    f"Speaker={speaker_vol}, Mic={mic_vol}"
                )
                return True
            else:
                _LOGGER.error(
                    f"Failed to set volumes: HTTP {response.status_code} - {response.text}"
                )
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
                verify=False,
            )

            if response.status_code == 200:
                try:
                    root = ET.fromstring(response.text)
                    speaker_elem = root.find(".//speakerVolume")
                    mic_elem = root.find(".//microphoneVolume")
                    settings = {
                        "speaker_volume": int(speaker_elem.text) if speaker_elem is not None else 80,
                        "microphone_volume": int(mic_elem.text) if mic_elem is not None else 45,
                    }
                    return settings
                except Exception as e:
                    _LOGGER.error(f"Failed to parse audio settings XML: {e}")
                    return None
            else:
                return None

        except requests.exceptions.RequestException as e:
            _LOGGER.error(f"Error getting settings: {e}")
            return None

    # ------------------------------------------------------------------ #
    # Smart Tracking (PTZ) methods
    # ------------------------------------------------------------------ #
    def _smart_tracking_urls(self):
        """Return candidate ISAPI endpoints for Smart Tracking."""
        return [
            f"{self.base_url}/ISAPI/PTZCtrl/channels/{self.channel}/smarttracking",
            f"{self.base_url}/ISAPI/Smart/PTZCtrl/channels/{self.channel}/smarttracking",
            f"{self.base_url}/ISAPI/PTZCtrl/channels/{self.channel}/smartTracking",
        ]

    def get_smart_tracking_config(self):
        """Get current Smart Tracking configuration."""
        for url in self._smart_tracking_urls():
            try:
                response = requests.get(
                    url,
                    auth=self.auth,
                    headers=self.headers,
                    timeout=10,
                    verify=False,
                )

                if response.status_code == 200:
                    try:
                        root = ET.fromstring(response.text)
                        enabled_elem = root.find(".//enabled")
                        duration_elem = root.find(".//duration")
                        settings = {
                            "enabled": (
                                enabled_elem.text.lower() == "true"
                                if enabled_elem is not None
                                else False
                            ),
                            "duration": (
                                int(duration_elem.text)
                                if duration_elem is not None
                                else 300
                            ),
                            "endpoint": url,
                        }
                        return settings
                    except Exception as e:
                        _LOGGER.error(f"Failed to parse Smart Tracking XML: {e}")
                        continue
                elif response.status_code == 404:
                    continue
                else:
                    _LOGGER.debug(
                        f"Smart Tracking GET {url} returned {response.status_code}"
                    )
                    continue

            except requests.exceptions.RequestException as e:
                _LOGGER.debug(f"Error contacting {url}: {e}")
                continue

        _LOGGER.error("Could not find a working Smart Tracking endpoint")
        return None

    def set_smart_tracking(self, enabled, duration=300):
        """Enable or disable Smart Tracking."""
        duration = max(0, min(300, duration))
        xml_payload = f"""<?xml version="1.0" encoding="UTF-8"?>
<SmartTrack>
    <enabled>{str(enabled).lower()}</enabled>
    <duration>{duration}</duration>
</SmartTrack>"""

        for url in self._smart_tracking_urls():
            try:
                response = requests.put(
                    url,
                    auth=self.auth,
                    headers=self.headers,
                    data=xml_payload,
                    timeout=10,
                    verify=False,
                )

                if response.status_code in [200, 201]:
                    _LOGGER.info(
                        f"Smart Tracking {'enabled' if enabled else 'disabled'} "
                        f"(duration: {duration}s) via {url}"
                    )
                    return True
                elif response.status_code == 404:
                    continue
                else:
                    _LOGGER.debug(
                        f"Smart Tracking PUT {url} returned {response.status_code}"
                    )
                    continue

            except requests.exceptions.RequestException as e:
                _LOGGER.debug(f"Error contacting {url}: {e}")
                continue

        _LOGGER.error("Failed to set Smart Tracking on any known endpoint")
        return False