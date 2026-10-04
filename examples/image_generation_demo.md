# Optional image generation demo

Use an existing outfit plan with the renderer and a provider:

```python
from scripts.image_provider import OpenAIImageProvider, generate_outfit_image

result = generate_outfit_image(outfit_plan, provider=OpenAIImageProvider(), output_path="outputs/look.png")
```

The structured result includes `status`, `prompt_used`, `image_path`, `render_mode`, and `render_spec`. Real generation requires a user-supplied `OPENAI_API_KEY`; no key or generated image is included in this repository.
