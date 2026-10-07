"""Tests for ClothingMatching-CN Skill's data-driven colour analysis."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.color_engine import analyze_color_pair, analyze_palette, normalize_color


class ColorEngineTests(unittest.TestCase):
    """Cover the documented Issue 4 normalization and relationship contract."""

    def test_alias_normalization(self) -> None:
        self.assertEqual(normalize_color("Grey")["canonical_color"], "gray")
        self.assertEqual(normalize_color("dark-grey")["canonical_color"], "charcoal")
        self.assertEqual(normalize_color("light blue")["canonical_color"], "light_blue")

    def test_tonal_pair_has_low_contrast(self) -> None:
        result = analyze_color_pair("black", "charcoal")

        self.assertEqual(result["relationship"], "tonal")
        self.assertEqual(result["contrast"], "low")
        self.assertEqual(result["temperature_relationship"], "neutral")

    def test_high_contrast_pair(self) -> None:
        result = analyze_color_pair("black", "white")

        self.assertEqual(result["relationship"], "high_contrast")
        self.assertEqual(result["contrast"], "high")

    def test_neutral_palette(self) -> None:
        result = analyze_palette(["black", "ivory", "charcoal"])

        self.assertEqual(result["dominant_relationship"], "neutral")
        self.assertEqual(result["neutral_ratio"], 1.0)

    def test_neutral_plus_accent_palette(self) -> None:
        result = analyze_palette(["black", "charcoal", "burgundy"])

        self.assertEqual(result["dominant_relationship"], "neutral_accent")
        self.assertEqual(result["neutral_ratio"], 2 / 3)

    def test_metallic_metadata(self) -> None:
        silver = normalize_color("silver")
        gold = normalize_color("gold")

        self.assertEqual(silver["attributes"]["family"], "metallic")
        self.assertEqual(silver["attributes"]["temperature"], "cool")
        self.assertEqual(gold["attributes"]["family"], "metallic")
        self.assertEqual(gold["attributes"]["temperature"], "warm")

    def test_unsupported_colour_is_reported_without_guessing(self) -> None:
        result = normalize_color("random_core_blue")

        self.assertIsNone(result["canonical_color"])
        self.assertEqual(result["unsupported_values"][0]["reason"], "unsupported_color")

    def test_case_and_separator_normalization(self) -> None:
        expected = "light_blue"
        for value in ("LIGHT-BLUE", "light_blue", "Light Blue"):
            self.assertEqual(normalize_color(value)["canonical_color"], expected)

    def test_explicit_complementary_relationship(self) -> None:
        result = analyze_color_pair("red", "green")

        self.assertEqual(result["relationship"], "complementary")

    def test_palette_preserves_partial_unsupported_input(self) -> None:
        result = analyze_palette(["black", "charcoal", "random_core_blue"])

        self.assertEqual(result["canonical_colors"], ["black", "charcoal"])
        self.assertEqual(result["dominant_relationship"], "tonal")
        self.assertEqual(len(result["unsupported_values"]), 1)
        self.assertTrue(result["warnings"])


if __name__ == "__main__":
    unittest.main()
