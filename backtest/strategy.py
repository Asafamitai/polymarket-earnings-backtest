"""Strategy logic for deciding positions based on edge."""


def decide_position(beat_rate: float, poly_yes_price: float, edge_threshold: float = 0.05) -> dict:
    """Decide whether to buy Yes, No, or Skip based on edge.

    Returns dict with: side (YES/NO/SKIP), edge, cost
    """
    yes_edge = beat_rate - poly_yes_price
    no_edge = (1 - beat_rate) - (1 - poly_yes_price)  # same as poly_yes_price - beat_rate

    if yes_edge >= edge_threshold:
        return {"side": "YES", "edge": yes_edge, "cost": poly_yes_price}
    elif no_edge >= edge_threshold:
        return {"side": "NO", "edge": no_edge, "cost": 1 - poly_yes_price}
    else:
        return {"side": "SKIP", "edge": max(yes_edge, no_edge), "cost": 0.0}
