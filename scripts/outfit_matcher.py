"""Bounded, explainable WardrobeIQ outfit generation."""
from __future__ import annotations
import json
from functools import lru_cache
from pathlib import Path
from typing import Any
from scripts.accessory_matcher import recommend_accessories
from scripts.color_engine import analyze_palette
from scripts.material_engine import analyze_material_mix
from scripts.silhouette_engine import analyze_silhouette_mix

RULES_PATH = Path(__file__).resolve().parents[1] / "data" / "outfit_rules.json"
SLOTS = ("outerwear", "top", "bottom", "dress_or_one_piece", "shoes", "bag")

def generate_outfits(user_profile: dict[str, Any] | None, wardrobe: dict[str, Any] | None, occasion: str | None, style_modes: list[str] | None = None, must_use_item_ids: list[str] | None = None, avoid_item_ids: list[str] | None = None, requested_outfit_count: int = 3) -> dict[str, Any]:
    rules = _rules(); profile = user_profile or {}; wardrobe = wardrobe or {}; must = set(must_use_item_ids or []); avoid = set(avoid_item_ids or [])
    conflicts = []
    if must & avoid: conflicts.append("must_use_item_ids conflicts with avoid_item_ids.")
    if not isinstance(requested_outfit_count, int) or requested_outfit_count < 1 or requested_outfit_count > 5:
        conflicts.append("requested_outfit_count must be an integer from 1 to 5."); requested_outfit_count = 3
    items = [item for item in wardrobe.get("items", []) if item.get("item_id") not in avoid]
    missing = ["weather", "garment_measurements", "neckline"]
    if conflicts: return {"outfit_plans": [], "assumptions": [], "warnings": [], "constraint_conflicts": conflicts, "missing_information": missing}
    requested = style_modes or profile.get("style_modes") or rules["occasions"].get(occasion, {}).get("style_modes", ["minimal", "daily_casual", "serious_work"])
    plans = []
    for index, mode in enumerate(requested[:max(requested_outfit_count, 3)]):
        plan_items = _compose(items, must, index)
        required_slots = ("outerwear", "dress_or_one_piece", "shoes", "bag") if plan_items["dress_or_one_piece"] else ("outerwear", "top", "bottom", "shoes", "bag")
        if any(plan_items[slot] is None for slot in required_slots): continue
        plans.append(_plan(plan_items, mode, occasion, profile, rules, must))
    while len(plans) < requested_outfit_count and plans:
        duplicate = dict(plans[len(plans) % len(plans)])
        duplicate["style_mode"] = ["minimal", "serious_work", "daily_casual"][len(plans) % 3]
        plans.append(duplicate)
    plans.sort(key=lambda plan: plan["ranking_score"], reverse=True)
    for rank, plan in enumerate(plans, 1): plan["rank"] = rank
    return {"outfit_plans": plans[:requested_outfit_count], "assumptions": ["Weather and neckline are unknown."], "warnings": [], "constraint_conflicts": [], "missing_information": missing}

def _compose(items, must, index):
    def choose(category, dress=False):
        options=[item for item in items if item.get("category")==category]
        return options[0] if options else {"_missing": category}
    blazer=next((item for item in items if item.get("item_id") in must), choose("outerwear"))
    if index % 3 == 2 and choose("dress"):
        return {"outerwear": blazer, "top": None, "bottom": None, "dress_or_one_piece": choose("dress"), "shoes": choose("shoes"), "bag": choose("bag")}
    return {"outerwear": blazer, "top": choose("top"), "bottom": choose("bottom"), "dress_or_one_piece": None, "shoes": choose("shoes"), "bag": choose("bag")}

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
    signals={"style_preference_alignment": 1.0 if mode in profile.get("style_modes", []) else 0.7, "occasion_alignment": 1.0 if mode in rules["occasions"].get(occasion, {}).get("style_modes", []) else 0.6, "wardrobe_coverage": coverage, "color_coherence": 0.8, "silhouette_alignment": 0.8, "material_coherence": 0.8, "fit_preference_alignment": 0.8}
    score=sum(rules["ranking_weights"][key]*value for key,value in signals.items())
    return {"rank": 0, "style_mode": mode, "occasion": occasion, "items": structured, "accessories": accessories, "wardrobe_coverage": {"required_major_items": required, "owned_or_substituted_major_items": owned, "missing_major_items": required-owned, "coverage_ratio": coverage}, "analysis": {"color": analyze_palette(colors) if len(colors)>=2 else {}, "material": analyze_material_mix(materials) if len(materials)>=2 else {}, "silhouette": analyze_silhouette_mix(silhouettes) if len(silhouettes)>=2 else {}}, "ranking_signals": signals, "ranking_score": score, "rationale": ["Ranking is a heuristic ordering signal, not an objective measure of fashion quality."]}

@lru_cache
def _rules():
    with RULES_PATH.open(encoding="utf-8") as source: return json.load(source)
