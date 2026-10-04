## Name

WardrobeIQ Skill — 智能穿搭、尺码与购物决策 Skill

## Purpose

Provide explainable fashion decision support for body-aware styling, size guidance, wardrobe matching, and shopping recommendations. This is an AI-agent-callable skill, not a website or application. Default all user-facing prose to Chinese unless the user requests another language; retain English JSON and code keys.

## When to Use

Use this skill when a user asks for:

- An outfit composition or several looks for a situation.
- Whether a specific product is suitable.
- A size recommendation from body data and, when available, a garment size chart.
- Matching with their existing wardrobe.
- Work, date, or daily styling.
- Accessory advice.
- Whether a bag can hold a laptop, water bottle, or umbrella.
- Whether a bag can approximately hold a known laptop, A4 document, 500ml bottle, or other stated carry item.
- Shopping recommendations for items missing from their wardrobe.
- A fashion sketch, fashion illustration board, or lookbook-sheet rendering of an existing outfit plan.

## Required Inputs

- `request`: a natural-language request or structured request describing the user's task, goal, occasion, or constraints.

The skill must work when this is the only input. Treat all unstated information as unknown. Never invent body measurements, garment dimensions, product capacity, ownership, budget, or preferences.

## Optional Inputs

- `user_profile`: body measurements, canonical fit preferences, style modes, colours, accessory preferences, usage contexts, and budget. Use `examples/user_profile.json` as the reference shape when supplied.
- `wardrobe`: the user's known items. Use the `items` shape in `examples/wardrobe.json` when supplied; the wardrobe, not a request field, establishes ownership.
- `product`: product name, category, price, colour, material, silhouette, size chart, garment measurements, care, and optional bag `dimensions_cm` or `capacity_l`.
- `size_chart`: brand- and garment-specific sizing information, if it is separate from `product`.
- `weather`: temperature, precipitation, wind, and indoor/outdoor context.
- `dress_code`, `duration`, `activity_level`, comfort needs, and carry-item dimensions.
- `must_use_item_ids`: owned items that must appear in a proposed outfit.
- `avoid_item_ids`: owned items that must not appear in a proposed outfit.
- `preferred_output_language`: defaults to `zh-CN`.

## Workflow

1. Extract occasion, goal, constraints, and known facts from the request. A natural-language request alone is sufficient to begin.
2. Separate three independent decisions: **body fit** (known body measurements and comfort), **garment fit** (cut, measurements, intended ease, and size chart), and **style intent** (occasion, silhouette, colours, and aesthetic). Do not use one as a substitute for another.
3. For outfit-generation requests, determine the applicable style modes. Support `serious_work`, `daily_casual`, `minimal`, and `maximal`; also support `business`, `relaxed_business`, `smart_casual`, `streetwear`, `feminine`, and `classic`.
4. Apply Wardrobe First in this strict order when wardrobe data is available: existing wardrobe -> substitutions -> missing item -> shopping specification -> product search. When no wardrobe is supplied, state that ownership is unknown and do not claim an item is owned.
5. Build and rank at least three complete, occasion-appropriate outfit plans by default. Rank them according to the user's supplied style preferences when available. Do not introduce an irrelevant date, social, or other occasion direction.
6. If no style preference exists, use reasonable directions that fit the request; `serious_work`, `daily_casual`, and `minimal` are suitable defaults when relevant, with `maximal` available as an additional direction.
7. If an item is genuinely missing, define a shopping specification with category, target fit and silhouette, preferred colours/materials, required features, compatibility with known items, budget, brand preferences, and shopping region. Search products only after this specification exists. For real results, accept only verified official brand product pages; reject marketplace, reseller, aggregator, missing-provenance, and domain-mismatched candidates. Do not convert currencies; state a currency mismatch instead.
8. For size advice, compare stated body data with the brand or garment size chart, identify the intended garment fit, and explain uncertainty. Do not give a definitive size when reliable dimensions are unavailable.
9. For bag capacity, use the Bag Capacity Engine to compare stated dimensions or capacity with each stated carry item. Require known dimensions where exact fit matters; report unknown rather than guessing. Treat every item-fit result as independent, not proof of simultaneous packing.
10. Return concise Chinese recommendations, rationale, assumptions, alternatives, and any information that would materially improve confidence.
11. For a requested visual render, pass the existing outfit plan to the Look Renderer. Hairstyle and headwear may be supplied as visual preferences; otherwise use bounded rendering defaults. They are rendering cues only, never grooming or outfit recommendations.

## Recommendation Rules

- Prioritize occasion, practicality, comfort, and wardrobe reuse before novelty.
- Prefer known owned items that satisfy the brief; do not recommend shopping merely to create variety.
- Keep colour, proportion, silhouette, and texture coherent with the user's style intent.
- Distinguish “can wear” from “best choice” and explain the deciding constraints.
- Treat price as a budget constraint, not a proxy for quality or suitability.
- Recommend accessories only when they improve proportion, formality, function, or the stated style direction.
- For product suitability, assess compatibility with the wardrobe, body and garment fit separately, style intent, practical needs, and budget.
- Use canonical machine-readable enum values in structured data, such as `client_meeting`, `relaxed_business`, `wool_blend`, `wide_leg`, and `soft_tailoring`.
- Flag assumptions in Chinese, state confidence limits, and avoid unsupported claims about sizing, capacity, stock, price, or product performance.

## Output Contract

Respond in Chinese by default with these elements, omitting only those that are irrelevant:

1. `推荐结论`: the ranked recommendation summary.
2. `搭配方案`: for an outfit-generation request, at least three complete, ranked outfit plans by default. Each plan may include `outerwear`, `top`, `bottom`, `dress_or_one_piece`, `shoes`, `bag`, `earrings`, `necklace`, `ring`, `bracelet`, and `watch`. Set irrelevant accessories or clothing slots to `None`; do not force every slot to be populated.
3. `理由`: occasion, style mode, proportion, colour, practicality, and known wardrobe-compatibility rationale for each plan.
4. `尺码/容量判断`: only when relevant; distinguish evidence from uncertainty.
5. `缺失单品与购物规格`: only if the known wardrobe cannot meet the need; provide a specification before any product search.
6. `假设与补充信息`: explicit assumptions, unknowns, and the details that would improve the result.

Use English keys when a JSON response is requested. Include `outfit_plans`, `assumptions`, `confidence_notes`, and `missing_information`; each item in `outfit_plans` should expose the complete-look slots above, with `null` for irrelevant JSON fields.

## Fallback Behaviour

When only a natural-language request or incomplete data is available, still provide at least three general but complete outfit plans in Chinese that fit the user's stated occasion and goal. Flag each assumption, do not invent body, profile, wardrobe, garment, capacity, or product data, and avoid definitive fit, size, capacity, or product claims. Do not force a date or social look for a work, interview, or other unrelated occasion. State which optional details would improve the result, such as body measurements, garment size chart, wardrobe inventory, target occasion, weather, preferred fit, style modes, colour preferences, carry-item dimensions, and budget.

## Examples

Use the sample files as a linked input set:

- `examples/user_profile.json`: optional profile schema with sizing, canonical preferences, and structured accessory data.
- `examples/wardrobe.json`: optional wardrobe schema with an owned black oversized blazer and unknown bag-capacity fields represented as `null`.
- `examples/sample_request.json`: a wardrobe-first `client_meeting` request using `must_use_item_ids` and `avoid_item_ids`.

For the sample request, begin with `outerwear_black_oversized_blazer`, compose at least three `relaxed_business` or `minimal` client-meeting plans from compatible known items, explain the result in Chinese, and define a missing-item specification only if the available wardrobe cannot achieve the stated goal.
