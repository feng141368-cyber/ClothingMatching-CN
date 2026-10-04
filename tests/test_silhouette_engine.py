"""Tests for WardrobeIQ's data-driven silhouette analysis."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.silhouette_engine import analyze_silhouette_mix, analyze_silhouette_pair, normalize_silhouette


class SilhouetteEngineTests(unittest.TestCase):
    def test_aliases(self) -> None:
        self.assertEqual(normalize_silhouette("wide leg")["canonical_silhouette"], "wide_leg")
        self.assertEqual(normalize_silhouette("A-line")["canonical_silhouette"], "a_line")
        self.assertEqual(normalize_silhouette("drop shoulder")["canonical_silhouette"], "dropped_shoulder")

    def test_metadata(self) -> None:
        self.assertEqual(normalize_silhouette("oversized")["attributes"]["volume"], "high")
        self.assertEqual(normalize_silhouette("fitted")["attributes"]["shape"], "fitted")
        self.assertEqual(normalize_silhouette("wide_leg")["attributes"]["shape"], "wide")
        self.assertEqual(normalize_silhouette("cropped")["attributes"]["length_effect"], "cropped")
        self.assertEqual(normalize_silhouette("structured")["attributes"]["structure"], "structured")

    def test_oversized_and_straight(self) -> None:
        result = analyze_silhouette_pair("oversized", "straight")
        self.assertEqual(result["proportion_pattern"], "loose_straight")

    def test_oversized_and_wide_leg(self) -> None:
        result = analyze_silhouette_pair("oversized", "wide_leg")
        self.assertEqual(result["volume_relationship"], "high_volume")
        self.assertNotIn("quality_score", result)

    def test_fitted_and_wide_leg(self) -> None:
        self.assertEqual(analyze_silhouette_pair("fitted", "wide_leg")["proportion_pattern"], "fitted_wide")

    def test_structured_and_soft(self) -> None:
        self.assertEqual(analyze_silhouette_pair("structured", "soft")["structure_relationship"], "structured_soft_contrast")

    def test_cropped_and_high_rise(self) -> None:
        self.assertEqual(analyze_silhouette_pair("cropped", "high_rise")["length_relationship"], "cropped_with_high_rise")

    def test_dropped_shoulder_is_valid_metadata(self) -> None:
        result = normalize_silhouette("dropped shoulder")
        self.assertEqual(result["canonical_silhouette"], "dropped_shoulder")
        self.assertEqual(result["warnings"], [])

    def test_unsupported_value(self) -> None:
        result = analyze_silhouette_pair("oversized", "magic_shape")
        self.assertEqual(result["silhouettes"][0], "oversized")
        self.assertEqual(result["unsupported_values"][0]["reason"], "unsupported_silhouette")

    def test_three_item_mix(self) -> None:
        result = analyze_silhouette_mix(["oversized", "fitted", "straight"])
        self.assertEqual(result["proportion_pattern"], "loose_fitted_straight")
        self.assertEqual(result["volume_pattern"], "mixed")

    def test_no_body_shape_fields(self) -> None:
        result = analyze_silhouette_mix(["oversized", "fitted", "straight"])
        self.assertNotIn("body_shape", result)
        self.assertNotIn("flattering_score", result)
        self.assertNotIn("slimming_score", result)
