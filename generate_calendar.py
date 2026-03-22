"""Generate upcoming earnings calendar data with live Polymarket prices."""
import json
import os
import warnings
import datetime
warnings.filterwarnings("ignore")

import yfinance as yf
import config
from backtest.beat_rate import overall_beat_rate
from data.earnings import fetch_earnings_history
from data.polymarket import fetch_active_earnings


def get_upcoming_earnings(tickers, weeks_ahead=4):
    """Fetch upcoming earnings dates + live Polymarket data."""
    # Get live Polymarket markets first (includes EPS thresholds)
    print("Fetching live Polymarket markets...")
    poly_markets = fetch_active_earnings()
    poly_by_ticker = {m["ticker"]: m for m in poly_markets}
    print(f"  Got {len(poly_by_ticker)} markets: {list(poly_by_ticker.keys())}")

    # Merge tickers
    all_tickers = list(set(tickers) | set(poly_by_ticker.keys()))

    results = []
    today = datetime.date.today()
    end = today + datetime.timedelta(weeks=weeks_ahead)

    for ticker in all_tickers:
        try:
            tk = yf.Ticker(ticker)
            cal = tk.calendar
            if not cal or "Earnings Date" not in cal:
                continue
            dates = cal["Earnings Date"]
            if not dates:
                continue
            earn_date = dates[0]
            if isinstance(earn_date, datetime.datetime):
                earn_date = earn_date.date()
            if earn_date < today - datetime.timedelta(days=7) or earn_date > end:
                continue

            # Get beat rate from yfinance history
            earnings = fetch_earnings_history(ticker, num_quarters=30)
            beat_rate = None
            last_eps = None
            if not earnings.empty:
                beat_rate = round(overall_beat_rate(earnings) * 100)
                last_row = earnings.iloc[-1]
                last_eps = round(float(last_row["eps_actual"]), 2)

            # Polymarket data (priority source for EPS and price)
            poly = poly_by_ticker.get(ticker)
            poly_price = None
            poly_eps = None
            poly_eps_type = None
            has_polymarket = False

            if poly:
                has_polymarket = True
                poly_price = poly["yes_price"]
                poly_eps = poly.get("eps_threshold")
                poly_eps_type = poly.get("eps_type", "unknown")

            # EPS estimate: prefer Polymarket threshold, fallback to yfinance
            eps_est = poly_eps
            if eps_est is None:
                yf_eps = cal.get("Earnings Average")
                eps_est = round(float(yf_eps), 2) if yf_eps else None

            eps_high = cal.get("Earnings High")
            eps_low = cal.get("Earnings Low")

            results.append({
                "ticker": ticker,
                "date": str(earn_date),
                "eps_estimate": eps_est,
                "eps_type": poly_eps_type if poly_eps_type else "consensus",
                "eps_high": round(float(eps_high), 2) if eps_high else None,
                "eps_low": round(float(eps_low), 2) if eps_low else None,
                "last_eps": last_eps,
                "beat_rate": beat_rate,
                "polymarket_price": round(poly_price * 100) if poly_price else None,
                "reported": earn_date < today,
                "has_polymarket": has_polymarket,
            })
        except Exception as e:
            print(f"  Skip {ticker}: {e}")
            continue

    results.sort(key=lambda x: x["date"])
    return results


def generate():
    print("Generating earnings calendar...\n")
    all_tickers = list(set(config.TICKERS))
    data = get_upcoming_earnings(all_tickers, weeks_ahead=4)
    print(f"\nFound {len(data)} upcoming earnings")

    output_path = os.path.join(config.OUTPUT_DIR, "calendar_data.json")
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved to {output_path}")


if __name__ == "__main__":
    generate()
