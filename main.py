"""Polymarket Earnings Call Backtest - Entry Point."""

import argparse
import warnings

warnings.filterwarnings("ignore")

import config
from backtest.simulator import run_backtest, summarize_results
from output.table import print_summary_table
from output.charts import plot_results


def main():
    parser = argparse.ArgumentParser(description="Polymarket Earnings Call Backtest")
    parser.add_argument("--edge-threshold", type=float, default=config.EDGE_THRESHOLD,
                        help=f"Minimum edge to trade (default: {config.EDGE_THRESHOLD})")
    parser.add_argument("--min-quarters", type=int, default=config.MIN_HISTORY_QUARTERS,
                        help=f"Min history quarters (default: {config.MIN_HISTORY_QUARTERS})")
    parser.add_argument("--bet-size", type=float, default=config.BET_SIZE,
                        help=f"Bet size per trade (default: ${config.BET_SIZE})")
    parser.add_argument("--no-charts", action="store_true", help="Skip chart generation")
    parser.add_argument("--tickers", nargs="+", help="Override ticker list")
    args = parser.parse_args()

    # Apply overrides
    config.EDGE_THRESHOLD = args.edge_threshold
    config.MIN_HISTORY_QUARTERS = args.min_quarters
    config.BET_SIZE = args.bet_size

    tickers = args.tickers or config.TICKERS
    print(f"Running backtest for {len(tickers)} tickers...")
    print(f"Edge threshold: {config.EDGE_THRESHOLD:.0%} | Min quarters: {config.MIN_HISTORY_QUARTERS} | Bet size: ${config.BET_SIZE}")

    results = {}

    for model in ["company_specific", "market_average"]:
        print(f"\n--- Price Model: {model.replace('_', ' ').title()} ---")
        df = run_backtest(tickers, price_model=model)
        summary = summarize_results(df)
        print_summary_table(summary, model_name=model.replace("_", " ").title())
        results[model] = {"df": df, "summary": summary}

    if not args.no_charts:
        print("\nGenerating charts...")
        plot_results(results)


if __name__ == "__main__":
    main()
