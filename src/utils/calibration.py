import json
import numpy as np
from typing import Tuple
import os


class CalibrationUtils:
    """Utility class for coordinate conversion using enhanced perspective transformation"""

    def __init__(self, calibration_file: str = "game_files/calibration.json"):
        """Initialize with calibration data from JSON file"""
        # Si le chemin n'est pas absolu, on le cherche par rapport à la racine du projet
        if not os.path.isabs(calibration_file):
            # Trouve la racine du projet en cherchant le dossier qui contient 'src'
            current = os.path.dirname(os.path.abspath(__file__))
            while current != os.path.dirname(current):  # Tant qu'on n'est pas à la racine
                if os.path.exists(os.path.join(current, 'src')) and os.path.exists(os.path.join(current, 'game_files')):
                    # On a trouvé la racine du projet
                    calibration_file = os.path.join(current, calibration_file)
                    break
                current = os.path.dirname(current)

            calibration_file = os.path.normpath(calibration_file)

        try:
            print(f"🔍 CalibrationUtils opening: {calibration_file}")
            with open(calibration_file, 'r') as f:
                data = json.load(f)
                print(f"📊 Loaded data has {len(data.get('points', []))} points")
                if data.get('points'):
                    print(f"   First point: {data['points'][0]}")

        except FileNotFoundError:
            raise FileNotFoundError(f"Calibration file '{calibration_file}' not found")
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in calibration file '{calibration_file}'")

        if "points" not in data or len(data["points"]) < 4:
            raise ValueError("Need at least 4 calibration points for perspective transformation")

        # Extract calibration points
        self.points = data["points"]
        self.calibration_type = data.get("calibration_type", "4-point")

        print(f"🎯 Using {self.calibration_type} calibration with {len(self.points)} points")

        # Calculate transformation matrices
        self._calculate_transformations()

    def _calculate_transformations(self):
        """Calculate enhanced perspective transformation matrices with improved accuracy"""
        # Extract source (mouse) and target (wiimote) points
        mouse_points = np.array([[p["mouse"]["x"], p["mouse"]["y"]] for p in self.points])
        wiimote_points = np.array([[p["wiimote"]["x"], p["wiimote"]["y"]] for p in self.points])

        # For better numerical stability, normalize coordinates
        self.mouse_center = np.mean(mouse_points, axis=0)
        self.wiimote_center = np.mean(wiimote_points, axis=0)

        self.mouse_scale = np.max(np.abs(mouse_points - self.mouse_center))
        self.wiimote_scale = np.max(np.abs(wiimote_points - self.wiimote_center))

        # Normalize points for better numerical conditioning
        mouse_normalized = (mouse_points - self.mouse_center) / self.mouse_scale
        wiimote_normalized = (wiimote_points - self.wiimote_center) / self.wiimote_scale

        # Calculate perspective transformations with normalized coordinates
        self.mouse_to_wiimote_matrix = self._calculate_perspective_matrix(mouse_normalized, wiimote_normalized)
        self.wiimote_to_mouse_matrix = self._calculate_perspective_matrix(wiimote_normalized, mouse_normalized)

        # Validate calibration quality
        self._validate_calibration()

    def _calculate_perspective_matrix(self, source: np.ndarray, target: np.ndarray) -> np.ndarray:
        """Calculate perspective transformation matrix using enhanced DLT with more points"""
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

        # Use weighted least squares for better accuracy with more points
        if n_points > 4:
            # Add slight weight to center points for stability
            weights = np.ones(2 * n_points)
            # Center point gets slightly higher weight if it exists (index 4 in 9-point grid)
            if n_points == 9:
                weights[8:10] *= 1.2  # Center point (point 5, indices 8,9)

            W = np.diag(weights)
            # Weighted least squares: (A^T W A)^-1 A^T W b
            try:
                ATA_inv = np.linalg.inv(A.T @ W @ A)
                params = ATA_inv @ A.T @ W @ b
            except np.linalg.LinAlgError:
                # Fallback to regularized solution
                params = np.linalg.lstsq(A, b, rcond=1e-10)[0]
        else:
            # Standard least squares for 4 points
            params = np.linalg.lstsq(A, b, rcond=None)[0]

        # Construct 3x3 perspective transformation matrix
        transform_matrix = np.array([
            [params[0], params[1], params[2]],  # [a, b, c]
            [params[3], params[4], params[5]],  # [d, e, f]
            [params[6], params[7], 1]  # [g, h, 1]
        ])

        return transform_matrix

    def _validate_calibration(self):
        """Validate calibration quality and provide feedback"""
        mouse_points = np.array([[p["mouse"]["x"], p["mouse"]["y"]] for p in self.points])
        wiimote_points = np.array([[p["wiimote"]["x"], p["wiimote"]["y"]] for p in self.points])

        total_error = 0
        max_error = 0

        for i, (mx, my) in enumerate(mouse_points):
            # Test forward transformation
            wx_pred, wy_pred = self.conversion(mx, my)
            wx_actual, wy_actual = wiimote_points[i]

            error = np.sqrt((wx_pred - wx_actual) ** 2 + (wy_pred - wy_actual) ** 2)
            total_error += error
            max_error = max(max_error, error)

        avg_error = total_error / len(self.points)

        print(f"📊 Calibration validation:")
        print(f"   Average error: {avg_error:.2f} pixels")
        print(f"   Maximum error: {max_error:.2f} pixels")
        print(f"   Quality: {'Excellent' if avg_error < 5 else 'Good' if avg_error < 15 else 'Needs improvement'}")

        if avg_error > 25:
            print("⚠️  Warning: High calibration error. Consider recalibrating.")

    def conversion(self, mouse_x: float, mouse_y: float) -> Tuple[float, float]:
        """Convert mouse coordinates to wiimote coordinates"""
        # Normalize input
        mouse_norm = np.array([mouse_x - self.mouse_center[0], mouse_y - self.mouse_center[1]]) / self.mouse_scale

        # Apply transformation
        wiimote_norm_x, wiimote_norm_y = self._perspective_transform(mouse_norm[0], mouse_norm[1],
                                                                     self.mouse_to_wiimote_matrix)

        # Denormalize output
        wiimote_x = wiimote_norm_x * self.wiimote_scale + self.wiimote_center[0]
        wiimote_y = wiimote_norm_y * self.wiimote_scale + self.wiimote_center[1]

        return float(wiimote_x), float(wiimote_y)

    def inverse_conversion(self, wiimote_x: float, wiimote_y: float) -> Tuple[float, float]:
        """Convert wiimote coordinates to mouse coordinates"""
        # Normalize input
        wiimote_norm = np.array(
            [wiimote_x - self.wiimote_center[0], wiimote_y - self.wiimote_center[1]]) / self.wiimote_scale

        # Apply transformation
        mouse_norm_x, mouse_norm_y = self._perspective_transform(wiimote_norm[0], wiimote_norm[1],
                                                                 self.wiimote_to_mouse_matrix)

        # Denormalize output
        mouse_x = mouse_norm_x * self.mouse_scale + self.mouse_center[0]
        mouse_y = mouse_norm_y * self.mouse_scale + self.mouse_center[1]

        return float(mouse_x), float(mouse_y)

    def _perspective_transform(self, x: float, y: float, matrix: np.ndarray) -> Tuple[float, float]:
        """Apply perspective transformation with improved numerical stability"""
        point = np.array([x, y, 1])
        transformed = matrix @ point

        # Handle perspective division with numerical stability
        if abs(transformed[2]) > 1e-10:
            x_new = transformed[0] / transformed[2]
            y_new = transformed[1] / transformed[2]
        else:
            # Fallback for numerical issues
            x_new = transformed[0]
            y_new = transformed[1]
            print("⚠️  Warning: Numerical instability in perspective transformation")

        return float(x_new), float(y_new)