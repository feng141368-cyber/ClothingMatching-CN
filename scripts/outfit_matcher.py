"""Bounded, explainable ClothingMatching-CN Skill outfit generation."""
from __future__ import annotations
import json
from itertools import product
from functools import lru_cache
from pathlib import Path
from typing import Any
from scripts.accessory_matcher import recommend_accessories
from scripts.color_engine import analyze_palette
from scripts.material_engine import analyze_material_mix
from scripts.silhouette_engine import analyze_silhouette_mix

RULES_PATH = Path(__file__).resolve().parents[1] / "data" / "outfit_rules.json"
SLOTS = ("outerwear", "top", "bottom", "dress_or_one_piece", "shoes", "bag")
SLOT_BY_CATEGORY = {
    "outerwear": "outerwear",
    "top": "top",
    "bottom": "bottom",
    "dress": "dress_or_one_piece",
    "one_piece": "dress_or_one_piece",
    "shoes": "shoes",
    "bag": "bag",
}

def generate_outfits(user_profile: dict[str, Any] | None, wardrobe: dict[str, Any] | None, occasion: str | None, style_modes: list[str] | None = None, must_use_item_ids: list[str] | None = None, avoid_item_ids: list[str] | None = None, requested_outfit_count: int = 3) -> dict[str, Any]:
    rules = _rules(); profile = user_profile or {}; wardrobe = wardrobe or {}; must = set(must_use_item_ids or []); avoid = set(avoid_item_ids or [])
    conflicts = []
    if must & avoid: conflicts.append("must_use_item_ids conflicts with avoid_item_ids.")
    if not isinstance(requested_outfit_count, int) or requested_outfit_count < 1 or requested_outfit_count > 5:
        conflicts.append("requested_outfit_count must be an integer from 1 to 5."); requested_outfit_count = 3
    all_items = wardrobe.get("items", [])
    item_by_id = {item.get("item_id"): item for item in all_items if item.get("item_id")}
    unavailable_must = sorted(item_id for item_id in must if item_id not in item_by_id)
    if unavailable_must:
        conflicts.append(f"must_use_item_ids are not in the wardrobe: {', '.join(unavailable_must)}.")
    must_by_slot: dict[str, list[dict[str, Any]]] = {}
    for item_id in must:
        item = item_by_id.get(item_id)
        if not item:
            continue
        slot = SLOT_BY_CATEGORY.get(item.get("category"))
        if slot is None:
            conflicts.append(f"must-use item {item_id} has no supported outfit slot.")
            continue
        must_by_slot.setdefault(slot, []).append(item)
    for slot, required_items in must_by_slot.items():
        if len(required_items) > 1:
            conflicts.append(f"multiple must-use items require the single {slot} slot.")
    if "dress_or_one_piece" in must_by_slot and ({"top", "bottom"} & must_by_slot.keys()):
        conflicts.append("dress_or_one_piece cannot be combined with must-use top or bottom items.")
    items = [item for item in all_items if item.get("item_id") not in avoid]
    missing = ["weather", "garment_measurements", "neckline"]
    if conflicts: return {"outfit_plans": [], "assumptions": [], "warnings": [], "constraint_conflicts": conflicts, "missing_information": missing}
    requested = style_modes or profile.get("style_modes") or rules["occasions"].get(occasion, {}).get("style_modes", ["minimal", "daily_casual", "serious_work"])
    plans = []
    seen_combinations = set()
    for template in rules["templates"]:
        for plan_items in _compose_combinations(items, template["name"], must_by_slot):
            major_item_ids = tuple(
                (plan_items[slot] or {}).get("item_id") for slot in SLOTS
            )
            if major_item_ids in seen_combinations:
                continue
            seen_combinations.add(major_item_ids)
            mode = _select_style_mode(requested, plan_items, occasion, profile, rules)
            plans.append(_plan(plan_items, mode, occasion, profile, rules, must))
    plans.sort(key=lambda plan: plan["ranking_score"], reverse=True)
    for rank, plan in enumerate(plans, 1): plan["rank"] = rank
    returned = plans[:requested_outfit_count]
    warnings = []
    if len(returned) < requested_outfit_count:
        warnings.append(
            f"Only {len(returned)} valid unique major-item combinations are available; "
            f"{requested_outfit_count} were requested."
        )
    return {"outfit_plans": returned, "assumptions": ["Weather and neckline are unknown."], "warnings": warnings, "constraint_conflicts": [], "missing_information": missing}

def _compose_combinations(items, template_name, must_by_slot):
    slots = ("outerwear", "top", "bottom", "shoes", "bag") if template_name == "separates" else ("outerwear", "dress_or_one_piece", "shoes", "bag")
    inactive_slots = {"dress_or_one_piece"} if template_name == "separates" else {"top", "bottom"}
    if template_name == "separates" and "dress_or_one_piece" in must_by_slot:
        return
    if template_name == "dress" and ({"top", "bottom"} & must_by_slot.keys()):
        return
    choices = []
    for slot in slots:
        category_choices = must_by_slot.get(slot) or [
            item for item in items if SLOT_BY_CATEGORY.get(item.get("category")) == slot
        ]
        if not category_choices:
            return
        choices.append(category_choices)
    for selected in product(*choices):
        plan = {slot: None for slot in SLOTS}
        plan.update(dict(zip(slots, selected)))
        for slot in inactive_slots:
            plan[slot] = None
        yield plan

def _select_style_mode(modes, items, occasion, profile, rules):
    available_modes = modes or ["minimal"]
    return max(
        available_modes,
        key=lambda mode: _style_score(mode, items, occasion, profile, rules),
    )

def _style_score(mode, items, occasion, profile, rules):
    clothing = [item for item in items.values() if item]
    item_alignment = sum(mode in item.get("style_tags", []) for item in clothing) / len(clothing)
    preference = 1.0 if mode in profile.get("style_modes", []) else 0.0
    occasion_alignment = 1.0 if mode in rules["occasions"].get(occasion, {}).get("style_modes", []) else 0.0
    return item_alignment + preference + occasion_alignment

def _plan(items, mode, occasion, profile, rules, must):
    clothing=[item for item in items.values() if item and not item.get("_missing")]
    colors=[item.get("color") for item in clothing if item.get("color")]
    materials=[item.get("material") for item in clothing if item.get("material")]
    silhouettes=[item.get("silhouette") for item in clothing if item.get("silhouette")]
    context={"colors": colors, "materials": materials, "silhouettes": silhouettes, "neckline": "unknown", "complexity": "low", "formality": rules["occasions"].get(occasion, {}).get("formality", "medium")}
    accessories=recommend_accessories(context, profile.get("accessory_preferences"), occasion, mode)["recommendations"]
    structured={}
    required=sum(item is not None for item in items.values()); owned=0
    for slot, item in items.items():
        if item is None: structured[slot]=None; continue
        if item.get("_missing"):
            structured[slot]={"item_id": None, "source": "missing_recommendation", "requirement": {"category": item["_missing"]}}; continue
        match_status=item.get("match_status", "exact_match")
        source="must_use" if item.get("item_id") in must else ("substitute" if match_status == "compatible_substitute" else "owned"); owned+=1
        structured[slot]={"item_id": item.get("item_id"), "source": source, "match_status": match_status}
    coverage=owned/required if required else 0
    preferred_colors = set(profile.get("color_preferences", {}).get("preferred", []))
    color_alignment = sum(color in preferred_colors for color in colors) / len(colors) if colors else 0.0
    style_alignment = sum(mode in item.get("style_tags", []) for item in clothing) / len(clothing) if clothing else 0.0
    occasion_items = sum(occasion in item.get("occasion_tags", []) for item in clothing) / len(clothing) if clothing else 0.0
    occasion_mode = 1.0 if mode in rules["occasions"].get(occasion, {}).get("style_modes", []) else 0.0
    fit_slots = {"top": "tops", "bottom": "trousers", "dress_or_one_piece": "dresses", "outerwear": "blazers"}
    fitted = [
        items[slot].get("fit") == profile.get("fit_preferences", {}).get(preference)
        for slot, preference in fit_slots.items() if items.get(slot)
    ]
    signals={"style_preference_alignment": (1.0 if mode in profile.get("style_modes", []) else 0.5) * (0.5 + 0.5 * style_alignment), "occasion_alignment": (occasion_mode + occasion_items) / 2, "wardrobe_coverage": coverage, "color_coherence": color_alignment, "silhouette_alignment": 1.0 if silhouettes else 0.0, "material_coherence": 1.0 if materials else 0.0, "fit_preference_alignment": sum(fitted) / len(fitted) if fitted else 0.0}
    score=sum(rules["ranking_weights"][key]*value for key,value in signals.items())
    return {"rank": 0, "style_mode": mode, "occasion": occasion, "items": structured, "accessories": accessories, "wardrobe_coverage": {"required_major_items": required, "owned_or_substituted_major_items": owned, "missing_major_items": required-owned, "coverage_ratio": coverage}, "analysis": {"color": analyze_palette(colors) if len(colors)>=2 else {}, "material": analyze_material_mix(materials) if len(materials)>=2 else {}, "silhouette": analyze_silhouette_mix(silhouettes) if len(silhouettes)>=2 else {}}, "ranking_signals": signals, "ranking_score": score, "rationale": ["Ranking is a heuristic ordering signal, not an objective measure of fashion quality."]}

@lru_cache
def _rules():
    with RULES_PATH.open(encoding="utf-8") as source: return json.load(source)
