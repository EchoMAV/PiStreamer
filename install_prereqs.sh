#!/bin/bash
# install prereqs for PiStreamer and associated tools

SUDO=$(test ${EUID} -ne 0 && which sudo)
$SUDO apt update
$SUDO apt install -y libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev libgstreamer-plugins-bad1.0-dev gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav gstreamer1.0-tools gstreamer1.0-x gstreamer1.0-alsa gstreamer1.0-gl gstreamer1.0-gtk3 gstreamer1.0-qt5 gstreamer1.0-pulseaudio
$SUDO apt install -y python3-libcamera libcamera-apps
$SUDO apt install -y python3-picamera2
$SUDO apt install -y ffmpeg
$SUDO apt install -y python3-opencv
$SUDO apt install -y python3-numpy
$SUDO apt install -y libzmq3-dev
$SUDO apt install -y python3-zmq
$SUDO apt install -y python3-piexif
$SUDO apt install -y python3-py3exiv2
