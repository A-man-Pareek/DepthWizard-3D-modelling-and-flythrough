/**
 * DepthWizard Disaster Service (Client-side)
 * Unified simulation controller and Three.js 3D hazard visualization constructor
 * supporting Flood, Wildfire, Cyclone, and Landslide.
 */

class DisasterService {
    constructor(gsdMeters = SimulationConfig.DEFAULT_GSD_METERS) {
        this.gsdMeters = gsdMeters;
        this.floodSim = new FloodSimulator(1024, 1024);
        this.wildfireSim = new WildfireSimulator(1024, 1024);
        this.cycloneSim = new CycloneSimulator(1024, 1024);
        this.landslideSim = new LandslideSimulator(1024, 1024, gsdMeters);
        this.calculator = new DamageCalculator(gsdMeters);
        this.classifier = ImpactClassifier;
    }

    /**
     * Executes any of the 4 disaster simulation scenarios.
     */
    runSimulation(disasterType, buildings, intensity = "medium", seed = 42, extraParams = {}) {
        disasterType = (disasterType || "FLOOD").toUpperCase();

        let scenario;
        if (disasterType === "FLOOD") {
            scenario = this.floodSim.generateFloodScenario(intensity, seed);
        } else if (disasterType === "WILDFIRE") {
            scenario = this.wildfireSim.generateWildfireScenario(intensity, seed, extraParams.windDirectionDeg || 45.0);
        } else if (disasterType === "CYCLONE") {
            scenario = this.cycloneSim.generateCycloneScenario(intensity, seed, extraParams.eyeX, extraParams.eyeY);
        } else if (disasterType === "LANDSLIDE") {
            scenario = this.landslideSim.generateLandslideScenario(intensity, seed);
        } else {
            scenario = this.floodSim.generateFloodScenario(intensity, seed);
        }

        // 2. Assess spatial footprint exposure
        const assessedRaw = this.calculator.assessAllBuildings(buildings, scenario);

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

        const sortedAffected = [...affectedBuildings].sort((a, b) => b.exposurePercentage - a.exposurePercentage);

        const hazardArea = scenario.floodedAreaSqMeters ||
                           scenario.burnedAreaSqMeters ||
                           scenario.impactedAreaSqMeters ||
                           scenario.displacedAreaSqMeters || 0;

        const infraEnv = this.calculator.assessInfrastructureAndEnvironment(scenario);
        const typeMeta = DisasterTypes[disasterType] || DisasterTypes.FLOOD;

        return {
            scenario: {
                name: "Synthetic Disaster Scenario",
                disasterType: disasterType,
                disasterMeta: typeMeta,
                intensity: intensity,
                intensityPreset: scenario.preset,
                seed: seed,
                disclaimer: "Simulation — not a real post-disaster observation",
                fullDisclaimer: SimulationConfig.SYNTHETIC_SIMULATION_DISCLAIMER
            },
            hazardLayer: scenario,
            summaryStatistics: {
                totalBuildings: totalBuildings,
                affectedBuildings: affectedCount,
                unaffectedBuildings: unaffectedCount,
                totalHazardAreaSqMeters: hazardArea,
                totalAffectedBuildingFootprintSqMeters: totalAffectedFootprintSqM,
                highAndCriticalCount: highAndCriticalCount,
                averageExposurePercentage: avgExposure,
                tierBreakdown: tierBreakdown,
                affectedRoadsLengthMeters: infraEnv.affectedRoadsLengthMeters,
                affectedVegetationAreaSqMeters: infraEnv.affectedVegetationAreaSqMeters,
                estimatedPopulation: infraEnv.estimatedPopulation
            },
            assessedBuildings: assessedBuildings,
            affectedBuildingsList: sortedAffected
        };
    }

    // Backward compatibility
    runFloodSimulation(buildings, intensity = "medium", seed = 42) {
        return this.runSimulation("FLOOD", buildings, intensity, seed);
    }

    /**
     * Builds the 3D Three.js visualization objects for any active hazard.
     */
    create3DHazardVisualization(hazardScenario, terrainGridData, heightExaggeration = 1.0) {
        const dType = hazardScenario.disasterType || "FLOOD";
        const group = new THREE.Group();
        group.name = "disasterSimulationGroup";

        const elevations = terrainGridData ? (terrainGridData.elevations || terrainGridData.groundHeights) : null;
        const N = terrainGridData ? (terrainGridData.gridSize || terrainGridData.gridWidth || 256) : 256;
        const getTerrainHeight = (px, py) => {
            if (!elevations) return 0.0;
            const gx = Math.min(N - 1, Math.max(0, Math.floor((px / 1024) * N)));
            const gy = Math.min(N - 1, Math.max(0, Math.floor((py / 1024) * N)));
            return (elevations[gy * N + gx] || 0.0) * heightExaggeration;
        };

        if (dType === "FLOOD") {
            // 🌊 FLOOD: Translucent water plane conforming to terrain with +0.22m elevation offset
            const gridRes = 128;
            const geom = new THREE.PlaneGeometry(1024, 1024, gridRes - 1, gridRes - 1);
            geom.rotateX(-Math.PI / 2);
            const pos = geom.attributes.position;
            const waterElev = (hazardScenario.waterSurfaceElevation || 1.8) * heightExaggeration;
            const offset = 0.22;

            for (let i = 0; i < pos.count; i++) {
                const vx = pos.getX(i);
                const vz = pos.getZ(i);
                const px = vx + 512;
                const py = vz + 512;

                if (hazardScenario.isPointFlooded(px, py)) {
                    const tHeight = getTerrainHeight(px, py);
                    pos.setY(i, Math.max(tHeight, waterElev) + offset);
                } else {
                    pos.setY(i, -20.0);
                }
            }
            geom.computeVertexNormals();

            const waterMat = new THREE.MeshStandardMaterial({
                color: hazardScenario.preset.color || 0x0284c7,
                roughness: 0.15,
                metalness: 0.1,
                transparent: true,
                opacity: 0.68,
                side: THREE.DoubleSide,
                depthWrite: false
            });
            group.add(new THREE.Mesh(geom, waterMat));

            // Glowing wave boundary line
            const boundary = hazardScenario.surgeBoundaryLine || [];
            const linePoints = [];
            for (let i = 0; i < boundary.length; i++) {
                const bx = boundary[i][0];
                const by = boundary[i][1];
                linePoints.push(new THREE.Vector3(bx - 512, getTerrainHeight(bx, by) + offset + 0.1, by - 512));
            }
            if (linePoints.length >= 2) {
                const lineGeom = new THREE.BufferGeometry().setFromPoints(linePoints);
                const lineMat = new THREE.LineBasicMaterial({ color: 0x38bdf8, linewidth: 3, transparent: true, opacity: 0.95 });
                group.add(new THREE.Line(lineGeom, lineMat));
            }

        } else if (dType === "WILDFIRE") {
            // 🔥 WILDFIRE: Charred terrain surface (+0.20m) and glowing amber fire perimeter
            const gridRes = 96;
            const geom = new THREE.PlaneGeometry(1024, 1024, gridRes - 1, gridRes - 1);
            geom.rotateX(-Math.PI / 2);
            const pos = geom.attributes.position;
            const offset = 0.20;

            for (let i = 0; i < pos.count; i++) {
                const px = pos.getX(i) + 512;
                const py = pos.getZ(i) + 512;
                if (hazardScenario.isPointBurned(px, py)) {
                    pos.setY(i, getTerrainHeight(px, py) + offset);
                } else {
                    pos.setY(i, -20.0);
                }
            }
            geom.computeVertexNormals();

            const burnMat = new THREE.MeshStandardMaterial({
                color: 0x1c1917, // Charred ash dark
                roughness: 0.95,
                metalness: 0.05,
                transparent: true,
                opacity: 0.75,
                depthWrite: false
            });
            group.add(new THREE.Mesh(geom, burnMat));

            // Glowing flame front perimeter line
            const perim = hazardScenario.perimeterLine || [];
            const linePts = [];
            for (let i = 0; i < perim.length; i++) {
                const px = perim[i][0];
                const py = perim[i][1];
                linePts.push(new THREE.Vector3(px - 512, getTerrainHeight(px, py) + offset + 0.15, py - 512));
            }
            if (linePts.length >= 2) {
                const lineGeom = new THREE.BufferGeometry().setFromPoints(linePts);
                const lineMat = new THREE.LineBasicMaterial({ color: 0xf97316, linewidth: 3, transparent: true, opacity: 0.95 });
                group.add(new THREE.Line(lineGeom, lineMat));
            }

        } else if (dType === "CYCLONE") {
            // 🌀 CYCLONE: Rotating spiral wind streamlines & eyewall perimeter
            const offset = 0.35;
            const streamlines = hazardScenario.streamlines || [];

            streamlines.forEach((arm, idx) => {
                const pts = [];
                arm.forEach(p => {
                    pts.push(new THREE.Vector3(p[0] - 512, getTerrainHeight(p[0], p[1]) + offset + (idx * 0.1), p[1] - 512));
                });
                if (pts.length >= 2) {
                    const armGeom = new THREE.BufferGeometry().setFromPoints(pts);
                    const armMat = new THREE.LineBasicMaterial({
                        color: 0xa855f7, // Purple/Violet wind flow
                        linewidth: 2.5,
                        transparent: true,
                        opacity: 0.85
                    });
                    group.add(new THREE.Line(armGeom, armMat));
                }
            });

            // Eyewall circle
            const eyePts = (hazardScenario.eyewallBoundary || []).map(p =>
                new THREE.Vector3(p[0] - 512, getTerrainHeight(p[0], p[1]) + offset + 0.2, p[1] - 512)
            );
            if (eyePts.length >= 2) {
                const eyeGeom = new THREE.BufferGeometry().setFromPoints(eyePts);
                const eyeMat = new THREE.LineBasicMaterial({ color: 0xc084fc, linewidth: 3, transparent: true, opacity: 0.95 });
                group.add(new THREE.Line(eyeGeom, eyeMat));
            }

        } else if (dType === "LANDSLIDE") {
            // ⛰️ LANDSLIDE: Earthy ochre debris flow surface (+0.25m) and scarp outline
            const gridRes = 96;
            const geom = new THREE.PlaneGeometry(1024, 1024, gridRes - 1, gridRes - 1);
            geom.rotateX(-Math.PI / 2);
            const pos = geom.attributes.position;
            const offset = 0.25;

            for (let i = 0; i < pos.count; i++) {
                const px = pos.getX(i) + 512;
                const py = pos.getZ(i) + 512;
                if (hazardScenario.isPointInLandslide(px, py)) {
                    pos.setY(i, getTerrainHeight(px, py) + offset + 0.3);
                } else {
                    pos.setY(i, -20.0);
                }
            }
            geom.computeVertexNormals();

            const debrisMat = new THREE.MeshStandardMaterial({
                color: 0x78350f, // Deep earthy mud/debris ochre
                roughness: 0.9,
                metalness: 0.05,
                transparent: true,
                opacity: 0.82,
                depthWrite: false
            });
            group.add(new THREE.Mesh(geom, debrisMat));

            // Debris boundary line
            const debrisPts = (hazardScenario.debrisBoundary || []).map(p =>
                new THREE.Vector3(p[0] - 512, getTerrainHeight(p[0], p[1]) + offset + 0.35, p[1] - 512)
            );
            if (debrisPts.length >= 2) {
                const dGeom = new THREE.BufferGeometry().setFromPoints(debrisPts);
                const dMat = new THREE.LineBasicMaterial({ color: 0xd97706, linewidth: 3, transparent: true, opacity: 0.95 });
                group.add(new THREE.Line(dGeom, dMat));
            }
        }

        return group;
    }

    // Backward compatibility
    create3DFloodVisualization(floodScenario, terrainGridData, heightExaggeration = 1.0) {
        return this.create3DHazardVisualization(floodScenario, terrainGridData, heightExaggeration);
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = DisasterService;
}
