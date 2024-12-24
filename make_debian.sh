#!/bin/bash
# create and install debian file for `pistreamer`

set -e

PACKAGE_NAME="pistreamer"
SUDO=$(test ${EUID} -ne 0 && which sudo)

$SUDO apt install -y dpkg

$SUDO rm -f *.deb

cd $PACKAGE_NAME
$SUDO cp usr/lib/python3.11/dist-packages/$PACKAGE_NAME/$PACKAGE_NAME.py usr/bin/$PACKAGE_NAME
$SUDO chmod 755 usr/bin/$PACKAGE_NAME
dpkg-deb --root-owner-group --build . ../
cd ..

DEB_FILE=$(find . -type f -name "*arm64.deb" | head -n 1)
echo "Debian file created: $DEB_FILE"
echo
echo "=======-------======="
echo
echo "Add $DEB_FILE to source control."
echo
echo "=======-------======="
