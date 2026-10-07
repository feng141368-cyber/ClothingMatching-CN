"""Tests for the structured ClothingMatching-CN Skill profile resolver."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.profile_resolver import resolve_profile


class ProfileResolverTests(unittest.TestCase):
    """Cover the documented Issue 2 normalization contract."""

    def test_complete_sample_profile_resolves_without_destructive_changes(self) -> None:
        sample_path = PROJECT_ROOT / "examples" / "user_profile.json"
        sample = json.loads(sample_path.read_text(encoding="utf-8"))

        result = resolve_profile(sample)

        self.assertEqual(result["profile"], sample)
        self.assertEqual(result["warnings"], [])
        self.assertEqual(result["unsupported_values"], [])
        self.assertEqual(result["missing_fields"], [])

    def test_partial_profile_preserves_missing_values_as_unknown(self) -> None:
        result = resolve_profile(
            {
                "body": {"height_cm": 168},
                "style_modes": ["minimal"],
            }
        )

        profile = result["profile"]
        self.assertEqual(profile["body"]["height_cm"], 168)
        self.assertIsNone(profile["body"]["shoulder_width_cm"])
        self.assertIsNone(profile["body"]["inseam_cm"])
        self.assertEqual(profile["style_modes"], ["minimal"])
        self.assertIn("body.shoulder_width_cm", result["missing_fields"])
        self.assertIn("body.inseam_cm", result["missing_fields"])

    def test_alias_normalization(self) -> None:
        result = resolve_profile(
            {
                "fit_preferences": {
                    "blazers": "Oversize",
                    "trousers": "wide leg",
                },
                "style_modes": ["Relaxed Business", "Smart Casual"],
                "style_keywords": ["soft tailoring"],
                "color_preferences": {"preferred": ["Grey"]},
            }
        )

        profile = result["profile"]
        self.assertEqual(profile["fit_preferences"]["blazers"], "oversized")
        self.assertEqual(profile["fit_preferences"]["trousers"], "wide_leg")
        self.assertEqual(profile["style_modes"], ["relaxed_business", "smart_casual"])
        self.assertEqual(profile["style_keywords"], ["soft_tailoring"])
        self.assertEqual(profile["color_preferences"]["preferred"], ["gray"])

    def test_invalid_measurement_is_reported_and_not_accepted(self) -> None:
        result = resolve_profile({"body": {"height_cm": -168}})

        self.assertIsNone(result["profile"]["body"]["height_cm"])
        self.assertTrue(
            any("body.height_cm must be a positive number" in warning for warning in result["warnings"])
        )

    def test_unknown_style_mode_is_reported_without_guessing(self) -> None:
        result = resolve_profile({"style_modes": ["random_core"]})

        self.assertEqual(result["profile"]["style_modes"], [])
        self.assertIn(
            {
                "field": "style_modes",
                "value": "random_core",
                "reason": "unsupported_style_mode",
            },
            result["unsupported_values"],
        )

    def test_empty_input_returns_canonical_profile_and_missing_fields(self) -> None:
        result = resolve_profile({})

        self.assertEqual(result["profile"]["body"], {
            "height_cm": None,
            "shoulder_width_cm": None,
            "bust_cm": None,
            "waist_cm": None,
            "hip_cm": None,
            "inseam_cm": None,
            "shoe_size_eu": None,
        })
        self.assertEqual(result["profile"]["style_modes"], [])
        self.assertEqual(result["profile"]["notes"], {})
        self.assertIn("body.height_cm", result["missing_fields"])
        self.assertIn("style_modes", result["missing_fields"])


if __name__ == "__main__":
    unittest.main()
