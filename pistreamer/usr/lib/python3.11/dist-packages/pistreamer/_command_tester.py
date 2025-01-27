#!/usr/bin/env python3

import json
from typing import Any, List, Tuple
from constants import CMD_SOCKET_PORT, CMD_SOCKET_HOST, CommandType, CommandProtocolType
import time
import socket
import zmq


if __name__ == "__main__":

    def _send_data_socket(commands: List[Tuple[Any, Any]]) -> None:
        for command in commands:
            data = f"{command[0].value} {command[1]}".strip()
            try:
                _data = data.strip().encode()
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((CMD_SOCKET_HOST, CMD_SOCKET_PORT))
                client_socket.sendall(_data)
            except Exception as e:
                print(f"{CMD_SOCKET_HOST}:{CMD_SOCKET_PORT} {e}")
            finally:
                client_socket.close()

    def _send_data_zeromq(commands: List[Tuple[Any, Any]]) -> None:
        try:
            context = zmq.Context()
            zeromq_socket = context.socket(zmq.PAIR)
            zeromq_socket.bind(f"tcp://*:{CMD_SOCKET_PORT}")
        except Exception as e:
            print(f"{CMD_SOCKET_HOST}:{CMD_SOCKET_PORT} {e}")
            return

        for command in commands:
            data = f"{command[0].value} { command[1]}".strip()
            zeromq_socket.send_string(data)

        zeromq_socket.close()

    def _send_data(commands: List[Tuple[Any, Any]]) -> None:
        ### ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        ###  Change protocol as needed
        protocol = CommandProtocolType.ZEROMQ.value
        # protocol = CommandProtocolType.SOCKET.value
        ### ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        print(f"Sending {len(commands)} commands via {protocol}")
        if protocol == CommandProtocolType.ZEROMQ.value:
            _send_data_zeromq(commands)
        else:
            _send_data_socket(commands)

    # Modify the command_type and command_value as needed
    commands = []

    #######-####### BITRATE #######-#######
    # commands.append((CommandType.BITRATE,"2500"))

    #######-####### ZOOM #######-#######
    # commands.append((CommandType.ZOOM, "2.0"))
    # commands.append((CommandType.MAX_ZOOM,"8.0"))
    # commands.append((CommandType.ZOOM, "in"))
    # commands.append((CommandType.ZOOM,"out"))
    # commands.append((CommandType.ZOOM,"stop"))

    #######-####### EXIF/KLV #######-#######
    # commands.append(
    #     (
    #         CommandType.GPS_DATA,
    #         json.dumps(
    #             {
    #                 "lat": 359686990,
    #                 "lon": -839290440,
    #                 "alt": 276,
    #                 "eph": 1,
    #                 "epv": 1,
    #                 "vel": 0,
    #                 "cog": 0,
    #                 "fix_type": 2,
    #                 "satellites_visible": 10,
    #                 "time_usec": 1730920262680000,
    #             }
    #         ),
    #     )
    # )

    # commands.append(
    #     (
    #         CommandType.MISC_DATA,
    #         json.dumps(
    #             {
    #                 "pitch": 0.1,
    #                 "roll": 0.02,
    #                 "camera_model": "IMX477",
    #                 "focal_length": (50, 1),
    #             }
    #         ),
    #     )
    # )

    #######-####### PHOTO #######-#######
    commands.append((CommandType.TAKE_PHOTO, "/mnt/external_sd/DCIM/testimage.jpg"))
    # commands.append((CommandType.TAKE_PHOTO, ""))

    #######-####### QGC #######-#######
    # commands.append((CommandType.GCS_IP,"192.168.1.124"))
    # commands.append((CommandType.GCS_PORT,"5600"))
    # commands.append((CommandType.GCS_HOST,"192.168.1.124:5600"))
    # commands.append((CommandType.START_GCS_STREAM,""))
    # commands.append((CommandType.STOP_GCS_STREAM,""))
    # commands.append((CommandType.STREAMING_PROTOCOL,"rtp"))

    #######-####### RECORD #######-#######
    # commands.append((CommandType.RECORD,""))
    # time.sleep(10)
    # commands.append((CommandType.STOP_RECORDING,""))

    #######-####### STABILIZE #######-#######
    # commands.append((CommandType.STABILIZE,"start"))
    # commands.append((CommandType.STABILIZE,"stop"))

    #######-####### TRACKING #######-#######
    # commands.append((CommandType.INIT_TRACKING_POI,"560,290"))

    _send_data(commands)
