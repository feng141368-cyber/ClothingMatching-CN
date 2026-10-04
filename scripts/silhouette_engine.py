"""Normalize known silhouette labels and describe data-driven relationships."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping


RULES_PATH = Path(__file__).resolve().parents[1] / "data" / "silhouette_rules.json"


def normalize_silhouette(value: str) -> dict[str, Any]:
    """Return canonical metadata for one known silhouette value."""

    rules = _load_rules()
    canonical = _canonical(value, rules)
    if canonical is None:
        return {"input": value, "canonical_silhouette": None, "attributes": None,
                "warnings": [f"Unsupported silhouette: {value!r}."],
                "unsupported_values": [_unsupported(value)]}
    return {"input": value, "canonical_silhouette": canonical,
            "attributes": dict(rules["silhouettes"][canonical]),
            "warnings": [], "unsupported_values": []}


def analyze_silhouette_pair(silhouette_a: str, silhouette_b: str) -> dict[str, Any]:
    """Analyze two silhouette labels without evaluating desirability."""

    first, second = normalize_silhouette(silhouette_a), normalize_silhouette(silhouette_b)
    values = [first["canonical_silhouette"], second["canonical_silhouette"]]
    warnings = first["warnings"] + second["warnings"]
    unsupported = first["unsupported_values"] + second["unsupported_values"]
    if None in values:
        return _unknown_pair(values, warnings, unsupported)
    rules = _load_rules()
    left, right = values
    attributes = [rules["silhouettes"][left], rules["silhouettes"][right]]
    explicit = rules["pair_rules"].get("|".join(sorted(values)), {})
    return {
        "silhouettes": values,
        "volume_relationship": explicit.get("volume_relationship", _volume(attributes)),
        "structure_relationship": explicit.get("structure_relationship", _structure(attributes)),
        "length_relationship": explicit.get("length_relationship", _length(attributes)),
        "shape_relationship": _shape(attributes),
        "proportion_pattern": explicit.get("proportion_pattern", _pattern(values, attributes)),
        "warnings": warnings,
        "unsupported_values": unsupported,
    }


def analyze_silhouette_mix(silhouettes: list[str]) -> dict[str, Any]:
    """Summarize two or more known silhouette labels."""

    if not isinstance(silhouettes, list) or len(silhouettes) < 2:
        return _unknown_mix(["silhouettes must be a list containing at least two values."])
    normalized = [normalize_silhouette(value) for value in silhouettes]
    canonical = [item["canonical_silhouette"] for item in normalized if item["canonical_silhouette"]]
    warnings = [warning for item in normalized for warning in item["warnings"]]
    unsupported = [value for item in normalized for value in item["unsupported_values"]]
    if len(canonical) < 2:
        warnings.append("At least two supported canonical silhouettes are required for mix analysis.")
        return _unknown_mix(warnings, canonical, unsupported)
    rules = _load_rules()
    attributes = [rules["silhouettes"][value] for value in canonical]
    explicit = rules["mix_rules"].get("|".join(canonical), {})
    return {
        "canonical_silhouettes": canonical,
        "volume_pattern": explicit.get("volume_pattern", _volume(attributes)),
        "proportion_pattern": explicit.get("proportion_pattern", _pattern(canonical, attributes)),
        "structure_mix": _structure(attributes),
        "length_mix": _length(attributes),
        "warnings": warnings,
        "unsupported_values": unsupported,
    }


@lru_cache
def _load_rules() -> dict[str, Any]:
    with RULES_PATH.open(encoding="utf-8") as rules_file:
        return json.load(rules_file)


def _canonical(value: Any, rules: Mapping[str, Any]) -> str | None:
    normalized = _identifier(value)
    if normalized is None:
        return None
    return rules["aliases"].get(normalized, normalized if normalized in rules["silhouettes"] else None)


def _identifier(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    words = value.strip().casefold().replace("-", " ").replace("_", " ").split()
    return "_".join(words) if words else None


def _unknown_pair(values: list[str | None], warnings: list[str], unsupported: list[dict[str, Any]]) -> dict[str, Any]:
    return {"silhouettes": values, "volume_relationship": "unknown", "structure_relationship": "unknown",
            "length_relationship": "unknown", "shape_relationship": "unknown", "proportion_pattern": "unknown",
            "warnings": warnings, "unsupported_values": unsupported}


def _unknown_mix(warnings: list[str], canonical: list[str] | None = None, unsupported: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {"canonical_silhouettes": canonical or [], "volume_pattern": "unknown", "proportion_pattern": "unknown",
            "structure_mix": "unknown", "length_mix": "unknown", "warnings": warnings,
            "unsupported_values": unsupported or []}


def _volume(attributes: list[Mapping[str, Any]]) -> str:
    volumes = [attribute["volume"] for attribute in attributes]
    if all(volume == "high" for volume in volumes):
        return "high_volume"
    if all(volume == "low" for volume in volumes):
        return "low_volume"
    return "mixed"


def _structure(attributes: list[Mapping[str, Any]]) -> str:
    structures = {attribute["structure"] for attribute in attributes}
    if structures == {"structured"}:
        return "structured_consistent"
    if structures <= {"soft", "medium"}:
        return "soft_consistent"
    if "structured" in structures and "soft" in structures:
        return "structured_soft_contrast"
    return "mixed"


def _length(attributes: list[Mapping[str, Any]]) -> str:
    effects = [attribute["length_effect"] for attribute in attributes if attribute["length_effect"] != "not_applicable"]
    if not effects:
        return "unknown"
    if all(effect == "long" for effect in effects):
        return "long_over_long"
    if "long" in effects and "standard" in effects:
        return "long_over_standard"
    if "cropped" in effects and "standard" in effects:
        return "cropped_over_standard"
    if len(set(effects)) == 1 and effects[0] == "standard":
        return "standard_consistent"
    return "mixed"


def _shape(attributes: list[Mapping[str, Any]]) -> str:
    shapes = {attribute["shape"] for attribute in attributes} - {"unknown"}
    return "unknown" if not shapes else "consistent" if len(shapes) == 1 else "mixed"


def _pattern(values: list[str], attributes: list[Mapping[str, Any]]) -> str:
    if all(value == "column" for value in values):
        return "column"
    if {attribute["structure"] for attribute in attributes} == {"structured", "soft"}:
        return "structured_soft"
    return "mixed"


def _unsupported(value: Any) -> dict[str, Any]:
    return {"field": "silhouette", "value": value, "reason": "unsupported_silhouette"}
