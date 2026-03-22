"""Core backtest simulation engine."""

import pandas as pd

import config
from data.earnings import fetch_earnings_history
from backtest.beat_rate import calculate_rolling_beat_rate
from backtest.strategy import decide_position


def _get_price(ticker: str, rolling_beat_rate: float, price_model: str) -> float:
    """Get the Polymarket Yes price based on the price model."""
    if price_model == "market_average":
        return config.MARKET_AVG_BEAT_RATE

    # company_specific model
    if ticker in config.POLYMARKET_PRICES:
        return config.POLYMARKET_PRICES[ticker]

    # Synthetic price: assume market is slightly efficient (beat_rate - 5%), clamped
    return max(0.50, min(0.95, rolling_beat_rate - 0.05))


def run_backtest(tickers: list = None, price_model: str = "company_specific") -> pd.DataFrame:
    """Run the full backtest simulation.

    Args:
        tickers: list of ticker symbols (defaults to config.TICKERS)
        price_model: "company_specific" or "market_average"

    Returns:
        DataFrame with columns: ticker, date, beat_rate, poly_price, side, edge,
                                cost, actual_beat, pnl, cumulative_pnl
    """
    if tickers is None:
        tickers = config.TICKERS

    all_trades = []

    for ticker in tickers:
        print(f"  Fetching {ticker}...")
        earnings = fetch_earnings_history(ticker, num_quarters=30)

        if len(earnings) < config.MIN_HISTORY_QUARTERS + 1:
            print(f"  Skipping {ticker}: only {len(earnings)} quarters (need {config.MIN_HISTORY_QUARTERS + 1})")
            continue

        rolling_br = calculate_rolling_beat_rate(earnings, min_periods=config.MIN_HISTORY_QUARTERS)

        for i in range(config.MIN_HISTORY_QUARTERS, len(earnings)):
            br = rolling_br.iloc[i]
            if pd.isna(br):
                continue

            poly_price = _get_price(ticker, br, price_model)
            position = decide_position(br, poly_price, config.EDGE_THRESHOLD)

            if position["side"] == "SKIP":
                continue

            actual_beat = earnings["beat"].iloc[i]

            # Calculate P&L
            if position["side"] == "YES":
                if actual_beat:
                    pnl = config.BET_SIZE * (1.0 / position["cost"] - 1.0)
                else:
                    pnl = -config.BET_SIZE
            else:  # NO
                if not actual_beat:
                    pnl = config.BET_SIZE * (1.0 / position["cost"] - 1.0)
                else:
                    pnl = -config.BET_SIZE

            all_trades.append({
                "ticker": ticker,
                "date": earnings["date"].iloc[i],
                "beat_rate": br,
                "poly_price": poly_price,
                "side": position["side"],
                "edge": position["edge"],
                "cost": position["cost"],
                "actual_beat": actual_beat,
                "pnl": round(pnl, 2),
            })

    if not all_trades:
        return pd.DataFrame()

    df = pd.DataFrame(all_trades)
    df = df.sort_values("date").reset_index(drop=True)
    df["cumulative_pnl"] = df["pnl"].cumsum()

    return df


def summarize_results(results_df: pd.DataFrame) -> dict:
    """Generate summary statistics from backtest results."""
    if results_df.empty:
        return {"total_trades": 0}

    total = len(results_df)
    wins = (results_df["pnl"] > 0).sum()
    losses = (results_df["pnl"] <= 0).sum()

    total_invested = (results_df["cost"] * config.BET_SIZE).sum()

    by_company = {}
    for ticker, group in results_df.groupby("ticker"):
        t = len(group)
        w = (group["pnl"] > 0).sum()
        by_company[ticker] = {
            "trades": t,
            "wins": w,
            "losses": t - w,
            "win_rate": w / t if t > 0 else 0,
            "total_pnl": round(group["pnl"].sum(), 2),
            "avg_edge": round(group["edge"].mean(), 4),
            "beat_rate": round(group["beat_rate"].mean(), 4),
        }

    return {
        "total_trades": total,
        "wins": int(wins),
        "losses": int(losses),
        "win_rate": round(wins / total, 4) if total > 0 else 0,
        "total_pnl": round(results_df["pnl"].sum(), 2),
        "roi": round(results_df["pnl"].sum() / total_invested, 4) if total_invested > 0 else 0,
        "avg_pnl_per_trade": round(results_df["pnl"].mean(), 2),
        "max_drawdown": round(_max_drawdown(results_df["cumulative_pnl"]), 2),
        "by_company": by_company,
    }


def _max_drawdown(cumulative_pnl: pd.Series) -> float:
    """Calculate maximum drawdown from cumulative P&L."""
    peak = cumulative_pnl.cummax()
    drawdown = cumulative_pnl - peak
    return drawdown.min()
