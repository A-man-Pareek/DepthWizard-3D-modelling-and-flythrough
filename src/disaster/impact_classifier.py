"""
Impact Classifier for DepthWizard.
Provides transparent, rule-based classification mapping exposure percentage
to hazard impact tiers with standardized styling and disclaimers.
"""

from typing import Dict, Any, List
from .simulation_config import IMPACT_CLASSES, SYNTHETIC_SIMULATION_DISCLAIMER

class ImpactClassifier:
    """
    Categorizes spatial flood exposure into standardized disaster assessment tiers.
    """

    @staticmethod
    def classify(exposure_percentage: float) -> Dict[str, Any]:
        """
        Classifies an individual exposure percentage into an impact tier.
        
        Args:
            exposure_percentage: Value between 0.0 and 100.0
            
        Returns:
            Dict containing classification details (tier, label, color, description)
        """
        exposure = max(0.0, min(100.0, float(exposure_percentage)))

        if exposure <= 0.0001:
            tier_key = "NONE"
        elif exposure <= 25.0:
            tier_key = "LOW"
        elif exposure <= 50.0:
            tier_key = "MODERATE"
        elif exposure <= 75.0:
            tier_key = "HIGH"
        else:
            tier_key = "CRITICAL"

        tier_info = IMPACT_CLASSES[tier_key]
        return {
            "impactTier": tier_key,
            "impactLabel": tier_info["label"],
            "impactColor": tier_info["color"],
            "badgeClass": tier_info["badgeClass"],
            "description": tier_info["description"],
            "disclaimer": SYNTHETIC_SIMULATION_DISCLAIMER
        }

    @classmethod
    def classify_buildings(cls, buildings_with_exposure: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enriches all building exposure records with impact classification data.
        """
        enriched = []
        for b in buildings_with_exposure:
            exp = b.get("exposurePercentage", 0.0)
            c_info = cls.classify(exp)
            enriched.append({**b, **c_info})
        return enriched
