#!/bin/bash
# create and install debian file if `pistreamer`

set -e

SUDO=$(test ${EUID} -ne 0 && which sudo)

$SUDO apt install -y dpkg

cd "pistreamer"
dpkg-deb --root-owner-group --build . ../
cd ..
$SUDO apt install ./pistreamer_* --reinstall
