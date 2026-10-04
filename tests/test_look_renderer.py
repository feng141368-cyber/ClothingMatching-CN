import unittest
from scripts.look_renderer import build_render_spec, render_outfit_prompt

PLAN={"style_mode":"relaxed_business","occasion":"client_meeting","items":{"outerwear":{"category":"blazer","color":"black"},"top":{"category":"top","color":"ivory"},"shoes":{"category":"loafers","color":"black"},"bag":{"category":"bag","color":"black"},"bottom":None},"accessories":{"earrings":{"category":"earrings","color":"silver"},"necklace":None}}
class LookRendererTests(unittest.TestCase):
 def test_default_mode(self): self.assertEqual(build_render_spec(PLAN)["render_mode"],"fashion_board")
 def test_sketch_mode(self): self.assertEqual(build_render_spec(PLAN,render_mode="fashion_sketch")["layout"]["views"],["front"])
 def test_board_layout(self): self.assertEqual(build_render_spec(PLAN)["layout"]["views"],["front","back"])
 def test_clothing_included(self): self.assertIn("outerwear",build_render_spec(PLAN)["outfit_summary"]["clothing"])
 def test_accessory_included(self): self.assertIn("earrings",build_render_spec(PLAN)["outfit_summary"]["accessories"])
 def test_hair_override(self): self.assertEqual(build_render_spec(PLAN,visual_preferences={"hairstyle":"low_bun"})["figure"]["hairstyle"],"low_bun")
 def test_hair_default(self): self.assertTrue(build_render_spec(PLAN)["figure"]["hairstyle"])
 def test_headwear(self): self.assertIn("headwear_detail",build_render_spec(PLAN,visual_preferences={"headwear":"floral_hat"})["layout"]["detail_panels"])
 def test_missing_slot_not_invented(self): self.assertNotIn("bottom",build_render_spec(PLAN)["outfit_summary"]["clothing"])
 def test_no_shopping_fields(self):
  self.assertNotIn("product_url",str(render_outfit_prompt(PLAN)))
 def test_no_body_language(self):
  text=str(render_outfit_prompt(PLAN)).lower()
  for word in ("flattering","slimming","body_shape","face_shape","beauty_score"): self.assertNotIn(word,text)
 def test_prompt_quality(self):
  text=render_outfit_prompt(PLAN)["prompt"].lower()
  for word in ("fashion illustration","front view","back view","detail"): self.assertIn(word,text)
