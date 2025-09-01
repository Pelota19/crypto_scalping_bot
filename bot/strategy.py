from typing import Literal, Optional, Sequence
import statistics

Signal = Optional[Literal["buy", "sell"]]

def sma(values: Sequence[float], period: int) -> float:
    if len(values) < period:
        raise ValueError("No hay suficientes datos para la SMA")
    return statistics.fmean(values[-period:])

class SMAScalpingStrategy:
    def __init__(self, fast: int, slow: int):
        if fast >= slow:
            raise ValueError("FAST_SMA debe ser menor que SLOW_SMA")
        self.fast = fast
        self.slow = slow
        self._last_fast = None
        self._last_slow = None

    def signal(self, closes: list[float]) -> Signal:
        if len(closes) < self.slow + 1:
            return None
        fast_now = sma(closes, self.fast)
        slow_now = sma(closes, self.slow)

        sig: Signal = None
        if self._last_fast is not None and self._last_slow is not None:
            crossed_up = self._last_fast <= self._last_slow and fast_now > slow_now
            crossed_down = self._last_fast >= self._last_slow and fast_now < slow_now
            if crossed_up:
                sig = "buy"
            elif crossed_down:
                sig = "sell"

        self._last_fast = fast_now
        self._last_slow = slow_now
        return sig
