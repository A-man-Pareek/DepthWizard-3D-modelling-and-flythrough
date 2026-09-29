/**
 * DepthWizard Disaster Types Registry (Client-side)
 * Extensible catalog of 4 hazard scenarios with accent colors and schemas.
 */

const DisasterTypes = {
    FLOOD: {
        key: "FLOOD",
        label: "Riverine & Coastal Flood",
        shortName: "Flood",
        icon: "🌊",
        accentColor: "#0284c7",
        accentGlow: "rgba(2, 132, 199, 0.4)",
        description: "Surge-driven water inundation advancing from shoreline and drainage corridors into low terrain.",
        legendType: "depth",
        legendTitle: "Flood Depth",
        legendLevels: ["0.2 m", "0.8 m", "1.5 m", "2.5 m", "3.5 m+"],
        isActive: true
    },
    WILDFIRE: {
        key: "WILDFIRE",
        label: "Wildfire / Urban Interface",
        shortName: "Wildfire",
        icon: "🔥",
        accentColor: "#ea580c",
        accentGlow: "rgba(234, 88, 12, 0.4)",
        description: "Vegetation-driven thermal spread advancing through canopy and adjacent structures.",
        legendType: "intensity",
        legendTitle: "Fire Intensity",
        legendLevels: ["Low (Surface)", "Moderate", "High (Canopy)", "Severe Conflagration"],
        isActive: true
    },
    CYCLONE: {
        key: "CYCLONE",
        label: "Cyclone / Extreme Wind Swath",
        shortName: "Cyclone",
        icon: "🌀",
        accentColor: "#7c3aed",
        accentGlow: "rgba(124, 58, 237, 0.4)",
        description: "High-velocity rotational wind vortex causing distributed rooftop and infrastructure shear.",
        legendType: "wind",
        legendTitle: "Wind Speed",
        legendLevels: ["65 km/h (Gale)", "120 km/h (Cat 1)", "180 km/h (Cat 3)", "250 km/h (Cat 5)"],
        isActive: true
    },
    LANDSLIDE: {
        key: "LANDSLIDE",
        label: "Slope Failure / Landslide",
        shortName: "Landslide",
        icon: "⛰️",
        accentColor: "#b45309",
        accentGlow: "rgba(180, 83, 9, 0.4)",
        description: "Downslope mass displacement of soil and debris along steep elevation gradients.",
        legendType: "slope",
        legendTitle: "Debris / Slope",
        legendLevels: ["Low Scour", "Debris Fan", "Deep Runout", "Mass Failure"],
        isActive: true
    }
};

if (typeof module !== 'undefined' && module.exports) {
    module.exports = DisasterTypes;
}
