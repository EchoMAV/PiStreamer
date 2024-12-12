from typing import Any, Optional, Tuple
import cv2
from pyzbar.pyzbar import decode
import numpy as np


def detect_qr_code(frame: np.ndarray) -> Tuple[Optional[str], Any]:
    """
    Converts the frame to grayscale and detects QR codes in the frame.
    """
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    qr_codes = decode(gray_frame)

    if qr_codes:
        for qr_code in qr_codes:
            qr_data = str(qr_code.data.decode("utf-8"))
            print(f"Detected QR Code")
            return qr_data, gray_frame

    return None, gray_frame
