#!/bin/bash
# create and install debian file if `pistreamer`

set -e

SUDO=$(test ${EUID} -ne 0 && which sudo)

$SUDO apt install -y dpkg

cd "pistreamer"
$SUDO cp usr/lib/python3.11/dist-packages/pistreamer/pistreamer.py usr/bin/pistreamer
$SUDO chmod 755 usr/bin/pistreamer
dpkg-deb --root-owner-group --build . ../
cd ..
$SUDO apt install ./pistreamer_* --reinstall
