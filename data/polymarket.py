"""Fetch earnings market data from Polymarket via Dome API + CLOB."""
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Optional, List, Dict

import requests

import config

logger = logging.getLogger(__name__)

GAMMA_URL = "https://gamma-api.polymarket.com/events"
CLOB_URL = "https://clob.polymarket.com"
DOME_URL = "https://api.domeapi.io/v1"
DOME_API_KEY = os.environ.get("DOME_API_KEY", "")

# Rate limit constants
CLOB_RATE_LIMIT = 0.15   # seconds between CLOB calls
GAMMA_RATE_LIMIT = 0.3   # seconds between Gamma pagination

CACHE_FILE = Path(config.CACHE_DIR) / "polymarket_earnings.json"


def _validate_dome_key() -> bool:
    """Check if Dome API key is configured."""
    if not DOME_API_KEY:
        logger.warning("DOME_API_KEY not set. Falling back to Gamma API.")
        return False
    return True


def _extract_ticker(title: str) -> Optional[str]:
    """Extract ticker from title like 'Will GameStop (GME) beat quarterly earnings?'"""
    match = re.search(r'\((\w+)\)', title)
    return match.group(1) if match else None


def _extract_eps_from_slug(slug: str) -> Optional[float]:
    """Extract EPS threshold from slug like 'gme-quarterly-earnings-nongaap-eps-03-24-2026-0pt37'"""
    match = re.search(r'(\d+)pt(\d+)$', slug)
    if match:
        value = float(f"{match.group(1)}.{match.group(2)}")
        # Validate: EPS should be in a reasonable range
        if -500.0 <= value <= 500.0:
            return value
        logger.warning(f"EPS value {value} from slug '{slug}' out of range, ignoring")
        return None
    return None


def _extract_eps_type_from_slug(slug: str) -> str:
    """Extract GAAP/non-GAAP from slug."""
    if 'nongaap' in slug:
        return 'non-gaap'
    elif 'gaap' in slug:
        return 'gaap'
    return 'unknown'


def _extract_date_from_slug(slug: str) -> Optional[str]:
    """Extract earnings date from slug like '...-03-24-2026-0pt37'"""
    match = re.search(r'(\d{2})-(\d{2})-(\d{4})', slug)
    if match:
        return f"{match.group(3)}-{match.group(1)}-{match.group(2)}"
    return None


def _fetch_with_retry(url: str, params: dict = None, headers: dict = None,
                      max_retries: int = 3, timeout: int = 10) -> Optional[dict]:
    """Fetch URL with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            if resp.status_code < 500:
                logger.warning(f"HTTP {resp.status_code} for {url}: {e}")
                return None  # don't retry client errors
            logger.warning(f"HTTP {resp.status_code} for {url}, retry {attempt+1}/{max_retries}")
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            logger.warning(f"Network error for {url}, retry {attempt+1}/{max_retries}: {e}")
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Invalid JSON from {url}: {e}")
            return None
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)
    logger.error(f"All {max_retries} retries failed for {url}")
    return None


# In-memory price cache: {token_id: (price, timestamp)}
_price_cache: Dict[str, tuple] = {}
PRICE_CACHE_TTL = 60  # seconds


def _get_clob_price(token_id: str) -> Optional[float]:
    """Get live price from Polymarket CLOB API with caching."""
    # Check cache
    if token_id in _price_cache:
        price, ts = _price_cache[token_id]
        if time.time() - ts < PRICE_CACHE_TTL:
            return price

    data = _fetch_with_retry(f"{CLOB_URL}/price", params={
        "token_id": token_id, "side": "buy"
    })
    if data and "price" in data:
        try:
            price = float(data["price"])
            _price_cache[token_id] = (price, time.time())
            return price
        except (ValueError, TypeError):
            return None
    return None


def _batch_clob_prices(token_ids: List[str]) -> Dict[str, Optional[float]]:
    """Fetch prices for multiple tokens, using cache where possible."""
    results = {}
    to_fetch = []

    for tid in token_ids:
        if tid in _price_cache:
            price, ts = _price_cache[tid]
            if time.time() - ts < PRICE_CACHE_TTL:
                results[tid] = price
                continue
        to_fetch.append(tid)

    # Fetch uncached prices
    for tid in to_fetch:
        results[tid] = _get_clob_price(tid)
        time.sleep(CLOB_RATE_LIMIT)

    return results


def _parse_dome_market(market: dict, prefetched_prices: Dict[str, float] = None) -> Optional[dict]:
    """Parse a Dome API market into our format."""
    title = market.get("title", "")
    ticker = _extract_ticker(title)
    if not ticker:
        return None

    slug = market.get("market_slug", "")
    eps_threshold = _extract_eps_from_slug(slug)
    eps_type = _extract_eps_type_from_slug(slug)
    earn_date = _extract_date_from_slug(slug)

    yes_token = market.get("side_a", {}).get("id")
    no_token = market.get("side_b", {}).get("id")

    # Get live price: prefer prefetched, fallback to individual fetch
    if prefetched_prices and yes_token in prefetched_prices:
        yes_price = prefetched_prices[yes_token]
    else:
        yes_price = _get_clob_price(yes_token) if yes_token else None

    return {
        "ticker": ticker,
        "question": title,
        "yes_price": yes_price,
        "eps_threshold": eps_threshold,
        "eps_type": eps_type,
        "earn_date": earn_date,
        "end_date": earn_date,
        "volume": market.get("volume_total", 0),
        "slug": slug,
        "yes_token_id": yes_token,
        "no_token_id": no_token,
        "closed": market.get("winning_side") is not None,
        "resolved": market.get("winning_side") is not None,
    }


def _parse_gamma_market(market: dict) -> Optional[dict]:
    """Parse a Gamma API market (used for closed/historical markets)."""
    question = market.get("question", "")
    ticker = _extract_ticker(question)
    if not ticker:
        return None

    try:
        prices = json.loads(market.get("outcomePrices", "[]"))
        yes_price = float(prices[0]) if prices else None
    except (json.JSONDecodeError, IndexError, ValueError):
        yes_price = None

    try:
        token_ids = json.loads(market.get("clobTokenIds", "[]"))
    except (json.JSONDecodeError, ValueError):
        token_ids = []

    # Extract EPS threshold from description
    desc = market.get("description", "")
    eps_threshold = None
    eps_type = "unknown"

    eps_match = re.search(r'(non-GAAP|GAAP) EPS (?:greater than|of|for the relevant quarter is) \$?([-\d.]+)', desc)
    if eps_match:
        eps_type = eps_match.group(1).lower()
        eps_threshold = float(eps_match.group(2))

    return {
        "ticker": ticker,
        "question": question,
        "yes_price": yes_price,
        "eps_threshold": eps_threshold,
        "eps_type": eps_type,
        "end_date": (market.get("endDate") or "")[:10],
        "volume": float(market.get("volume", 0) or 0),
        "liquidity": float(market.get("liquidity", 0) or 0),
        "best_bid": float(market.get("bestBid", 0) or 0),
        "best_ask": float(market.get("bestAsk", 0) or 0),
        "spread": float(market.get("spread", 0) or 0),
        "slug": market.get("slug", ""),
        "yes_token_id": token_ids[0] if len(token_ids) > 0 else None,
        "no_token_id": token_ids[1] if len(token_ids) > 1 else None,
        "closed": market.get("closed", False),
        "resolved": market.get("resolved", False),
    }


def fetch_active_earnings() -> List[dict]:
    """Fetch all active (open) earnings markets via Dome API + CLOB prices."""
    if not _validate_dome_key():
        return _fetch_active_earnings_gamma()

    data = _fetch_with_retry(
        f"{DOME_URL}/polymarket/markets",
        headers={"x-api-key": DOME_API_KEY},
        params={"limit": 100, "search": "earnings", "status": "open"},
        timeout=15,
    )
    if not data or "markets" not in data:
        logger.warning("Dome API returned no data, falling back to Gamma API")
        return _fetch_active_earnings_gamma()

    # Batch-fetch all CLOB prices at once (instead of one-by-one in parse)
    dome_markets = data["markets"]
    token_ids = [m.get("side_a", {}).get("id") for m in dome_markets if m.get("side_a", {}).get("id")]
    logger.info(f"Batch-fetching {len(token_ids)} CLOB prices...")
    prefetched = _batch_clob_prices(token_ids)

    markets = []
    for m in dome_markets:
        parsed = _parse_dome_market(m, prefetched_prices=prefetched)
        if parsed:
            markets.append(parsed)

    return markets


def _fetch_active_earnings_gamma() -> List[dict]:
    """Fallback: fetch from Gamma API."""
    data = _fetch_with_retry(GAMMA_URL, params={
        "active": "true",
        "closed": "false",
        "tag_id": "1013",
        "limit": 100,
    }, timeout=15)
    if not data:
        logger.error("Gamma API also failed. Returning empty list.")
        return []

    events = data if isinstance(data, list) else [data]
    markets = []
    for event in events:
        for m in event.get("markets", []):
            parsed = _parse_gamma_market(m)
            if parsed:
                markets.append(parsed)
    return markets


def fetch_closed_earnings(limit: int = 500) -> List[dict]:
    """Fetch closed/resolved earnings markets for backtesting."""
    all_markets = []
    page = 0
    per_page = 100

    while len(all_markets) < limit:
        data = _fetch_with_retry(GAMMA_URL, params={
            "closed": "true",
            "tag_id": "1013",
            "limit": per_page,
            "offset": page * per_page,
        }, timeout=15)
        if not data:
            break

        events = data if isinstance(data, list) else [data]
        if not events:
            break

        for event in events:
            for m in event.get("markets", []):
                parsed = _parse_gamma_market(m)
                if parsed:
                    parsed["actual_beat"] = parsed["yes_price"] is not None and parsed["yes_price"] > 0.5
                    all_markets.append(parsed)

        page += 1
        if len(events) < per_page:
            break
        time.sleep(GAMMA_RATE_LIMIT)

    return all_markets[:limit]


def fetch_order_book(token_id: str) -> Optional[Dict]:
    """Fetch order book for a token from the CLOB API."""
    data = _fetch_with_retry(f"{CLOB_URL}/book", params={"token_id": token_id})
    return data if data else {"asks": [], "bids": []}


def calc_execution_price(order_book: Dict, side: str, amount_usd: float) -> Dict:
    """Calculate actual execution price given order book depth and bet size."""
    if side == "buy":
        levels = sorted(order_book.get("asks", []), key=lambda x: float(x["price"]))
    else:
        levels = sorted(order_book.get("bids", []), key=lambda x: float(x["price"]), reverse=True)

    if not levels:
        return {"avg_price": None, "total_shares": 0, "total_cost": 0,
                "slippage": 0, "levels_used": 0, "depth_available": 0, "fills": []}

    best_price = float(levels[0]["price"])
    remaining = amount_usd
    total_shares = 0
    total_cost = 0
    fills = []

    for level in levels:
        price = float(level["price"])
        size = float(level["size"])
        level_cost = price * size

        if remaining <= 0:
            break

        if level_cost <= remaining:
            total_shares += size
            total_cost += level_cost
            remaining -= level_cost
            fills.append({"price": price, "shares": size, "cost": round(level_cost, 2)})
        else:
            shares = remaining / price
            total_shares += shares
            total_cost += remaining
            fills.append({"price": price, "shares": round(shares, 2), "cost": round(remaining, 2)})
            remaining = 0

    avg_price = total_cost / total_shares if total_shares > 0 else None
    slippage = (avg_price - best_price) / best_price if avg_price and best_price else 0
    depth = sum(float(l["price"]) * float(l["size"]) for l in levels)

    return {
        "avg_price": round(avg_price, 4) if avg_price else None,
        "best_price": best_price,
        "total_shares": round(total_shares, 2),
        "total_cost": round(total_cost, 2),
        "slippage": round(slippage, 4),
        "levels_used": len(fills),
        "depth_available": round(depth, 2),
        "payout_if_win": round(total_shares, 2),
        "profit_if_win": round(total_shares - total_cost, 2),
        "fills": fills,
    }


def get_execution_prices(markets: List[dict], bet_size: float = 100) -> Dict[str, Dict]:
    """For each active market, get actual execution prices for YES and NO."""
    results = {}

    for m in markets:
        ticker = m["ticker"]
        yes_token = m.get("yes_token_id")
        no_token = m.get("no_token_id")
        if not yes_token or not no_token:
            continue

        try:
            yes_book = fetch_order_book(yes_token)
            no_book = fetch_order_book(no_token)
            time.sleep(0.2)

            yes_exec = calc_execution_price(yes_book, "buy", bet_size)
            no_exec = calc_execution_price(no_book, "buy", bet_size)

            results[ticker] = {
                "yes": yes_exec,
                "no": no_exec,
                "yes_mid": m["yes_price"],
                "spread": m.get("spread", 0),
                "volume": m.get("volume", 0),
                "liquidity": m.get("liquidity", 0),
            }
        except Exception as e:
            logger.warning(f"Skip {ticker} order book: {e}")
            continue

    return results


def get_active_prices() -> Dict[str, float]:
    """Return {ticker: yes_price} for all active earnings markets."""
    markets = fetch_active_earnings()
    return {m["ticker"]: m["yes_price"] for m in markets if m["yes_price"] is not None}


def cache_all():
    """Fetch and cache all earnings data (active + closed)."""
    import os
    os.makedirs(config.CACHE_DIR, exist_ok=True)

    logger.info("Fetching active earnings markets (Dome + CLOB)...")
    active = fetch_active_earnings()
    logger.info(f"Found {len(active)} active markets")

    logger.info("Fetching closed earnings markets (Gamma)...")
    closed = fetch_closed_earnings(limit=500)
    logger.info(f"Found {len(closed)} closed markets")

    data = {"active": active, "closed": closed, "timestamp": time.time()}
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, indent=2)
    logger.info(f"Cached to {CACHE_FILE}")

    return data


def load_cached() -> dict:
    """Load cached Polymarket data."""
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {"active": [], "closed": []}


if __name__ == "__main__":
    data = cache_all()

    print("\n=== Active Earnings Markets ===")
    for m in data["active"]:
        p = m['yes_price']
        eps = m.get('eps_threshold', '?')
        eps_t = m.get('eps_type', '?')
        print(f"  {m['ticker']:>6}: Yes={p*100:.0f}%  EPS=${eps} ({eps_t})  Date={m.get('earn_date','?')}")

    print(f"\n=== Closed Markets Summary ===")
    beats = sum(1 for m in data["closed"] if m.get("actual_beat"))
    total = len(data["closed"])
    print(f"  {beats}/{total} beat ({beats/total*100:.0f}%)")
