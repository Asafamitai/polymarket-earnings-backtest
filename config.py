"""Configuration for Polymarket Earnings Call Backtest."""

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

# ~50 S&P 500 tickers across sectors
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
]

# Backtest parameters
MIN_HISTORY_QUARTERS = 8   # Minimum quarters of history before trading
BET_SIZE = 100             # Fixed bet size per trade ($)
EDGE_THRESHOLD = 0.03      # Minimum edge to take a trade (3%)
BEAT_INCLUDES_MEET = False  # True: actual >= estimate, False: actual > estimate
MARKET_AVG_BEAT_RATE = 0.75  # S&P 500 average beat rate for market_average model

# Cache settings
CACHE_DIR = "data/cache"
CACHE_TTL_HOURS = 24
