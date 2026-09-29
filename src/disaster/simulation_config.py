"""
DepthWizard Disaster Simulation Configuration.
Defines constants, intensity presets, GSD metric scale factors,
and impact classification thresholds for all 4 disaster scenarios
(Flood, Wildfire, Cyclone, Landslide).
"""

# Ground Sample Distance (meters per pixel)
DEFAULT_GSD_METERS = 0.35
# Area factor: 1 pixel^2 in square meters (0.35 * 0.35 = 0.1225 m^2)
PIXEL_AREA_TO_SQ_METERS = DEFAULT_GSD_METERS * DEFAULT_GSD_METERS

# 1. Flood Intensity Presets
FLOOD_INTENSITIES = {
    "low": {
        "name": "Low Surge Flood",
        "description": "Minor coastal/river overflow affecting immediate low-lying banks",
        "surgeElevationMeters": 0.8,
        "maxInlandPenetrationPixels": 120,   # Approx 42m inland
        "waterSurfaceElevation": 0.8,
        "roughness": 0.05,
        "colorHex": "#0284c7"
    },
    "medium": {
        "name": "Moderate Surge Flood",
        "description": "Significant tidal/river surge inundating shoreline infrastructure and road corridors",
        "surgeElevationMeters": 2.2,
        "maxInlandPenetrationPixels": 280,   # Approx 98m inland
        "waterSurfaceElevation": 1.8,
        "roughness": 0.08,
        "colorHex": "#0369a1"
    },
    "high": {
        "name": "Severe Inundation Disaster",
        "description": "Catastrophic storm surge penetrating deep inland through natural drainage corridors",
        "surgeElevationMeters": 4.5,
        "maxInlandPenetrationPixels": 480,   # Approx 168m inland
        "waterSurfaceElevation": 3.2,
        "roughness": 0.12,
        "colorHex": "#075985"
    }
}

# 2. Wildfire Intensity Presets
WILDFIRE_INTENSITIES = {
    "low": {
        "name": "Low Intensity Ground Fire",
        "description": "Surface litter and underbrush burning with low flame length (~1.5m)",
        "spreadRadiusPixels": 140,           # Approx 49m
        "windSpeedKmh": 18.0,
        "firelineIntensityKwm": 850.0,
        "canopyBurnFactor": 0.35,
        "colorHex": "#f97316"
    },
    "medium": {
        "name": "Moderate Canopy Fire",
        "description": "Active crown fire spreading through tree canopies and adjacent structures (~3.5m flames)",
        "spreadRadiusPixels": 280,           # Approx 98m
        "windSpeedKmh": 38.0,
        "firelineIntensityKwm": 2400.0,
        "canopyBurnFactor": 0.70,
        "colorHex": "#ea580c"
    },
    "high": {
        "name": "Catastrophic Firestorm",
        "description": "Severe conflagration driven by extreme winds, creating rapid structural ignition (>6m flames)",
        "spreadRadiusPixels": 460,           # Approx 161m
        "windSpeedKmh": 65.0,
        "firelineIntensityKwm": 6500.0,
        "canopyBurnFactor": 0.95,
        "colorHex": "#c2410c"
    }
}

# 3. Cyclone Intensity Presets (Holland Vortex Parameters)
CYCLONE_INTENSITIES = {
    "low": {
        "name": "Category 1 Tropical Cyclone",
        "description": "Gale force winds causing minor roof sheet, foliage, and billboard damage",
        "maxWindSpeedKmh": 125.0,
        "radiusMaxWindsPixels": 180,
        "cycloneRadiusPixels": 380,
        "centralPressureHpa": 985.0,
        "colorHex": "#8b5cf6"
    },
    "medium": {
        "name": "Category 3 Severe Cyclone",
        "description": "Devastating winds capable of structural roof failure, uprooting trees, and downed powerlines",
        "maxWindSpeedKmh": 185.0,
        "radiusMaxWindsPixels": 220,
        "cycloneRadiusPixels": 520,
        "centralPressureHpa": 955.0,
        "colorHex": "#7c3aed"
    },
    "high": {
        "name": "Category 5 Super Cyclone",
        "description": "Extremely catastrophic sustained winds causing catastrophic structural and canopy destruction",
        "maxWindSpeedKmh": 255.0,
        "radiusMaxWindsPixels": 260,
        "cycloneRadiusPixels": 700,
        "centralPressureHpa": 915.0,
        "colorHex": "#6d28d9"
    }
}

# 4. Landslide Intensity Presets
LANDSLIDE_INTENSITIES = {
    "low": {
        "name": "Minor Slope Slump",
        "description": "Localized shallow soil slip along exposed embankments and steep cuts",
        "criticalSlopeDegrees": 22.0,
        "runoutDistancePixels": 120,
        "debrisDepthMeters": 0.9,
        "colorHex": "#d97706"
    },
    "medium": {
        "name": "Debris Flow & Scour",
        "description": "Rapid mass movement carrying mud, loose boulders, and soil down drainage gullies",
        "criticalSlopeDegrees": 16.0,
        "runoutDistancePixels": 260,
        "debrisDepthMeters": 2.2,
        "colorHex": "#b45309"
    },
    "high": {
        "name": "Major Deep-Seated Landslide",
        "description": "Catastrophic hillside failure generating extensive debris field burying structures",
        "criticalSlopeDegrees": 11.0,
        "runoutDistancePixels": 440,
        "debrisDepthMeters": 4.5,
        "colorHex": "#92400e"
    }
}

# Unified Impact Classification Rules based on Footprint Exposure Percentage
IMPACT_CLASSES = {
    "NONE": {
        "label": "No Impact",
        "minExposure": 0.0,
        "maxExposure": 0.0,
        "color": "#64748b",      # Slate grey
        "badgeClass": "badge-none",
        "description": "No hazard footprint entered structure footprint."
    },
    "LOW": {
        "label": "Low Impact",
        "minExposure": 0.001,
        "maxExposure": 25.0,
        "color": "#eab308",      # Soft Yellow
        "badgeClass": "badge-low",
        "description": "Minor perimeter exposure (1-25% footprint exposed)."
    },
    "MODERATE": {
        "label": "Moderate Impact",
        "minExposure": 25.0,
        "maxExposure": 50.0,
        "color": "#f97316",      # Amber / Orange
        "badgeClass": "badge-mod",
        "description": "Partial structure exposure (25-50% footprint exposed)."
    },
    "HIGH": {
        "label": "High Impact",
        "minExposure": 50.0,
        "maxExposure": 75.0,
        "color": "#ef4444",      # Red-Orange
        "badgeClass": "badge-high",
        "description": "Extensive structure exposure (50-75% footprint exposed)."
    },
    "CRITICAL": {
        "label": "Critical Impact",
        "minExposure": 75.0,
        "maxExposure": 100.0,
        "color": "#dc2626",      # Deep Crimson
        "badgeClass": "badge-crit",
        "description": "Severe spatial inundation or direct impact (>75% footprint exposed)."
    }
}

# Universal disclaimer for synthetic post-disaster simulations
SYNTHETIC_SIMULATION_DISCLAIMER = (
    "Synthetic Disaster Scenario: Simulation generated from pre-disaster single-view baseline. "
    "Calculated exposure represents spatial footprint overlap with the simulated hazard zone, "
    "not observed structural failure or collapsed integrity."
)
