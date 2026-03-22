"""Calculate rolling beat rates from earnings history."""

import pandas as pd


def calculate_rolling_beat_rate(earnings_df: pd.DataFrame, min_periods: int = 4, recency_weight: float = 4.0) -> pd.Series:
    """Calculate rolling beat rate at each quarter using only prior data.

    Uses exponential recency weighting: more recent quarters count more.
    recency_weight > 1.0 means recent quarters are weighted more heavily.
    Returns NaN for the first min_periods entries.
    """
    n = len(earnings_df)
    rates = pd.Series([float("nan")] * n, index=earnings_df.index)

    for i in range(min_periods, n):
        past_beats = earnings_df["beat"].iloc[:i].values
        num = len(past_beats)
        if recency_weight > 1.0:
            # Exponential weights: most recent gets highest weight
            weights = [recency_weight ** (j / max(num - 1, 1)) for j in range(num)]
            total_w = sum(weights)
            rates.iloc[i] = sum(b * w for b, w in zip(past_beats, weights)) / total_w
        else:
            rates.iloc[i] = past_beats.sum() / num

    return rates


def overall_beat_rate(earnings_df: pd.DataFrame) -> float:
    """Calculate overall beat rate across all quarters."""
    if earnings_df.empty:
        return 0.0
    return earnings_df["beat"].sum() / len(earnings_df)
