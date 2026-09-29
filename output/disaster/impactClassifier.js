/**
 * DepthWizard Impact Classifier (Client-side)
 * Standardized rule-based categorization of exposure percentages.
 */

class ImpactClassifier {
    static classify(exposurePercentage) {
        const exp = Math.max(0.0, Math.min(100.0, Number(exposurePercentage) || 0.0));

        let tierKey;
        if (exp <= 0.0001) {
            tierKey = "NONE";
        } else if (exp <= 25.0) {
            tierKey = "LOW";
        } else if (exp <= 50.0) {
            tierKey = "MODERATE";
        } else if (exp <= 75.0) {
            tierKey = "HIGH";
        } else {
            tierKey = "CRITICAL";
        }

        const tierInfo = SimulationConfig.IMPACT_CLASSES[tierKey];
        return {
            impactTier: tierKey,
            impactLabel: tierInfo.label,
            impactColorHex: tierInfo.colorHex,
            impactColorThree: tierInfo.colorThree,
            badgeClass: tierInfo.badgeClass,
            tierDescription: tierInfo.description,
            disclaimer: SimulationConfig.SYNTHETIC_SIMULATION_DISCLAIMER
        };
    }

    static classifyBuildings(buildingsWithExposure) {
        return buildingsWithExposure.map(b => {
            const classification = this.classify(b.exposurePercentage);
            return { ...b, ...classification };
        });
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = ImpactClassifier;
}
