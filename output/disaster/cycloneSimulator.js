/**
 * DepthWizard Cyclone Simulator (Client-side)
 * Holland vortex wind velocity model with logarithmic spiral streamlines.
 */

class CycloneSimulator {
    constructor(width = 1024, height = 1024) {
        this.width = width;
        this.height = height;
    }

    generateCycloneScenario(intensity = "medium", seed = 42, eyeX = null, eyeY = null) {
        const preset = SimulationConfig.CYCLONE_INTENSITIES[intensity] || SimulationConfig.CYCLONE_INTENSITIES.medium;
        const vMax = preset.maxWindSpeedKmh;
        const rMax = preset.radiusMaxWindsPixels;
        const rOuter = preset.cycloneRadiusPixels;

        const ex = eyeX !== null ? eyeX : (440.0 + (seed % 100) - 50.0);
        const ey = eyeY !== null ? eyeY : (400.0 + (seed % 100) - 50.0);

        const galeThreshold = 65.0; // km/h

        const getWindSpeedAt = (px, py) => {
            const dx = px - ex;
            const dy = py - ey;
            const dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < 20) return vMax * 0.15; // Eye
            if (dist > rOuter * 1.25) return 20.0; // Background wind

            const baseV = vMax * ((2.0 * rMax * dist) / (rMax * rMax + dist * dist + 1e-6));
            const angle = Math.atan2(dy, dx);
            const spiralPhase = (angle - 0.45 * Math.log(Math.max(10.0, dist))) * 2.0;
            const armBoost = Math.cos(spiralPhase + (seed % 10)) * 0.15 + 1.0;
            return baseV * armBoost;
        };

        const isPointInSwath = (px, py) => {
            return getWindSpeedAt(px, py) >= galeThreshold;
        };

        // Generate spiral streamline paths for 3D visualization (3 concentric spiral arms)
        const streamlines = [];
        const numArms = 3;
        for (let a = 0; a < numArms; a++) {
            const startAngle = (a * 2.0 * Math.PI) / numArms + (seed % 5);
            const armPoints = [];
            const steps = 48;
            for (let s = 0; s < steps; s++) {
                const progress = s / steps;
                const r = 35 + progress * (rOuter - 35);
                const theta = startAngle + progress * 3.5; // Spiral rotation
                const sx = ex + r * Math.cos(theta);
                const sy = ey + r * Math.sin(theta);
                if (sx >= 0 && sx <= this.width && sy >= 0 && sy <= this.height) {
                    armPoints.push([Math.round(sx * 10) / 10, Math.round(sy * 10) / 10]);
                }
            }
            if (armPoints.length >= 2) streamlines.push(armPoints);
        }

        // Eyewall boundary circle
        const eyewallBoundary = [];
        for (let i = 0; i <= 40; i++) {
            const th = (i / 40) * 2.0 * Math.PI;
            eyewallBoundary.push([
                Math.round((ex + rMax * Math.cos(th)) * 10) / 10,
                Math.round((ey + rMax * Math.sin(th)) * 10) / 10
            ]);
        }

        // Swath outer boundary
        const swathBoundary = [];
        for (let i = 0; i <= 48; i++) {
            const th = (i / 48) * 2.0 * Math.PI;
            const armVariation = Math.cos(th * 2.0 + (seed % 10)) * (rOuter * 0.12);
            const rEffective = rOuter + armVariation;
            swathBoundary.push([
                Math.min(this.width - 2, Math.max(2, Math.round((ex + rEffective * Math.cos(th)) * 10) / 10)),
                Math.min(this.height - 2, Math.max(2, Math.round((ey + rEffective * Math.sin(th)) * 10) / 10))
            ]);
        }

        const impactedPixels = Math.round(Math.PI * (rOuter ** 2) * 0.85);
        const impactedAreaSqMeters = Math.round(impactedPixels * SimulationConfig.PIXEL_AREA_TO_SQ_METERS * 100) / 100;

        return {
            disasterType: "CYCLONE",
            intensity: intensity,
            preset: preset,
            seed: seed,
            eyePosition: { x: Math.round(ex), y: Math.round(ey) },
            maxWindSpeedKmh: vMax,
            radiusMaxWindsPixels: rMax,
            centralPressureHpa: preset.centralPressureHpa,
            impactedPixels: impactedPixels,
            impactedAreaSqMeters: impactedAreaSqMeters,
            polygons: [swathBoundary],
            streamlines: streamlines,
            eyewallBoundary: eyewallBoundary,
            isPointInSwath: isPointInSwath,
            isPointFlooded: isPointInSwath, // Unified interface for damageCalculator
            getWindSpeedAt: getWindSpeedAt
        };
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = CycloneSimulator;
}
