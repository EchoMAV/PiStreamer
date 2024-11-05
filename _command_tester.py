#!/usr/bin/env python3

from constants import CMD_SOCKET_PORT, CMD_SOCKET_HOST, CommandType, MessageProtocolType
import time
import socket

if __name__ == "__main__":

    def _send_data_socket(command_type: CommandType, command_value: str = "") -> None:
        data = f"{command_type.value} {command_value}".strip()
        try:
            _data = data.strip().encode()
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((CMD_SOCKET_HOST, CMD_SOCKET_PORT))
            client_socket.sendall(_data)
        except Exception as e:
            print(f"{CMD_SOCKET_HOST}:{CMD_SOCKET_PORT} {e}")
        finally:
            client_socket.close()

    def _send_data(command_type: CommandType, command_value: str = "") -> None:
        # change this to control which protocol to use
        protocol = MessageProtocolType.ZEROMQ.value
        if protocol == MessageProtocolType.ZEROMQ.value:
            pass
        else:
            _send_data_socket(command_type, command_value)

    # Modify the command_type and command_value as needed

    #######-####### BITRATE #######-#######
    # _send_data(command_type=CommandType.BITRATE, command_value="2500")

    #######-####### ZOOM #######-#######
    _send_data(command_type=CommandType.ZOOM, command_value="2.0")
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

    #######-####### QGC #######-#######
    # _send_data(command_type=CommandType.GCS_IP, command_value="192.168.1.124")
    # _send_data(command_type=CommandType.GCS_PORT, command_value="5600")
    # _send_data(command_type=CommandType.GCS_HOST, command_value="192.168.1.124:5600")
    # _send_data(command_type=CommandType.START_GCS_STREAM)
    # _send_data(command_type=CommandType.STOP_GCS_STREAM)
    # _send_data(command_type=CommandType.STREAMING_PROTOCOL, command_value="rtp")

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
