from typing import Final
from enum import Enum

FRAMERATE: Final = 30
MIN_ZOOM: Final = 1.0
DEFAULT_MAX_ZOOM = 16.0  # this has the potential to change
DEFAULT_CONFIG_PATH: Final = "477-Pi4.json"
STREAMING_FRAMESIZE: Final = "1280x720"  # 720p
STILL_FRAMESIZE: Final = "4056x3040"  # 12 MP
ZOOM_RATE: Final = 1.65  # zoom rate per second
MEDIA_FILES_DIRECTORY: Final = "MediaFiles"
CMD_SOCKET_HOST = "0.0.0.0"
OUTPUT_SOCKET_HOST = "localhost"
CMD_SOCKET_PORT = 54321
OUTPUT_SOCKET_PORT = 54322
MAX_SOCKET_CONNECTIONS = 3
INIT_BBOX_COLOR = (128, 128, 128)  # Grey color in BGR
ACTIVE_BBOX_COLOR = (0, 0, 255)  # Red color in BGR


class CommandType(Enum):
    """
    Commands pistreamer reads from a defined socket which is sent data by other processes.
    Some commands require a value to be passed with them and others are standalone.
    """

    ### vvvv Setting the IP, PORT, or HOST will start it and set it to preferred and stop the ATAK stream
    QGC_IP = "qgc_ip"  # `qgc_ip 192.168.1.50` is an example
    QGC_PORT = "qgc_port"  # `qgc_port 5601` is an example
    QGC_HOST = "gsc_host"  # `gsc_host 192.168.1.50:5601` is an example
    START_QGC_STREAM = "start_qgc_stream"  # uses the ip/port set by the above commands
    STOP_QGC_STREAM = "stop_qgc_stream"
    ### ^^^^
    ### vvvv Setting the ATAK host will start it and set it to preferred and stop the QGC stream
    ATAK_HOST = "atak_host"  # `atak_host 224.1.1.1:5002` is an example
    START_ATAK_STREAM = "start_atak_stream"  # uses the ip/port set by the host
    STOP_ATAK_STREAM = "stop_atak_stream"
    ### ^^^^
    BITRATE = "bitrate"  # `bitrate 2500` is an example`
    RECORD = "record"  # record <Optional: file_name>` is an example
    STOP_RECORDING = "stop_recording"
    ZOOM = "zoom"  # `zoom 1.0`, `zoom in`, `zoom stop` are examples
    MAX_ZOOM = "max_zoom"  # `max_zoom 8.0` is an example
    TAKE_PHOTO = "take_photo"  # `take_photo <Optional: file_name>` is an example
    STABILIZE = "stabilize"
    INIT_TRACKING_POI = "init_tracking_poi"  # `init_tracking_poi x,y` is an example
    STOP_TRACKING = "stop_tracking"


class OutputCommandType(Enum):
    """
    Commands pistreamer writes to an output socket for other processes to read
    """

    ZOOM_LEVEL = "zoomLevel"  # defined at https://mavlink.io/en/messages/common.html#CAMERA_SETTINGS


class ZoomStatus(Enum):
    STOP = "stop"
    IN = "in"
    OUT = "out"


class TrackStatus(Enum):
    STOP = "stop"
    ACTIVE = "active"
    INIT = "init"
    NONE = "none"
