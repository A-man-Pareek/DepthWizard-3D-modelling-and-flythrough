"""
Disaster Types Registry for DepthWizard.
Provides an extensible framework to register and configure different
hazard simulation modules (Flood, Wildfire, Cyclone, Landslide).
"""

from typing import Dict, Any

class DisasterType:
    def __init__(self, key: str, label: str, icon: str, description: str, color_hex: str, is_active: bool = True):
        self.key = key
        self.label = label
        self.icon = icon
        self.description = description
        self.color_hex = color_hex
        self.is_active = is_active

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "icon": self.icon,
            "description": self.description,
            "colorHex": self.color_hex,
            "isActive": self.is_active
        }

DISASTER_REGISTRY: Dict[str, DisasterType] = {
    "FLOOD": DisasterType(
        key="FLOOD",
        label="Riverine & Coastal Flood",
        icon="🌊",
        description="Surge-driven water inundation advancing from shoreline and drainage corridors into low terrain.",
        color_hex="#0284c7",
        is_active=True
    ),
    "WILDFIRE": DisasterType(
        key="WILDFIRE",
        label="Wildfire / Urban Interface",
        icon="🔥",
        description="Vegetation-driven thermal spread advancing through canopy and adjacent structures.",
        color_hex="#ea580c",
        is_active=True
    ),
    "CYCLONE": DisasterType(
        key="CYCLONE",
        label="Cyclone / Extreme Wind Swath",
        icon="🌀",
        description="High-velocity rotational wind vortex causing distributed rooftop and infrastructure shear.",
        color_hex="#7c3aed",
        is_active=True
    ),
    "LANDSLIDE": DisasterType(
        key="LANDSLIDE",
        label="Slope Failure / Landslide",
        icon="⛰️",
        description="Downslope mass displacement of soil and debris along steep elevation gradients.",
        color_hex="#b45309",
        is_active=True
    )
}

def get_active_disaster_types() -> Dict[str, Dict[str, Any]]:
    return {k: v.to_dict() for k, v in DISASTER_REGISTRY.items() if v.is_active}

def get_all_disaster_types() -> Dict[str, Dict[str, Any]]:
    return {k: v.to_dict() for k, v in DISASTER_REGISTRY.items()}
