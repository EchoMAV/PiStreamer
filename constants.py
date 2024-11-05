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

    ### vvvv Setting the IP, PORT, or HOST will start the active GCS type (QGC or ATAK)
    GCS_IP = "gcs_ip"  # `gcs_ip_ip 192.168.1.50` is an example
    GCS_PORT = "gcs_port"  # `gcs_port 5601` is an example
    GCS_HOST = "gcs_host"  # `gcs_host 192.168.1.50:5601` is an example
    START_GCS_STREAM = "start_gcs_stream"  # uses the ip/port set by the above commands
    STOP_GCS_STREAM = "stop_gcs_stream"
    STREAMING_PROTOCOL = "streaming_protocol"  # `streaming_protocol rtp` is an example
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


class StreamingProtocolType(Enum):
    """
    The format in which the camera feed is streamed via a ffmpeg process
    """

    RTP = "rtp"  # Used for QGroundControl
    MPEG_TS = "mpegts"  # Used for Android (Tactical Assault/Team Awareness) Kit


class CommandProtocolType(Enum):
    """
    The mechanism in which commands and mavlink data are sent to the pistreamer and how
    the pistreamer sends output data back to listening processes.
    """

    SOCKET = "socket"
    ZEROMQ = "zeromq"
