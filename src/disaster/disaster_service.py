"""
Disaster Service for DepthWizard.
Unified orchestrator coordinating hazard scenario generation (Flood, Wildfire,
Cyclone, Landslide), geometric damage intersection, impact classification,
and comprehensive multi-hazard reporting.
"""

from typing import Dict, Any, List, Optional
import numpy as np
from .simulation_config import (
    DEFAULT_GSD_METERS,
    SYNTHETIC_SIMULATION_DISCLAIMER
)
from .disaster_types import DISASTER_REGISTRY
from .flood_simulator import FloodSimulator
from .wildfire_simulator import WildfireSimulator
from .cyclone_simulator import CycloneSimulator
from .landslide_simulator import LandslideSimulator
from .damage_calculator import DamageCalculator
from .impact_classifier import ImpactClassifier

class DisasterService:
    """
    High-level facade coordinating all disaster impact assessments.
    """

    def __init__(self, gsd_meters: float = DEFAULT_GSD_METERS, width: int = 1024, height: int = 1024):
        self.gsd_meters = gsd_meters
        self.width = width
        self.height = height
        self.flood_sim = FloodSimulator(width, height)
        self.wildfire_sim = WildfireSimulator(width, height)
        self.cyclone_sim = CycloneSimulator(width, height)
        self.landslide_sim = LandslideSimulator(width, height, gsd_meters)
        self.calculator = DamageCalculator(gsd_meters)
        self.classifier = ImpactClassifier()

    def run_simulation(
        self,
        disaster_type: str,
        buildings: List[Dict[str, Any]],
        intensity: str = "medium",
        seed: int = 42,
        ground_elevation: Optional[np.ndarray] = None,
        vegetation_mask: Optional[np.ndarray] = None,
        road_mask: Optional[np.ndarray] = None,
        water_mask: Optional[np.ndarray] = None,
        extra_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes a complete disaster scenario based on disaster_type.
        """
        disaster_type = disaster_type.upper()
        if disaster_type not in DISASTER_REGISTRY:
            disaster_type = "FLOOD"

        extra = extra_params or {}

        # 1. Generate Hazard Scenario
        if disaster_type == "FLOOD":
            hazard_data = self.flood_sim.generate_flood_scenario(
                intensity=intensity,
                seed=seed,
                ground_elevation=ground_elevation,
                water_mask=water_mask
            )
        elif disaster_type == "WILDFIRE":
            hazard_data = self.wildfire_sim.generate_wildfire_scenario(
                intensity=intensity,
                seed=seed,
                wind_direction_deg=extra.get("windDirectionDeg", 45.0),
                vegetation_mask=vegetation_mask,
                ground_elevation=ground_elevation
            )
        elif disaster_type == "CYCLONE":
            hazard_data = self.cyclone_sim.generate_cyclone_scenario(
                intensity=intensity,
                seed=seed,
                eye_x=extra.get("eyeX"),
                eye_y=extra.get("eyeY")
            )
        elif disaster_type == "LANDSLIDE":
            hazard_data = self.landslide_sim.generate_landslide_scenario(
                intensity=intensity,
                seed=seed,
                ground_elevation=ground_elevation
            )
        else:
            raise ValueError(f"Unknown disaster type: {disaster_type}")

        hazard_mask = hazard_data["mask"]

        # 2. Intersect with Building Footprints
        assessed_raw = self.calculator.assess_all_buildings(buildings, hazard_mask)

        # 3. Classify Impact Tiers
        assessed_buildings = self.classifier.classify_buildings(assessed_raw)

        # 4. Assess Infrastructure and Environment
        infra_env = self.calculator.assess_infrastructure_and_environment(
            hazard_mask, road_mask=road_mask, vegetation_mask=vegetation_mask
        )

        # 5. Compute Aggregate Statistics
        total_buildings = len(assessed_buildings)
        affected_buildings = [b for b in assessed_buildings if b["isAffected"]]
        affected_count = len(affected_buildings)
        unaffected_count = total_buildings - affected_count

        total_affected_footprint_sqm = round(
            sum(b["affectedAreaSqMeters"] for b in affected_buildings), 2
        )

        high_crit_count = sum(
            1 for b in assessed_buildings if b["impactTier"] in ("HIGH", "CRITICAL")
        )

        avg_exposure = (
            round(sum(b["exposurePercentage"] for b in affected_buildings) / affected_count, 1)
            if affected_count > 0 else 0.0
        )

        tier_counts = {"NONE": 0, "LOW": 0, "MODERATE": 0, "HIGH": 0, "CRITICAL": 0}
        for b in assessed_buildings:
            tier = b["impactTier"]
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        affected_buildings.sort(key=lambda b: b["exposurePercentage"], reverse=True)

        hazard_area_sqm = (
            hazard_data.get("floodedAreaSqMeters") or
            hazard_data.get("burnedAreaSqMeters") or
            hazard_data.get("impactedAreaSqMeters") or
            hazard_data.get("displacedAreaSqMeters") or 0.0
        )

        type_meta = DISASTER_REGISTRY[disaster_type].to_dict()

        return {
            "scenario": {
                "name": "Synthetic Disaster Scenario",
                "disasterType": disaster_type,
                "disasterMeta": type_meta,
                "intensity": intensity,
                "intensityPreset": hazard_data.get("preset", {}),
                "seed": seed,
                "disclaimer": "Simulation — not a real post-disaster observation",
                "fullDisclaimer": SYNTHETIC_SIMULATION_DISCLAIMER
            },
            "hazardLayer": {
                "polygons": hazard_data.get("polygons", []),
                "hazardAreaSqMeters": hazard_area_sqm,
                "data": {k: v for k, v in hazard_data.items() if k not in ("mask", "polygons")}
            },
            "summaryStatistics": {
                "totalBuildings": total_buildings,
                "affectedBuildings": affected_count,
                "unaffectedBuildings": unaffected_count,
                "totalHazardAreaSqMeters": hazard_area_sqm,
                "totalAffectedBuildingFootprintSqMeters": total_affected_footprint_sqm,
                "highAndCriticalCount": high_crit_count,
                "averageExposurePercentage": avg_exposure,
                "tierBreakdown": tier_counts,
                "affectedRoadsLengthMeters": infra_env["affectedRoadsLengthMeters"],
                "affectedVegetationAreaSqMeters": infra_env["affectedVegetationAreaSqMeters"],
                "estimatedPopulationImpact": "Unavailable (Requires Census Layer)"
            },
            "assessedBuildings": assessed_buildings,
            "affectedBuildingsList": affected_buildings
        }

    # Backward compatibility
    def run_flood_simulation(self, buildings, intensity="medium", seed=42, ground_elevation=None, water_mask=None):
        return self.run_simulation("FLOOD", buildings, intensity=intensity, seed=seed, ground_elevation=ground_elevation, water_mask=water_mask)
