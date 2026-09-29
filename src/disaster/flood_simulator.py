"""
Flood Simulator Module for DepthWizard.
Generates spatially coherent, elevation-aware synthetic flood inundation zones
advancing inland from natural water boundaries (river/coastline),
including water depth estimation.
"""

import numpy as np
import cv2
from typing import Dict, Any, List, Optional
from .simulation_config import FLOOD_INTENSITIES, PIXEL_AREA_TO_SQ_METERS

class FloodSimulator:
    """
    Simulates a riverine / coastal storm surge flood scenario.
    Deterministic with seed for reproducible demonstrations.
    """

    def __init__(self, width: int = 1024, height: int = 1024):
        self.width = width
        self.height = height

    def generate_flood_scenario(
        self,
        intensity: str = "medium",
        seed: int = 42,
        direction: str = "north_to_south",
        ground_elevation: Optional[np.ndarray] = None,
        water_mask: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """
        Generates synthetic flood polygon and inundation mask.
        """
        if intensity not in FLOOD_INTENSITIES:
            intensity = "medium"

        preset = FLOOD_INTENSITIES[intensity]
        np.random.seed(seed)

        base_water_line = 460.0
        max_inland = preset["maxInlandPenetrationPixels"]
        surge_elev = preset["surgeElevationMeters"]

        # Generate harmonic shoreline surge front
        x_coords = np.arange(self.width, dtype=np.float32)
        wave1 = np.sin(x_coords * (2 * np.pi / 400.0) + (seed % 100)) * (max_inland * 0.25)
        wave2 = np.cos(x_coords * (2 * np.pi / 180.0) + (seed % 50)) * (max_inland * 0.15)
        wave3 = np.sin(x_coords * (2 * np.pi / 70.0) + (seed % 25)) * (max_inland * 0.08)

        surge_y = base_water_line + (max_inland * 0.65) + wave1 + wave2 + wave3

        flood_mask = np.zeros((self.height, self.width), dtype=np.uint8)
        y_indices = np.arange(self.height)[:, None]

        raw_inundation = y_indices <= surge_y[None, :]

        if ground_elevation is not None:
            elev_barrier = ground_elevation > (surge_elev + 1.2)
            low_channels = ground_elevation < (surge_elev * 0.8)
            raw_inundation = (raw_inundation & (~elev_barrier)) | (
                (y_indices <= (surge_y[None, :] + max_inland * 0.35)) & low_channels
            )

        flood_mask[raw_inundation] = 255

        # Morphological smoothing
        k_size = 11 if intensity == "high" else 7
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k_size, k_size))
        flood_mask = cv2.morphologyEx(flood_mask, cv2.MORPH_CLOSE, kernel)
        flood_mask = cv2.GaussianBlur(flood_mask, (9, 9), 3.0)
        flood_mask = (flood_mask >= 120).astype(np.uint8) * 255

        # Extract flood contours
        contours, _ = cv2.findContours(flood_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        flood_polygons: List[List[List[float]]] = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 500:
                epsilon = max(1.5, 0.003 * cv2.arcLength(cnt, True))
                approx = cv2.approxPolyDP(cnt, epsilon, True)
                if len(approx) >= 3:
                    pts = approx.reshape(-1, 2).astype(float).tolist()
                    flood_polygons.append(pts)

        flooded_pixels = int(np.sum(flood_mask > 0))
        flooded_area_sqm = round(flooded_pixels * PIXEL_AREA_TO_SQ_METERS, 2)

        # Depth grid calculation
        mean_depth = 1.2
        max_depth = surge_elev
        if ground_elevation is not None:
            depth_map = np.maximum(0.0, preset["waterSurfaceElevation"] - ground_elevation)
            depth_map[flood_mask == 0] = 0.0
            flooded_depths = depth_map[flood_mask > 0]
            if len(flooded_depths) > 0:
                mean_depth = round(float(np.mean(flooded_depths)), 2)
                max_depth = round(float(np.max(flooded_depths)), 2)

        return {
            "disasterType": "FLOOD",
            "intensity": intensity,
            "preset": preset,
            "seed": seed,
            "waterSurfaceElevation": preset["waterSurfaceElevation"],
            "surgeElevationMeters": surge_elev,
            "estimatedMeanDepthMeters": mean_depth,
            "estimatedMaxDepthMeters": max_depth,
            "floodedPixels": flooded_pixels,
            "floodedAreaSqMeters": flooded_area_sqm,
            "polygons": flood_polygons,
            "mask": flood_mask
        }
