"""Normalize structured user-profile data into WardrobeIQ's canonical schema.

The resolver intentionally accepts structured input only. Natural-language
extraction, fit decisions, and recommendation logic belong to later layers.
"""

from __future__ import annotations

from copy import deepcopy
from numbers import Real
from typing import Any, Mapping


BODY_FIELDS = (
    "height_cm",
    "shoulder_width_cm",
    "bust_cm",
    "waist_cm",
    "hip_cm",
    "inseam_cm",
    "shoe_size_eu",
)

FIT_PREFERENCE_FIELDS = ("tops", "shirts", "blazers", "trousers", "dresses")

STYLE_MODES = frozenset(
    {
        "serious_work",
        "daily_casual",
        "minimal",
        "maximal",
        "business",
        "relaxed_business",
        "smart_casual",
        "streetwear",
        "feminine",
        "classic",
    }
)

FIT_PREFERENCES = frozenset(
    {"fitted", "slim", "regular", "straight", "relaxed", "oversized", "wide_leg"}
)

STYLE_MODE_ALIASES = {
    **{style_mode.replace("_", " "): style_mode for style_mode in STYLE_MODES},
}

FIT_PREFERENCE_ALIASES = {
    **{fit_preference.replace("_", " "): fit_preference for fit_preference in FIT_PREFERENCES},
    "oversize": "oversized",
}

COLOR_ALIASES = {"grey": "gray"}

CANONICAL_TOP_LEVEL_FIELDS = frozenset(
    {
        "user_id",
        "body",
        "fit_preferences",
        "style_modes",
        "style_keywords",
        "color_preferences",
        "accessory_preferences",
        "usage_contexts",
        "budget",
        "notes",
    }
)


def resolve_profile(profile_input: dict[str, Any]) -> dict[str, Any]:
    """Resolve structured profile input into the canonical WardrobeIQ schema.

    Missing optional fields stay as ``None``, empty lists, or empty mappings.
    Invalid values are replaced with the corresponding unknown value and are
    reported in ``warnings``. Unsupported style modes and unrecognized input
    fields are reported in ``unsupported_values`` rather than guessed.
    """

    profile = _empty_profile()
    warnings: list[str] = []
    unsupported_values: list[dict[str, Any]] = []

    if not isinstance(profile_input, Mapping):
        warnings.append("profile_input must be a mapping.")
        return _result(profile, warnings, unsupported_values)

    _report_unknown_fields(
        profile_input,
        CANONICAL_TOP_LEVEL_FIELDS,
        "",
        unsupported_values,
    )

    user_id = profile_input.get("user_id")
    if user_id is not None:
        if isinstance(user_id, str) and user_id.strip():
            profile["user_id"] = user_id.strip()
        else:
            warnings.append("user_id must be a non-empty string when supplied.")

    body_input = _mapping_field(profile_input, "body", warnings)
    if body_input is not None:
        _report_unknown_fields(body_input, frozenset(BODY_FIELDS), "body", unsupported_values)
        for field in BODY_FIELDS:
            profile["body"][field] = _positive_measurement(
                body_input.get(field),
                f"body.{field}",
                warnings,
            )

    fit_input = _mapping_field(profile_input, "fit_preferences", warnings)
    if fit_input is not None:
        _report_unknown_fields(
            fit_input,
            frozenset(FIT_PREFERENCE_FIELDS),
            "fit_preferences",
            unsupported_values,
        )
        for field in FIT_PREFERENCE_FIELDS:
            value = fit_input.get(field)
            if value is not None:
                normalized = _normalize_alias(value, FIT_PREFERENCE_ALIASES)
                if normalized is None:
                    warnings.append(
                        f"fit_preferences.{field} must be a supported fit preference."
                    )
                else:
                    profile["fit_preferences"][field] = normalized

    profile["style_modes"] = _normalize_style_modes(
        profile_input.get("style_modes"),
        warnings,
        unsupported_values,
    )
    profile["style_keywords"] = _normalize_identifier_list(
        profile_input.get("style_keywords"),
        "style_keywords",
        warnings,
        unsupported_values,
    )

    colors_input = _mapping_field(profile_input, "color_preferences", warnings)
    if colors_input is not None:
        _report_unknown_fields(
            colors_input,
            frozenset({"preferred", "avoid"}),
            "color_preferences",
            unsupported_values,
        )
        profile["color_preferences"]["preferred"] = _normalize_identifier_list(
            colors_input.get("preferred"),
            "color_preferences.preferred",
            warnings,
            unsupported_values,
            aliases=COLOR_ALIASES,
        )
        profile["color_preferences"]["avoid"] = _normalize_identifier_list(
            colors_input.get("avoid"),
            "color_preferences.avoid",
            warnings,
            unsupported_values,
            aliases=COLOR_ALIASES,
        )

    accessories_input = _mapping_field(profile_input, "accessory_preferences", warnings)
    if accessories_input is not None:
        accessory_fields = frozenset(profile["accessory_preferences"])
        _report_unknown_fields(
            accessories_input,
            accessory_fields,
            "accessory_preferences",
            unsupported_values,
        )
        for field in profile["accessory_preferences"]:
            aliases = COLOR_ALIASES if field == "preferred_colors" else None
            profile["accessory_preferences"][field] = _normalize_identifier_list(
                accessories_input.get(field),
                f"accessory_preferences.{field}",
                warnings,
                unsupported_values,
                aliases=aliases,
            )

    profile["usage_contexts"] = _normalize_identifier_list(
        profile_input.get("usage_contexts"),
        "usage_contexts",
        warnings,
        unsupported_values,
    )

    budget_input = _mapping_field(profile_input, "budget", warnings)
    if budget_input is not None:
        _report_unknown_fields(
            budget_input,
            frozenset({"currency", "max_total"}),
            "budget",
            unsupported_values,
        )
        currency = budget_input.get("currency")
        if currency is not None:
            if isinstance(currency, str) and currency.strip():
                profile["budget"]["currency"] = currency.strip().upper()
            else:
                warnings.append("budget.currency must be a non-empty string when supplied.")

        max_total = budget_input.get("max_total")
        if max_total is not None:
            if _is_number(max_total) and max_total >= 0:
                profile["budget"]["max_total"] = max_total
            else:
                warnings.append(
                    "budget.max_total must be a non-negative number when supplied."
                )

    notes = profile_input.get("notes")
    if notes is not None:
        if isinstance(notes, Mapping):
            profile["notes"] = deepcopy(dict(notes))
        else:
            warnings.append("notes must be a mapping when supplied.")

    return _result(profile, warnings, unsupported_values, profile_input)


def _empty_profile() -> dict[str, Any]:
    """Create a canonical profile with no inferred values."""

    return {
        "user_id": None,
        "body": {field: None for field in BODY_FIELDS},
        "fit_preferences": {field: None for field in FIT_PREFERENCE_FIELDS},
        "style_modes": [],
        "style_keywords": [],
        "color_preferences": {"preferred": [], "avoid": []},
        "accessory_preferences": {
            "preferred_metals": [],
            "preferred_colors": [],
            "preferred_scale": [],
            "preferred_shapes": [],
            "preferred_types": [],
            "avoid": [],
        },
        "usage_contexts": [],
        "budget": {"currency": None, "max_total": None},
        "notes": {},
    }


def _result(
    profile: dict[str, Any],
    warnings: list[str],
    unsupported_values: list[dict[str, Any]],
    source: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the public result shape with useful missing-field paths."""

    return {
        "profile": profile,
        "warnings": warnings,
        "unsupported_values": unsupported_values,
        "missing_fields": _missing_fields(profile, source),
    }


def _mapping_field(
    source: Mapping[str, Any],
    field: str,
    warnings: list[str],
) -> Mapping[str, Any] | None:
    """Return a supplied mapping field or report a malformed value."""

    value = source.get(field)
    if value is None:
        return None
    if isinstance(value, Mapping):
        return value
    warnings.append(f"{field} must be a mapping when supplied.")
    return None


def _positive_measurement(
    value: Any,
    field_path: str,
    warnings: list[str],
) -> int | float | None:
    """Validate a supplied measurement without imposing demographic assumptions."""

    if value is None:
        return None
    if _is_number(value) and value > 0:
        return value
    warnings.append(f"{field_path} must be a positive number when supplied.")
    return None


def _is_number(value: Any) -> bool:
    """Return whether a value is numeric but not a boolean."""

    return isinstance(value, Real) and not isinstance(value, bool)


def _normalize_style_modes(
    value: Any,
    warnings: list[str],
    unsupported_values: list[dict[str, Any]],
) -> list[str]:
    """Normalize supported style-mode aliases and report unsupported values."""

    if value is None:
        return []
    if not isinstance(value, list):
        warnings.append("style_modes must be a list when supplied.")
        return []

    normalized_values: list[str] = []
    for item in value:
        normalized = _normalize_alias(item, STYLE_MODE_ALIASES)
        if normalized is None:
            unsupported_values.append(
                {
                    "field": "style_modes",
                    "value": item,
                    "reason": "unsupported_style_mode",
                }
            )
            continue
        _append_unique(normalized_values, normalized)
    return normalized_values


def _normalize_identifier_list(
    value: Any,
    field_path: str,
    warnings: list[str],
    unsupported_values: list[dict[str, Any]],
    *,
    aliases: Mapping[str, str] | None = None,
) -> list[str]:
    """Normalize a list of enum-like identifiers without expanding a taxonomy."""

    if value is None:
        return []
    if not isinstance(value, list):
        warnings.append(f"{field_path} must be a list when supplied.")
        return []

    normalized_values: list[str] = []
    for item in value:
        normalized = _normalize_identifier(item)
        if normalized is None:
            unsupported_values.append(
                {
                    "field": field_path,
                    "value": item,
                    "reason": "malformed_identifier",
                }
            )
            continue
        if aliases is not None:
            normalized = aliases.get(normalized.replace("_", " "), normalized)
        _append_unique(normalized_values, normalized)
    return normalized_values


def _normalize_alias(value: Any, aliases: Mapping[str, str]) -> str | None:
    """Normalize an input token and return a known canonical alias."""

    normalized = _normalize_identifier(value)
    if normalized is None:
        return None
    return aliases.get(normalized.replace("_", " "))


def _normalize_identifier(value: Any) -> str | None:
    """Convert case, hyphen, and whitespace variants to snake_case."""

    if not isinstance(value, str):
        return None
    words = value.strip().casefold().replace("-", " ").replace("_", " ").split()
    return "_".join(words) if words else None


def _append_unique(values: list[str], value: str) -> None:
    """Append a normalized identifier once while preserving input order."""

    if value not in values:
        values.append(value)


def _report_unknown_fields(
    source: Mapping[str, Any],
    allowed_fields: frozenset[str],
    prefix: str,
    unsupported_values: list[dict[str, Any]],
) -> None:
    """Record unrecognized structured fields rather than silently retaining them."""

    for field, value in source.items():
        if field not in allowed_fields:
            path = f"{prefix}.{field}" if prefix else field
            unsupported_values.append(
                {
                    "field": path,
                    "value": value,
                    "reason": "unsupported_field",
                }
            )


def _missing_fields(
    profile: Mapping[str, Any],
    source: Mapping[str, Any] | None,
) -> list[str]:
    """Return canonical optional fields that remain unknown after resolution."""

    missing: list[str] = []
    if profile["user_id"] is None:
        missing.append("user_id")

    for section in ("body", "fit_preferences"):
        for field, value in profile[section].items():
            if value is None:
                missing.append(f"{section}.{field}")

    for section in ("style_modes", "style_keywords", "usage_contexts", "notes"):
        if not _supplied_as_expected_type(source, section, list if section != "notes" else Mapping):
            missing.append(section)

    for section in ("color_preferences", "accessory_preferences"):
        source_section = source.get(section) if isinstance(source, Mapping) else None
        for field, value in profile[section].items():
            if (
                not isinstance(source_section, Mapping)
                or field not in source_section
                or not isinstance(source_section[field], list)
            ):
                missing.append(f"{section}.{field}")

    for field, value in profile["budget"].items():
        if value is None:
            missing.append(f"budget.{field}")

    return missing


def _supplied_as_expected_type(
    source: Mapping[str, Any] | None,
    field: str,
    expected_type: type[Any],
) -> bool:
    """Return whether an optional field was explicitly supplied in valid shape."""

    return (
        isinstance(source, Mapping)
        and field in source
        and isinstance(source[field], expected_type)
    )
