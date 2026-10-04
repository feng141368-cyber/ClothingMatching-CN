import json
import unittest
from pathlib import Path

from scripts.outfit_matcher import generate_outfits

ROOT = Path(__file__).resolve().parents[1]

def sample():
    return (json.loads((ROOT/"examples/user_profile.json").read_text()),
            json.loads((ROOT/"examples/wardrobe.json").read_text()),
            json.loads((ROOT/"examples/sample_request.json").read_text()))

def walk(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from walk(child)
    elif isinstance(value, list):
        for child in value: yield from walk(child)

class OutfitMatcherTests(unittest.TestCase):
    def result(self, **overrides):
        profile, wardrobe, request = sample()
        overrides.setdefault("must_use_item_ids", request["must_use_item_ids"])
        return generate_outfits(profile, wardrobe, request["occasion"], **overrides)

    def test_sample_e2e_returns_ranked_three_plans(self):
        plans=self.result()["outfit_plans"]; self.assertGreaterEqual(len(plans),3); self.assertEqual([p["rank"] for p in plans],list(range(1,len(plans)+1)))

    def test_must_use_blazer_appears_in_every_plan(self):
        for plan in self.result()["outfit_plans"]: self.assertTrue(any(slot and slot["item_id"]=="outerwear_black_oversized_blazer" for slot in plan["items"].values()))

    def test_avoid_item_never_appears(self):
        plans=self.result(avoid_item_ids=["top_ivory_knit_shell"])["outfit_plans"]
        self.assertTrue(all(all(not slot or slot["item_id"]!="top_ivory_knit_shell" for slot in p["items"].values()) for p in plans))

    def test_constraint_conflict_is_explicit(self):
        self.assertTrue(self.result(must_use_item_ids=["x"],avoid_item_ids=["x"])["constraint_conflicts"])

    def test_style_preference_signal_ranks_minimal_above_maximal(self):
        result=self.result(style_modes=["minimal","maximal"]); plans=result["outfit_plans"]
        self.assertGreaterEqual(next(p["ranking_signals"]["style_preference_alignment"] for p in plans if p["style_mode"]=="minimal"),next(p["ranking_signals"]["style_preference_alignment"] for p in plans if p["style_mode"]=="maximal"))

    def test_client_meeting_signal_rewards_compatible_mode(self):
        plans=self.result(style_modes=["party","relaxed_business"])["outfit_plans"]
        self.assertGreater(next(p["ranking_signals"]["occasion_alignment"] for p in plans if p["style_mode"]=="relaxed_business"),next(p["ranking_signals"]["occasion_alignment"] for p in plans if p["style_mode"]=="party"))

    def test_coverage_excludes_accessories(self):
        coverage=self.result()["outfit_plans"][0]["wardrobe_coverage"]
        self.assertEqual(coverage["coverage_ratio"], coverage["owned_or_substituted_major_items"]/coverage["required_major_items"])

    def test_color_engine_analysis_is_exposed(self):
        self.assertIn("contrast",self.result()["outfit_plans"][0]["analysis"]["color"])

    def test_material_engine_analysis_is_exposed(self):
        self.assertIn("texture_density",self.result()["outfit_plans"][0]["analysis"]["material"])

    def test_silhouette_engine_analysis_is_exposed(self):
        self.assertIn("canonical_silhouettes",self.result()["outfit_plans"][0]["analysis"]["silhouette"])

    def test_accessory_matcher_output_is_exposed(self):
        self.assertIn("earrings",self.result()["outfit_plans"][0]["accessories"])

    def test_three_plans_differ_by_style_or_major_slot(self):
        plans=self.result()["outfit_plans"]; fingerprints={(p["style_mode"],tuple((slot or {}).get("item_id") for slot in p["items"].values())) for p in plans}
        self.assertEqual(len(fingerprints),len(plans))

    def test_output_has_no_shopping_fields(self):
        self.assertFalse({"brand","price","product_url","retailer","shopping_link","sku"} & set(walk(self.result())))

    def test_output_has_no_body_desirability_fields(self):
        self.assertFalse({"beauty_score","attractiveness","body_score","flattering_score","slimming_score"} & set(walk(self.result())))
