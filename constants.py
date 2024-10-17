from typing import Final
from enum import Enum

FRAMERATE: Final = 30
MIN_ZOOM: Final = 1.0
DEFAULT_MAX_ZOOM = 16.0  # this has the potential to change
DEFAULT_CONFIG_PATH: Final = "477-Pi4.json"
STREAMING_FRAMESIZE: Final = "1280x720"  # 720p
STILL_FRAMESIZE: Final = "3840x2160"  # 4K
INPUT_FIFO_PATH: Final = "/tmp/pistreamer"
OUTPUT_FIFO_PATH: Final = "/tmp/pistreamer_output"
ZOOM_RATE: Final = 1.65  # zoom rate per second
MEDIA_FILES_DIRECTORY: Final = "MediaFiles"


class CommandType(Enum):
    """
    Commands pistreamer reads from FIFO from other processes.
    Some commands require a value to be passed with them and others are standalone.
    """

    STOP = "stop"
    KILL = "kill"
    BITRATE = "bitrate"  # `bitrate 2500` is an example`
    GCS_IP = "gcs_ip"  # `gcs_ip 192.168.1.50` is an example
    GCS_PORT = "gcs_port"  # `gcs_port 5601` is an example
    GCS_HOST = "gsc_host"  # `gsc_host 192.168.1.50:5601` is an example
    RECORD = "record"  # record <Optional: file_name>` is an example
    STOP_RECORDING = "stop_recording"
    START_GCS_STREAM = "start_gcs_stream"
    STOP_GCS_STREAM = "stop_gcs_stream"
    ZOOM = "zoom"  # `zoom 1.0`, `zoom in`, `zoom stop` are examples
    MAX_ZOOM = "max_zoom"  # `max_zoom 8.0` is an example
    TAKE_PHOTO = "take_photo"  # `take_photo <Optional: file_name>` is an example
    ATAK_HOST = "atak_host"  # `atak_host 192.168.1.1:5600` is an example
    STOP_ATAK = "stop_atak"
    STABILIZE = "stabilize"


class OutputCommandType(Enum):
    """
    Commands pistreamer writes to FIFO for other processes to read
    """

    ZOOM_LEVEL = "zoomLevel"  # defined at https://mavlink.io/en/messages/common.html#CAMERA_SETTINGS


class ZoomStatus(Enum):
    STOP = "stop"
    IN = "in"
    OUT = "out"
