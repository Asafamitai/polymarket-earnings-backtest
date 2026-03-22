"""Refresh all data: Polymarket prices, calendar, backtest, recommendations."""
import warnings
warnings.filterwarnings("ignore")

print("=" * 60)
print("REFRESHING ALL DATA")
print("=" * 60)

# 1. Cache Polymarket data
print("\n[1/4] Fetching Polymarket data...")
from data.polymarket import cache_all, load_cached
poly_data = cache_all()

# Update config with live prices
live_prices = {m["ticker"]: m["yes_price"] for m in poly_data["active"] if m["yes_price"] is not None}
import config
config.POLYMARKET_PRICES = live_prices
print(f"  Updated {len(live_prices)} live prices in config")

# 2. Generate calendar
print("\n[2/4] Generating calendar...")
from generate_calendar import generate as gen_calendar
gen_calendar()

# 3. Generate backtest UI data (uses updated config)
print("\n[3/4] Generating backtest data...")
from generate_ui_data import generate as gen_ui
gen_ui()

# 4. Generate recommendations
print("\n[4/4] Generating recommendations...")
from recommendations import generate_recommendations
generate_recommendations()

print("\n" + "=" * 60)
print("ALL DATA REFRESHED")
print("=" * 60)
