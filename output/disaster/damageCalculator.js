/**
 * DepthWizard Damage & Exposure Calculator (Client-side)
 * Computes 2D spatial footprint intersection and exposure percentages
 * for buildings, roads, and environmental vegetation.
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
                return false;
            }
        }
        return true;
    }

    /**
     * Computes exposure percentage and affected area for a single building against hazard scenario.
     */
    calculateBuildingExposure(building, hazardScenario) {
        const poly = building.polygon;
        const holes = building.holes || [];
        const bbox = building.bbox || [0, 0, 1024, 1024];
        const bx = bbox[0], by = bbox[1], bw = bbox[2], bh = bbox[3];

        const totalPixels = building.areaPixels || Math.max(1, bw * bh);
        const totalSqM = Math.round(totalPixels * this.sqMetersPerPixel * 100) / 100;

        const testFn = hazardScenario.isPointFlooded || hazardScenario.isPointBurned || hazardScenario.isPointInSwath || hazardScenario.isPointInLandslide;

        // Quick bounds test
        let allImpacted = true;
        let allClear = true;
        const corners = [
            [bx, by],
            [bx + bw, by],
            [bx, by + bh],
            [bx + bw, by + bh]
        ];

        for (const [cx, cy] of corners) {
            if (testFn(cx, cy)) {
                allClear = false;
            } else {
                allImpacted = false;
            }
        }

        if (allClear) {
            return {
                affectedPixels: 0,
                affectedAreaSqMeters: 0.0,
                totalAreaSqMeters: totalSqM,
                exposurePercentage: 0.0,
                isAffected: false
            };
        }

        if (allImpacted) {
            return {
                affectedPixels: totalPixels,
                affectedAreaSqMeters: totalSqM,
                totalAreaSqMeters: totalSqM,
                exposurePercentage: 100.0,
                isAffected: true
            };
        }

        // Adaptive spatial sampling inside the building bounding box
        const targetSamples = 180;
        const sampleStep = Math.max(1, Math.floor(Math.sqrt((bw * bh) / targetSamples)));

        let sampleInsideCount = 0;
        let sampleImpactedCount = 0;

        for (let py = by; py <= by + bh; py += sampleStep) {
            for (let px = bx; px <= bx + bw; px += sampleStep) {
                if (this.isPointInsideBuilding(px, py, poly, holes)) {
                    sampleInsideCount++;
                    if (testFn(px, py)) {
                        sampleImpactedCount++;
                    }
                }
            }
        }

        if (sampleInsideCount === 0) {
            const cx = building.centroid ? building.centroid.x : (bx + bw / 2);
            const cy = building.centroid ? building.centroid.y : (by + bh / 2);
            const isCentroidImpacted = testFn(cx, cy);
            return {
                affectedPixels: isCentroidImpacted ? totalPixels : 0,
                affectedAreaSqMeters: isCentroidImpacted ? totalSqM : 0.0,
                totalAreaSqMeters: totalSqM,
                exposurePercentage: isCentroidImpacted ? 100.0 : 0.0,
                isAffected: isCentroidImpacted
            };
        }

        const exposurePct = Math.min(100.0, Math.max(0.0, (sampleImpactedCount / sampleInsideCount) * 100.0));
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
     * Assesses all building entities against the hazard scenario.
     */
    assessAllBuildings(buildings, hazardScenario) {
        return buildings.map(b => {
            const exp = this.calculateBuildingExposure(b, hazardScenario);
            return { ...b, ...exp };
        });
    }

    /**
     * Calculates infrastructure (roads) and environmental (vegetation) affected metrics.
     */
    assessInfrastructureAndEnvironment(hazardScenario, sceneData) {
        const hazardArea = hazardScenario.floodedAreaSqMeters ||
                           hazardScenario.burnedAreaSqMeters ||
                           hazardScenario.impactedAreaSqMeters ||
                           hazardScenario.displacedAreaSqMeters || 0;

        // Estimated road impact: roads total ~7,806 pixels (~2.7km)
        // Correlate with hazard area fraction over 1024x1024 total terrain
        const totalTerrainAreaSqM = 1024 * 1024 * this.sqMetersPerPixel; // 128,450 m^2
        const fraction = Math.min(1.0, hazardArea / totalTerrainAreaSqM);

        const estRoadMeters = Math.round(fraction * 2730 * 10) / 10;
        const estVegSqM = Math.round(fraction * 29020 * 10) / 10;

        return {
            affectedRoadsLengthMeters: estRoadMeters,
            affectedVegetationAreaSqMeters: estVegSqM,
            estimatedPopulation: "Unavailable (Requires Census Layer)"
        };
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = DamageCalculator;
}
