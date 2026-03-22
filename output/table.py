"""Console output formatting."""

from tabulate import tabulate


def print_summary_table(summary: dict, model_name: str = ""):
    """Print formatted summary table to console."""
    if summary["total_trades"] == 0:
        print("No trades generated.")
        return

    header = f"=== Backtest Results: {model_name} ===" if model_name else "=== Backtest Results ==="
    print(f"\n{header}")
    print(f"Total Trades: {summary['total_trades']}")
    print(f"Wins: {summary['wins']} | Losses: {summary['losses']}")
    print(f"Win Rate: {summary['win_rate']:.1%}")
    print(f"Total P&L: ${summary['total_pnl']:,.2f}")
    print(f"ROI: {summary['roi']:.2%}")
    print(f"Avg P&L/Trade: ${summary['avg_pnl_per_trade']:.2f}")
    print(f"Max Drawdown: ${summary['max_drawdown']:.2f}")

    # Per-company breakdown
    rows = []
    for ticker, stats in sorted(summary["by_company"].items(), key=lambda x: x[1]["total_pnl"], reverse=True):
        rows.append([
            ticker,
            f"{stats['beat_rate']:.0%}",
            stats["trades"],
            stats["wins"],
            f"{stats['win_rate']:.0%}",
            f"${stats['total_pnl']:,.2f}",
            f"{stats['avg_edge']:.1%}",
        ])

    print("\n" + tabulate(
        rows,
        headers=["Ticker", "Beat Rate", "Trades", "Wins", "Win Rate", "P&L", "Avg Edge"],
        tablefmt="simple",
    ))
    print()
