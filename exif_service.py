from typing import Tuple, Union
from constants import ExifDataGPS
import piexif
from PIL import Image


class EXIFService:
    def __init__(self, gps_data: ExifDataGPS, file_name: str):
        self.gps_data = gps_data
        self.file_name = file_name

    def _convert_to_exif_format(
        self, degrees: int, minutes: int, seconds: float
    ) -> Tuple[Tuple[int, int], Tuple[int, int], Tuple[Union[int, float], int]]:
        """
        Converts degrees, minutes, seconds to EXIF format
        """
        return ((degrees * 1, 1), (minutes * 1, 1), (seconds * 100, 100))

    def _get_exif_gps_data(self) -> dict:
        return {
            piexif.GPSIFD.GPSLatitude: self._convert_to_exif_format(
                self.gps_data.GPSLatitude
            ),
            piexif.GPSIFD.GPSLatitudeRef: self.gps_data.GPSLatitudeRef.encode(),
            piexif.GPSIFD.GPSLongitude: self._convert_to_exif_format(
                self.gps_data.GPSLongitude
            ),
            piexif.GPSIFD.GPSLongitudeRef: self.gps_data.GPSLongitudeRef.encode(),
            piexif.GPSIFD.GPSAltitude: self.gps_data.GPSAltitude,
            piexif.GPSIFD.GPSAltitudeRef: self.gps_data.GPSAltitudeRef,
            piexif.GPSIFD.GPSDateStamp: self.gps_data.GPSDateStamp.encode(),
            piexif.GPSIFD.GPSTimeStamp: self.gps_data.GPSTimeStamp,
        }

    def _get_exif_bytes(self) -> bytes:
        """
        Returns the bytes of the EXIF formatted GPS formatted data
        """
        exif_dict = {"GPS": self._get_exif_gps_data()}
        return piexif.dump(exif_dict)

    def add_exif_metadata(self) -> None:
        if not self.gps_data:
            print("No GPS data to add")
            return
        image = Image.open(self.file_name)
        image.save(self.file_name, exif=self._get_exif_bytes())
