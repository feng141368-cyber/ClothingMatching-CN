# WardrobeIQ Skill

> **智能穿搭、尺码与购物决策 Skill**
> An explainable fashion decision-support skill for body-aware styling, size guidance, wardrobe matching and shopping recommendations.

WardrobeIQ Skill is an AI-agent-callable skill that turns a natural-language fashion request, plus any available profile, wardrobe, and product context, into transparent styling guidance. It is a **skill foundation**, not a website or application: there is no web UI, account system, database, or trained model in this repository.

## What it does

The foundation defines a reusable instruction contract for an AI agent to:

- Produce at least three complete, ranked outfit plans by default for outfit-generation requests.
- Support `serious_work`, `daily_casual`, `minimal`, `maximal`, `business`, `relaxed_business`, `smart_casual`, `streetwear`, `feminine`, and `classic` style modes.
- Assess whether a specific product suits known fit, style, practical, and budget goals.
- Give size guidance from supplied body measurements and a garment's size chart.
- Match known clothing before suggesting a purchase.
- Recommend accessories and assess bag capacity for a laptop, water bottle, or umbrella when dimensions are available.
- Specify a missing item before any future product search.

Only a natural-language `request` is required. Profile, wardrobe, product, size-chart, weather, and budget data are optional context; the skill records unknowns rather than inventing them. User-facing recommendations default to Chinese while JSON keys remain English for predictable agent and tool integration.

## Why I built it

Fashion advice is often opaque, product-first, and disconnected from clothes people already own. WardrobeIQ starts with the wardrobe when it is available and makes each recommendation traceable: it separates body fit, garment fit, and style intent; explains substitutions; and turns a genuine gap into a constrained shopping brief rather than an arbitrary product link.

This is **not a trained fashion AI model**. It is deliberately a rule-based, constraint-aware, explainable ranking system. The Issue 1 scope establishes the instruction, sample data, and future-facing contract; it does not claim that automated scoring, product retrieval, image understanding, size-chart extraction, or matching engines are implemented.

## Implemented foundations

- Profile Resolver ✅
- Fit Engine ✅
- Colour Engine ✅
- Material Engine ✅
- Silhouette Engine ✅
- Accessories Matcher ✅
- Wardrobe Matcher ✅
- Outfit Matcher ✅
- Shopping Resolver ✅
- Bag Capacity Engine ✅
- Look Renderer ✅
- OpenAI Image Provider ✅

## Shopping Resolver

Shopping specifications are built only from established `missing_recommendation` gaps. The production provider contract defaults to `official_sources_only: true`: a real candidate must declare `source_type: "brand_official"`, a verified official domain, and a product URL whose host exactly matches that domain. Marketplace, reseller, aggregator, missing-provenance, and domain-mismatched candidates are rejected.

The executable MVP uses only a provider-agnostic local `MockProductProvider`. Every catalog record is explicitly a `mock_fixture`, carries no official URL, and demonstrates the contract without claiming real products, stock, or availability. Product match scores are heuristic ordering signals, not measures of product quality, durability, value, authenticity, or fashion correctness. Budget currencies must match exactly; WardrobeIQ does not perform FX conversion. Preferred brands influence otherwise comparable candidates, avoided brands are excluded, and a differing declared source region is exposed as `region_mismatch`.

## Bag Capacity Engine

`estimate_bag_capacity()` derives an approximate geometric volume from known dimensions, while `analyze_carry_requirements()` checks each known item independently. Capacity estimates are approximate; independent item fit does not prove simultaneous packing; external bag dimensions may overestimate internal usable space.

```python
from scripts.capacity_estimator import estimate_bag_capacity, analyze_carry_requirements

bag = {"width_cm": 28, "height_cm": 20, "depth_cm": 11}
result = analyze_carry_requirements(
    bag,
    [{"item_type": "phone", "width_cm": 7, "height_cm": 15, "depth_cm": 1},
     {"item_type": "laptop", "width_cm": 30, "height_cm": 21, "depth_cm": 1.5}],
)
```

## Look Renderer

`build_render_spec()` and `render_outfit_prompt()` convert an existing structured outfit plan into a fashion-illustration prompt and board-style rendering specification for easier human interpretation. It supports `fashion_sketch` and `fashion_board`, plus optional hairstyle and headwear as rendering cues only; it does not generate images or alter outfit recommendations.

## Outfit Matcher

`generate_outfits()` composes bounded, wardrobe-first plans from normalized inputs and exposes transparent heuristic ranking signals. Outfit ranking is heuristic and explainable; it is not an objective measure of fashion quality.

## Core capabilities

| Capability | Foundation behaviour |
| --- | --- |
| Natural-language starting point | Works from a request alone and identifies the context that remains unknown. |
| Multi-look styling | Defines at least three ranked, complete, occasion-appropriate outfit plans by default. |
| Style modes | Defines canonical style modes without forcing an irrelevant style or occasion. |
| Body-aware styling | Uses supplied measurements and fit preferences without inferring missing body data or deriving size from weight. |
| Size guidance | Compares available body and garment measurements, then states uncertainty when a size chart is absent. |
| Wardrobe-first matching | Looks for known owned items, then substitutions, before defining a missing item or product-search specification. |
| Accessory and bag advice | Provides optional accessory slots and checks stated carry needs against stated bag capacity. |
| Explainability | Produces Chinese rationale, assumptions, trade-offs, and next details that would improve confidence. |

## Architecture

```text
Natural-language request + optional profile / wardrobe / product context
                              |
                              v
                       SKILL.md instructions
                              |
                              v
constraints -> style modes -> wardrobe-first reasoning -> ranked plans
                              |
                              v
 Chinese explanation + assumptions + shopping specification
```

## OpenAI Image Provider

WardrobeIQ optionally turns a Look Renderer spec into a generated fashion-illustration artifact through a provider-based image layer. `OpenAIImageProvider` reads the user-supplied `OPENAI_API_KEY`; `MockImageProvider` keeps tests offline. Image generation is optional, provider-dependent, and subject to prompt fidelity.

`SKILL.md` is the agent-facing interface. The JSON files in `examples/` provide an intentionally small, portable schema reference. Issue 2 implements the structured Profile Resolver, Issue 3 implements the Fit Engine, and Issue 4 implements the Colour Engine; their modules and unit tests are in `scripts/` and `tests/`. Other directories remain reserved for later implementation stages.

## Recommendation pipeline

The intended pipeline is:

1. Normalize a natural-language or structured request into occasion, goal, and known constraints.
2. Keep **body fit**, **garment fit**, and **style intent** as independent constraints.
3. Select applicable style modes; prefer supplied profile preferences and otherwise use directions relevant to the request.
4. Build and rank at least three complete outfit plans for outfit-generation requests.
5. When wardrobe data exists, check known items and substitutions before identifying a missing item.
6. Turn a genuine gap into a shopping specification before any future product search.
7. Return a Chinese explanation with assumptions and confidence limits.

Issue 2 implements the structured Profile Resolver, Issue 3 implements explainable measurement-based Fit Analysis, and Issue 4 implements deterministic colour relationship analysis. Matching, scoring, catalog search, and all other recommendation engines remain planned extensions rather than working features.

## Profile Resolver

`resolve_profile(profile_input: dict) -> dict` converts structured or partially structured profile data into the canonical Issue 1 schema. It normalizes only straightforward aliases, such as `oversize` to `oversized`, `wide leg` to `wide_leg`, `Relaxed Business` to `relaxed_business`, `soft tailoring` to `soft_tailoring`, and `grey` to `gray`.

Unsupported style modes and malformed values are reported instead of guessed. Missing optional data stays `null`, `[]`, or `{}` and is listed under `missing_fields`; the resolver does not parse arbitrary natural language or infer body measurements, body shape, or size.

```python
from scripts.profile_resolver import resolve_profile

result = resolve_profile({
    "style_modes": ["Relaxed Business"],
    "fit_preferences": {
        "blazers": "Oversize"
    }
})
```

## Fit Engine

`analyze_fit(body, garment, category)` compares only known body and garment measurements using category-specific heuristic ease rules from `data/fit_rules.json`. It reports each measurement, calculated ease, a qualitative fit classification, confidence, missing fields, and any invalid values. Shoulder construction is reported independently for shirts, blazers, and coats.

```python
from scripts.fit_engine import analyze_fit

result = analyze_fit(
    body={"bust_cm": 82, "shoulder_width_cm": 37},
    garment={"bust_cm": 100, "shoulder_width_cm": 41},
    category="blazer",
)
```

Fit analysis **is not size recommendation**. It does not infer missing measurements, leg silhouettes, body shape, or user preferences.

## Colour Engine

`normalize_color`, `analyze_color_pair`, and `analyze_palette` normalize known colour labels and describe their data-driven attributes, contrast, and explicit relationships. Colour metadata, aliases, neutral membership, and harmony pairs are maintained in `data/color_rules.json`.

```python
from scripts.color_engine import analyze_palette

result = analyze_palette([
    "black",
    "charcoal",
    "silver",
])
```

Colour relationship analysis **is not styling recommendation**. It does not analyze images, skin tone, undertone, seasonal palettes, or personal characteristics.

## Material Engine

`normalize_material`, `analyze_material_pair`, and `analyze_material_mix` normalize known material labels and describe data-driven material attributes and relationships.

```python
from scripts.material_engine import analyze_material_pair

result = analyze_material_pair(
    "wool",
    "silk",
)
```

Material relationship analysis **is not styling recommendation**. Material metadata **is not a quality rating**; it does not score quality, sustainability, or comfort.

## Silhouette Engine

```python
from scripts.silhouette_engine import analyze_silhouette_mix

result = analyze_silhouette_mix([
    "oversized",
    "fitted",
    "straight",
])
```

Silhouette relationship analysis **is not outfit recommendation**. Silhouette analysis **is not body-shape analysis**.

## Accessories Matcher

```python
from scripts.accessory_matcher import recommend_accessories

result = recommend_accessories(
    outfit_context={"colors": ["black", "charcoal"], "neckline": "turtleneck", "complexity": "low", "formality": "high"},
    accessory_preferences={"preferred_metals": ["silver"], "preferred_shapes": ["geometric"], "preferred_scale": ["small", "medium"]},
    style_mode="minimal",
)
```

Accessory matching **is not full outfit recommendation**. Accessory specification **is not product recommendation**.

## Example

The example request asks for three polished, approachable weekday client-meeting outfits built around the known oversized black blazer:

```json
{
  "occasion": "client_meeting",
  "goal": "polished_and_approachable_without_being_overly_formal",
  "must_use_item_ids": ["outerwear_black_oversized_blazer"],
  "avoid_item_ids": [],
  "requested_outfit_count": 3,
  "preferred_output_language": "zh-CN"
}
```

An agent following `SKILL.md` should first inspect supplied wardrobe data, compose and rank three complete looks from known items, explain fit and styling trade-offs in Chinese, and only then describe a missing item if necessary. Full sample inputs are in `examples/user_profile.json`, `examples/wardrobe.json`, and `examples/sample_request.json`.

## Scoring logic

The future ranking model is intentionally explainable rather than black-box. A candidate look or product is expected to be evaluated against these transparent factors:

| Factor | Intended question |
| --- | --- |
| Occasion alignment | Does it meet the dress code, activity, and practical constraints? |
| Body and garment fit | Do known measurements, intended ease, and garment shape work together? |
| Style alignment | Does it support the requested style mode, silhouette, aesthetic, and colour preferences? |
| Wardrobe compatibility | Can it combine with known owned pieces and increase outfit reuse? |
| Practicality | Is it suitable for weather, movement, comfort, care, and carry needs? |
| Budget alignment | Does the proposed item stay within the stated budget? |

No numerical weights or executable scorer are included yet. Until they exist, agents should explain qualitative trade-offs rather than fabricate a score.

## Project structure

```text
.
├── SKILL.md                   # Agent-callable instruction and output contract
├── README.md                  # Portfolio overview and scope
├── requirements.txt           # Python 3.11+ standard-library-only note
├── examples/
│   ├── user_profile.json      # Optional sizing and preference schema example
│   ├── wardrobe.json          # Known-item and unknown-capacity schema example
│   └── sample_request.json    # Wardrobe-first multi-look request
├── data/                      # Reserved for future local datasets
│   ├── accessory_rules.json    # Accessory intensity and neckline heuristics
│   ├── color_rules.json        # Canonical colours and relationship heuristics
│   ├── fit_rules.json          # Category-specific ease heuristics
│   ├── material_rules.json     # Canonical materials and relationship heuristics
│   └── silhouette_rules.json   # Canonical silhouettes and relationship heuristics
├── scripts/
│   ├── accessory_matcher.py    # Outfit context -> accessory specifications
│   ├── color_engine.py         # Known colour labels -> relationship analysis
│   ├── fit_engine.py           # Known measurements -> explainable fit analysis
│   ├── material_engine.py      # Known materials -> relationship analysis
│   ├── profile_resolver.py     # Structured input -> canonical profile resolver
│   └── silhouette_engine.py    # Known silhouettes -> relationship analysis
└── tests/
    ├── test_accessory_matcher.py # Accessories Matcher unit tests
    ├── test_color_engine.py    # Colour Engine unit tests
    ├── test_fit_engine.py      # Fit Engine unit tests
    ├── test_material_engine.py # Material Engine unit tests
    ├── test_profile_resolver.py # Resolver unit tests
    └── test_silhouette_engine.py # Silhouette Engine unit tests
    └── test_profile_resolver.py # Resolver unit tests
```

## Limitations

- No trained fashion AI model, product catalog, live search, image analysis, or recommendation service is included.
- The skill cannot validate size without reliable brand- and garment-specific measurements.
- Sample measurements and preferences are illustrative, not medical, body-shape, or personal-style diagnoses.
- Weight is intentionally absent from the sample profile and must not be used to derive body shape or size.
- Recommendations do not invent missing profile, wardrobe, garment, capacity, weather, or budget data.
- Outcomes depend on complete, current inputs and the user's stated preferences.

## Future extensions

- Rule engines for matching and the remaining documented pipeline.
- Structured validation and fixture-based tests for wardrobes and requests.
- Brand-size-chart parsing and explainable ease calculations.
- Product-search adapters that consume the shopping specification rather than bypass wardrobe-first reasoning.
- Optional weather, calendar, packing-list, and sustainability constraints.
- A persisted wardrobe inventory and confidence-aware feedback loop, if a later product scope needs them.
