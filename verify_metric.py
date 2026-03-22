"""Verify script for auto-research-loop: outputs the ROI metric."""
import sys
import warnings
warnings.filterwarnings("ignore")

import config
from backtest.simulator import run_backtest, summarize_results


def get_roi():
    """Run backtest and return ROI as a single number."""
    tickers = config.TICKERS
    df = run_backtest(tickers, price_model="market_average")
    summary = summarize_results(df)

    total_pnl = summary["total_pnl"]
    total_trades = summary["total_trades"]
    total_bet = total_trades * config.BET_SIZE

    roi = (total_pnl / total_bet * 100) if total_bet > 0 else 0
    win_rate = summary["win_rate"] * 100

    # Print metric value (last line is what the loop reads)
    print(f"trades={total_trades} wins={summary['wins']} pnl=${total_pnl:.0f} win_rate={win_rate:.1f}%", file=sys.stderr)
    print(f"{roi:.2f}")


if __name__ == "__main__":
    get_roi()
