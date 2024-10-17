#!/usr/bin/env python3

from command_service import CommandService
from constants import CommandType
import time

command_service = CommandService()

# Modify the command_type and command_value as needed=

#######-####### BITRATE #######-#######
# command_service.add_input_command(command_type=CommandType.BITRATE, command_value="2010")

#######-####### ZOOM #######-#######
command_service.add_input_command(command_type=CommandType.ZOOM, command_value="1.0")
# command_service.add_input_command(command_type=CommandType.MAX_ZOOM, command_value="8.0")
# command_service.add_input_command(command_type=CommandType.ZOOM, command_value="in")
# command_service.add_input_command(command_type=CommandType.ZOOM, command_value="out")
# time.sleep(2)
# command_service.add_input_command(command_type=CommandType.ZOOM, command_value="stop")

#######-####### PHOTO #######-#######
# command_service.add_input_command(command_type=CommandType.TAKE_PHOTO)

#######-####### ATAK #######-#######
# command_service.add_input_command(
#     command_type=CommandType.ATAK_HOST, command_value="224.1.1.1:5002"
# )

#######-####### GCS #######-#######
# command_service.add_input_command(command_type=CommandType.GCS_IP, command_value="192.168.1.124")
# command_service.add_input_command(command_type=CommandType.GCS_PORT, command_value="5600")
# command_service.add_input_command(command_type=CommandType.GCS_HOST, command_value="192.168.1.124:5600")
# command_service.add_input_command(command_type=CommandType.START_GCS_STREAM)
# command_service.add_input_command(command_type=CommandType.STOP_GCS_STREAM)

#######-####### RECORD #######-#######
# command_service.add_input_command(command_type=CommandType.RECORD)
# time.sleep(15)
# command_service.add_input_command(command_type=CommandType.STOP_RECORDING)

#######-####### STABILIZE #######-#######
# command_service.add_input_command(command_type=CommandType.STABILIZE, command_value="start")
# command_service.add_input_command(
#     command_type=CommandType.STABILIZE, command_value="stop"
# )
