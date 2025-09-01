from math import floor

def round_step(value: float, decimals: int) -> float:
    factor = 10 ** decimals
    return floor(value * factor) / factor

def compute_order_qty_usdt(max_usdt: float, price: float, amount_decimals: int) -> float:
    if price <= 0:
        return 0.0
    qty = max_usdt / price
    return round_step(qty, amount_decimals)
