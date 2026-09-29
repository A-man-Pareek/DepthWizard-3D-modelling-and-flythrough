/**
 * DepthWizard Wildfire Simulator (Client-side)
 * Generates wind-driven elliptical burn perimeters with harmonic perimeter fingers.
 */

class WildfireSimulator {
    constructor(width = 1024, height = 1024) {
        this.width = width;
        this.height = height;
    }

    generateWildfireScenario(intensity = "medium", seed = 42, windDirectionDeg = 45.0) {
        const preset = SimulationConfig.WILDFIRE_INTENSITIES[intensity] || SimulationConfig.WILDFIRE_INTENSITIES.medium;
        const spreadR = preset.spreadRadiusPixels;
        const windSpeed = preset.windSpeedKmh;

        // Ignition center in vegetated area (south-central)
        const cx = 480.0 + (seed % 60) - 30.0;
        const cy = 680.0 + (seed % 80) - 40.0;

        const windRad = (windDirectionDeg * Math.PI) / 180.0;
        const lengthToWidth = 1.0 + (windSpeed / 25.0);
        const a = spreadR * lengthToWidth;
        const b = spreadR;

        // Shift focus forward along wind
        const forwardShift = a * 0.45;
        const focusX = cx + forwardShift * Math.cos(windRad);
        const focusY = cy - forwardShift * Math.sin(windRad);

        const cosW = Math.cos(windRad);
        const sinW = Math.sin(windRad);

        const isPointBurned = (px, py) => {
            const dx = px - focusX;
            const dy = py - focusY;
            const xPrime = dx * cosW - dy * sinW;
            const yPrime = dx * sinW + dy * cosW;

            const dist = Math.sqrt((xPrime / a) ** 2 + (yPrime / b) ** 2);
            const angle = Math.atan2(yPrime, xPrime);
            const noise = Math.sin(angle * 3.0 + (seed % 20)) * 0.16 +
                          Math.cos(angle * 7.0 + (seed % 35)) * 0.09 +
                          Math.sin(angle * 13.0 + (seed % 50)) * 0.04;
            return dist <= (1.0 + noise);
        };

        // Sample closed boundary line around perimeter
        const boundaryPoints = [];
        const numSteps = 72;
        for (let i = 0; i <= numSteps; i++) {
            const theta = (i / numSteps) * 2.0 * Math.PI;
            const noise = Math.sin(theta * 3.0 + (seed % 20)) * 0.16 +
                          Math.cos(theta * 7.0 + (seed % 35)) * 0.09 +
                          Math.sin(theta * 13.0 + (seed % 50)) * 0.04;
            const rPrime = 1.0 + noise;

            const xPrime = a * rPrime * Math.cos(theta);
            const yPrime = b * rPrime * Math.sin(theta);

            // Rotate back from wind-aligned frame
            const rx = xPrime * cosW + yPrime * sinW + focusX;
            const ry = -xPrime * sinW + yPrime * cosW + focusY;

            boundaryPoints.push([
                Math.min(this.width - 2, Math.max(2, Math.round(rx * 10) / 10)),
                Math.min(this.height - 2, Math.max(2, Math.round(ry * 10) / 10))
            ]);
        }

        // Polygon area using shoelace formula
        let shoelace = 0;
        for (let i = 0; i < boundaryPoints.length - 1; i++) {
            shoelace += boundaryPoints[i][0] * boundaryPoints[i + 1][1] - boundaryPoints[i + 1][0] * boundaryPoints[i][1];
        }
        const burnedPixels = Math.max(500, Math.round(Math.abs(shoelace) / 2.0));
        const burnedAreaSqMeters = Math.round(burnedPixels * SimulationConfig.PIXEL_AREA_TO_SQ_METERS * 100) / 100;

        return {
            disasterType: "WILDFIRE",
            intensity: intensity,
            preset: preset,
            seed: seed,
            windDirectionDeg: windDirectionDeg,
            windSpeedKmh: windSpeed,
            firelineIntensityKwm: preset.firelineIntensityKwm,
            burnedPixels: burnedPixels,
            burnedAreaSqMeters: burnedAreaSqMeters,
            polygons: [boundaryPoints],
            perimeterLine: boundaryPoints,
            isPointBurned: isPointBurned,
            isPointFlooded: isPointBurned, // Unified interface
            ignitionCenter: { x: Math.round(focusX), y: Math.round(focusY) }
        };
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = WildfireSimulator;
}
