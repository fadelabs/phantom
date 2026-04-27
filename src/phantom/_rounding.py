"""Shared numeric rounding utilities for Pydantic model validators."""

from __future__ import annotations


def round_db(v: float | None, dp: int = 2) -> float | None:
    """Round a dB value. Returns None unchanged."""
    return round(v, dp) if v is not None else v


def round_hz(v: float | None, dp: int = 1) -> float | None:
    """Round a Hz value. Returns None unchanged."""
    return round(v, dp) if v is not None else v


def round_db_list(v: list[float] | None, dp: int = 2) -> list[float] | None:
    """Round a list of dB values. Returns None unchanged."""
    return [round(x, dp) for x in v] if v is not None else v


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
