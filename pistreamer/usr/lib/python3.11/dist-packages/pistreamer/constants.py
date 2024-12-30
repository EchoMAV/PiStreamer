#!/usr/bin/env python3
from typing import Final, Tuple
from enum import Enum
from dataclasses import dataclass

FRAMERATE: Final = 30
MIN_ZOOM: Final = 1.0
DEFAULT_MAX_ZOOM = 16.0  # this has the potential to change
DEFAULT_CONFIG_PATH: Final = "477-Pi4.json"
STREAMING_FRAMESIZE: Final = "1280x720"  # 720p
QR_CODE_FRAMESIZE: Final = "1920x1080"  # 1080p
STILL_FRAMESIZE: Final = "4056x3040"  # 12 MP
ZOOM_RATE: Final = 1.65  # zoom rate per second
CMD_SOCKET_HOST = "0.0.0.0"
OUTPUT_SOCKET_HOST = "localhost"
CMD_SOCKET_PORT = 54321
OUTPUT_SOCKET_PORT = 54322
MAX_SOCKET_CONNECTIONS = 3
INIT_BBOX_COLOR = (128, 128, 128)  # Grey color in BGR
ACTIVE_BBOX_COLOR = (0, 0, 255)  # Red color in BGR
NAMESPACE_URI = "http://pix4d.com/camera/1.0/"
NAMESPACE_PREFIX = "Camera"
CONFIGURED_MICROHARD_IP_PREFIX = "172.20.2"
MONARK_ID_FILE_NAME: Final = "/usr/local/echopilot/monarkProxy/monark_id.txt"
SD_CARD_LOCATION: Final = "/dev/mmcblk1p1"
SD_CARD_MOUNTED_LOCATION: Final = "/mnt/external_sd"
MEDIA_FILES_DIRECTORY: Final = f"{SD_CARD_MOUNTED_LOCATION}/DCIM"
ENCRYPTION_KEY: Final = "ENCRYPTION_KEY"
MICROHARD_DEFAULT_IP: Final = "192.168.168.1"
PAIR_STATUS_FILE_PATH: Final = "/tmp/pair_status.txt"  # used so that the microhard service can check the status of the microhard (also serves as lockfile)
GPIO_LOW: Final = 1  # the SBX board inverts this logic


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
    GPS_DATA = "gps_data"  # `gps_data '{"lat": 359686990, "lon": -839290440, "alt": 276, "eph": 1, "epv": 1, "vel": 0, "cog": 0, "fix_type": 2, "satellites_visible": 10, "time_usec": 1730920262680000}'` is an example
    MISC_DATA = "misc_data"  # `misc_data '{"pitch": 0.1, "roll": 0.02, "camera_model": "IMX477", "focal_length": [50, 1]}'` is an example


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


@dataclass
class MavlinkGPSData:
    """
    Defines the fields coming from a MAVLink GPS_RAW_INT messages for both EXIF and KLV data.
    Note, EXIF doesn't support all of these fields but KLV and XMP can.
    See https://data.pix4d.com/misc/KB/documents/Exif_tags_for_project_creation-Pix4D_products.pdf
    """

    lat: int = 0  # Latitude in 1e-7 degrees, e.g., 37.4243276° N = 374243276
    lon: int = 0  # Longitude in 1e-7 degrees, e.g., -122.071482° W = -122071482
    alt: int = 0  # Altitude in millimeters above mean sea level
    eph: int = 0  # GPS HDOP horizontal dilution of position in cm (higher is worse)
    epv: int = 0  # GPS VDOP vertical dilution of position in cm (higher is worse)
    vel: int = 0  # GPS ground speed in cm/s
    cog: int = 0  # Course over ground (heading) in centi-degrees
    fix_type: int = 0  # GPS fix type, e.g., 0: no fix, 1: 2D fix, 2: 3D fix
    satellites_visible: int = 0  # Number of visible satellites
    time_usec: int = 0  # Timestamp (microseconds since UNIX epoch)


@dataclass
class MavlinkMiscData:
    """
    Defines the fields coming from MAVLink camera/position like ATTITUDE messages for both EXIF and KLV data.
    """

    pitch: float = 0.0  # radians (positive is up, negative is down)
    roll: float = (
        0.0  # radians (positive is right side down, negative is left side down)
    )
    camera_model: str = "Unknown"  # i.e. IMX477
    focal_length: Tuple[int, int] = (0, 0)  # i.e (50, 1) for 50mm


class RadioType(Enum):
    """
    The types of radios supported by the SBX pistreamer.
    """

    MICROHARD = "microhard"
    HERELINK = "herelink"
