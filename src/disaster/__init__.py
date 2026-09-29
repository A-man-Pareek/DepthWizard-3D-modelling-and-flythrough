"""
DepthWizard Disaster Simulation Package.
Provides hazard generation, damage calculation, impact classification,
and disaster impact analytics for 4 hazard types (Flood, Wildfire, Cyclone, Landslide).
"""

from .simulation_config import (
    DEFAULT_GSD_METERS,
    PIXEL_AREA_TO_SQ_METERS,
    FLOOD_INTENSITIES,
    WILDFIRE_INTENSITIES,
    CYCLONE_INTENSITIES,
    LANDSLIDE_INTENSITIES,
    IMPACT_CLASSES,
    SYNTHETIC_SIMULATION_DISCLAIMER
)
from .disaster_types import (
    DisasterType,
    DISASTER_REGISTRY,
    get_active_disaster_types,
    get_all_disaster_types
)
from .flood_simulator import FloodSimulator
from .wildfire_simulator import WildfireSimulator
from .cyclone_simulator import CycloneSimulator
from .landslide_simulator import LandslideSimulator
from .damage_calculator import DamageCalculator
from .impact_classifier import ImpactClassifier
from .disaster_service import DisasterService

__all__ = [
    "DEFAULT_GSD_METERS",
    "PIXEL_AREA_TO_SQ_METERS",
    "FLOOD_INTENSITIES",
    "WILDFIRE_INTENSITIES",
    "CYCLONE_INTENSITIES",
    "LANDSLIDE_INTENSITIES",
    "IMPACT_CLASSES",
    "SYNTHETIC_SIMULATION_DISCLAIMER",
    "DisasterType",
    "DISASTER_REGISTRY",
    "get_active_disaster_types",
    "get_all_disaster_types",
    "FloodSimulator",
    "WildfireSimulator",
    "CycloneSimulator",
    "LandslideSimulator",
    "DamageCalculator",
    "ImpactClassifier",
    "DisasterService"
]
