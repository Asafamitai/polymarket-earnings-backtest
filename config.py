"""Configuration for Polymarket Earnings Call Backtest."""
import logging
import os

logger = logging.getLogger(__name__)

# Observed Polymarket Yes prices from the earnings calendar (March 2026)
POLYMARKET_PRICES = {
    "GME": 0.90,
    "CTAS": 0.89,
    "PAYX": 0.75,
    "PDD": 0.73,
    "CHWY": 0.82,
    "DBI": 0.64,
    "NMAX": 0.63,
}

# ~60 tickers across sectors + Polymarket active
TICKERS = [
    # Polymarket observed
    "GME", "CTAS", "PAYX", "PDD", "CHWY", "DBI", "NMAX",
    # Tech
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "CRM", "ORCL", "INTC", "AMD", "QCOM", "AVGO",
    # Finance
    "JPM", "BAC", "WFC", "GS",
    # Healthcare
    "JNJ", "UNH", "PFE", "MRK", "LLY", "ABBV", "TMO",
    # Energy
    "XOM", "CVX",
    # Consumer
    "PG", "KO", "PEP", "COST", "WMT", "HD", "MCD", "NKE", "DIS", "NFLX",
    # Industrial
    "CAT", "BA", "GE", "UPS", "FDX",
    # Auto
    "GM", "F",
    # Utilities
    "NEE", "SO",
    # Polymarket active (additional)
    "PLAY", "BYND", "SPCE", "BIRD", "RH", "FDS", "MKC", "CAG", "LW", "MSM",
]

# Backtest parameters
MIN_HISTORY_QUARTERS = 6   # Minimum quarters of history before trading
BET_SIZE = 100             # Fixed bet size per trade ($)
EDGE_THRESHOLD = 0.03      # Minimum edge to take a trade (3%)
BEAT_INCLUDES_MEET = False  # True: actual >= estimate, False: actual > estimate
MARKET_AVG_BEAT_RATE = 0.75  # S&P 500 average beat rate for market_average model

# Cache settings
CACHE_DIR = "data/cache"
CACHE_TTL_HOURS = 24

# Output settings
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "output")


def validate_config():
    """Validate configuration at startup. Log warnings for issues."""
    issues = []

    if not os.environ.get("DOME_API_KEY"):
        issues.append("DOME_API_KEY not set — will use Gamma API fallback (slower, no CLOB prices)")

    if not 0.0 < EDGE_THRESHOLD < 1.0:
        issues.append(f"EDGE_THRESHOLD={EDGE_THRESHOLD} is outside (0, 1) range")

    if not 1 <= MIN_HISTORY_QUARTERS <= 30:
        issues.append(f"MIN_HISTORY_QUARTERS={MIN_HISTORY_QUARTERS} is outside [1, 30] range")

    if BET_SIZE <= 0:
        issues.append(f"BET_SIZE={BET_SIZE} must be positive")

    if not 0.0 < MARKET_AVG_BEAT_RATE < 1.0:
        issues.append(f"MARKET_AVG_BEAT_RATE={MARKET_AVG_BEAT_RATE} is outside (0, 1) range")

    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if issues:
        for issue in issues:
            logger.warning(f"[CONFIG] {issue}")
    else:
        logger.info(f"[CONFIG] OK — {len(TICKERS)} tickers, edge={EDGE_THRESHOLD}, min_q={MIN_HISTORY_QUARTERS}")

    return len(issues) == 0
