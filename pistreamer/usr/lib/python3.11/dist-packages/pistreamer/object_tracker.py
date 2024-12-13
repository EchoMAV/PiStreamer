from typing import Tuple
import cv2
import numpy as np

from constants import ACTIVE_BBOX_COLOR


class ObjectTracker:
    def __init__(self):
        self.tracker = None
        self.x_center = None
        self.y_center = None
        self.thickness = 2  # Thickness of the bb border

    def _init_tracking_poi(self, x_center: int, y_center: int):
        self.x_center = x_center
        self.y_center = y_center

    def _draw_point(self, frame: np.ndarray) -> None:
        color = (0, 0, 255)

        # Define the thickness of the lines
        thickness = 2

        # Draw two diagonal lines to form an "X"
        s = 3
        cv2.line(
            frame,
            (self.x_center - s, self.y_center - s),
            (self.x_center + s, self.y_center + s),
            color,
            thickness,
        )
        cv2.line(
            frame,
            (self.x_center - s, self.y_center + s),
            (self.x_center + s, self.y_center - s),
            color,
            thickness,
        )

    def _init_bounding_box(self, frame: np.ndarray) -> bool:
        # self._draw_point(frame)
        # return

        best_contour = None
        min_distance = float("inf")

        # Step 1: Convert the frame to grayscale
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Step 2: Apply Gaussian blur to reduce noise (optional for performance)
        blurred = cv2.GaussianBlur(gray_frame, (5, 5), 0)

        # Step 3: Canny edge detection
        canny_threshold1 = 50
        canny_threshold2 = 150
        edges = cv2.Canny(blurred, canny_threshold1, canny_threshold2)

        # Step 4: Find contours
        contours, _ = cv2.findContours(
            edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        # Step 5: Find the best contour that contains the point
        for contour in contours:
            if (
                cv2.pointPolygonTest(contour, (self.x_center, self.y_center), False)
                >= 0
            ):  # Point is inside or on the contour
                # Calculate the moments to get the centroid of the contour
                M = cv2.moments(contour)
                if M["m00"] != 0:
                    centroid_x = int(M["m10"] / M["m00"])
                    centroid_y = int(M["m01"] / M["m00"])

                    # Compute the Euclidean distance between the centroid and the point
                    distance = np.sqrt(
                        (centroid_x - self.x_center) ** 2
                        + (centroid_y - self.y_center) ** 2
                    )

                    # Select the contour with the minimum distance
                    if distance < min_distance:
                        min_distance = distance
                        best_contour = contour

        # Step 6: Set bounding box for the best contour if found
        if best_contour is not None:
            self.bounding_box = cv2.boundingRect(best_contour)
            print(f"Found bounding box: {self.bounding_box}")
            # TODO self.tracker = cv2.TrackerCSRT_create()
            return True

        print(f"No object detected at {self.x_center},{self.y_center}")
        return False

    def track_object(self, frame: np.ndarray) -> Tuple[bool, np.ndarray]:
        if not self.tracker:
            return False, frame
        ret, self.bounding_box = self.tracker.update(frame)
        if ret:
            self.draw_bounding_box(frame, ACTIVE_BBOX_COLOR)
        return ret, frame

    def draw_bounding_box(
        self, frame: np.ndarray, color: Tuple[int, int, int]
    ) -> np.ndarray:
        (x, y, w, h) = [int(v) for v in self.bounding_box]
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, self.thickness)
        return frame
