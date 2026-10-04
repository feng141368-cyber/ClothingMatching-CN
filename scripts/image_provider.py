"""Optional provider-based image generation for Look Renderer prompts."""
from __future__ import annotations
import base64
import json
import os
from pathlib import Path
from typing import Any, Protocol
from urllib.request import Request, urlopen
from scripts.look_renderer import render_outfit_prompt

class ImageProvider(Protocol):
 def generate_image(self, prompt: str, render_spec: dict[str, Any] | None = None, output_path: str | None = None) -> dict[str, Any]: ...

def _path(output_path):
 path = Path(output_path or "outputs/generated_look.png"); path.parent.mkdir(parents=True, exist_ok=True); return path

class MockImageProvider:
 def generate_image(self, prompt, render_spec=None, output_path=None):
  path = _path(output_path); path.write_bytes(b"mock-image-artifact")
  return {"provider":"mock","status":"generated","prompt_used":prompt,"image_path":str(path),"model":None,"warnings":["mock_artifact"],"missing_information":[]}

class OpenAIImageProvider:
 def __init__(self, model="gpt-image-1", size=None, quality="medium", background=None, output_format="png", api_key=None):
  self.model, self.size, self.quality, self.background, self.output_format = model, size, quality, background, output_format
  self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
 def generate_image(self, prompt, render_spec=None, output_path=None):
  if not self.api_key: return {"provider":"openai","status":"error","error":"missing_openai_api_key","warnings":[]}
  mode=(render_spec or {}).get("render_mode","fashion_board"); size=self.size or ("1536x1024" if mode=="fashion_board" else "1024x1536")
  body={"model":self.model,"prompt":prompt,"size":size,"quality":self.quality,"output_format":self.output_format}
  if self.background: body["background"]=self.background
  try:
   request=Request("https://api.openai.com/v1/images/generations",data=json.dumps(body).encode(),headers={"Authorization":f"Bearer {self.api_key}","Content-Type":"application/json"},method="POST")
   response=json.loads(urlopen(request, timeout=60).read())
   encoded=response.get("data",[{}])[0].get("b64_json")
   if not encoded: return {"provider":"openai","status":"error","error":"invalid_generation_response","warnings":[]}
   path=_path(output_path); path.write_bytes(base64.b64decode(encoded))
   return {"provider":"openai","status":"generated","prompt_used":prompt,"image_path":str(path),"model":self.model,"size":size,"warnings":[],"missing_information":[]}
  except Exception:
   return {"provider":"openai","status":"error","error":"provider_generation_failed","warnings":[]}

def generate_outfit_image(outfit_plan, user_profile=None, render_mode="fashion_board", visual_preferences=None, provider=None, output_path=None):
 render=render_outfit_prompt(outfit_plan,user_profile,render_mode,visual_preferences)
 result=(provider or OpenAIImageProvider()).generate_image(render["prompt"],render["render_spec"],output_path)
 result["render_mode"]=render["render_mode"]; result["render_spec"]=render["render_spec"]
 return result
