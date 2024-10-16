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


class CommandType(Enum):
    """
    Commands pistreamer reads from FIFO from other processes
    """

    STOP = "stop"
    KILL = "kill"
    BITRATE = "bitrate"
    GCS_IP = "gcs_ip"
    GCS_PORT = "gcs_port"
    GCS_HOST = (
        "gsc_host"  # use this if you want to change ip address and port simultaneously
    )
    RECORD = "record"
    STOP_RECORDING = "stop_recording"
    START_GCS_STREAM = "start_gcs_stream"
    STOP_GCS_STREAM = "stop_gcs_stream"
    ZOOM = "zoom"
    MAX_ZOOM = "max_zoom"
    TAKE_PHOTO = "take_photo"
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
