"""Generate trading recommendations with real order book execution prices."""
import json
import math
import warnings
warnings.filterwarnings("ignore")

import config
from data.earnings import fetch_earnings_history
from data.polymarket import fetch_active_earnings, get_execution_prices
from backtest.beat_rate import calculate_rolling_beat_rate, overall_beat_rate


def kelly_fraction(p, odds):
    """Kelly criterion: optimal bet fraction. p=win prob, odds=net payout per $1 bet."""
    if odds <= 0:
        return 0
    f = (p * odds - (1 - p)) / odds
    return max(0, f)


def generate_recommendations(bet_size=100):
    # Load calendar data
    with open("output/calendar_data.json") as f:
        calendar = json.load(f)

    # Load backtest data for historical performance
    with open("output/ui_data.json") as f:
        backtest = json.load(f)

    # Fetch live order book execution prices
    print("Fetching live order books from Polymarket CLOB...")
    active_markets = fetch_active_earnings()
    exec_prices = get_execution_prices(active_markets, bet_size=bet_size)
    print(f"  Got order books for {len(exec_prices)} markets")

    upcoming = [e for e in calendar if not e.get("reported", False)]

    recs = []
    for item in upcoming:
        ticker = item["ticker"]
        bt = backtest.get(ticker, {})
        exec_data = exec_prices.get(ticker)

        # Get rolling beat rate from full history
        earnings = fetch_earnings_history(ticker, num_quarters=30)
        if earnings.empty:
            continue

        rolling_br = calculate_rolling_beat_rate(earnings, min_periods=4)
        current_beat_rate = rolling_br.iloc[-1] if len(rolling_br) > 0 else None
        if current_beat_rate is None or math.isnan(current_beat_rate):
            continue

        total_quarters = len(earnings)
        beats = int(earnings["beat"].sum())

        # --- Confidence factors ---
        sample_conf = min(1.0, total_quarters / 20)
        recent_8 = earnings.tail(8)
        recent_beat_rate = recent_8["beat"].mean() if len(recent_8) >= 4 else current_beat_rate
        consistency = 1.0 - abs(recent_beat_rate - current_beat_rate)
        last_4 = earnings.tail(4)["beat"].tolist()
        streak_bonus = sum(last_4) / len(last_4) if last_4 else 0.5
        bt_trades = bt.get("market_average_num_trades", 0)
        bt_win_rate = bt.get("market_average_win_rate", 0)
        bt_pnl = bt.get("market_average_total_pnl", 0)
        track_record = bt_win_rate if bt_trades >= 3 else 0.5

        raw_confidence = (
            sample_conf * 0.25 +
            consistency * 0.20 +
            streak_bonus * 0.20 +
            track_record * 0.35
        )
        confidence = round(raw_confidence * 100)

        # --- Position decision ---
        # If we have real order book data, use execution prices
        # Otherwise fall back to mid-market price
        if exec_data:
            yes_exec = exec_data["yes"]
            no_exec = exec_data["no"]
            mid_price = exec_data["yes_mid"]

            # Check YES side with real execution cost
            yes_avg_price = yes_exec["avg_price"]
            no_avg_price = no_exec["avg_price"]

            candidates = []

            if yes_avg_price and yes_avg_price > 0:
                yes_edge = current_beat_rate - yes_avg_price
                if yes_edge >= config.EDGE_THRESHOLD:
                    candidates.append({
                        "side": "YES",
                        "exec_price": yes_avg_price,
                        "mid_price": mid_price,
                        "slippage": yes_exec["slippage"],
                        "edge": yes_edge,
                        "cost": yes_avg_price,
                        "win_prob": current_beat_rate,
                        "payout_if_win": yes_exec["profit_if_win"],
                        "loss_if_lose": yes_exec["total_cost"],
                        "total_shares": yes_exec["total_shares"],
                        "depth_available": yes_exec["depth_available"],
                        "levels_used": yes_exec["levels_used"],
                        "fills": yes_exec["fills"],
                    })

            if no_avg_price and no_avg_price > 0:
                no_edge = (1 - current_beat_rate) - no_avg_price
                if no_edge >= config.EDGE_THRESHOLD:
                    candidates.append({
                        "side": "NO",
                        "exec_price": no_avg_price,
                        "mid_price": 1 - mid_price if mid_price else None,
                        "slippage": no_exec["slippage"],
                        "edge": no_edge,
                        "cost": no_avg_price,
                        "win_prob": 1 - current_beat_rate,
                        "payout_if_win": no_exec["profit_if_win"],
                        "loss_if_lose": no_exec["total_cost"],
                        "total_shares": no_exec["total_shares"],
                        "depth_available": no_exec["depth_available"],
                        "levels_used": no_exec["levels_used"],
                        "fills": no_exec["fills"],
                    })

            if not candidates:
                continue

            # Pick best candidate by EV
            for c in candidates:
                if c["payout_if_win"] > 0 and c["loss_if_lose"] > 0:
                    c["ev_per_bet"] = c["win_prob"] * c["payout_if_win"] - (1 - c["win_prob"]) * c["loss_if_lose"]
                    odds = c["payout_if_win"] / c["loss_if_lose"]
                    c["kelly_fraction"] = kelly_fraction(c["win_prob"], odds)
                    variance = c["win_prob"] * (c["payout_if_win"] ** 2) + (1 - c["win_prob"]) * (c["loss_if_lose"] ** 2) - c["ev_per_bet"] ** 2
                    std = math.sqrt(max(0, variance))
                    c["ev_to_risk"] = c["ev_per_bet"] / std if std > 0 else 0
                    c["confidence_ratio"] = c["ev_per_bet"] / (101 - confidence) if confidence < 100 else c["ev_per_bet"]
                else:
                    c["ev_per_bet"] = 0
                    c["kelly_fraction"] = 0
                    c["ev_to_risk"] = 0
                    c["confidence_ratio"] = 0

            best = max(candidates, key=lambda x: x["ev_per_bet"])
            has_orderbook = True

        else:
            # Fallback: use mid-market price from calendar
            poly_price_pct = item.get("polymarket_price")
            if poly_price_pct is None:
                # Use market average
                poly_price_pct = config.MARKET_AVG_BEAT_RATE * 100

            price = poly_price_pct / 100
            yes_edge = current_beat_rate - price
            no_edge = price - current_beat_rate

            if yes_edge >= config.EDGE_THRESHOLD:
                side, edge, cost, win_prob = "YES", yes_edge, price, current_beat_rate
            elif no_edge >= config.EDGE_THRESHOLD:
                side, edge, cost, win_prob = "NO", no_edge, 1 - price, 1 - current_beat_rate
            else:
                continue

            payout_if_win = bet_size * (1.0 / cost - 1.0)
            loss_if_lose = bet_size
            ev = win_prob * payout_if_win - (1 - win_prob) * loss_if_lose
            odds = payout_if_win / loss_if_lose
            kf = kelly_fraction(win_prob, odds)
            variance = win_prob * (payout_if_win ** 2) + (1 - win_prob) * (loss_if_lose ** 2) - ev ** 2
            std = math.sqrt(max(0, variance))
            ev_to_risk = ev / std if std > 0 else 0
            cr = ev / (101 - confidence) if confidence < 100 else ev

            best = {
                "side": side, "exec_price": cost, "mid_price": cost,
                "slippage": 0, "edge": edge, "cost": cost,
                "win_prob": win_prob, "payout_if_win": payout_if_win,
                "loss_if_lose": loss_if_lose, "total_shares": 0,
                "depth_available": 0, "levels_used": 0, "fills": [],
                "ev_per_bet": ev, "kelly_fraction": kf,
                "ev_to_risk": ev_to_risk, "confidence_ratio": cr,
            }
            has_orderbook = False

        recs.append({
            "ticker": ticker,
            "date": item["date"],
            "eps_estimate": item.get("eps_estimate"),
            "beat_rate": round(current_beat_rate * 100, 1),
            "recent_beat_rate": round(recent_beat_rate * 100, 1),
            "total_quarters": total_quarters,
            "beats": beats,
            "last_4_beats": sum(last_4),
            "confidence": confidence,
            "bt_trades": bt_trades,
            "bt_win_rate": round(bt_win_rate * 100) if bt_trades > 0 else None,
            "bt_pnl": bt_pnl,
            "has_orderbook": has_orderbook,
            **{k: v for k, v in best.items() if k != "fills"},  # exclude fills from JSON
        })

    # Sort by confidence_ratio
    recs.sort(key=lambda r: r["confidence_ratio"], reverse=True)

    # Save to JSON
    with open("output/recommendations.json", "w") as f:
        json.dump(recs, f, indent=2)

    # Print table
    print("\n" + "=" * 140)
    print(f"{'EARNINGS RECOMMENDATIONS (with Order Book Execution Prices)':^140}")
    print("=" * 140)
    print(f"{'Ticker':<7} {'Date':<12} {'Side':<5} {'Beat%':>6} {'Mid':>5} {'Exec':>5} {'Slip':>6} "
          f"{'Edge':>6} {'Win$':>7} {'Lose$':>7} {'EV/$':>7} {'Conf':>5} {'EV/Risk':>8} {'Kelly':>7} "
          f"{'Depth':>8} {'Rating':<6}")
    print("-" * 140)

    for r in recs:
        cr = r["confidence_ratio"]
        stars = "★" * min(5, max(1, int(cr / 1.5) + 1)) if cr > 0 else "★"
        stars = stars.ljust(5, '☆')

        mid_pct = f"{r.get('mid_price', 0)*100:.0f}%" if r.get('mid_price') else "N/A"
        exec_pct = f"{r['exec_price']*100:.0f}%" if r.get('exec_price') else "N/A"
        slip = f"{r.get('slippage', 0)*100:.1f}%" if r.get('has_orderbook') else "-"
        depth = f"${r.get('depth_available', 0):,.0f}" if r.get('has_orderbook') else "-"

        print(f"{r['ticker']:<7} {r['date']:<12} {r['side']:<5} {r['beat_rate']:>5.1f}% "
              f"{mid_pct:>5} {exec_pct:>5} {slip:>6} "
              f"{r['edge']*100:>5.1f}% "
              f"${r['payout_if_win']:>5.0f} ${r['loss_if_lose']:>5.0f} "
              f"${r['ev_per_bet']:>5.1f} "
              f"{r['confidence']:>4}% {r['ev_to_risk']:>7.2f} "
              f"{r['kelly_fraction']*100:>5.1f}% "
              f"{depth:>8} {stars}")

    print("-" * 140)

    # Summary
    total_ev = sum(r["ev_per_bet"] for r in recs)
    avg_conf = sum(r["confidence"] for r in recs) / len(recs) if recs else 0
    with_ob = sum(1 for r in recs if r.get("has_orderbook"))
    print(f"\n{'Total recommendations:':<30} {len(recs)} ({with_ob} with live order book)")
    print(f"{'Combined EV (all bets):':<30} ${total_ev:.1f}")
    print(f"{'Average confidence:':<30} {avg_conf:.0f}%")

    print("\n" + "=" * 140)
    print("KEY METRICS:")
    print(f"  Mid       = Mid-market price (Gamma API)")
    print(f"  Exec      = Actual execution price from order book (what you'd really pay)")
    print(f"  Slip      = Slippage: how much worse than best price")
    print(f"  Edge      = Beat rate minus execution price")
    print(f"  Win$      = Profit if correct (shares - cost)")
    print(f"  Lose$     = Loss if wrong (total cost)")
    print(f"  EV/$      = Expected value accounting for real execution cost")
    print(f"  Depth     = Total liquidity available in order book")
    print("=" * 140)

    return recs


if __name__ == "__main__":
    recs = generate_recommendations(bet_size=100)
