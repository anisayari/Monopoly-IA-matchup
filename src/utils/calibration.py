import json
import numpy as np
from typing import Tuple


class CalibrationUtils:
    """Utility class for coordinate conversion using perspective transformation"""

    def __init__(self, calibration_file: str = "calibration.json"):
        """Initialize with calibration data from JSON file"""
        try:
            with open(calibration_file, 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Calibration file '{calibration_file}' not found")
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in calibration file '{calibration_file}'")

        if "points" not in data or len(data["points"]) < 4:
            raise ValueError("Need at least 4 calibration points for perspective transformation")

        # Extract calibration points
        self.points = data["points"]

        # Calculate transformation matrices
        self._calculate_transformations()

    def _calculate_transformations(self):
        """Calculate perspective transformation matrices"""
        # Extract source (mouse) and target (wiimote) points
        mouse_points = np.array([[p["mouse"]["x"], p["mouse"]["y"]] for p in self.points])
        wiimote_points = np.array([[p["wiimote"]["x"], p["wiimote"]["y"]] for p in self.points])

        # Calculate perspective transformations
        self.mouse_to_wiimote_matrix = self._calculate_perspective_matrix(mouse_points, wiimote_points)
        self.wiimote_to_mouse_matrix = self._calculate_perspective_matrix(wiimote_points, mouse_points)

    def _calculate_perspective_matrix(self, source: np.ndarray, target: np.ndarray) -> np.ndarray:
        """Calculate perspective transformation matrix using DLT (Direct Linear Transform)"""
        n_points = source.shape[0]

        # Create coefficient matrix for perspective transformation
        A = np.zeros((2 * n_points, 8))
        b = np.zeros(2 * n_points)

        for i in range(n_points):
            x, y = source[i]
            x_prime, y_prime = target[i]

            # First equation: ax + by + c - x'*gx - x'*hy = x'
            A[2 * i] = [x, y, 1, 0, 0, 0, -x_prime * x, -x_prime * y]
            b[2 * i] = x_prime

            # Second equation: dx + ey + f - y'*gx - y'*hy = y'
            A[2 * i + 1] = [0, 0, 0, x, y, 1, -y_prime * x, -y_prime * y]
            b[2 * i + 1] = y_prime

        # Solve for transformation parameters [a,b,c,d,e,f,g,h]
        params = np.linalg.lstsq(A, b, rcond=None)[0]

        # Construct 3x3 perspective transformation matrix
        transform_matrix = np.array([
            [params[0], params[1], params[2]],  # [a, b, c]
            [params[3], params[4], params[5]],  # [d, e, f]
            [params[6], params[7], 1]           # [g, h, 1]
        ])

        return transform_matrix

    def conversion(self, mouse_x: float, mouse_y: float) -> Tuple[float, float]:
        """Convert mouse coordinates to wiimote coordinates"""
        return self._perspective_transform(mouse_x, mouse_y, self.mouse_to_wiimote_matrix)

    def inverse_conversion(self, wiimote_x: float, wiimote_y: float) -> Tuple[float, float]:
        """Convert wiimote coordinates to mouse coordinates"""
        return self._perspective_transform(wiimote_x, wiimote_y, self.wiimote_to_mouse_matrix)

    def _perspective_transform(self, x: float, y: float, matrix: np.ndarray) -> Tuple[float, float]:
        """Apply perspective transformation"""
        point = np.array([x, y, 1])
        transformed = matrix @ point

        # Handle perspective division
        if transformed[2] != 0:
            x_new = transformed[0] / transformed[2]
            y_new = transformed[1] / transformed[2]
        else:
            x_new = transformed[0]
            y_new = transformed[1]

        return float(x_new), float(y_new)