import json
import numpy as np
from typing import Tuple


class CalibrationUtils:
    """Utility class for coordinate conversion using calibration data"""

    def __init__(self, calibration_file: str = "calibration.json"):
        """Initialize with calibration data from JSON file"""
        try:
            with open(calibration_file, 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Calibration file '{calibration_file}' not found")
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in calibration file '{calibration_file}'")

        if "points" not in data or len(data["points"]) < 3:
            raise ValueError("Need at least 3 calibration points for affine transformation")

        self.points = data["points"]
        self._calculate_transformations()

    def _calculate_transformations(self):
        """Calculate affine transformation matrices"""
        # Extract mouse and wiimote points
        mouse_points = np.array([[p["mouse"]["x"], p["mouse"]["y"]] for p in self.points])
        wiimote_points = np.array([[p["wiimote"]["x"], p["wiimote"]["y"]] for p in self.points])

        # Calculate transformation matrices
        self.mouse_to_wiimote_matrix = self._calculate_affine_matrix(mouse_points, wiimote_points)
        self.wiimote_to_mouse_matrix = self._calculate_affine_matrix(wiimote_points, mouse_points)

    def _calculate_affine_matrix(self, source: np.ndarray, target: np.ndarray) -> np.ndarray:
        """Calculate affine transformation matrix using least squares"""
        n_points = source.shape[0]

        # Create coefficient matrix for affine transformation
        A = np.zeros((2 * n_points, 6))
        b = np.zeros(2 * n_points)

        for i in range(n_points):
            # X coordinate transformation: target_x = a*source_x + b*source_y + tx
            A[2 * i, 0] = source[i, 0]      # a coefficient
            A[2 * i, 1] = source[i, 1]      # b coefficient
            A[2 * i, 2] = 1                 # tx coefficient
            b[2 * i] = target[i, 0]         # target x

            # Y coordinate transformation: target_y = c*source_x + d*source_y + ty
            A[2 * i + 1, 3] = source[i, 0]  # c coefficient
            A[2 * i + 1, 4] = source[i, 1]  # d coefficient
            A[2 * i + 1, 5] = 1             # ty coefficient
            b[2 * i + 1] = target[i, 1]     # target y

        # Solve for transformation parameters [a, b, tx, c, d, ty]
        params = np.linalg.lstsq(A, b, rcond=None)[0]

        # Construct 3x3 transformation matrix
        return np.array([
            [params[0], params[1], params[2]],  # [a, b, tx]
            [params[3], params[4], params[5]],  # [c, d, ty]
            [0, 0, 1]                           # [0, 0, 1]
        ])

    def conversion(self, mouse_x: float, mouse_y: float) -> Tuple[float, float]:
        """Convert mouse coordinates to wiimote coordinates"""
        point = np.array([mouse_x, mouse_y, 1])
        transformed = self.mouse_to_wiimote_matrix @ point
        return float(transformed[0]), float(transformed[1])

    def inverse_conversion(self, wiimote_x: float, wiimote_y: float) -> Tuple[float, float]:
        """Convert wiimote coordinates to mouse coordinates"""
        point = np.array([wiimote_x, wiimote_y, 1])
        transformed = self.wiimote_to_mouse_matrix @ point
        return float(transformed[0]), float(transformed[1])