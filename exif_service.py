from datetime import datetime, timezone
from typing import Tuple
from constants import MavlinkGPSData, MavlinkMiscData
import piexif
from PIL import Image
import pyexiv2
import math


class EXIFService:
    def __init__(
        self, gps_data: MavlinkGPSData, misc_data: MavlinkMiscData, file_name: str
    ):
        self.gps_data = gps_data
        self.misc_data = misc_data
        self.file_name = file_name
        _now = datetime.now()
        self.current_datetime = _now.strftime("%Y:%m:%d %H:%M:%S")
        self.current_datetime_ms = int(_now.timestamp() * 1000)

    def _convert_coord_to_exif_format(
        self, gps_coord: int, is_latitude: bool
    ) -> Tuple[Tuple[Tuple[int, int], Tuple[int, int], Tuple[int, int]], str]:
        """
        Converts latitude or longitude in 1e-7 degrees format to EXIF format.
        """
        decimal_degrees = gps_coord / 1e7

        # Extract degrees, minutes, and seconds
        degrees = int(decimal_degrees)
        minutes_decimal = (decimal_degrees - degrees) * 60
        minutes = int(minutes_decimal)
        seconds = (minutes_decimal - minutes) * 60

        # Format for EXIF GPS format
        exif_coord = (
            (degrees, 1),
            (minutes, 1),
            (int(seconds * 10000), 10000),  # Use 4 decimal places for seconds
        )

        if is_latitude:
            exif_ref = "N" if decimal_degrees >= 0 else "S"
        else:
            exif_ref = "E" if decimal_degrees >= 0 else "W"

        return exif_coord, exif_ref

    def _get_exif_gps_data(self) -> dict:
        lat, lat_ref = self._convert_coord_to_exif_format(
            self.gps_data.lat, is_latitude=True
        )
        lon, lon_ref = self._convert_coord_to_exif_format(
            self.gps_data.lon, is_latitude=False
        )

        # Convert to datetime
        _gps_timestamp = datetime.fromtimestamp(
            self.gps_data.time_usec / 1e6, tz=timezone.utc
        )

        return {
            piexif.GPSIFD.GPSLatitude: lat,
            piexif.GPSIFD.GPSLatitudeRef: lat_ref.encode(),
            piexif.GPSIFD.GPSLongitude: lon,
            piexif.GPSIFD.GPSLongitudeRef: lon_ref.encode(),
            piexif.GPSIFD.GPSAltitude: (int(self.gps_data.alt * 1000), 1000),
            piexif.GPSIFD.GPSAltitudeRef: 0,  # above mean sea level
            piexif.GPSIFD.GPSDateStamp: _gps_timestamp.strftime("%Y:%m:%d").encode(),
            piexif.GPSIFD.GPSTimeStamp: (
                (_gps_timestamp.hour, 1),
                (_gps_timestamp.minute, 1),
                (_gps_timestamp.second, 1),
            ),
        }

    def _get_exif_misc_data(self) -> dict:
        return {
            piexif.ExifIFD.FocalLength: self.misc_data.focal_length,
            piexif.ExifIFD.DateTimeOriginal: self.current_datetime.encode(),
            piexif.ExifIFD.SubSecTimeOriginal: str(self.current_datetime_ms).encode(),
        }

    def _get_exif_bytes(self) -> bytes:
        """
        Returns the bytes of the EXIF formatted GPS formatted data
        """
        exif_dict = {
            "GPS": self._get_exif_gps_data(),
            "Exif": self._get_exif_misc_data(),
            "0th": {piexif.ImageIFD.Model: self.misc_data.camera_model.encode()},
        }
        return piexif.dump(exif_dict)

    def _add_xmp_data(self) -> None:
        """
        Adds XMP metadata for yaw, pitch, and roll since this is not supported by EXIF
        but still common for photogrammetry software.
        """

        metadata = pyexiv2.ImageMetadata(self.file_name)
        # import pdb
        # pdb.set_trace()
        metadata.read()

        # Set XMP tags for misc GPS/camera data
        metadata[
            "Xmp.Camera.RigRelatives"
        ] = f"{self.gps_data.cog * 0.01 * (math.pi / 180)}, {self.misc_data.pitch}, {self.misc_data.roll}"
        metadata[
            "Xmp.Camera.GPSXYAccuracy"
        ] = f"{self.gps_data.eph / 100.0}"  # Convert cm to m
        metadata[
            "Xmp.Camera.GPSZAccuracy"
        ] = f"{self.gps_data.epv / 100.0}"  # Convert cm to m

        metadata.write()  # Write XMP data to the image

    def add_metadata(self) -> None:
        print(f"Adding metadata to {self.file_name}")
        if not self.gps_data and not self.misc_data:
            print("No GPS and Camera data to add")
            return
        image = Image.open(self.file_name)
        image.save(self.file_name, exif=self._get_exif_bytes())

        # Add XMP metadata for pitch, roll etc.

        self._add_xmp_data()
