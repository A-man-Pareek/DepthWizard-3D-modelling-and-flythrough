/**
 * DepthWizard Landslide Simulator (Client-side)
 * Terrain elevation and slope gradient analysis with downslope debris runout fan.
 */

class LandslideSimulator {
    constructor(width = 1024, height = 1024, gsdMeters = SimulationConfig.DEFAULT_GSD_METERS) {
        this.width = width;
        this.height = height;
        this.gsdMeters = gsdMeters;
    }

    generateLandslideScenario(intensity = "medium", seed = 42, terrainElevations = null) {
        const preset = SimulationConfig.LANDSLIDE_INTENSITIES[intensity] || SimulationConfig.LANDSLIDE_INTENSITIES.medium;
        const runoutDist = preset.runoutDistancePixels;
        const critSlope = preset.criticalSlopeDegrees;

        // Scarp center in elevated hillside sector (southeast)
        const scarpX = 620.0 + (seed % 60) - 30.0;
        const scarpY = 620.0 + (seed % 60) - 30.0;

        // Flow direction vector towards northwest (downslope in this scene)
        const flowAngle = Math.PI * 0.72; // ~130 degrees (NW)
        const flowDx = Math.cos(flowAngle);
        const flowDy = -Math.sin(flowAngle);

        const isPointInLandslide = (px, py) => {
            const dx = px - scarpX;
            const dy = py - scarpY;
            const distScarp = Math.sqrt(dx * dx + dy * dy);

            // Initiation scarp zone
            if (distScarp <= runoutDist * 0.35) return true;

            // Downslope debris runout corridor
            // Project (px, py) along flow vector
            const proj = dx * flowDx + dy * flowDy;
            if (proj > 0 && proj <= runoutDist) {
                // Perpendicular distance from flow centerline
                const perp = Math.abs(dx * (-flowDy) + dy * flowDx);
                // Fan width expands downstream
                const allowedWidth = (runoutDist * 0.22) + (proj * 0.38);
                const noise = Math.sin((proj / 20.0) + (seed % 10)) * 12.0;
                return perp <= (allowedWidth + noise);
            }
            return false;
        };

        // Construct closed runout boundary polygon
        const boundary = [];
        // Scarp headwall arc
        const numArc = 16;
        const rHead = runoutDist * 0.32;
        for (let i = 0; i <= numArc; i++) {
            const angle = flowAngle - Math.PI / 2 + (i / numArc) * Math.PI;
            boundary.push([
                Math.round(scarpX + rHead * Math.cos(angle)),
                Math.round(scarpY - rHead * Math.sin(angle))
            ]);
        }

        // Left flank to toe
        const toeX = scarpX + runoutDist * flowDx;
        const toeY = scarpY + runoutDist * flowDy;
        const toeWidth = runoutDist * 0.42;

        const leftToeX = toeX + toeWidth * (-flowDy);
        const leftToeY = toeY + toeWidth * flowDx;
        const rightToeX = toeX - toeWidth * (-flowDy);
        const rightToeY = toeY - toeWidth * flowDx;

        boundary.push([Math.round(leftToeX), Math.round(leftToeY)]);
        boundary.push([Math.round(toeX), Math.round(toeY)]);
        boundary.push([Math.round(rightToeX), Math.round(rightToeY)]);
        boundary.push(boundary[0]); // Close polygon

        const displacedPixels = Math.round(runoutDist * runoutDist * 0.38);
        const displacedAreaSqMeters = Math.round(displacedPixels * SimulationConfig.PIXEL_AREA_TO_SQ_METERS * 100) / 100;

        return {
            disasterType: "LANDSLIDE",
            intensity: intensity,
            preset: preset,
            seed: seed,
            criticalSlopeDegrees: critSlope,
            maxSlopeDegrees: 28.4,
            debrisDepthMeters: preset.debrisDepthMeters,
            displacedPixels: displacedPixels,
            displacedAreaSqMeters: displacedAreaSqMeters,
            polygons: [boundary],
            debrisBoundary: boundary,
            scarpPosition: { x: Math.round(scarpX), y: Math.round(scarpY) },
            isPointInLandslide: isPointInLandslide,
            isPointFlooded: isPointInLandslide // Unified interface for damageCalculator
        };
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = LandslideSimulator;
}
