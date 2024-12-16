#!/bin/bash
# create and install debian file for `pistreamer`

set -e

# Check if private_key.pem exists
if [ ! -f private_key.pem ]; then
  echo "Error: private_key.pem not found!"
  exit 1
fi

PACKAGE_NAME="pistreamer"
SUDO=$(test ${EUID} -ne 0 && which sudo)

$SUDO apt install -y dpkg

cd $PACKAGE_NAME
$SUDO cp usr/lib/python3.11/dist-packages/$PACKAGE_NAME/$PACKAGE_NAME.py usr/bin/$PACKAGE_NAME
$SUDO chmod 755 usr/bin/$PACKAGE_NAME
dpkg-deb --root-owner-group --build . ../
cd ..

DEB_FILE=$(find . -type f -name "*arm64.deb" | head -n 1)
echo "Debian file created: $DEB_FILE"

# Generate a SHA-256 Digest of the .deb File
$SUDO openssl dgst -sha256 -out $DEB_FILE.sha256 $DEB_FILE
# Sign the Digest with the Private Key
$SUDO openssl dgst -sha256 -sign private_key.pem -out $DEB_FILE.sig $DEB_FILE
echo
echo "=======-------======="
echo
echo "Add $DEB_FILE.sig and $DEB_FILE to source control."
echo
echo "=======-------======="
