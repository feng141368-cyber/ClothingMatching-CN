"""Translate an existing outfit plan into a non-generative illustration specification."""
from __future__ import annotations
from typing import Any

_HAIR = {"serious_work": "low_bun", "business": "sleek_ponytail", "relaxed_business": "soft_ponytail", "minimal": "straight_long", "feminine": "loose_waves", "maximal": "editorial_updo"}

def _known(value):
    return isinstance(value, dict) and value.get("source") != "missing_recommendation"

def _describe(value):
    if not _known(value): return None
    fields = [value.get(k) for k in ("color", "fit", "silhouette", "material", "sub_category", "category") if value.get(k)]
    if not fields and value.get("name"): fields = [value["name"]]
    return " ".join(str(v).replace("_", " ") for v in fields) or None

def build_render_spec(outfit_plan: dict[str, Any], user_profile: dict[str, Any] | None = None, render_mode: str = "fashion_board", visual_preferences: dict[str, Any] | None = None) -> dict[str, Any]:
    prefs = visual_preferences or {}; mode = render_mode if render_mode in {"fashion_board", "fashion_sketch"} else "fashion_board"
    items = outfit_plan.get("items", outfit_plan.get("slots", {})); accessories = outfit_plan.get("accessories", {})
    style = outfit_plan.get("style_mode") or (user_profile or {}).get("style_modes", [None])[0]
    hair = prefs.get("hairstyle") or _HAIR.get(style, "soft_ponytail")
    clothing = {key: _describe(value) for key, value in items.items() if _describe(value)}
    adornments = {key: _describe(value) for key, value in accessories.items() if _describe(value)}
    panels = []
    if prefs.get("headwear"): panels.append("headwear_detail")
    if adornments.get("earrings") or adornments.get("necklace"): panels.append("neckline_and_jewellery")
    if clothing: panels.append("fabric_detail")
    if clothing.get("shoes"): panels.append("shoe_detail")
    if clothing.get("bag"): panels.append("bag_detail")
    layout = {"views": ["front"] if mode == "fashion_sketch" else ["front", "back"], "detail_panels": panels[:5], "background": prefs.get("background_tone", "warm_ivory"), "typography_style": "editorial_serif_with_handwritten_accents" if mode == "fashion_board" else "minimal_annotation"}
    warnings = ["partial_outfit_rendered"] if any(isinstance(v,dict) and v.get("source") == "missing_recommendation" for v in items.values()) else []
    return {"render_mode": mode, "layout": layout, "figure": {"hairstyle": hair, "hair_length": prefs.get("hair_length"), "hair_texture": prefs.get("hair_texture"), "headwear": prefs.get("headwear", "none"), "pose": prefs.get("figure_pose", "front_facing_relaxed")}, "outfit_summary": {"style_mode": style, "occasion": outfit_plan.get("occasion"), "clothing": clothing, "accessories": adornments}, "style_notes": ["rendering_cues_only"], "warnings": warnings}

def render_outfit_prompt(outfit_plan: dict[str, Any], user_profile: dict[str, Any] | None = None, render_mode: str = "fashion_board", visual_preferences: dict[str, Any] | None = None) -> dict[str, Any]:
    spec = build_render_spec(outfit_plan, user_profile, render_mode, visual_preferences)
    s, f, l = spec["outfit_summary"], spec["figure"], spec["layout"]
    garments = ", ".join(s["clothing"].values()) or "known outfit components"
    accessories = ", ".join(s["accessories"].values()) or "no additional accessories"
    views = "front view and back view" if len(l["views"]) == 2 else "single full-body front view"
    panels = ", ".join(l["detail_panels"]) or "limited detail panels"
    prompt = f"Create an elegant fashion illustration {spec['render_mode']} on a {l['background']} background. Show {views}, featuring {garments}. Accessories: {accessories}. Style mode: {s['style_mode'] or 'neutral'}. Hairstyle cue: {f['hairstyle']}; headwear: {f['headwear']}. Include {panels}. Delicate ink linework, soft watercolor and marker wash, elongated stylized fashion-illustration proportions, editorial serif and handwritten annotation accents, clean luxury lookbook mood."
    return {"render_mode": spec["render_mode"], "prompt": prompt, "render_spec": spec, "warnings": spec["warnings"], "missing_information": []}
