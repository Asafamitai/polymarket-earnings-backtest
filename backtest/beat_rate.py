"""Calculate rolling beat rates from earnings history."""

import math

import pandas as pd


def calculate_rolling_beat_rate(earnings_df: pd.DataFrame, min_periods: int = 4, recency_weight: float = 4.0) -> pd.Series:
    """Calculate rolling beat rate at each quarter using only prior data.

    Uses exponential recency weighting: more recent quarters count more.
    recency_weight > 1.0 means recent quarters are weighted more heavily.
    Returns NaN for the first min_periods entries.
    """
    if earnings_df.empty or "beat" not in earnings_df.columns:
        return pd.Series(dtype=float)

    n = len(earnings_df)
    rates = pd.Series([float("nan")] * n, index=earnings_df.index)

    for i in range(min_periods, n):
        past_beats = earnings_df["beat"].iloc[:i].values
        num = len(past_beats)
        if num == 0:
            continue
        if recency_weight > 1.0:
            weights = [recency_weight ** (j / max(num - 1, 1)) for j in range(num)]
            total_w = sum(weights)
            if total_w > 0:
                val = sum(b * w for b, w in zip(past_beats, weights)) / total_w
                rates.iloc[i] = max(0.0, min(1.0, val))  # clamp to [0, 1]
        else:
            rates.iloc[i] = past_beats.sum() / num

    return rates


def overall_beat_rate(earnings_df: pd.DataFrame) -> float:
    """Calculate overall beat rate across all quarters."""
    if earnings_df.empty or "beat" not in earnings_df.columns:
        return 0.0
    count = len(earnings_df)
    if count == 0:
        return 0.0
    return float(earnings_df["beat"].sum()) / count


def safe_beat_rate(value) -> float:
    """Return a safe beat rate value, replacing NaN/None with 0.0."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return 0.0
    return max(0.0, min(1.0, float(value)))
