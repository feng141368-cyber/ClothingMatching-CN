"""Normalize known materials and describe their data-driven relationships."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping


RULES_PATH = Path(__file__).resolve().parents[1] / "data" / "material_rules.json"
WEIGHT_ORDER = {"light": 0, "medium": 1, "heavy": 2}
DENSITY_ORDER = {"low": 0, "medium": 1, "high": 2}
SEASONS = ("spring", "summer", "autumn", "winter")


def normalize_material(material: str) -> dict[str, Any]:
    """Return canonical metadata for one known material label."""

    rules = _load_rules()
    canonical = _canonical_material(material, rules)
    if canonical is None:
        return {
            "input": material,
            "canonical_material": None,
            "attributes": None,
            "warnings": [f"Unsupported material: {material!r}."],
            "unsupported_values": [_unsupported(material)],
        }
    return {
        "input": material,
        "canonical_material": canonical,
        "attributes": dict(rules["materials"][canonical]),
        "warnings": [],
        "unsupported_values": [],
    }


def analyze_material_pair(material_a: str, material_b: str) -> dict[str, Any]:
    """Describe two known materials without making a quality or styling judgment."""

    first = normalize_material(material_a)
    second = normalize_material(material_b)
    canonical_materials = [first["canonical_material"], second["canonical_material"]]
    warnings = first["warnings"] + second["warnings"]
    unsupported_values = first["unsupported_values"] + second["unsupported_values"]
    if None in canonical_materials:
        return _unknown_pair(canonical_materials, warnings, unsupported_values)

    rules = _load_rules()
    first_name, second_name = canonical_materials
    first_attributes = rules["materials"][first_name]
    second_attributes = rules["materials"][second_name]
    explicit = rules["pair_rules"].get("|".join(sorted(canonical_materials)), {})
    return {
        "materials": canonical_materials,
        "texture_contrast": explicit.get(
            "texture_contrast",
            _texture_contrast(first_attributes, second_attributes),
        ),
        "visual_weight_balance": _weight_balance(first_attributes, second_attributes),
        "structure_relationship": explicit.get(
            "structure_relationship",
            _structure_relationship(first_attributes, second_attributes),
        ),
        "surface_relationship": explicit.get(
            "surface_relationship",
            _surface_relationship(first_attributes, second_attributes),
        ),
        "shared_seasons": _shared_seasons([first_attributes, second_attributes]),
        "formality_relationship": _formality_relationship(first_attributes, second_attributes),
        "warnings": warnings,
        "unsupported_values": unsupported_values,
    }


def analyze_material_mix(materials: list[str]) -> dict[str, Any]:
    """Summarize two or more known materials while preserving unsupported inputs."""

    if not isinstance(materials, list) or len(materials) < 2:
        return {
            "canonical_materials": [],
            "overall_visual_weight": "unknown",
            "texture_density": "unknown",
            "structure_mix": "unknown",
            "shared_seasons": [],
            "warnings": ["materials must be a list containing at least two values."],
            "unsupported_values": [],
        }

    normalized = [normalize_material(material) for material in materials]
    canonical_materials = [
        item["canonical_material"] for item in normalized if item["canonical_material"] is not None
    ]
    warnings = [warning for item in normalized for warning in item["warnings"]]
    unsupported_values = [
        value for item in normalized for value in item["unsupported_values"]
    ]
    if len(canonical_materials) < 2:
        warnings.append("At least two supported canonical materials are required for mix analysis.")
        return {
            "canonical_materials": canonical_materials,
            "overall_visual_weight": "unknown",
            "texture_density": "unknown",
            "structure_mix": "unknown",
            "shared_seasons": [],
            "warnings": warnings,
            "unsupported_values": unsupported_values,
        }

    rules = _load_rules()
    attributes = [rules["materials"][material] for material in canonical_materials]
    return {
        "canonical_materials": canonical_materials,
        "overall_visual_weight": _mix_weight(attributes),
        "texture_density": _mix_density(attributes),
        "structure_mix": _mix_structure(attributes),
        "shared_seasons": _shared_seasons(attributes),
        "warnings": warnings,
        "unsupported_values": unsupported_values,
    }


@lru_cache
def _load_rules() -> dict[str, Any]:
    """Load material vocabulary, metadata, aliases, and explicit pair rules."""

    with RULES_PATH.open(encoding="utf-8") as rules_file:
        return json.load(rules_file)


def _canonical_material(material: Any, rules: Mapping[str, Any]) -> str | None:
    """Normalize case and separators, applying only explicit aliases."""

    normalized = _identifier(material)
    if normalized is None:
        return None
    return rules["aliases"].get(
        normalized,
        normalized if normalized in rules["materials"] else None,
    )


def _identifier(value: Any) -> str | None:
    """Convert a non-empty enum-like label to snake_case."""

    if not isinstance(value, str):
        return None
    words = value.strip().casefold().replace("-", " ").replace("_", " ").split()
    return "_".join(words) if words else None


def _unknown_pair(
    materials: list[str | None],
    warnings: list[str],
    unsupported_values: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return stable unknown dimensions when either material is unsupported."""

    return {
        "materials": materials,
        "texture_contrast": "unknown",
        "visual_weight_balance": "unknown",
        "structure_relationship": "unknown",
        "surface_relationship": "unknown",
        "shared_seasons": [],
        "formality_relationship": "unknown",
        "warnings": warnings,
        "unsupported_values": unsupported_values,
    }


def _texture_contrast(first: Mapping[str, Any], second: Mapping[str, Any]) -> str:
    """Compare material texture tags using an intentionally small heuristic."""

    if set(first["texture"]) & set(second["texture"]):
        return "low"
    if {first["visual_weight"], second["visual_weight"]} == {"light", "heavy"}:
        return "high"
    return "medium"


def _weight_balance(first: Mapping[str, Any], second: Mapping[str, Any]) -> str:
    """Describe visual-weight consistency without evaluating desirability."""

    first_weight = first["visual_weight"]
    second_weight = second["visual_weight"]
    return first_weight if first_weight == second_weight else "mixed"


def _structure_relationship(first: Mapping[str, Any], second: Mapping[str, Any]) -> str:
    """Describe structure similarity or structured-fluid contrast."""

    structures = {first["structure"], second["structure"]}
    if structures == {"structured", "fluid"}:
        return "structured_fluid_contrast"
    if len(structures) == 1:
        structure = structures.pop()
        return f"{structure}_consistent" if structure in {"soft", "structured"} else "consistent"
    return "mixed"


def _surface_relationship(first: Mapping[str, Any], second: Mapping[str, Any]) -> str:
    """Describe broad surface effects from explicit surface tags."""

    first_surface = set(first["surface_tags"])
    second_surface = set(second["surface_tags"])
    if first_surface & second_surface:
        return "consistent"
    if "matte" in first_surface | second_surface and "lustrous" in first_surface | second_surface:
        return "matte_lustrous_contrast"
    if "napped" in first_surface | second_surface and "lustrous" in first_surface | second_surface:
        return "high_surface_interest"
    return "mixed"


def _shared_seasons(attributes: list[Mapping[str, Any]]) -> list[str]:
    """Intersect broad seasonality while honoring an all-season metadata value."""

    season_sets = []
    for attribute in attributes:
        seasons = set(attribute["seasonality"])
        season_sets.append(set(SEASONS) if "all_season" in seasons else seasons)
    shared = set.intersection(*season_sets)
    return [season for season in SEASONS if season in shared]


def _formality_relationship(first: Mapping[str, Any], second: Mapping[str, Any]) -> str:
    """Report metadata agreement without an occasion judgment."""

    if "variable" in {first["formality"], second["formality"]}:
        return "unknown"
    return "similar" if first["formality"] == second["formality"] else "mixed"


def _mix_weight(attributes: list[Mapping[str, Any]]) -> str:
    """Return a dominant or mixed visual-weight description."""

    weights = [attribute["visual_weight"] for attribute in attributes]
    return weights[0] if len(set(weights)) == 1 else "mixed"


def _mix_density(attributes: list[Mapping[str, Any]]) -> str:
    """Return the strongest declared texture-density tag in a material mix."""

    densities = [attribute["texture_density"] for attribute in attributes]
    return max(densities, key=DENSITY_ORDER.__getitem__)


def _mix_structure(attributes: list[Mapping[str, Any]]) -> str:
    """Summarize structures across a material mix."""

    structures = {attribute["structure"] for attribute in attributes}
    if structures == {"structured"}:
        return "structured_consistent"
    if structures == {"soft"}:
        return "soft_consistent"
    if "structured" in structures and "fluid" in structures:
        return "structured_fluid_contrast"
    return "mixed"


def _unsupported(value: Any) -> dict[str, Any]:
    """Return a predictable unsupported material value."""

    return {"field": "material", "value": value, "reason": "unsupported_material"}
