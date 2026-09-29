/**
 * DepthWizard Flood Simulator (Client-side)
 * Generates spatially coherent synthetic flood polygons and wave fronts.
 */

class FloodSimulator {
    constructor(width = 1024, height = 1024) {
        this.width = width;
        this.height = height;
    }

    /**
     * Computes the flood frontier Y coordinate for a given X coordinate.
     */
    getSurgeY(x, maxInland, seed) {
        const baseWaterLine = 460.0;
        const wave1 = Math.sin(x * (2 * Math.PI / 400.0) + (seed % 100)) * (maxInland * 0.25);
        const wave2 = Math.cos(x * (2 * Math.PI / 180.0) + (seed % 50)) * (maxInland * 0.15);
        const wave3 = Math.sin(x * (2 * Math.PI / 70.0) + (seed % 25)) * (maxInland * 0.08);
        return baseWaterLine + (maxInland * 0.65) + wave1 + wave2 + wave3;
    }

    /**
     * Generates the synthetic flood polygon and front boundary.
     */
    generateFloodScenario(intensity = "medium", seed = 42) {
        const preset = SimulationConfig.FLOOD_INTENSITIES[intensity] || SimulationConfig.FLOOD_INTENSITIES.medium;
        const maxInland = preset.maxInlandPenetrationPixels;

        // Sample the surge boundary line from x = 0 to x = 1024
        const surgeBoundaryLine = [];
        const numSteps = 128;
        const step = this.width / numSteps;

        for (let i = 0; i <= numSteps; i++) {
            const x = Math.min(this.width, i * step);
            const y = Math.min(this.height - 2, Math.max(10, this.getSurgeY(x, maxInland, seed)));
            surgeBoundaryLine.push([x, y]);
        }

        // Construct closed flood polygon enclosing top water boundary down to surge boundary:
        // (0,0) -> (1024, 0) -> (1024, y_end) -> surge line backwards -> (0, y_start) -> (0, 0)
        const floodPolygon = [
            [0, 0],
            [this.width, 0],
            [this.width, surgeBoundaryLine[surgeBoundaryLine.length - 1][1]]
        ];

        for (let i = surgeBoundaryLine.length - 1; i >= 0; i--) {
            floodPolygon.push([surgeBoundaryLine[i][0], surgeBoundaryLine[i][1]]);
        }
        floodPolygon.push([0, surgeBoundaryLine[0][1]]);
        floodPolygon.push([0, 0]);

        // Approximate total flooded area: integrate surge line across width
        let totalPixelArea = 0;
        for (let i = 0; i < surgeBoundaryLine.length - 1; i++) {
            const x0 = surgeBoundaryLine[i][0];
            const y0 = surgeBoundaryLine[i][1];
            const x1 = surgeBoundaryLine[i + 1][0];
            const y1 = surgeBoundaryLine[i + 1][1];
            const dx = x1 - x0;
            const avgY = (y0 + y1) / 2.0;
            totalPixelArea += dx * avgY;
        }

        const floodedPixels = Math.round(totalPixelArea);
        const floodedAreaSqMeters = Math.round(floodedPixels * SimulationConfig.PIXEL_AREA_TO_SQ_METERS * 100) / 100;

        return {
            disasterType: "FLOOD",
            intensity: intensity,
            preset: preset,
            seed: seed,
            waterSurfaceElevation: preset.waterSurfaceElevation,
            surgeElevationMeters: preset.surgeElevationMeters,
            floodedPixels: floodedPixels,
            floodedAreaSqMeters: floodedAreaSqMeters,
            polygons: [floodPolygon],
            surgeBoundaryLine: surgeBoundaryLine,
            isPointFlooded: (px, py) => {
                const frontierY = this.getSurgeY(px, maxInland, seed);
                return py <= frontierY;
            }
        };
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = FloodSimulator;
}
