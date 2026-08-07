"""Shared numeric rounding utilities for Pydantic model validators."""

from __future__ import annotations

from functools import partial
from typing import Callable, ClassVar

from pydantic import BaseModel, model_validator


def round_db(v: float | None, dp: int = 2) -> float | None:
    """Round a dB value. Returns None unchanged."""
    return round(v, dp) if v is not None else v


def round_hz(v: float | None, dp: int = 1) -> float | None:
    """Round a Hz value. Returns None unchanged."""
    return round(v, dp) if v is not None else v


def round_ratio(v: float | None, dp: int = 4) -> float | None:
    """Round a dimensionless ratio. Returns None unchanged."""
    return round(v, dp) if v is not None else v


def round_ratio_list(v: list[float] | None, dp: int = 4) -> list[float] | None:
    """Round a list of dimensionless ratios. Returns None unchanged."""
    return [round(x, dp) for x in v] if v is not None else v


def round_ms(v: float | None, dp: int = 2) -> float | None:
    """Round a milliseconds value. Returns None unchanged."""
    return round(v, dp) if v is not None else v


def round_pct(v: float | None, dp: int = 1) -> float | None:
    """Round a percentage value. Returns None unchanged."""
    return round(v, dp) if v is not None else v


def round_db_dict(v: dict[str, float] | None, dp: int = 2) -> dict[str, float] | None:
    """Round all values in a dict of dB values. Returns None unchanged."""
    return {k: round(val, dp) for k, val in v.items()} if v is not None else v


def round_list(v: list[float] | None, dp: int = 4) -> list[float] | None:
    """Round each value in a unit-neutral list. Returns None unchanged.

    The unit-neutral primitive: use for values with no dB/ratio semantics
    (e.g. RangeDeviationResult.target_range), so unit-typed helpers are not
    borrowed for the wrong units (review F8).
    """
    return [round(x, dp) for x in v] if v is not None else v


def round_dict(v: dict[str, float] | None, dp: int = 2) -> dict[str, float] | None:
    """Round each value in a unit-neutral dict. Returns None unchanged.

    The unit-neutral primitive: use for values with no dB semantics (e.g.
    PhaseResult.per_band_correlation, unit-neutral correlation coefficients),
    so round_db_dict is not borrowed for the wrong unit (review F8).
    """
    return {k: round(val, dp) for k, val in v.items()} if v is not None else v


class RoundedModel(BaseModel):
    """Base model that applies per-field rounding on validation (B.3).

    Subclasses declare ``_ROUND_FIELDS``: ``{field_name: rounding callable}``.
    A ``mode="before"`` model validator applies each callable to the incoming
    value before field validation, replacing the repeated
    ``@field_validator`` boilerplate that used to wrap every helper in this
    module (23 decorators across src). The callables are the same ones the
    decorators called, so emitted values are numerically identical.

    A field whose incoming value is present-but-``None`` passes through
    unchanged (the helpers are None-tolerant anyway); the field's own
    validation (type coercion, required) is untouched. ``model_copy`` does not
    revalidate, exactly as before.
    """

    _ROUND_FIELDS: ClassVar[dict[str, Callable[[object], object]]] = {}

    @model_validator(mode="before")
    @classmethod
    def _apply_declared_rounding(cls, values):
        """Round each declared field that is present and not None."""
        if not isinstance(values, dict):
            return values
        spec = cls._ROUND_FIELDS
        if not spec:
            return values
        # New dict: never mutate caller-owned input.
        updated = dict(values)
        for field, fn in spec.items():
            if field in updated and updated[field] is not None:
                updated[field] = fn(updated[field])
        return updated


# Round to 3 decimals: used by facade's StemDiagnosticResult.duration_seconds.
round_duration = partial(round, ndigits=3)
