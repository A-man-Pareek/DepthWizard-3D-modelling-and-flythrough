"""
Landslide Simulator Module for DepthWizard.
Performs topographic slope stability analysis on HTC-DCNet elevation models,
identifying critical initiation scarps and downslope debris runout zones.
"""

import numpy as np
import cv2
from typing import Dict, Any, List, Optional
from .simulation_config import LANDSLIDE_INTENSITIES, PIXEL_AREA_TO_SQ_METERS, DEFAULT_GSD_METERS

class LandslideSimulator:
    """
    Simulates slope failure and mass displacement based on terrain elevation gradients.
    """

    def __init__(self, width: int = 1024, height: int = 1024, gsd_meters: float = DEFAULT_GSD_METERS):
        self.width = width
        self.height = height
        self.gsd_meters = gsd_meters

    def compute_slope_map(self, elevation: np.ndarray) -> np.ndarray:
        """
        Calculates terrain slope in degrees using NumPy elevation gradients.
        """
        elev_f32 = elevation.astype(np.float32)
        gy, gx = np.gradient(elev_f32, self.gsd_meters, self.gsd_meters)
        gradient_mag = np.sqrt(gx ** 2 + gy ** 2)
        slope_deg = np.degrees(np.arctan(gradient_mag))
        return slope_deg

    def generate_landslide_scenario(
        self,
        intensity: str = "medium",
        seed: int = 42,
        ground_elevation: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """
        Generates slope failure scarp and debris accumulation zone.
        """
        if intensity not in LANDSLIDE_INTENSITIES:
            intensity = "medium"

        preset = LANDSLIDE_INTENSITIES[intensity]
        np.random.seed(seed)

        # Synthetic fallback elevation with a hill if none provided
        if ground_elevation is None:
            ground_elevation = np.zeros((self.height, self.width), dtype=np.float32)
            y_g, x_g = np.ogrid[:self.height, :self.width]
            ground_elevation = np.maximum(0.0, 28.0 - 0.04 * (x_g - 650) - 0.05 * (y_g - 700))

        slope_map = self.compute_slope_map(ground_elevation)
        crit_slope = preset["criticalSlopeDegrees"]
        runout_dist = preset["runoutDistancePixels"]

        # High slope initiation scarps
        scarp_candidates = slope_map >= crit_slope

        # Focus scarp in a coherent hill slope sector (southeast)
        scarp_center_x = 620.0 + (seed % 60) - 30.0
        scarp_center_y = 620.0 + (seed % 60) - 30.0

        y_grid, x_grid = np.ogrid[:self.height, :self.width]
        dist_from_focus = np.sqrt((x_grid - scarp_center_x) ** 2 + (y_grid - scarp_center_y) ** 2)

        # Initiation zone: steep ground within candidate area
        initiation_mask = scarp_candidates & (dist_from_focus <= runout_dist * 0.55)

        if np.sum(initiation_mask) < 200:
            initiation_mask = dist_from_focus <= (runout_dist * 0.45)

        # Downslope propagation: flow along steepest descent direction
        runout_mask = np.zeros((self.height, self.width), dtype=np.uint8)
        runout_mask[initiation_mask] = 255

        flow_dx = -0.55
        flow_dy = -0.83
        steps = int(runout_dist / 6)

        kernel_spread = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
        accumulated = runout_mask.copy()

        for s in range(1, steps + 1):
            shift_x = int(s * 6 * flow_dx)
            shift_y = int(s * 6 * flow_dy)
            M = np.float32([[1, 0, shift_x], [0, 1, shift_y]])
            shifted = cv2.warpAffine(runout_mask, M, (self.width, self.height))
            fan_ksize = max(3, int(5 + s * 1.2))
            if fan_ksize % 2 == 0: fan_ksize += 1
            fan_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (fan_ksize, fan_ksize))
            shifted = cv2.dilate(shifted, fan_kernel)
            accumulated = cv2.bitwise_or(accumulated, shifted)

        # Morphological smoothing
        accumulated = cv2.morphologyEx(accumulated, cv2.MORPH_CLOSE, kernel_spread)
        accumulated = cv2.GaussianBlur(accumulated, (9, 9), 2.5)
        final_mask = (accumulated >= 90).astype(np.uint8) * 255

        # Extract contours
        contours, _ = cv2.findContours(final_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        landslide_polygons: List[List[List[float]]] = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 400:
                epsilon = max(1.5, 0.0035 * cv2.arcLength(cnt, True))
                approx = cv2.approxPolyDP(cnt, epsilon, True)
                if len(approx) >= 3:
                    pts = approx.reshape(-1, 2).astype(float).tolist()
                    landslide_polygons.append(pts)

        displaced_pixels = int(np.sum(final_mask > 0))
        displaced_area_sqm = round(displaced_pixels * PIXEL_AREA_TO_SQ_METERS, 2)
        max_slope_val = round(float(np.max(slope_map[final_mask > 0])) if displaced_pixels > 0 else 24.5, 1)

        return {
            "disasterType": "LANDSLIDE",
            "intensity": intensity,
            "preset": preset,
            "seed": seed,
            "criticalSlopeDegrees": crit_slope,
            "maxSlopeDegrees": max_slope_val,
            "debrisDepthMeters": preset["debrisDepthMeters"],
            "displacedPixels": displaced_pixels,
            "displacedAreaSqMeters": displaced_area_sqm,
            "polygons": landslide_polygons,
            "mask": final_mask,
            "scarpCenter": {"x": round(scarp_center_x, 1), "y": round(scarp_center_y, 1)}
        }
