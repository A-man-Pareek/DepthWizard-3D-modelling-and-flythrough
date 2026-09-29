"""
Cyclone Simulator Module for DepthWizard.
Generates rotational wind velocity fields and impact corridors
using the Holland vortex model with logarithmic spiral streamlines.
"""

import numpy as np
import cv2
from typing import Dict, Any, List, Optional
from .simulation_config import CYCLONE_INTENSITIES, PIXEL_AREA_TO_SQ_METERS

class CycloneSimulator:
    """
    Simulates a tropical cyclone / extreme wind corridor.
    Calculates radial wind decay, eyewall boundary, and logarithmic streamlines.
    """

    def __init__(self, width: int = 1024, height: int = 1024):
        self.width = width
        self.height = height

    def generate_cyclone_scenario(
        self,
        intensity: str = "medium",
        seed: int = 42,
        eye_x: Optional[float] = None,
        eye_y: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Generates cyclone wind field, eyewall perimeter, and high-impact swath.
        """
        if intensity not in CYCLONE_INTENSITIES:
            intensity = "medium"

        preset = CYCLONE_INTENSITIES[intensity]
        np.random.seed(seed)

        # Eye center position: default slightly off-center (advancing from northwest)
        if eye_x is None:
            eye_x = 420.0 + (seed % 100) - 50.0
        if eye_y is None:
            eye_y = 380.0 + (seed % 100) - 50.0

        v_max = preset["maxWindSpeedKmh"]
        r_max = preset["radiusMaxWindsPixels"]
        r_outer = preset["cycloneRadiusPixels"]

        # Radial grid calculation
        y_grid, x_grid = np.ogrid[:self.height, :self.width]
        dx = x_grid - eye_x
        dy = y_grid - eye_y
        dist = np.sqrt(dx ** 2 + dy ** 2)

        # Holland parametric wind velocity: V(r) = V_max * ( (2 * r_max * r) / (r_max^2 + r^2) )
        with np.errstate(divide='ignore', invalid='ignore'):
            velocity_field = v_max * ((2.0 * r_max * dist) / (r_max ** 2 + dist ** 2 + 1e-6))
        velocity_field[dist < 25] = v_max * 0.15 # Calm eye

        # Impact threshold: winds exceeding gale force (65 km/h)
        gale_threshold = 65.0
        impact_mask = (velocity_field >= gale_threshold) & (dist <= r_outer)

        # Add spiral arm variations
        angles = np.arctan2(dy, dx)
        # Logarithmic spiral arm modulation (2 main spiral rain/wind bands)
        spiral_phase = (angles - 0.45 * np.log(np.maximum(10.0, dist))) * 2.0
        arm_boost = np.cos(spiral_phase + (seed % 10)) * 0.15 + 1.0
        effective_velocity = velocity_field * arm_boost

        final_mask = np.zeros((self.height, self.width), dtype=np.uint8)
        final_mask[effective_velocity >= gale_threshold] = 255

        # Smoothing
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
        final_mask = cv2.morphologyEx(final_mask, cv2.MORPH_CLOSE, kernel)
        final_mask = cv2.GaussianBlur(final_mask, (7, 7), 2.0)
        final_mask = (final_mask >= 120).astype(np.uint8) * 255

        # Extract contours
        contours, _ = cv2.findContours(final_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        swath_polygons: List[List[List[float]]] = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 800:
                epsilon = max(1.5, 0.003 * cv2.arcLength(cnt, True))
                approx = cv2.approxPolyDP(cnt, epsilon, True)
                if len(approx) >= 3:
                    pts = approx.reshape(-1, 2).astype(float).tolist()
                    swath_polygons.append(pts)

        impact_pixels = int(np.sum(final_mask > 0))
        impact_area_sqm = round(impact_pixels * PIXEL_AREA_TO_SQ_METERS, 2)

        return {
            "disasterType": "CYCLONE",
            "intensity": intensity,
            "preset": preset,
            "seed": seed,
            "eyePosition": {"x": round(eye_x, 1), "y": round(eye_y, 1)},
            "maxWindSpeedKmh": v_max,
            "radiusMaxWindsPixels": r_max,
            "centralPressureHpa": preset["centralPressureHpa"],
            "impactedPixels": impact_pixels,
            "impactedAreaSqMeters": impact_area_sqm,
            "polygons": swath_polygons,
            "mask": final_mask
        }
