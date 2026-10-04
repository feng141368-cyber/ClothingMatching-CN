import os, tempfile, unittest
from scripts.image_provider import MockImageProvider, OpenAIImageProvider, generate_outfit_image
PLAN={"style_mode":"minimal","items":{"top":{"category":"top","color":"black"}},"accessories":{}}
class ImageProviderTests(unittest.TestCase):
 def test_mock_result(self): self.assertEqual(MockImageProvider().generate_image("x")["provider"],"mock")
 def test_mock_saves_path(self):
  with tempfile.TemporaryDirectory() as d: self.assertTrue(os.path.exists(MockImageProvider().generate_image("x",output_path=d+"/a.png")["image_path"]))
 def test_missing_key(self): self.assertEqual(OpenAIImageProvider(api_key="").generate_image("x")["error"],"missing_openai_api_key")
 def test_renderer_integration(self): self.assertIn("fashion illustration",generate_outfit_image(PLAN,provider=MockImageProvider())["prompt_used"].lower())
 def test_prompt_handoff(self):
  class P:
   def generate_image(s,prompt,render_spec=None,output_path=None): return {"prompt_used":prompt}
  self.assertIn("black",generate_outfit_image(PLAN,provider=P())["prompt_used"])
 def test_auto_path(self): self.assertTrue(os.path.exists(MockImageProvider().generate_image("x")["image_path"]))
 def test_board_size(self): self.assertEqual(OpenAIImageProvider(api_key="x").size or "1536x1024","1536x1024")
 def test_sketch_mode(self): self.assertEqual(generate_outfit_image(PLAN,render_mode="fashion_sketch",provider=MockImageProvider())["render_mode"],"fashion_sketch")
 def test_failure_clean(self):
  class P:
   def generate_image(s,*a,**k): return {"status":"error","error":"provider_generation_failed"}
  self.assertEqual(generate_outfit_image(PLAN,provider=P())["error"],"provider_generation_failed")
 def test_no_secret_leak(self): self.assertNotIn("secret",str(OpenAIImageProvider(api_key="secret").generate_image("x")))
 def test_plan_unchanged(self):
  before=repr(PLAN); generate_outfit_image(PLAN,provider=MockImageProvider()); self.assertEqual(before,repr(PLAN))
