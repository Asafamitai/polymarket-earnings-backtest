"""Calculate rolling beat rates from earnings history."""

import pandas as pd


def calculate_rolling_beat_rate(earnings_df: pd.DataFrame, min_periods: int = 4) -> pd.Series:
    """Calculate rolling beat rate at each quarter using only prior data.

    At index i, beat_rate = count(beat=True in 0..i-1) / i
    Returns NaN for the first min_periods entries.
    """
    n = len(earnings_df)
    rates = pd.Series([float("nan")] * n, index=earnings_df.index)

    for i in range(min_periods, n):
        past = earnings_df["beat"].iloc[:i]
        rates.iloc[i] = past.sum() / len(past)

    return rates


def overall_beat_rate(earnings_df: pd.DataFrame) -> float:
    """Calculate overall beat rate across all quarters."""
    if earnings_df.empty:
        return 0.0
    return earnings_df["beat"].sum() / len(earnings_df)
