"""Tests for category-specific WardrobeIQ fit analysis."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.fit_engine import analyze_fit


class FitEngineTests(unittest.TestCase):
    """Cover the documented Issue 3 fit-analysis contract."""

    def test_blazer_bust_ease_classifies_as_oversized(self) -> None:
        result = analyze_fit(
            body={"bust_cm": 82, "shoulder_width_cm": 37},
            garment={
                "bust_cm": 100,
                "shoulder_width_cm": 41,
                "intended_fit": "oversized",
            },
            category="blazer",
        )

        self.assertEqual(result["fit_classification"], "oversized")
        self.assertEqual(result["confidence"], "high")
        self.assertEqual(result["measurement_analysis"]["bust_cm"]["ease"], 18)
        self.assertEqual(result["measurement_analysis"]["shoulder_width_cm"]["difference"], 4)
        self.assertEqual(result["measurement_analysis"]["shoulder_width_cm"]["label"], "extended")

    def test_regular_shirt_uses_shirt_specific_rules(self) -> None:
        result = analyze_fit(
            body={"bust_cm": 90},
            garment={"bust_cm": 100},
            category="shirt",
        )

        self.assertEqual(result["fit_classification"], "regular")
        self.assertEqual(result["confidence"], "medium")

    def test_partial_information_still_returns_lower_confidence_analysis(self) -> None:
        result = analyze_fit(
            body={"bust_cm": 82},
            garment={"bust_cm": 100},
            category="blazer",
        )

        self.assertEqual(result["fit_classification"], "oversized")
        self.assertEqual(result["confidence"], "medium")
        self.assertIn("body.shoulder_width_cm", result["missing_fields"])
        self.assertIn("garment.shoulder_width_cm", result["missing_fields"])

    def test_missing_garment_measurements_remains_unknown(self) -> None:
        result = analyze_fit(
            body={"bust_cm": 82},
            garment={},
            category="blazer",
        )

        self.assertEqual(result["fit_classification"], "unknown")
        self.assertEqual(result["measurement_analysis"], {})

    def test_invalid_measurement_is_reported_and_ignored(self) -> None:
        result = analyze_fit(
            body={"bust_cm": 82},
            garment={"bust_cm": -100},
            category="blazer",
        )

        self.assertEqual(result["fit_classification"], "unknown")
        self.assertTrue(
            any("garment.bust_cm must be a positive number" in warning for warning in result["warnings"])
        )
        self.assertIn("garment.bust_cm", result["missing_fields"])

    def test_intended_fit_alignment_does_not_override_measured_fit(self) -> None:
        result = analyze_fit(
            body={"bust_cm": 82},
            garment={"bust_cm": 100, "intended_fit": "oversized"},
            category="blazer",
        )

        self.assertEqual(result["measured_fit"], "oversized")
        self.assertEqual(result["intended_fit"], "oversized")
        self.assertEqual(result["fit_alignment"], "aligned")

    def test_intended_fit_mismatch_reports_looser_than_intended(self) -> None:
        result = analyze_fit(
            body={"bust_cm": 82},
            garment={"bust_cm": 100, "intended_fit": "regular"},
            category="blazer",
        )

        self.assertEqual(result["measured_fit"], "oversized")
        self.assertEqual(result["fit_alignment"], "looser_than_intended")

    def test_trousers_expose_waist_and_hip_fit_without_leg_silhouette(self) -> None:
        result = analyze_fit(
            body={"waist_cm": 64, "hip_cm": 89},
            garment={"waist_cm": 69, "hip_cm": 101},
            category="trousers",
        )

        self.assertEqual(result["waist_fit"], "regular")
        self.assertEqual(result["hip_fit"], "relaxed")
        self.assertEqual(result["overall_fit"], "relaxed")
        self.assertNotIn("leg_silhouette", result)

    def test_mixed_dress_fit_exposes_regional_disagreement(self) -> None:
        result = analyze_fit(
            body={"bust_cm": 82, "waist_cm": 64, "hip_cm": 89},
            garment={"bust_cm": 84, "waist_cm": 72, "hip_cm": 107},
            category="dress",
        )

        self.assertEqual(result["fit_classification"], "mixed")
        self.assertEqual(result["overall_fit"], "mixed")
        self.assertEqual(result["measurement_analysis"]["bust_cm"]["fit"], "fitted")
        self.assertEqual(result["measurement_analysis"]["waist_cm"]["fit"], "regular")
        self.assertEqual(result["measurement_analysis"]["hip_cm"]["fit"], "oversized")


if __name__ == "__main__":
    unittest.main()
