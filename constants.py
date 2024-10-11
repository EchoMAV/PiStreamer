from typing import Final
from enum import Enum

FRAMERATE: Final = 30
MIN_ZOOM: Final = 1.0
MAX_ZOOM: Final = 8.0
DEFAULT_CONFIG_PATH: Final = "477-Pi4.json"
STREAMING_FRAMESIZE: Final = "1280x720"  # 720p
STILL_FRAMESIZE: Final = "3840x2160"  # 4K
INPUT_FIFO_PATH: Final = "/tmp/pistreamer"
OUTPUT_FIFO_PATH: Final = "/tmp/pistreamer_output"


class CommandType(Enum):
    STOP = "stop"
    KILL = "kill"
    BITRATE = "bitrate"
    PORT = "port"
    IP_ADDRESS = "ip_address"
    RECORD = "record"
    STOP_RECORDING = "stop_recording"
    START_GCS_STREAM = "start_gcs_stream"
    STOP_GCS_STREAM = "stop_gcs_stream"
    ZOOM = "zoom"
    TAKE_PHOTO = "take_photo"
    ATAK_HOST = "atak_host"  # `atak_host 192.168.1.1:5600` is an example
    STOP_ATAK = "stop_atak"
    STABILIZE = "stabilize"


class CommandStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
