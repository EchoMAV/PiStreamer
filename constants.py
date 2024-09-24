from typing import Final
from enum import Enum

FRAMERATE: Final = 30
MIN_ZOOM: Final = 1.0
MAX_ZOOM: Final = 8.0
DEFAULT_CONFIG_PATH: Final = "477-Pi4.json"
STABILIZATION_FRAMESIZE: Final = "640x360"  # Pretty low
STREAMING_FRAMESIZE: Final = "1280x720"  # 720p
STILL_FRAMESIZE: Final = "3840x2160"  # 4K


class CommandType(Enum):
    STOP = "stop"
    KILL = "kill"
    BITRATE = "bitrate"
    PORT = "port"
    IP_ADDRESS = "ip_address"
    RECORD = "record"
    STOP_RECORDING = "stop_recording"
    ZOOM = "zoom"
    TAKE_PHOTO = "take_photo"
    ATAK_HOST = "atak_host"  # `atak_host 192.168.1.1:5600` is an example
    STOP_ATAK = "atak_host"


class CommandStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
