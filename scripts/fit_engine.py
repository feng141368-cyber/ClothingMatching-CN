"""Explain known body and garment measurements with category-specific ease rules."""

from __future__ import annotations

import json
from functools import lru_cache
from numbers import Real
from pathlib import Path
from typing import Any, Mapping


FIT_ORDER = {
    "fitted": 0,
    "slim": 1,
    "regular": 2,
    "relaxed": 3,
    "oversized": 4,
    "extreme_oversized": 5,
}

FIT_CLASSES = frozenset((*FIT_ORDER, "unknown"))
RULES_PATH = Path(__file__).resolve().parents[1] / "data" / "fit_rules.json"


def analyze_fit(
    body: dict[str, Any],
    garment: dict[str, Any],
    category: str,
) -> dict[str, Any]:
    """Analyze known body and garment measurements without recommending a size.

    Measurements are analyzed only when both corresponding body and garment
    values are positive numbers. Missing or malformed measurements remain
    unknown, are recorded in the result, and never trigger inference.
    """

    rules = _load_rules()
    warnings: list[str] = []
    missing_fields: list[str] = []
    normalized_category = _normalize_category(category)

    if normalized_category not in rules:
        warnings.append(f"Unsupported garment category: {category!r}.")
        return _empty_result(
            normalized_category or "unknown",
            warnings,
            missing_fields,
        )

    category_rules = rules[normalized_category]
    body_data = _validated_mapping(body, "body", warnings)
    garment_data = _validated_mapping(garment, "garment", warnings)
    measurement_analysis: dict[str, dict[str, Any]] = {}
    regional_fits: dict[str, str] = {}

    for measurement, measurement_rule in category_rules["measurement_rules"].items():
        body_value = _measurement(
            body_data,
            measurement,
            "body",
            warnings,
            missing_fields,
        )
        garment_value = _measurement(
            garment_data,
            measurement,
            "garment",
            warnings,
            missing_fields,
        )
        if body_value is None or garment_value is None:
            continue

        ease = garment_value - body_value
        fit = _classify_ease(ease, measurement_rule["ease_thresholds_cm"])
        measurement_analysis[measurement] = {
            "body": body_value,
            "garment": garment_value,
            "ease": ease,
            "fit": fit,
        }
        regional_fits[measurement] = fit

    if category_rules["shoulder_analysis"]:
        shoulder_analysis = _analyze_shoulders(
            body_data,
            garment_data,
            rules["metadata"]["shoulder_difference_labels_cm"],
            warnings,
            missing_fields,
        )
        if shoulder_analysis is not None:
            measurement_analysis["shoulder_width_cm"] = shoulder_analysis

    fit_classification, extra_output = _overall_fit(
        category_rules,
        regional_fits,
    )
    confidence = _confidence(
        category_rules,
        regional_fits,
        fit_classification,
        shoulder_analyzed="shoulder_width_cm" in measurement_analysis,
    )
    intended_fit = _intended_fit(garment_data, warnings)
    fit_alignment = _fit_alignment(intended_fit, fit_classification)

    result = {
        "category": normalized_category,
        "fit_classification": fit_classification,
        "measurement_analysis": measurement_analysis,
        "confidence": confidence,
        "warnings": warnings,
        "missing_fields": _unique(missing_fields),
        "intended_fit": intended_fit,
        "measured_fit": fit_classification,
        "fit_alignment": fit_alignment,
    }
    result.update(extra_output)
    return result


@lru_cache
def _load_rules() -> dict[str, Any]:
    """Load the versioned, category-specific heuristic rules."""

    with RULES_PATH.open(encoding="utf-8") as rules_file:
        return json.load(rules_file)


def _empty_result(
    category: str,
    warnings: list[str],
    missing_fields: list[str],
) -> dict[str, Any]:
    """Return the predictable result structure for unsupported categories."""

    return {
        "category": category,
        "fit_classification": "unknown",
        "measurement_analysis": {},
        "confidence": "low",
        "warnings": warnings,
        "missing_fields": missing_fields,
        "intended_fit": None,
        "measured_fit": "unknown",
        "fit_alignment": "unknown",
    }


def _validated_mapping(
    value: Any,
    name: str,
    warnings: list[str],
) -> Mapping[str, Any]:
    """Return a mapping input or treat malformed structured input as empty."""

    if isinstance(value, Mapping):
        return value
    warnings.append(f"{name} must be a mapping.")
    return {}


def _measurement(
    source: Mapping[str, Any],
    field: str,
    source_name: str,
    warnings: list[str],
    missing_fields: list[str],
) -> int | float | None:
    """Read one positive measurement and report invalid or absent values."""

    value = source.get(field)
    field_path = f"{source_name}.{field}"
    if value is None:
        missing_fields.append(field_path)
        return None
    if isinstance(value, Real) and not isinstance(value, bool) and value > 0:
        return value
    warnings.append(f"{field_path} must be a positive number when supplied.")
    missing_fields.append(field_path)
    return None


def _classify_ease(
    ease: int | float,
    thresholds: Mapping[str, list[int | float | None]],
) -> str:
    """Classify an ease value using the selected category's external rules."""

    for fit_class, (minimum, maximum) in thresholds.items():
        if ease >= minimum and (maximum is None or ease < maximum):
            return fit_class
    return "unknown"


def _analyze_shoulders(
    body: Mapping[str, Any],
    garment: Mapping[str, Any],
    labels: Mapping[str, int | float],
    warnings: list[str],
    missing_fields: list[str],
) -> dict[str, Any] | None:
    """Report shoulder construction separately from the main ease result."""

    body_shoulder = _measurement(
        body,
        "shoulder_width_cm",
        "body",
        warnings,
        missing_fields,
    )
    garment_shoulder = _measurement(
        garment,
        "shoulder_width_cm",
        "garment",
        warnings,
        missing_fields,
    )
    if body_shoulder is None or garment_shoulder is None:
        return None

    difference = garment_shoulder - body_shoulder
    if difference < labels["narrower_max"]:
        label = "narrower"
    elif difference <= labels["close_max"]:
        label = "close"
    elif difference <= labels["extended_max"]:
        label = "extended"
    else:
        label = "strongly_extended"

    return {
        "body": body_shoulder,
        "garment": garment_shoulder,
        "difference": difference,
        "label": label,
    }


def _overall_fit(
    category_rules: Mapping[str, Any],
    regional_fits: Mapping[str, str],
) -> tuple[str, dict[str, str]]:
    """Produce a category-appropriate overall classification from regional fits."""

    strategy = category_rules["classification_strategy"]
    if strategy == "primary":
        primary_measurements = [
            name
            for name, rule in category_rules["measurement_rules"].items()
            if rule["role"] == "primary"
        ]
        for measurement in primary_measurements:
            if measurement in regional_fits:
                return regional_fits[measurement], {}
        return "unknown", {}

    if strategy == "bottom":
        waist_fit = regional_fits.get("waist_cm", "unknown")
        hip_fit = regional_fits.get("hip_cm", "unknown")
        overall_fit = _combine_regional_fits([waist_fit, hip_fit])
        return overall_fit, {
            "waist_fit": waist_fit,
            "hip_fit": hip_fit,
            "overall_fit": overall_fit,
        }

    if strategy == "dress":
        overall_fit = _combine_regional_fits(
            [
                regional_fits.get("bust_cm", "unknown"),
                regional_fits.get("waist_cm", "unknown"),
                regional_fits.get("hip_cm", "unknown"),
            ],
            minimum_count=category_rules["minimum_measurements_for_classification"],
        )
        return overall_fit, {"overall_fit": overall_fit}

    return "unknown", {}


def _combine_regional_fits(
    fits: list[str],
    *,
    minimum_count: int = 1,
) -> str:
    """Combine regional fit classes while exposing genuine regional disagreement."""

    known_fits = [fit for fit in fits if fit in FIT_ORDER]
    if len(known_fits) < minimum_count:
        return "unknown"

    ranks = [FIT_ORDER[fit] for fit in known_fits]
    if max(ranks) - min(ranks) > 1:
        return "mixed"
    return max(known_fits, key=FIT_ORDER.__getitem__)


def _confidence(
    category_rules: Mapping[str, Any],
    regional_fits: Mapping[str, str],
    fit_classification: str,
    *,
    shoulder_analyzed: bool,
) -> str:
    """Return a qualitative confidence based on analyzed, not inferred, fields."""

    if fit_classification == "unknown":
        return "low"

    primary_available = any(
        rule["role"] == "primary" and field in regional_fits
        for field, rule in category_rules["measurement_rules"].items()
    )
    supporting_available = any(
        rule["role"] == "supporting" and field in regional_fits
        for field, rule in category_rules["measurement_rules"].items()
    )
    if primary_available and (supporting_available or shoulder_analyzed):
        return "high"
    if primary_available:
        return "medium"
    return "low"


def _intended_fit(garment: Mapping[str, Any], warnings: list[str]) -> str | None:
    """Normalize valid intended-fit metadata without allowing it to override data."""

    value = garment.get("intended_fit")
    if value is None:
        return None
    normalized = _normalize_category(value)
    aliases = {"oversize": "oversized"}
    normalized = aliases.get(normalized, normalized)
    if normalized in FIT_CLASSES - {"unknown"}:
        return normalized
    warnings.append("garment.intended_fit must be a supported fit classification.")
    return None


def _fit_alignment(intended_fit: str | None, measured_fit: str) -> str:
    """Compare metadata to the measured result without changing the result."""

    if (
        intended_fit not in FIT_ORDER
        or measured_fit not in FIT_ORDER
    ):
        return "unknown"
    if intended_fit == measured_fit:
        return "aligned"
    if FIT_ORDER[measured_fit] > FIT_ORDER[intended_fit]:
        return "looser_than_intended"
    return "tighter_than_intended"


def _normalize_category(value: Any) -> str:
    """Normalize a compact enum-like input to snake_case."""

    if not isinstance(value, str):
        return ""
    words = value.strip().casefold().replace("-", " ").replace("_", " ").split()
    return "_".join(words)


def _unique(values: list[str]) -> list[str]:
    """Return values in first-seen order without duplicates."""

    return list(dict.fromkeys(values))
