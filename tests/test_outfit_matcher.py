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

    def test_sample_returns_only_its_two_real_unique_combinations(self):
        result=self.result(); plans=result["outfit_plans"]
        self.assertEqual(len(plans),2)
        self.assertEqual([p["rank"] for p in plans],list(range(1,len(plans)+1)))
        self.assertTrue(result["warnings"])

    def test_must_use_blazer_appears_in_every_plan(self):
        for plan in self.result()["outfit_plans"]: self.assertTrue(any(slot and slot["item_id"]=="outerwear_black_oversized_blazer" for slot in plan["items"].values()))

    def test_avoid_item_never_appears(self):
        plans=self.result(avoid_item_ids=["top_ivory_knit_shell"])["outfit_plans"]
        self.assertTrue(all(all(not slot or slot["item_id"]!="top_ivory_knit_shell" for slot in p["items"].values()) for p in plans))

    def test_constraint_conflict_is_explicit(self):
        self.assertTrue(self.result(must_use_item_ids=["x"],avoid_item_ids=["x"])["constraint_conflicts"])

    def test_style_preference_signal_uses_actual_item_tags(self):
        result=self.result(style_modes=["minimal","maximal"]); plans=result["outfit_plans"]
        self.assertTrue(all(p["style_mode"]=="minimal" for p in plans))
        self.assertTrue(all(p["ranking_signals"]["style_preference_alignment"] > 0 for p in plans))

    def test_client_meeting_signal_rewards_compatible_mode(self):
        plans=self.result(style_modes=["party","relaxed_business"])["outfit_plans"]
        self.assertTrue(all(p["style_mode"]=="relaxed_business" for p in plans))
        self.assertTrue(all(p["ranking_signals"]["occasion_alignment"] > 0 for p in plans))

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

    def test_plans_differ_by_major_item_ids_not_style_name(self):
        plans=self.result()["outfit_plans"]; fingerprints={tuple((p["items"][slot] or {}).get("item_id") for slot in ("outerwear","top","bottom","dress_or_one_piece","shoes","bag")) for p in plans}
        self.assertEqual(len(fingerprints),len(plans))

    def test_separates_use_real_top_and_bottom_combinations(self):
        profile, wardrobe, request = sample()
        wardrobe["items"].append({**wardrobe["items"][1], "item_id": "top_black_mock", "color": "black"})
        wardrobe["items"].append({**wardrobe["items"][2], "item_id": "bottom_navy_mock", "color": "navy"})
        result=generate_outfits(profile, wardrobe, request["occasion"], must_use_item_ids=request["must_use_item_ids"], requested_outfit_count=5)
        separates=[plan for plan in result["outfit_plans"] if plan["items"]["dress_or_one_piece"] is None]
        fingerprints={(plan["items"]["top"]["item_id"], plan["items"]["bottom"]["item_id"]) for plan in separates}
        self.assertEqual(len(fingerprints),4)

    def test_must_use_item_is_placed_in_its_actual_category(self):
        profile, wardrobe, request = sample()
        result=generate_outfits(profile, wardrobe, request["occasion"], must_use_item_ids=["top_ivory_knit_shell"], requested_outfit_count=3)
        self.assertTrue(all(plan["items"]["top"]["item_id"]=="top_ivory_knit_shell" for plan in result["outfit_plans"]))
        self.assertTrue(all(plan["items"]["outerwear"]["item_id"]=="outerwear_black_oversized_blazer" for plan in result["outfit_plans"]))

    def test_unavailable_must_use_item_is_explicit(self):
        result=self.result(must_use_item_ids=["not_in_wardrobe"])
        self.assertEqual(result["outfit_plans"],[])
        self.assertTrue(result["constraint_conflicts"])

    def test_incompatible_dress_and_top_must_use_is_explicit(self):
        result=self.result(must_use_item_ids=["dress_navy_knit_midi", "top_ivory_knit_shell"])
        self.assertEqual(result["outfit_plans"],[])
        self.assertTrue(result["constraint_conflicts"])

    def test_avoid_required_item_reduces_actual_combinations(self):
        result=self.result(avoid_item_ids=["outerwear_black_oversized_blazer"])
        self.assertEqual(result["outfit_plans"],[])
        self.assertTrue(result["constraint_conflicts"])

    def test_dress_combination_has_no_top_or_bottom(self):
        dress_plan=next(plan for plan in self.result()["outfit_plans"] if plan["items"]["dress_or_one_piece"])
        self.assertEqual(dress_plan["items"]["dress_or_one_piece"]["item_id"],"dress_navy_knit_midi")
        self.assertIsNone(dress_plan["items"]["top"])
        self.assertIsNone(dress_plan["items"]["bottom"])

    def test_actual_content_scores_are_sorted_without_copying(self):
        profile, wardrobe, request = sample()
        wardrobe["items"].append({**wardrobe["items"][1], "item_id": "top_red_party", "color": "red", "style_tags": ["party"], "occasion_tags": ["party"]})
        result=generate_outfits(profile, wardrobe, request["occasion"], must_use_item_ids=request["must_use_item_ids"], requested_outfit_count=4)
        scores=[plan["ranking_score"] for plan in result["outfit_plans"]]
        self.assertEqual(scores,sorted(scores,reverse=True))
        self.assertGreater(len(set(scores)),1)

    def test_output_has_no_shopping_fields(self):
        self.assertFalse({"brand","price","product_url","retailer","shopping_link","sku"} & set(walk(self.result())))

    def test_output_has_no_body_desirability_fields(self):
        self.assertFalse({"beauty_score","attractiveness","body_score","flattering_score","slimming_score"} & set(walk(self.result())))
