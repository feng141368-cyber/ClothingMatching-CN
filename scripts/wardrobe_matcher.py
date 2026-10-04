"""Wardrobe-first matching for normalized structured item requirements."""
from __future__ import annotations
from typing import Any

def find_wardrobe_candidates(requirement: dict[str, Any], wardrobe: dict[str, Any], avoid_item_ids: list[str] | None = None) -> list[dict[str, Any]]:
    avoid = set(avoid_item_ids or [])
    items = wardrobe.get("items", []) if isinstance(wardrobe, dict) else []
    category = requirement.get("category")
    sub = requirement.get("sub_category")
    colors = set(requirement.get("color_family", []))
    silhouettes = set(requirement.get("silhouette", []))
    candidates = []
    for item in items:
        if item.get("item_id") in avoid or item.get("category") != category:
            continue
        exact = (not sub or item.get("sub_category") == sub) and (not colors or item.get("color") in colors) and (not silhouettes or item.get("silhouette") in silhouettes)
        candidates.append({"item": item, "status": "exact_match" if exact else "compatible_substitute"})
    return sorted(candidates, key=lambda entry: (entry["status"] != "exact_match", entry["item"].get("item_id", "")))

def match_wardrobe_item(requirement: dict[str, Any], wardrobe: dict[str, Any], avoid_item_ids: list[str] | None = None) -> dict[str, Any]:
    candidates = find_wardrobe_candidates(requirement, wardrobe, avoid_item_ids)
    if candidates:
        return {"status": candidates[0]["status"], "item": candidates[0]["item"]}
    return {"status": "missing", "item": None, "requirement": requirement}
