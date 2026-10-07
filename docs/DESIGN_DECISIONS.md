# ClothingMatching-CN Skill Design Decisions

## Wardrobe first

The system checks owned items before identifying a gap. This supports reuse, makes ownership explicit, and prevents a shopping request from bypassing available clothes.

## Uniqueness comes from real item IDs

An outfit is unique only when its major clothing, shoe, bag, or outerwear `item_id` combination differs. Style labels, ranks, and accessory-only changes do not create a new outfit.

## Requested counts are not artificially filled

`requested_outfit_count` is a target, not permission to duplicate a plan. When valid unique combinations are insufficient, the matcher returns the actual count and a warning.

## Hard constraints outrank ranking

Must-use and avoid constraints are validated before composition. Contradictory, unavailable, unsupported, or mutually incompatible must-use items produce explicit `constraint_conflicts`; ranking never overrides them.

## Unknown data remains unknown

Measurements, ownership, garment dimensions, capacity, and other absent values are not inferred. Modules report missing or unsupported information instead of presenting a fabricated result.

## Scores are heuristic

Ranking scores order local candidates by transparent signals. They are not objective fashion-quality, attractiveness, body, or commercial scores.

## Official source provenance for shopping

The shopping contract requires verified official-source provenance for real candidates. The repository uses mock fixtures only and does not perform live shopping.

## Actual image generation is deferred

The Look Renderer creates offline text specifications and prompts to make plans easier to interpret. Actual image generation is deliberately deferred: it would introduce provider cost, credentials, network behavior, and output variability outside the offline core.
