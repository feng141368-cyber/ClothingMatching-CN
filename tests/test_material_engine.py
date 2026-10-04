"""Tests for WardrobeIQ's data-driven material analysis."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.material_engine import (
    analyze_material_mix,
    analyze_material_pair,
    normalize_material,
)


class MaterialEngineTests(unittest.TestCase):
    """Cover the documented Issue 5 material-analysis contract."""

    def test_alias_normalization(self) -> None:
        self.assertEqual(normalize_material("faux leather")["canonical_material"], "faux_leather")
        self.assertEqual(normalize_material("wool blend")["canonical_material"], "wool_blend")

    def test_canonical_metadata(self) -> None:
        self.assertEqual(normalize_material("wool")["attributes"]["family"], "natural")
        self.assertEqual(normalize_material("silk")["attributes"]["structure"], "fluid")
        self.assertEqual(normalize_material("denim")["attributes"]["family"], "construction")
        self.assertEqual(normalize_material("polyester")["attributes"]["family"], "synthetic")

    def test_wool_and_silk_expose_contrasts(self) -> None:
        result = analyze_material_pair("wool", "silk")

        self.assertEqual(result["texture_contrast"], "high")
        self.assertEqual(result["visual_weight_balance"], "mixed")
        self.assertEqual(result["structure_relationship"], "structured_fluid_contrast")
        self.assertEqual(result["surface_relationship"], "matte_lustrous_contrast")

    def test_low_contrast_pair(self) -> None:
        result = analyze_material_pair("cotton", "cashmere")

        self.assertEqual(result["texture_contrast"], "low")
        self.assertEqual(result["structure_relationship"], "soft_consistent")

    def test_heavy_material_mix(self) -> None:
        result = analyze_material_mix(["wool", "knit", "corduroy"])

        self.assertEqual(result["overall_visual_weight"], "heavy")
        self.assertEqual(result["texture_density"], "high")

    def test_shared_seasonality(self) -> None:
        result = analyze_material_pair("wool", "silk")

        self.assertEqual(result["shared_seasons"], ["spring", "autumn"])

    def test_unsupported_material_is_reported(self) -> None:
        result = normalize_material("magic_luxury_fabric")

        self.assertIsNone(result["canonical_material"])
        self.assertEqual(result["unsupported_values"][0]["reason"], "unsupported_material")

    def test_case_and_separator_normalization(self) -> None:
        for value in ("WOOL-BLEND", "wool blend", "wool_blend"):
            self.assertEqual(normalize_material(value)["canonical_material"], "wool_blend")

    def test_outputs_do_not_include_quality_or_ranking_fields(self) -> None:
        result = analyze_material_pair("wool", "silk")

        self.assertNotIn("quality_score", result)
        self.assertNotIn("premium_score", result)
        self.assertNotIn("ranking", result)

    def test_partial_unsupported_mix_preserves_known_summary(self) -> None:
        result = analyze_material_mix(["wool", "knit", "magic_luxury_fabric"])

        self.assertEqual(result["canonical_materials"], ["wool", "knit"])
        self.assertEqual(result["overall_visual_weight"], "heavy")
        self.assertEqual(len(result["unsupported_values"]), 1)
        self.assertTrue(result["warnings"])


if __name__ == "__main__":
    unittest.main()
