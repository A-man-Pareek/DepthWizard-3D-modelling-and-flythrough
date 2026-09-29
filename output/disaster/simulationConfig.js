/**
 * DepthWizard Disaster Simulation Configuration (Client-side)
 * Constants, intensity presets for 4 hazards, metric conversions, and impact tiers.
 */

const SimulationConfig = {
    // Ground Sample Distance (meters per pixel)
    DEFAULT_GSD_METERS: 0.35,
    // 1 pixel^2 = 0.1225 m^2
    PIXEL_AREA_TO_SQ_METERS: 0.35 * 0.35,

    // 1. Flood Intensity Presets
    FLOOD_INTENSITIES: {
        low: {
            name: "Low Surge Flood",
            description: "Minor coastal/river overflow affecting immediate low-lying shoreline",
            surgeElevationMeters: 0.8,
            maxInlandPenetrationPixels: 120,   // Approx 42m inland
            waterSurfaceElevation: 0.8,
            roughness: 0.05,
            color: 0x0284c7,
            colorHex: "#0284c7"
        },
        medium: {
            name: "Moderate Surge Flood",
            description: "Significant tidal/river surge inundating shoreline infrastructure and road corridors",
            surgeElevationMeters: 2.2,
            maxInlandPenetrationPixels: 280,   // Approx 98m inland
            waterSurfaceElevation: 1.8,
            roughness: 0.08,
            color: 0x0369a1,
            colorHex: "#0369a1"
        },
        high: {
            name: "Severe Inundation Disaster",
            description: "Catastrophic storm surge penetrating deep inland through natural drainage corridors",
            surgeElevationMeters: 4.5,
            maxInlandPenetrationPixels: 480,   // Approx 168m inland
            waterSurfaceElevation: 3.2,
            roughness: 0.12,
            color: 0x075985,
            colorHex: "#075985"
        }
    },

    // 2. Wildfire Intensity Presets
    WILDFIRE_INTENSITIES: {
        low: {
            name: "Low Surface Fire",
            description: "Ground fire consuming underbrush with short flame lengths (~1.5m)",
            spreadRadiusPixels: 140,           // Approx 49m
            windSpeedKmh: 18.0,
            firelineIntensityKwm: 850.0,
            canopyBurnFactor: 0.35,
            color: 0xf97316,
            colorHex: "#f97316"
        },
        medium: {
            name: "Moderate Crown Fire",
            description: "Active canopy fire spreading through tree crowns and nearby buildings (~3.5m flames)",
            spreadRadiusPixels: 280,           // Approx 98m
            windSpeedKmh: 38.0,
            firelineIntensityKwm: 2400.0,
            canopyBurnFactor: 0.70,
            color: 0xea580c,
            colorHex: "#ea580c"
        },
        high: {
            name: "Severe Firestorm",
            description: "Extreme wind-driven conflagration causing rapid structural ignition (>6m flames)",
            spreadRadiusPixels: 460,           // Approx 161m
            windSpeedKmh: 65.0,
            firelineIntensityKwm: 6500.0,
            canopyBurnFactor: 0.95,
            color: 0xc2410c,
            colorHex: "#c2410c"
        }
    },

    // 3. Cyclone Intensity Presets
    CYCLONE_INTENSITIES: {
        low: {
            name: "Category 1 Tropical Cyclone",
            description: "Gale-force winds causing minor roof sheet, foliage, and sign damage",
            maxWindSpeedKmh: 125.0,
            radiusMaxWindsPixels: 180,
            cycloneRadiusPixels: 380,
            centralPressureHpa: 985.0,
            color: 0x8b5cf6,
            colorHex: "#8b5cf6"
        },
        medium: {
            name: "Category 3 Severe Cyclone",
            description: "Devastating winds capable of structural roof failure and uprooting trees",
            maxWindSpeedKmh: 185.0,
            radiusMaxWindsPixels: 220,
            cycloneRadiusPixels: 520,
            centralPressureHpa: 955.0,
            color: 0x7c3aed,
            colorHex: "#7c3aed"
        },
        high: {
            name: "Category 5 Super Cyclone",
            description: "Extremely catastrophic sustained winds causing widespread structural shear",
            maxWindSpeedKmh: 255.0,
            radiusMaxWindsPixels: 260,
            cycloneRadiusPixels: 700,
            centralPressureHpa: 915.0,
            color: 0x6d28d9,
            colorHex: "#6d28d9"
        }
    },

    // 4. Landslide Intensity Presets
    LANDSLIDE_INTENSITIES: {
        low: {
            name: "Minor Slope Slump",
            description: "Localized shallow soil movement along exposed road cuts and steep banks",
            criticalSlopeDegrees: 22.0,
            runoutDistancePixels: 120,
            debrisDepthMeters: 0.9,
            color: 0xd97706,
            colorHex: "#d97706"
        },
        medium: {
            name: "Debris Flow & Scour",
            description: "Rapid mass movement carrying mud and loose soil down drainage gullies",
            criticalSlopeDegrees: 16.0,
            runoutDistancePixels: 260,
            debrisDepthMeters: 2.2,
            color: 0xb45309,
            colorHex: "#b45309"
        },
        high: {
            name: "Major Deep-Seated Landslide",
            description: "Catastrophic hillside failure generating extensive debris field burying structures",
            criticalSlopeDegrees: 11.0,
            runoutDistancePixels: 440,
            debrisDepthMeters: 4.5,
            color: 0x92400e,
            colorHex: "#92400e"
        }
    },

    // Unified Impact Classification Rules
    IMPACT_CLASSES: {
        NONE: {
            tier: "NONE",
            label: "No Impact",
            minExposure: 0.0,
            maxExposure: 0.0,
            colorHex: "#64748b",
            colorThree: 0x64748b,
            badgeClass: "badge-none",
            description: "No hazard entered structure footprint."
        },
        LOW: {
            tier: "LOW",
            label: "Low Impact",
            minExposure: 0.001,
            maxExposure: 25.0,
            colorHex: "#eab308",
            colorThree: 0xeab308,
            badgeClass: "badge-low",
            description: "Minor perimeter exposure (1-25% footprint exposed)."
        },
        MODERATE: {
            tier: "MODERATE",
            label: "Moderate Impact",
            minExposure: 25.0,
            maxExposure: 50.0,
            colorHex: "#f97316",
            colorThree: 0xf97316,
            badgeClass: "badge-mod",
            description: "Partial structure exposure (25-50% footprint exposed)."
        },
        HIGH: {
            tier: "HIGH",
            label: "High Impact",
            minExposure: 50.0,
            maxExposure: 75.0,
            colorHex: "#ef4444",
            colorThree: 0xef4444,
            badgeClass: "badge-high",
            description: "Extensive structure exposure (50-75% footprint exposed)."
        },
        CRITICAL: {
            tier: "CRITICAL",
            label: "Critical Impact",
            minExposure: 75.0,
            maxExposure: 100.0,
            colorHex: "#dc2626",
            colorThree: 0xdc2626,
            badgeClass: "badge-crit",
            description: "Severe direct impact (>75% footprint exposed)."
        }
    },

    SYNTHETIC_SIMULATION_DISCLAIMER: "Synthetic Disaster Scenario: Simulation generated from pre-disaster single-view baseline. Calculated exposure represents spatial footprint overlap with the simulated hazard zone, not observed structural failure or collapsed integrity."
};

if (typeof module !== 'undefined' && module.exports) {
    module.exports = SimulationConfig;
}
