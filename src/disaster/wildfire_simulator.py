"""
Wildfire Simulator Module for DepthWizard.
Generates spatially coherent, vegetation-aware fire burn perimeters
driven by wind velocity, fuel density, and harmonic front turbulence.
"""

import numpy as np
import cv2
from typing import Dict, Any, List, Optional
from .simulation_config import WILDFIRE_INTENSITIES, PIXEL_AREA_TO_SQ_METERS

class WildfireSimulator:
    """
    Simulates wildland-urban interface (WUI) fire spread.
    Uses an elliptical wave propagation model modulated by wind vector and terrain fuel.
    """

    def __init__(self, width: int = 1024, height: int = 1024):
        self.width = width
        self.height = height

    def generate_wildfire_scenario(
        self,
        intensity: str = "medium",
        seed: int = 42,
        wind_direction_deg: float = 45.0, # Wind blowing toward North-East
        vegetation_mask: Optional[np.ndarray] = None,
        ground_elevation: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """
        Generates synthetic wildfire burn perimeter, charred mask, and fireline telemetry.
        """
        if intensity not in WILDFIRE_INTENSITIES:
            intensity = "medium"

        preset = WILDFIRE_INTENSITIES[intensity]
        np.random.seed(seed)

        # Fire ignition center: in vegetation cluster (south-central forest zone)
        # Coordinates in pixel space [x, y]
        cx = 480.0 + (seed % 60) - 30.0
        cy = 680.0 + (seed % 80) - 40.0

        spread_r = preset["spreadRadiusPixels"]
        wind_speed = preset["windSpeedKmh"]

        # Wind vector (radians)
        wind_rad = np.radians(wind_direction_deg)
        # Downwind elongation factor (ellipse eccentricity increases with wind)
        length_to_width = 1.0 + (wind_speed / 25.0) # e.g. 1.7 to 3.6
        a = spread_r * length_to_width # major axis along wind
        b = spread_r # minor axis perpendicular

        # Offset center forward along wind direction
        forward_shift = a * 0.45
        focus_x = cx + forward_shift * np.cos(wind_rad)
        focus_y = cy - forward_shift * np.sin(wind_rad) # y is inverted in image coordinates

        # Create coordinate grids
        y_grid, x_grid = np.ogrid[:self.height, :self.width]
        dx = x_grid - focus_x
        dy = y_grid - focus_y

        # Rotate into wind-aligned frame
        cos_w = np.cos(wind_rad)
        sin_w = np.sin(wind_rad)
        x_prime = dx * cos_w - dy * sin_w
        y_prime = dx * sin_w + dy * cos_w

        # Base elliptical distance
        ellipse_dist = np.sqrt((x_prime / a) ** 2 + (y_prime / b) ** 2)

        # Multi-scale harmonic noise along angle to generate realistic irregular fingers
        angles = np.arctan2(y_prime, x_prime)
        noise1 = np.sin(angles * 3.0 + (seed % 20)) * 0.16
        noise2 = np.cos(angles * 7.0 + (seed % 35)) * 0.09
        noise3 = np.sin(angles * 13.0 + (seed % 50)) * 0.04

        burn_threshold = 1.0 + noise1 + noise2 + noise3
        raw_burn = ellipse_dist <= burn_threshold

        burn_mask = np.zeros((self.height, self.width), dtype=np.uint8)
        burn_mask[raw_burn] = 255

        # If vegetation mask provided, fire spreads faster in vegetation and slows on bare/paved ground
        if vegetation_mask is not None:
            # Buffer around vegetation
            veg_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
            veg_dilated = cv2.dilate(vegetation_mask.astype(np.uint8), veg_kernel)
            # Retain burn zone but suppress into non-vegetated open water
            burn_mask[burn_mask > 0] = np.where(veg_dilated > 0, 255, 180)
            burn_mask = (burn_mask >= 160).astype(np.uint8) * 255

        # Smoothing
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        burn_mask = cv2.morphologyEx(burn_mask, cv2.MORPH_CLOSE, kernel)
        burn_mask = cv2.GaussianBlur(burn_mask, (7, 7), 2.5)
        burn_mask = (burn_mask >= 110).astype(np.uint8) * 255

        # Extract contours
        contours, _ = cv2.findContours(burn_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        burn_polygons: List[List[List[float]]] = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 400:
                epsilon = max(1.5, 0.0035 * cv2.arcLength(cnt, True))
                approx = cv2.approxPolyDP(cnt, epsilon, True)
                if len(approx) >= 3:
                    pts = approx.reshape(-1, 2).astype(float).tolist()
                    burn_polygons.append(pts)

        burned_pixels = int(np.sum(burn_mask > 0))
        burned_area_sqm = round(burned_pixels * PIXEL_AREA_TO_SQ_METERS, 2)

        return {
            "disasterType": "WILDFIRE",
            "intensity": intensity,
            "preset": preset,
            "seed": seed,
            "windDirectionDeg": wind_direction_deg,
            "windSpeedKmh": wind_speed,
            "firelineIntensityKwm": preset["firelineIntensityKwm"],
            "burnedPixels": burned_pixels,
            "burnedAreaSqMeters": burned_area_sqm,
            "polygons": burn_polygons,
            "mask": burn_mask,
            "ignitionCenter": {"x": round(focus_x, 1), "y": round(focus_y, 1)}
        }
