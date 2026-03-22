"""Fetch historical earnings data via yfinance with caching."""

import json
import os
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

import config


def _cache_path(ticker: str) -> Path:
    return Path(config.CACHE_DIR) / f"{ticker}.json"


def _is_cache_fresh(path: Path) -> bool:
    if not path.exists():
        return False
    age_hours = (time.time() - path.stat().st_mtime) / 3600
    return age_hours < config.CACHE_TTL_HOURS


def fetch_earnings_history(ticker: str, num_quarters: int = 20) -> pd.DataFrame:
    """Fetch earnings history for a ticker. Returns DataFrame with columns:
    date, eps_estimate, eps_actual, beat
    Sorted by date ascending (oldest first).
    """
    cache_file = _cache_path(ticker)

    if _is_cache_fresh(cache_file):
        with open(cache_file) as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])
            return df.tail(num_quarters).reset_index(drop=True)

    try:
        t = yf.Ticker(ticker)
        ed = t.earnings_dates
    except Exception as e:
        print(f"  Warning: failed to fetch {ticker}: {e}")
        return pd.DataFrame()

    if ed is None or ed.empty:
        return pd.DataFrame()

    df = ed.reset_index()
    df = df.rename(columns={
        "Earnings Date": "date",
        "EPS Estimate": "eps_estimate",
        "Reported EPS": "eps_actual",
    })
    df = df[["date", "eps_estimate", "eps_actual"]].copy()

    # Remove future earnings (no actual yet)
    df = df.dropna(subset=["eps_actual"])
    # Remove rows with no estimate
    df = df.dropna(subset=["eps_estimate"])

    # Determine beat
    if config.BEAT_INCLUDES_MEET:
        df["beat"] = df["eps_actual"] >= df["eps_estimate"]
    else:
        df["beat"] = df["eps_actual"] > df["eps_estimate"]

    # Sort oldest first
    df = df.sort_values("date").reset_index(drop=True)

    # Cache
    os.makedirs(config.CACHE_DIR, exist_ok=True)
    cache_data = df.copy()
    cache_data["date"] = cache_data["date"].astype(str)
    cache_data.to_json(str(cache_file), orient="records", indent=2)

    return df.tail(num_quarters).reset_index(drop=True)
