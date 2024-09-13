from typing import Final
from enum import Enum

COMMANDS_FILE_PATH:Final = "/tmp/pistreamer"
FIFO_CAM_PATH:Final = "/tmp/imx477"
FRAMERATE: Final = 30
DEFAULT_CONFIG_PATH: Final = "477-Pi4.json"
STABILIZATION_FRAMERATE: Final = "640x360"

class PiCameraCommand(Enum):
    STOP = "stop"
    KILL = "kill"
    BITRATE = "bitrate"
    PORT = "port"
    IP_ADDRESS = "ip_address"
    RECORD = "record"
    STOP_RECORDING = "stop_recording"