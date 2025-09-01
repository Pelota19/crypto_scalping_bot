from math import floor

def round_step(value: float, decimals: int) -> float:
    factor = 10 ** decimals
    return floor(value * factor) / factor

def compute_futures_order_qty_usdt(max_notional_usdt: float, price: float, leverage: int, amount_decimals: int) -> float:
    if price <= 0 or leverage <= 0:
        return 0.0
    # notional = qty * price; qty = (max_notional_usdt * leverage) / price
    qty = (max_notional_usdt * leverage) / price
    return round_step(qty, amount_decimals)