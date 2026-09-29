"""
Damage & Exposure Calculator for DepthWizard.
Performs 2D spatial footprint intersection between synthetic hazard zones
and building footprints, road infrastructure, and environmental vegetation.
"""

import numpy as np
import cv2
from typing import Dict, Any, List, Optional
from .simulation_config import PIXEL_AREA_TO_SQ_METERS, DEFAULT_GSD_METERS

class DamageCalculator:
    """
    Computes spatial exposure metrics for structures, roads, and environment.
    """

    def __init__(self, gsd_meters: float = DEFAULT_GSD_METERS):
        self.gsd_meters = gsd_meters
        self.sq_meters_per_pixel = gsd_meters * gsd_meters

    def calculate_building_exposure(
        self,
        building: Dict[str, Any],
        hazard_mask: np.ndarray
    ) -> Dict[str, Any]:
        """
        Calculates exact footprint intersection with the hazard mask.
        """
        bx, by, bw, bh = building.get("bbox", [0, 0, hazard_mask.shape[1], hazard_mask.shape[0]])
        pad = 2
        H, W = hazard_mask.shape
        x0 = max(0, bx - pad)
        y0 = max(0, by - pad)
        x1 = min(W, bx + bw + pad)
        y1 = min(H, by + bh + pad)

        roi_w = x1 - x0
        roi_h = y1 - y0

        if roi_w <= 0 or roi_h <= 0:
            return {
                "affectedPixels": 0,
                "affectedAreaSqMeters": 0.0,
                "totalAreaSqMeters": round(building.get("areaPixels", 0) * self.sq_meters_per_pixel, 2),
                "exposurePercentage": 0.0,
                "isAffected": False
            }

        b_roi = np.zeros((roi_h, roi_w), dtype=np.uint8)
        poly = np.array(building["polygon"], dtype=np.int32) - np.array([x0, y0], dtype=np.int32)
        cv2.fillPoly(b_roi, [poly], 255)

        for hole in building.get("holes", []):
            if len(hole) >= 3:
                h_poly = np.array(hole, dtype=np.int32) - np.array([x0, y0], dtype=np.int32)
                cv2.fillPoly(b_roi, [h_poly], 0)

        f_roi = hazard_mask[y0:y1, x0:x1]

        intersection = (b_roi == 255) & (f_roi > 0)
        affected_pixels = int(np.sum(intersection))
        total_pixels = building.get("areaPixels", int(np.sum(b_roi == 255)))

        if total_pixels <= 0:
            total_pixels = max(1, affected_pixels)

        exposure_pct = min(100.0, max(0.0, (affected_pixels / float(total_pixels)) * 100.0))
        affected_sqm = round(affected_pixels * self.sq_meters_per_pixel, 2)
        total_sqm = round(total_pixels * self.sq_meters_per_pixel, 2)

        return {
            "affectedPixels": affected_pixels,
            "affectedAreaSqMeters": affected_sqm,
            "totalAreaSqMeters": total_sqm,
            "exposurePercentage": round(exposure_pct, 2),
            "isAffected": affected_pixels > 0
        }

    def assess_all_buildings(
        self,
        buildings: List[Dict[str, Any]],
        hazard_mask: np.ndarray
    ) -> List[Dict[str, Any]]:
        """
        Assesses all buildings in the scene against the hazard mask.
        """
        results = []
        for b in buildings:
            exposure_info = self.calculate_building_exposure(b, hazard_mask)
            b_result = {**b, **exposure_info}
            results.append(b_result)
        return results

    def assess_infrastructure_and_environment(
        self,
        hazard_mask: np.ndarray,
        road_mask: Optional[np.ndarray] = None,
        vegetation_mask: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """
        Calculates impact on road networks and vegetation/environmental canopy.
        """
        metrics = {
            "affectedRoadsPixels": 0,
            "affectedRoadsLengthMeters": 0.0,
            "affectedVegetationPixels": 0,
            "affectedVegetationAreaSqMeters": 0.0
        }

        if road_mask is not None:
            r_overlap = (road_mask > 0) & (hazard_mask > 0)
            r_pixels = int(np.sum(r_overlap))
            # Average road width ~5 pixels, so centerline length ~ pixels / 5 * 0.35m
            r_meters = round(r_pixels * 0.07, 1)
            metrics["affectedRoadsPixels"] = r_pixels
            metrics["affectedRoadsLengthMeters"] = r_meters

        if vegetation_mask is not None:
            v_overlap = (vegetation_mask > 0) & (hazard_mask > 0)
            v_pixels = int(np.sum(v_overlap))
            v_sqm = round(v_pixels * self.sq_meters_per_pixel, 2)
            metrics["affectedVegetationPixels"] = v_pixels
            metrics["affectedVegetationAreaSqMeters"] = v_sqm

        return metrics
