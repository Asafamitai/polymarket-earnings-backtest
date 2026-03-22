"""Visualization charts for backtest results."""

import matplotlib.pyplot as plt
import pandas as pd


def plot_results(results: dict, output_dir: str = "output"):
    """Generate charts comparing both price models.

    Args:
        results: dict with keys "company_specific" and "market_average",
                 each containing {"df": DataFrame, "summary": dict}
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Polymarket Earnings Backtest Results", fontsize=14, fontweight="bold")

    # 1. Cumulative P&L comparison
    ax = axes[0, 0]
    for model_name, data in results.items():
        df = data["df"]
        if df.empty:
            continue
        label = model_name.replace("_", " ").title()
        ax.plot(range(len(df)), df["cumulative_pnl"], label=label)
    ax.set_xlabel("Trade #")
    ax.set_ylabel("Cumulative P&L ($)")
    ax.set_title("Cumulative P&L")
    ax.legend()
    ax.axhline(y=0, color="gray", linestyle="--", alpha=0.5)
    ax.grid(True, alpha=0.3)

    # 2. Beat rate distribution
    ax = axes[0, 1]
    for model_name, data in results.items():
        df = data["df"]
        if df.empty:
            continue
        label = model_name.replace("_", " ").title()
        ax.hist(df["beat_rate"], bins=20, alpha=0.5, label=label)
    ax.set_xlabel("Beat Rate")
    ax.set_ylabel("Frequency")
    ax.set_title("Beat Rate Distribution (at trade time)")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 3. Edge vs P&L scatter (using first model with data)
    ax = axes[1, 0]
    for model_name, data in results.items():
        df = data["df"]
        if df.empty:
            continue
        colors = ["green" if p > 0 else "red" for p in df["pnl"]]
        ax.scatter(df["edge"], df["pnl"], c=colors, alpha=0.5, s=20)
        ax.set_xlabel("Edge")
        ax.set_ylabel("P&L ($)")
        ax.set_title(f"Edge vs P&L ({model_name.replace('_', ' ').title()})")
        ax.axhline(y=0, color="gray", linestyle="--", alpha=0.5)
        ax.grid(True, alpha=0.3)
        break

    # 4. Per-company P&L (market_average model, top 15)
    ax = axes[1, 1]
    model_data = results.get("market_average") or results.get("company_specific")
    if model_data and not model_data["df"].empty:
        company_pnl = model_data["df"].groupby("ticker")["pnl"].sum().sort_values()
        top = company_pnl.tail(15) if len(company_pnl) > 15 else company_pnl
        colors = ["green" if v > 0 else "red" for v in top.values]
        ax.barh(top.index, top.values, color=colors)
        ax.set_xlabel("Total P&L ($)")
        ax.set_title("P&L by Company (Market Avg Model)")
        ax.axvline(x=0, color="gray", linestyle="--", alpha=0.5)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(f"{output_dir}/backtest_results.png", dpi=150, bbox_inches="tight")
    print(f"Charts saved to {output_dir}/backtest_results.png")
    plt.show()
