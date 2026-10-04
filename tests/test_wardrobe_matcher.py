import unittest
from scripts.wardrobe_matcher import match_wardrobe_item
class WardrobeMatcherTests(unittest.TestCase):
 def test_exact_and_missing(self):
  wardrobe={"items":[{"item_id":"a","category":"bottom","sub_category":"trousers","color":"charcoal","silhouette":"wide_leg"}]}
  self.assertEqual(match_wardrobe_item({"category":"bottom","sub_category":"trousers","color_family":["charcoal"],"silhouette":["wide_leg"]},wardrobe)["status"],"exact_match")
  self.assertEqual(match_wardrobe_item({"category":"bag"},wardrobe)["status"],"missing")
 def test_compatible_substitute_status(self):
  wardrobe={"items":[{"item_id":"a","category":"bottom","sub_category":"jeans","color":"black","silhouette":"straight"}]}
  self.assertEqual(match_wardrobe_item({"category":"bottom","sub_category":"trousers","color_family":["charcoal"]},wardrobe)["status"],"compatible_substitute")
 def test_substitute_source_is_preserved_in_final_plan(self):
  from scripts.outfit_matcher import generate_outfits
  wardrobe={"items":[{"item_id":"o","category":"outerwear"},{"item_id":"t","category":"top"},{"item_id":"b","category":"bottom","match_status":"compatible_substitute"},{"item_id":"s","category":"shoes"},{"item_id":"g","category":"bag"}]}
  plan=generate_outfits({},wardrobe,"client_meeting")["outfit_plans"][0]
  self.assertEqual(plan["items"]["bottom"]["source"],"substitute")
