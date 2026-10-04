"""Approximate geometric bag capacity and independent carry-item fit checks."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

RULES = json.loads((Path(__file__).resolve().parents[1] / "data" / "carry_item_rules.json").read_text())

def _positive(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0 else None

def estimate_bag_capacity(bag: dict[str, Any]) -> dict[str, Any]:
    warnings, dimensions = [], {}
    for key in ("width_cm", "height_cm", "depth_cm"):
        value = _positive(bag.get(key))
        dimensions[key] = value
        if bag.get(key) is not None and value is None: warnings.append(f"invalid_bag.{key}")
    factor = _positive(bag.get("usable_factor")) or 0.75
    if not 0.70 <= factor <= 0.80: warnings.append("usable_factor_outside_recommended_range")
    gross = None if None in dimensions.values() else round(dimensions["width_cm"] * dimensions["height_cm"] * dimensions["depth_cm"] / 1000, 2)
    if gross is None: warnings.append("insufficient_dimensions_for_estimate")
    else: warnings.append("estimated_capacity_only")
    if bag.get("dimension_type") == "external": warnings.append("external_dimensions_may_overestimate_internal_space")
    elif bag.get("dimension_type") is None: warnings.append("dimension_type_unknown")
    return {"bag_dimensions_cm": dimensions, "stated_capacity_l": _positive(bag.get("capacity_l")),
            "estimated_gross_capacity_l": gross, "estimated_usable_capacity_l": round(gross * factor, 2) if gross is not None else None,
            "usable_factor": factor, "warnings": warnings}

def _item_dimensions(item: dict[str, Any]) -> tuple[dict[str, float | None], bool, list[str]]:
    values = {k: _positive(item.get(k)) for k in ("width_cm", "height_cm", "depth_cm", "diameter_cm", "length_cm")}
    reference = False
    if item.get("item_type") in RULES["reference_items"]:
        ref = RULES["reference_items"][item["item_type"]]
        for key in ("width_cm", "height_cm", "depth_cm"):
            if values[key] is None and ref.get(key) is not None: values[key] = ref[key]; reference = True
    invalid = [f"item.{key}" for key in values if item.get(key) is not None and values[key] is None]
    return values, reference, invalid

def check_item_fit(bag: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    dims, reference, invalid = _item_dimensions(item); margin = RULES["fit_margin_cm"]
    bag_dims = {k: _positive(bag.get(k)) for k in ("width_cm", "height_cm", "depth_cm")}
    base = {"item": {"item_type": item.get("item_type"), "name": item.get("name")}, "warnings": invalid}
    rectangular = item.get("item_type") not in ("bottle", "small_umbrella")
    if rectangular:
        required = ("width_cm", "height_cm") + (() if item.get("item_type") == "a4_document" else ("depth_cm",))
        missing = [f"item.{k}" for k in required if dims[k] is None] + [f"bag.{k}" for k in required if bag_dims[k] is None]
        if missing: return base | {"fit_status": "unknown", "confidence": "low", "missing_information": missing}
        options = [("landscape", dims["width_cm"], dims["height_cm"]), ("portrait", dims["height_cm"], dims["width_cm"])]
    else:
        length = dims["height_cm"] or dims["length_cm"]; diameter = dims["diameter_cm"]
        missing = (["item.diameter_cm"] if diameter is None else []) + (["item.height_cm_or_length_cm"] if length is None else []) + [f"bag.{k}" for k in ("width_cm", "height_cm", "depth_cm") if bag_dims[k] is None]
        if missing: return base | {"fit_status": "unknown", "confidence": "low", "missing_information": missing}
        options = [("upright", diameter, length), ("sideways", length, diameter)]
        dims["depth_cm"] = diameter
    for orientation, width, height in options:
        depth_fits = dims["depth_cm"] is None or dims["depth_cm"] + margin <= bag_dims["depth_cm"]
        if width + margin <= bag_dims["width_cm"] and height + margin <= bag_dims["height_cm"] and depth_fits:
            opening_w, opening_h = _positive(bag.get("opening_width_cm")), _positive(bag.get("opening_height_cm"))
            if opening_w and opening_h and not ((width <= opening_w and height <= opening_h) or (width <= opening_h and height <= opening_w)):
                return base | {"fit_status": "does_not_fit", "confidence": "high", "warnings": base["warnings"] + ["opening_constraint"]}
            return base | {"fit_status": "fits", "orientation": orientation, "clearance_cm": {"width": round(bag_dims["width_cm"]-width,2), "height": round(bag_dims["height_cm"]-height,2), "depth": round(bag_dims["depth_cm"]-dims["depth_cm"],2) if dims["depth_cm"] is not None else None}, "confidence": "medium" if reference else "high", "warnings": base["warnings"] + ([] if opening_w else ["opening_dimensions_unknown"])}
    return base | {"fit_status": "does_not_fit", "confidence": "medium" if reference else "high"}

def analyze_carry_requirements(bag: dict[str, Any], carry_items: list[dict[str, Any]]) -> dict[str, Any]:
    items = [check_item_fit(bag, item) for item in carry_items]
    statuses = {item["fit_status"] for item in items}
    overall = "all_individually_fit" if statuses == {"fits"} else "some_do_not_fit" if "does_not_fit" in statuses else "unknown"
    return {"items": items, "overall_independent_fit_status": overall, "warnings": ["independent_fit_does_not_prove_simultaneous_packing"]}
