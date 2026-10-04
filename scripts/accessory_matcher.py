"""Generate constrained accessory specifications from known context and preferences."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping


RULES_PATH = Path(__file__).resolve().parents[1] / "data" / "accessory_rules.json"
SCALE_ORDER = {"small": 0, "medium": 1, "statement": 2}


def recommend_accessories(
    outfit_context: dict[str, Any],
    accessory_preferences: dict[str, Any] | None = None,
    occasion: str | None = None,
    style_mode: str | None = None,
) -> dict[str, Any]:
    """Return explainable accessory specifications without products or outfit advice."""

    rules = _load_rules()
    context = outfit_context if isinstance(outfit_context, Mapping) else {}
    warnings = [] if isinstance(outfit_context, Mapping) else ["outfit_context must be a mapping."]
    preferences = accessory_preferences if isinstance(accessory_preferences, Mapping) else {}
    if accessory_preferences is not None and not isinstance(accessory_preferences, Mapping):
        warnings.append("accessory_preferences must be a mapping when supplied.")
    missing = [field for field in ("neckline", "colors", "materials", "silhouettes") if field not in context]
    avoid = {_token(value) for value in preferences.get("avoid", []) if _token(value)}
    preferred_types = [_token(value) for value in preferences.get("preferred_types", []) if _token(value)]
    allowed_types = set(preferred_types) if preferred_types else set(rules["categories"])
    metal = _metal(preferences, context)
    max_scale = _max_scale(rules, occasion, style_mode, _token(context.get("complexity")) or "unknown", avoid)
    scale = _scale(preferences, max_scale, avoid)
    neckline = _token(context.get("neckline")) or "unknown"
    neckline_rule = rules["necklines"].get(neckline, rules["necklines"]["unknown"])
    structured = "structured" in {_token(value) for value in context.get("silhouettes", [])}
    shape = _shape(preferences, structured)
    recommendations: dict[str, dict[str, Any] | None] = {category: None for category in rules["categories"]}
    rationale = [f"Preference priority: {' > '.join(rules['metadata']['preference_priority'])}."]

    if "earrings" in allowed_types:
        recommendations["earrings"] = {"type": shape if shape in rules["types"]["earrings"] else "stud", "shape": shape, "metal": metal, "color": metal, "scale": scale}
    necklace_type = neckline_rule["necklace"]
    if "necklace" in allowed_types and necklace_type and "necklace" not in avoid:
        recommendations["necklace"] = {"type": necklace_type, "metal": metal, "color": metal, "scale": "small" if scale == "statement" else scale, "has_pendant": necklace_type in {"pendant", "lariat"}}
    if "ring" in allowed_types:
        recommendations["ring"] = {"type": "band", "metal": metal, "color": metal, "scale": "small"}
    if "bracelet" in allowed_types and style_mode != "minimal":
        recommendations["bracelet"] = {"type": "chain", "metal": metal, "color": metal, "scale": "small"}
    if "watch" in allowed_types and occasion in {"client_meeting", "interview", "formal_meeting", "weekday_office"}:
        recommendations["watch"] = {"type": "minimal_metal", "metal": metal, "color": metal, "scale": "small"}

    _enforce_hierarchy(recommendations, style_mode)
    if preferences.get("preferred_metals"):
        rationale.append(f"{metal} follows the supplied metal preference.")
    if structured and shape == "geometric":
        rationale.append("Geometric jewellery follows the supplied structured silhouette context.")
    if neckline == "turtleneck":
        rationale.append("The turtleneck leaves the necklace optional and keeps earrings as the focal category.")
    return {"recommendations": recommendations, "rationale": rationale, "warnings": warnings,
            "unsupported_values": [], "missing_information": missing}


@lru_cache
def _load_rules() -> dict[str, Any]:
    with RULES_PATH.open(encoding="utf-8") as source:
        return json.load(source)


def _token(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    words = value.strip().casefold().replace("-", " ").replace("_", " ").split()
    return "_".join(words) if words else None


def _metal(preferences: Mapping[str, Any], context: Mapping[str, Any]) -> str:
    preferred = [_token(value) for value in preferences.get("preferred_metals", [])]
    if next((value for value in preferred if value), None):
        return next(value for value in preferred if value)
    colors = {_token(value) for value in context.get("colors", [])}
    return "silver" if colors & {"silver", "black", "charcoal", "navy"} else "gold"


def _max_scale(rules: Mapping[str, Any], occasion: str | None, style_mode: str | None, complexity: str, avoid: set[str]) -> str:
    candidates = [rules["style_modes"].get(_token(style_mode) or "", {"max_scale": "medium"})["max_scale"],
                  rules["occasions"].get(_token(occasion) or "", {"max_scale": "statement"})["max_scale"],
                  rules["complexity"].get(complexity, rules["complexity"]["unknown"])["max_scale"]]
    maximum = min(candidates, key=SCALE_ORDER.__getitem__)
    return "medium" if maximum == "statement" and "statement" in avoid else maximum


def _scale(preferences: Mapping[str, Any], maximum: str, avoid: set[str]) -> str:
    preferred = [_token(value) for value in preferences.get("preferred_scale", [])]
    valid = [value for value in preferred if value in SCALE_ORDER and value not in avoid and SCALE_ORDER[value] <= SCALE_ORDER[maximum]]
    return valid[-1] if valid else maximum


def _shape(preferences: Mapping[str, Any], structured: bool) -> str:
    shapes = [_token(value) for value in preferences.get("preferred_shapes", [])]
    if structured and "geometric" in shapes:
        return "geometric"
    return next((shape for shape in shapes if shape), "stud")


def _enforce_hierarchy(recommendations: dict[str, dict[str, Any] | None], style_mode: str | None) -> None:
    earrings = recommendations["earrings"]
    if earrings and earrings["scale"] == "statement" and style_mode != "maximal":
        recommendations["necklace"] = None
    elif earrings and earrings["scale"] == "statement" and recommendations["necklace"]:
        recommendations["necklace"]["scale"] = "small"
