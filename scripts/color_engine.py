"""Normalize known colour labels and analyze data-driven colour relationships."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping


BRIGHTNESS_ORDER = {"dark": 0, "medium": 1, "light": 2}
RULES_PATH = Path(__file__).resolve().parents[1] / "data" / "color_rules.json"


def normalize_color(color: str) -> dict[str, Any]:
    """Normalize one known colour label and return its canonical attributes.

    Unsupported values are reported instead of approximated to a nearby colour.
    """

    rules = _load_rules()
    canonical = _canonical_color(color, rules)
    if canonical is None:
        return {
            "input": color,
            "canonical_color": None,
            "attributes": None,
            "warnings": [_color_warning(color)],
            "unsupported_values": [_unsupported_color(color)],
        }

    return {
        "input": color,
        "canonical_color": canonical,
        "attributes": dict(rules["colors"][canonical]),
        "warnings": [],
        "unsupported_values": [],
    }


def analyze_color_pair(color_a: str, color_b: str) -> dict[str, Any]:
    """Analyze an explicit, known colour relationship without styling advice."""

    rules = _load_rules()
    first = normalize_color(color_a)
    second = normalize_color(color_b)
    canonical_colors = [first["canonical_color"], second["canonical_color"]]
    warnings = first["warnings"] + second["warnings"]
    unsupported_values = first["unsupported_values"] + second["unsupported_values"]

    if None in canonical_colors:
        return {
            "colors": canonical_colors,
            "relationship": "unknown",
            "contrast": "unknown",
            "temperature_relationship": "unknown",
            "explanation": "A colour relationship requires two supported canonical colours.",
            "warnings": warnings,
            "unsupported_values": unsupported_values,
        }

    first_color, second_color = canonical_colors
    first_attributes = rules["colors"][first_color]
    second_attributes = rules["colors"][second_color]
    contrast = _contrast(first_attributes, second_attributes)
    relationship = _pair_relationship(
        first_color,
        second_color,
        first_attributes,
        second_attributes,
        contrast,
        rules,
    )
    temperature_relationship = _temperature_relationship(
        first_attributes["temperature"],
        second_attributes["temperature"],
    )
    return {
        "colors": canonical_colors,
        "relationship": relationship,
        "contrast": contrast,
        "temperature_relationship": temperature_relationship,
        "explanation": _pair_explanation(
            first_color,
            second_color,
            relationship,
            contrast,
            temperature_relationship,
        ),
        "warnings": warnings,
        "unsupported_values": unsupported_values,
    }


def analyze_palette(colors: list[str]) -> dict[str, Any]:
    """Summarize known colour metadata and relationships for a palette of two or more."""

    if not isinstance(colors, list) or len(colors) < 2:
        return {
            "canonical_colors": [],
            "dominant_relationship": "unknown",
            "contrast": "unknown",
            "temperature": "unknown",
            "neutral_ratio": 0.0,
            "warnings": ["colors must be a list containing at least two values."],
            "unsupported_values": [],
        }

    normalized = [normalize_color(color) for color in colors]
    canonical_colors = [
        item["canonical_color"]
        for item in normalized
        if item["canonical_color"] is not None
    ]
    warnings = [
        warning
        for item in normalized
        for warning in item["warnings"]
    ]
    unsupported_values = [
        value
        for item in normalized
        for value in item["unsupported_values"]
    ]

    if len(canonical_colors) < 2:
        warnings.append("At least two supported canonical colours are required for palette analysis.")
        return {
            "canonical_colors": canonical_colors,
            "dominant_relationship": "unknown",
            "contrast": "unknown",
            "temperature": "unknown",
            "neutral_ratio": 0.0,
            "warnings": warnings,
            "unsupported_values": unsupported_values,
        }

    rules = _load_rules()
    attributes = [rules["colors"][color] for color in canonical_colors]
    pair_results = [
        analyze_color_pair(canonical_colors[index], canonical_colors[next_index])
        for index in range(len(canonical_colors))
        for next_index in range(index + 1, len(canonical_colors))
    ]
    neutral_count = sum(attribute["is_neutral"] for attribute in attributes)
    neutral_ratio = neutral_count / len(canonical_colors)
    return {
        "canonical_colors": canonical_colors,
        "dominant_relationship": _palette_relationship(
            canonical_colors,
            attributes,
            pair_results,
        ),
        "contrast": _palette_contrast(pair_results),
        "temperature": _palette_temperature(attributes),
        "neutral_ratio": neutral_ratio,
        "warnings": warnings,
        "unsupported_values": unsupported_values,
    }


@lru_cache
def _load_rules() -> dict[str, Any]:
    """Load canonical colour data and explicit relationships from JSON."""

    with RULES_PATH.open(encoding="utf-8") as rules_file:
        return json.load(rules_file)


def _canonical_color(color: Any, rules: Mapping[str, Any]) -> str | None:
    """Canonicalize case and separators, then apply only explicit aliases."""

    normalized = _normalize_identifier(color)
    if normalized is None:
        return None
    return rules["aliases"].get(
        normalized,
        normalized if normalized in rules["colors"] else None,
    )


def _normalize_identifier(value: Any) -> str | None:
    """Convert a non-empty colour label to a separator-independent identifier."""

    if not isinstance(value, str):
        return None
    words = value.strip().casefold().replace("-", " ").replace("_", " ").split()
    return "_".join(words) if words else None


def _contrast(
    first_attributes: Mapping[str, Any],
    second_attributes: Mapping[str, Any],
) -> str:
    """Classify qualitative contrast from data-provided brightness attributes."""

    difference = abs(
        BRIGHTNESS_ORDER[first_attributes["brightness"]]
        - BRIGHTNESS_ORDER[second_attributes["brightness"]]
    )
    return ("low", "medium", "high")[difference]


def _pair_relationship(
    first_color: str,
    second_color: str,
    first_attributes: Mapping[str, Any],
    second_attributes: Mapping[str, Any],
    contrast: str,
    rules: Mapping[str, Any],
) -> str:
    """Classify only known pair relationships and neutral/tonal conventions."""

    if first_color == second_color:
        return "monochromatic"
    explicit = _explicit_relationship(first_color, second_color, rules)
    if explicit is not None:
        return explicit
    if first_attributes["is_neutral"] and second_attributes["is_neutral"]:
        return "high_contrast" if contrast == "high" else "tonal"
    if first_attributes["family"] == second_attributes["family"]:
        return "tonal"
    if first_attributes["is_neutral"] or second_attributes["is_neutral"]:
        return "neutral_accent"
    return "high_contrast" if contrast == "high" else "low_contrast"


def _explicit_relationship(
    first_color: str,
    second_color: str,
    rules: Mapping[str, Any],
) -> str | None:
    """Look up only relationships explicitly supplied in the data file."""

    color_pair = frozenset((first_color, second_color))
    for relationship, pairs in rules["harmony_relationships"].items():
        if any(color_pair == frozenset(pair) for pair in pairs):
            return relationship
    return None


def _temperature_relationship(first: str, second: str) -> str:
    """Describe the pair's temperature compatibility without a preference judgment."""

    if first == second:
        return first
    if "neutral" in {first, second}:
        return "neutral"
    return "mixed"


def _pair_explanation(
    first_color: str,
    second_color: str,
    relationship: str,
    contrast: str,
    temperature_relationship: str,
) -> str:
    """Return a factual machine-oriented relationship explanation."""

    return (
        f"{first_color} and {second_color} are classified as {relationship}; "
        f"their brightness contrast is {contrast} and their temperature relationship is "
        f"{temperature_relationship}."
    )


def _palette_relationship(
    canonical_colors: list[str],
    attributes: list[Mapping[str, Any]],
    pair_results: list[Mapping[str, Any]],
) -> str:
    """Summarize palette composition from neutral membership and pair data."""

    neutral_count = sum(attribute["is_neutral"] for attribute in attributes)
    non_neutral_count = len(attributes) - neutral_count
    if neutral_count == len(attributes):
        relationships = {result["relationship"] for result in pair_results}
        return "tonal" if relationships <= {"tonal", "monochromatic"} else "neutral"
    if neutral_count >= 1 and non_neutral_count == 1:
        return "neutral_accent"
    if len(set(canonical_colors)) == 1:
        return "monochromatic"

    relationships = [result["relationship"] for result in pair_results]
    for relationship in ("complementary", "analogous", "tonal", "high_contrast", "low_contrast"):
        if relationship in relationships:
            return relationship
    return "mixed"


def _palette_contrast(pair_results: list[Mapping[str, Any]]) -> str:
    """Use the strongest known pair contrast as the palette contrast summary."""

    contrast_order = {"low": 0, "medium": 1, "high": 2}
    known_contrasts = [
        result["contrast"]
        for result in pair_results
        if result["contrast"] in contrast_order
    ]
    if not known_contrasts:
        return "unknown"
    return max(known_contrasts, key=contrast_order.__getitem__)


def _palette_temperature(attributes: list[Mapping[str, Any]]) -> str:
    """Summarize temperatures without claiming a personal-colour conclusion."""

    if all(attribute["is_neutral"] for attribute in attributes):
        return "neutral"
    temperatures = {attribute["temperature"] for attribute in attributes}
    return temperatures.pop() if len(temperatures) == 1 else "mixed"


def _color_warning(value: Any) -> str:
    """Describe one unsupported colour value without guessing a substitute."""

    return f"Unsupported color: {value!r}."


def _unsupported_color(value: Any) -> dict[str, Any]:
    """Return the predictable unsupported-value representation."""

    return {
        "field": "color",
        "value": value,
        "reason": "unsupported_color",
    }
