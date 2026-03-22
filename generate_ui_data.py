"""Generate JSON data for the web UI."""

import json
import warnings
warnings.filterwarnings("ignore")

import config
from data.earnings import fetch_earnings_history
from backtest.beat_rate import calculate_rolling_beat_rate, overall_beat_rate
from backtest.simulator import run_backtest, summarize_results


def generate():
    tickers = config.TICKERS
    companies = {}

    for ticker in tickers:
        print(f"  {ticker}...")
        earnings = fetch_earnings_history(ticker, num_quarters=30)
        if earnings.empty:
            continue

        br = overall_beat_rate(earnings)
        poly_price = config.POLYMARKET_PRICES.get(ticker)

        # Earnings history for the table
        history = []
        for _, row in earnings.iterrows():
            history.append({
                "date": str(row["date"])[:10],
                "eps_estimate": round(row["eps_estimate"], 3),
                "eps_actual": round(row["eps_actual"], 3),
                "beat": bool(row["beat"]),
            })

        companies[ticker] = {
            "ticker": ticker,
            "beat_rate": round(br, 4),
            "total_quarters": len(earnings),
            "beats": int(earnings["beat"].sum()),
            "misses": int((~earnings["beat"]).sum()),
            "polymarket_price": poly_price,
            "history": history,
        }

    # Run backtests for both models
    for model in ["company_specific", "market_average"]:
        print(f"\nRunning {model} backtest...")
        df = run_backtest(tickers, price_model=model)
        if df.empty:
            continue
        for ticker, group in df.groupby("ticker"):
            if ticker not in companies:
                continue
            trades = []
            for _, row in group.iterrows():
                trades.append({
                    "date": str(row["date"])[:10],
                    "beat_rate": round(row["beat_rate"], 4),
                    "poly_price": round(row["poly_price"], 4),
                    "side": row["side"],
                    "edge": round(row["edge"], 4),
                    "cost": round(row["cost"], 4),
                    "actual_beat": bool(row["actual_beat"]),
                    "pnl": round(row["pnl"], 2),
                })
            w = sum(1 for t in trades if t["pnl"] > 0)
            total_pnl = sum(t["pnl"] for t in trades)
            companies[ticker][f"{model}_trades"] = trades
            companies[ticker][f"{model}_total_pnl"] = round(total_pnl, 2)
            companies[ticker][f"{model}_win_rate"] = round(w / len(trades), 4) if trades else 0
            companies[ticker][f"{model}_num_trades"] = len(trades)

    with open("output/ui_data.json", "w") as f:
        json.dump(companies, f, indent=2)
    print(f"\nSaved data for {len(companies)} companies to output/ui_data.json")


if __name__ == "__main__":
    generate()
