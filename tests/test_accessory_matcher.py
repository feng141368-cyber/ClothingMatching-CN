"""Tests for constrained accessory specifications."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.accessory_matcher import recommend_accessories


class AccessoryMatcherTests(unittest.TestCase):
    def test_silver_preference_wins(self):
        result = recommend_accessories({}, {"preferred_metals": ["silver"]})
        self.assertEqual(result["recommendations"]["earrings"]["metal"], "silver")

    def test_minimal_is_limited(self):
        result = recommend_accessories({}, style_mode="minimal")
        self.assertEqual(result["recommendations"]["earrings"]["scale"], "small")
        self.assertIsNone(result["recommendations"]["bracelet"])

    def test_maximal_allows_richer_not_all_statement(self):
        result = recommend_accessories({}, style_mode="maximal")
        scales = [item["scale"] for item in result["recommendations"].values() if item]
        self.assertIn("statement", scales)
        self.assertIn("small", scales)

    def test_turtleneck_prioritizes_earrings(self):
        result = recommend_accessories({"neckline": "turtleneck"})
        self.assertIsNone(result["recommendations"]["necklace"])
        self.assertIsNotNone(result["recommendations"]["earrings"])

    def test_v_neck_supports_pendant(self):
        result = recommend_accessories({"neckline": "v_neck"})
        self.assertEqual(result["recommendations"]["necklace"]["type"], "pendant")

    def test_statement_earrings_reduce_necklace(self):
        result = recommend_accessories({"neckline": "v_neck"}, {"preferred_scale": ["statement"]}, style_mode="maximal")
        self.assertEqual(result["recommendations"]["necklace"]["scale"], "small")

    def test_avoid_overrides_maximal(self):
        result = recommend_accessories({}, {"avoid": ["statement"]}, style_mode="maximal")
        self.assertNotEqual(result["recommendations"]["earrings"]["scale"], "statement")

    def test_structured_context_prefers_geometric(self):
        result = recommend_accessories({"silhouettes": ["structured"]}, {"preferred_shapes": ["geometric"]})
        self.assertEqual(result["recommendations"]["earrings"]["shape"], "geometric")

    def test_incomplete_context_is_safe(self):
        self.assertTrue(recommend_accessories({}, {"preferred_metals": ["silver"]})["recommendations"])

    def test_no_preferences_has_conservative_defaults(self):
        result = recommend_accessories({})
        self.assertEqual(result["recommendations"]["earrings"]["scale"], "medium")

    def test_output_has_no_personal_fields(self):
        result = recommend_accessories({})
        self.assertNotIn("gender", result)
        self.assertNotIn("face_shape", result)
        self.assertNotIn("body_shape", result)

    def test_output_has_no_shopping_fields(self):
        rendered = str(recommend_accessories({}))
        for field in ("brand", "price", "product_url", "shopping_link"):
            self.assertNotIn(field, rendered)
