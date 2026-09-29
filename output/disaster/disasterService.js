/**
 * DepthWizard Disaster Service (Client-side)
 * High-level simulation controller and 3D visualization constructor.
 */

class DisasterService {
    constructor(gsdMeters = SimulationConfig.DEFAULT_GSD_METERS) {
        this.gsdMeters = gsdMeters;
        this.simulator = new FloodSimulator(1024, 1024);
        this.calculator = new DamageCalculator(gsdMeters);
        this.classifier = ImpactClassifier;
    }

    /**
     * Executes the synthetic flood scenario calculation.
     */
    runFloodSimulation(buildings, intensity = "medium", seed = 42) {
        // 1. Generate procedural flood scenario
        const floodScenario = this.simulator.generateFloodScenario(intensity, seed);

        // 2. Assess spatial footprint exposure
        const assessedRaw = this.calculator.assessAllBuildings(buildings, floodScenario);

        // 3. Classify into impact tiers
        const assessedBuildings = this.classifier.classifyBuildings(assessedRaw);

        // 4. Compute scene aggregate statistics
        const totalBuildings = assessedBuildings.length;
        const affectedBuildings = assessedBuildings.filter(b => b.isAffected);
        const affectedCount = affectedBuildings.length;
        const unaffectedCount = totalBuildings - affectedCount;

        const totalAffectedFootprintSqM = Math.round(
            affectedBuildings.reduce((sum, b) => sum + (b.affectedAreaSqMeters || 0), 0) * 100
        ) / 100;

        const highAndCriticalCount = assessedBuildings.filter(
            b => b.impactTier === "HIGH" || b.impactTier === "CRITICAL"
        ).length;

        const avgExposure = affectedCount > 0
            ? Math.round((affectedBuildings.reduce((sum, b) => sum + (b.exposurePercentage || 0), 0) / affectedCount) * 10) / 10
            : 0.0;

        const tierBreakdown = { NONE: 0, LOW: 0, MODERATE: 0, HIGH: 0, CRITICAL: 0 };
        assessedBuildings.forEach(b => {
            if (tierBreakdown[b.impactTier] !== undefined) {
                tierBreakdown[b.impactTier]++;
            }
        });

        // Sort descending by exposure percentage for dashboard view
        const sortedAffected = [...affectedBuildings].sort((a, b) => b.exposurePercentage - a.exposurePercentage);

        return {
            scenario: {
                name: "Synthetic Disaster Scenario",
                disasterType: "FLOOD",
                intensity: intensity,
                intensityPreset: floodScenario.preset,
                seed: seed,
                disclaimer: "Simulation — not a real post-disaster observation",
                fullDisclaimer: SimulationConfig.SYNTHETIC_SIMULATION_DISCLAIMER
            },
            floodLayer: floodScenario,
            summaryStatistics: {
                totalBuildings: totalBuildings,
                affectedBuildings: affectedCount,
                unaffectedBuildings: unaffectedCount,
                totalFloodedAreaSqMeters: floodScenario.floodedAreaSqMeters,
                totalAffectedBuildingFootprintSqMeters: totalAffectedFootprintSqM,
                highAndCriticalCount: highAndCriticalCount,
                averageExposurePercentage: avgExposure,
                tierBreakdown: tierBreakdown
            },
            assessedBuildings: assessedBuildings,
            affectedBuildingsList: sortedAffected
        };
    }

    /**
     * Builds the Three.js 3D visualization objects for the flood simulation:
     * - Translucent water surface conforming to terrain with +0.18m elevation offset to prevent z-fighting
     * - Glowing front surge boundary line
     */
    create3DFloodVisualization(floodScenario, terrainGridData, heightExaggeration = 1.0) {
        const group = new THREE.Group();
        group.name = "floodSimulationGroup";

        const gridRes = 128; // Grid resolution for water surface
        const geom = new THREE.PlaneGeometry(1024, 1024, gridRes - 1, gridRes - 1);
        geom.rotateX(-Math.PI / 2); // Lay flat on X-Z plane

        const pos = geom.attributes.position;
        const waterElev = floodScenario.waterSurfaceElevation * heightExaggeration;
        const offsetAboveGround = 0.22; // Height offset in meters to eliminate z-fighting

        const maxInland = floodScenario.preset.maxInlandPenetrationPixels;
        const seed = floodScenario.seed;

        // Sample terrain height function if available
        const elevations = terrainGridData ? (terrainGridData.elevations || terrainGridData.groundHeights) : null;
        const N = terrainGridData ? (terrainGridData.gridSize || terrainGridData.gridWidth || 256) : 256;
        const getTerrainHeight = (px, py) => {
            if (!elevations) return 0.0;
            const gx = Math.min(N - 1, Math.max(0, Math.floor((px / 1024) * N)));
            const gy = Math.min(N - 1, Math.max(0, Math.floor((py / 1024) * N)));
            return (elevations[gy * N + gx] || 0.0) * heightExaggeration;
        };

        // Deform vertices to match flood level
        for (let i = 0; i < pos.count; i++) {
            const vx = pos.getX(i); // [-512, 512]
            const vz = pos.getZ(i); // [-512, 512]

            const px = vx + 512;
            const py = vz + 512;

            const surgeFrontierY = this.simulator.getSurgeY(px, maxInland, seed);

            if (py <= surgeFrontierY) {
                // Point is flooded
                const tHeight = getTerrainHeight(px, py);
                // Water elevation is at least the surge level or slightly above ground
                const surfaceY = Math.max(tHeight, waterElev) + offsetAboveGround;
                pos.setY(i, surfaceY);
            } else {
                // Point is dry: drop below terrain so it is naturally hidden
                pos.setY(i, -20.0);
            }
        }
        geom.computeVertexNormals();

        // Realistic translucent water material
        const waterMaterial = new THREE.MeshStandardMaterial({
            color: floodScenario.preset.color || 0x0284c7,
            roughness: 0.15,
            metalness: 0.1,
            transparent: true,
            opacity: 0.68,
            side: THREE.DoubleSide,
            depthWrite: false // Prevents sorting artifacts with buildings
        });

        const waterMesh = new THREE.Mesh(geom, waterMaterial);
        waterMesh.receiveShadow = false;
        group.add(waterMesh);

        // Glowing perimeter surge boundary line
        const linePoints = [];
        const boundary = floodScenario.surgeBoundaryLine || [];
        for (let i = 0; i < boundary.length; i++) {
            const bx = boundary[i][0];
            const by = boundary[i][1];
            const vx = bx - 512;
            const vz = by - 512;
            const vy = getTerrainHeight(bx, by) + offsetAboveGround + 0.1;
            linePoints.push(new THREE.Vector3(vx, vy, vz));
        }

        if (linePoints.length >= 2) {
            const lineGeom = new THREE.BufferGeometry().setFromPoints(linePoints);
            const lineMat = new THREE.LineBasicMaterial({
                color: 0x38bdf8, // Vibrant cyan/sky blue
                linewidth: 3,
                transparent: true,
                opacity: 0.95
            });
            const lineMesh = new THREE.Line(lineGeom, lineMat);
            group.add(lineMesh);
        }

        return group;
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = DisasterService;
}
