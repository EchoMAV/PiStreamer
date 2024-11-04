#!/usr/bin/env python3

from command_service import CommandService
from constants import CMD_SOCKET_PORT, CMD_SOCKET_HOST, CommandType
import time


def _send_data(command_type: CommandType, command_value: str = "") -> None:
    data = f"{command_type.value} {command_value}".strip()
    CommandService.send_data_out(data=data, host=CMD_SOCKET_HOST, port=CMD_SOCKET_PORT)


# Modify the command_type and command_value as needed=

#######-####### BITRATE #######-#######
# _send_data(command_type=CommandType.BITRATE, command_value="3000")

#######-####### ZOOM #######-#######
# _send_data(command_type=CommandType.ZOOM, command_value="4.0")
# time.sleep(2)
# _send_data(command_type=CommandType.ZOOM, command_value="3.0")
# time.sleep(2)
# _send_data(command_type=CommandType.ZOOM, command_value="2.0")
# _send_data(command_type=CommandType.MAX_ZOOM, command_value="8.0")
# _send_data(command_type=CommandType.ZOOM, command_value="in")
# _send_data(command_type=CommandType.ZOOM, command_value="out")
# time.sleep(2)
# _send_data(command_type=CommandType.ZOOM, command_value="stop")

#######-####### PHOTO #######-#######
# _send_data(command_type=CommandType.TAKE_PHOTO)

#######-####### ATAK #######-#######
_send_data(command_type=CommandType.GCS_HOST, command_value="192.168.1.124:5600")

#######-####### QGC #######-#######
# _send_data(command_type=CommandType.GCS_IP, command_value="192.168.1.124")
# _send_data(command_type=CommandType.GCS_PORT, command_value="5600")
# _send_data(command_type=CommandType.GCS_HOST, command_value="192.168.1.124:5600")
# _send_data(command_type=CommandType.START_GCS_STREAM)
# _send_data(command_type=CommandType.STOP_GCS_STREAM)

#######-####### RECORD #######-#######
# _send_data(command_type=CommandType.RECORD)
# time.sleep(10)
# _send_data(command_type=CommandType.STOP_RECORDING)

#######-####### STABILIZE #######-#######
# _send_data(command_type=CommandType.STABILIZE, command_value="start")
# _send_data(
#     command_type=CommandType.STABILIZE, command_value="stop"
# )

#######-####### TRACKING #######-#######
# _send_data(command_type=CommandType.INIT_TRACKING_POI, command_value="560,290")
