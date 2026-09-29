/**
 * DepthWizard Damage & Exposure Calculator (Client-side)
 * Computes 2D spatial footprint intersection and exposure percentages.
 */

class DamageCalculator {
    constructor(gsdMeters = SimulationConfig.DEFAULT_GSD_METERS) {
        this.gsdMeters = gsdMeters;
        this.sqMetersPerPixel = gsdMeters * gsdMeters;
    }

    /**
     * Standard Jordan Curve point-in-polygon test.
     */
    pointInPolygon(px, py, polygon) {
        let inside = false;
        const n = polygon.length;
        for (let i = 0, j = n - 1; i < n; j = i++) {
            const xi = polygon[i][0], yi = polygon[i][1];
            const xj = polygon[j][0], yj = polygon[j][1];

            const intersect = ((yi > py) !== (yj > py)) &&
                (px < (xj - xi) * (py - yi) / (yj - yi + 1e-9) + xi);
            if (intersect) inside = !inside;
        }
        return inside;
    }

    /**
     * Tests if point is inside building footprint (inside outer polygon AND outside all holes).
     */
    isPointInsideBuilding(px, py, polygon, holes = []) {
        if (!this.pointInPolygon(px, py, polygon)) return false;
        for (let k = 0; k < holes.length; k++) {
            if (this.pointInPolygon(px, py, holes[k])) {
                return false; // Point is inside an interior courtyard/hole
            }
        }
        return true;
    }

    /**
     * Computes exposure percentage and affected area for a single building.
     */
    calculateBuildingExposure(building, floodScenario) {
        const poly = building.polygon;
        const holes = building.holes || [];
        const bbox = building.bbox || [0, 0, 1024, 1024]; // [bx, by, bw, bh]
        const bx = bbox[0], by = bbox[1], bw = bbox[2], bh = bbox[3];

        const totalPixels = building.areaPixels || Math.max(1, bw * bh);
        const totalSqM = Math.round(totalPixels * this.sqMetersPerPixel * 100) / 100;

        // Quick bounds check against surge boundary
        let allFlooded = true;
        let allDry = true;

        // Test corners of bounding box
        const corners = [
            [bx, by],
            [bx + bw, by],
            [bx, by + bh],
            [bx + bw, by + bh]
        ];

        for (const [cx, cy] of corners) {
            if (floodScenario.isPointFlooded(cx, cy)) {
                allDry = false;
            } else {
                allFlooded = false;
            }
        }

        if (allDry) {
            return {
                affectedPixels: 0,
                affectedAreaSqMeters: 0.0,
                totalAreaSqMeters: totalSqM,
                exposurePercentage: 0.0,
                isAffected: false
            };
        }

        if (allFlooded) {
            return {
                affectedPixels: totalPixels,
                affectedAreaSqMeters: totalSqM,
                totalAreaSqMeters: totalSqM,
                exposurePercentage: 100.0,
                isAffected: true
            };
        }

        // Adaptive spatial sampling inside the building bounding box
        const targetSamples = 200;
        const sampleStep = Math.max(1, Math.floor(Math.sqrt((bw * bh) / targetSamples)));

        let sampleInsideCount = 0;
        let sampleFloodedCount = 0;

        for (let py = by; py <= by + bh; py += sampleStep) {
            for (let px = bx; px <= bx + bw; px += sampleStep) {
                if (this.isPointInsideBuilding(px, py, poly, holes)) {
                    sampleInsideCount++;
                    if (floodScenario.isPointFlooded(px, py)) {
                        sampleFloodedCount++;
                    }
                }
            }
        }

        if (sampleInsideCount === 0) {
            // Fallback: check building centroid
            const cx = building.centroid ? building.centroid.x : (bx + bw / 2);
            const cy = building.centroid ? building.centroid.y : (by + bh / 2);
            const isCentroidFlooded = floodScenario.isPointFlooded(cx, cy);
            const exp = isCentroidFlooded ? 100.0 : 0.0;
            return {
                affectedPixels: isCentroidFlooded ? totalPixels : 0,
                affectedAreaSqMeters: isCentroidFlooded ? totalSqM : 0.0,
                totalAreaSqMeters: totalSqM,
                exposurePercentage: exp,
                isAffected: isCentroidFlooded
            };
        }

        const exposurePct = Math.min(100.0, Math.max(0.0, (sampleFloodedCount / sampleInsideCount) * 100.0));
        const affectedPixels = Math.round((exposurePct / 100.0) * totalPixels);
        const affectedSqM = Math.round(affectedPixels * this.sqMetersPerPixel * 100) / 100;

        return {
            affectedPixels: affectedPixels,
            affectedAreaSqMeters: affectedSqM,
            totalAreaSqMeters: totalSqM,
            exposurePercentage: Math.round(exposurePct * 10) / 10,
            isAffected: exposurePct > 0.0
        };
    }

    /**
     * Assesses all building entities against the flood scenario.
     */
    assessAllBuildings(buildings, floodScenario) {
        return buildings.map(b => {
            const exp = this.calculateBuildingExposure(b, floodScenario);
            return { ...b, ...exp };
        });
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = DamageCalculator;
}
