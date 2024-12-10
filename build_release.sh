#!/bin/bash

VERSION="1.0"

# Source folder containing Python files
SOURCE_DIR="."
# Target folder to store minified files
MINIFIED_DIR="./release_build"

# Create the target directory if it doesn't exist
mkdir -p "$MINIFIED_DIR"

# Loop through all Python files and minify them
for file in "$SOURCE_DIR"/*.py; do
    echo "Minifying $file..."
    filename=$(basename "$file")
    pyminifier --obfuscate-variables --obfuscate-functions "$file" > "$MINIFIED_DIR/$filename"
done

echo "Minification complete. Minified files are in $MINIFIED_DIR."

cd "$MINIFIED_DIR"
pyinstaller --onefile --collect-all python pistreamer_v2.py
pyinstaller  pistreamer_v2.spec

echo "Build complete. Executable is at $MINIFIED_DIR/dist/pistreamer_v2"

echo "Creating deb file..."

# Define the package directory structure
PACKAGE_NAME="pistreamer"
PACKAGE_DIR="./deb_build/$PACKAGE_NAME"
DEBIAN_DIR="$PACKAGE_DIR/DEBIAN"
BIN_DIR="$PACKAGE_DIR/usr/local/bin"

# Create directories
mkdir -p "$DEBIAN_DIR" "$BIN_DIR"

# Create a placeholder for the control file
cat <<EOF > "$DEBIAN_DIR/control"
Package: $PACKAGE_NAME
Version: $VERSION
Section: network
Priority: important
Architecture: arm64
Maintainer: MONARK monark@echomav.com
Description: Runs pistreamer to stream video to the GCS
EOF

# Create a placeholder for the executable
cp "$MINIFIED_DIR/dist/$PACKAGE_NAME" "$BIN_DIR/$PACKAGE_NAME"
chmod +x "$BIN_DIR/$PACKAGE_NAME"


# Build the deb package
cd "$PACKAGE_DIR"
DEB_NAME="$PACKAGE_NAME_$VERSION_arm64.deb"
dpkg-deb --build "$PACKAGE_NAME" "$DEB_NAME"
mv "$DEB_NAME" "../$DEB_NAME"


# Confirm the structure
echo "SUCCESS"
