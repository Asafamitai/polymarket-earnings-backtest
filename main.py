"""Polymarket Earnings Call Backtest - Entry Point."""

import argparse
import logging
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

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

    # Validate CLI args
    if not 0.0 < args.edge_threshold < 1.0:
        parser.error("--edge-threshold must be between 0.0 and 1.0")
    if not 1 <= args.min_quarters <= 30:
        parser.error("--min-quarters must be between 1 and 30")
    if args.bet_size <= 0:
        parser.error("--bet-size must be positive")

    # Apply overrides
    config.EDGE_THRESHOLD = args.edge_threshold
    config.MIN_HISTORY_QUARTERS = args.min_quarters
    config.BET_SIZE = args.bet_size

    # Validate config
    config.validate_config()

    tickers = args.tickers or config.TICKERS
    logger.info(f"Running backtest for {len(tickers)} tickers...")
    logger.info(f"Edge threshold: {config.EDGE_THRESHOLD:.0%} | Min quarters: {config.MIN_HISTORY_QUARTERS} | Bet size: ${config.BET_SIZE}")

    results = {}

    for model in ["company_specific", "market_average"]:
        logger.info(f"--- Price Model: {model.replace('_', ' ').title()} ---")
        df = run_backtest(tickers, price_model=model)
        summary = summarize_results(df)
        print_summary_table(summary, model_name=model.replace("_", " ").title())
        results[model] = {"df": df, "summary": summary}

    if not args.no_charts:
        logger.info("Generating charts...")
        plot_results(results)


if __name__ == "__main__":
    main()
