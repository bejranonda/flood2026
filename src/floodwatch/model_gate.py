"""When a model change makes a unit (a gauge, a dam) worse — beyond chance (owner 2026-10-06, D-107).

The owner's rule: count a unit as made worse only if its error rises by more than 3 % **and** a resampling test says the
rise is real, not chance; every unit's change is reported either way. The errors are paired (the new and the old method
on the same issue times). A forecast's errors come in spells — forecasts issued on neighbouring days share most of their
days — so the resampling keeps runs of `block` issues together (moving-block bootstrap; a block of at least the
horizon). The rise is "real" when its one-sided lower bound (`LEVEL`) is above zero.
"""
from __future__ import annotations

import numpy as np

MIN_RISE = 0.03  # owner 2026-10-06 (D-107): smaller rises do not count, however steady
LEVEL = 0.95     # one-sided confidence that the rise is above zero
N_BOOT = 2000


def _measure(abs_err: np.ndarray, metric: str) -> np.ndarray | float:
    """Mean (MAE) or root-mean-square (RMSE) of absolute errors along the last axis."""
    return np.sqrt((abs_err * abs_err).mean(-1)) if metric == "rmse" else abs_err.mean(-1)


def made_worse(new_err, old_err, block: int, metric: str = "mae", min_rise: float = MIN_RISE, level: float = LEVEL,
               n_boot: int = N_BOOT, seed: int = 0) -> dict:
    """{"rise", "low", "worse", "tested", "n"} for paired errors (any sign) of the new and the old method.

    rise = error_new / error_old − 1 (MAE or RMSE); low = the rise's one-sided lower bound from a moving-block bootstrap
    of `block` consecutive issues; worse = rise > min_rise and low > 0. Pairs with a missing value are dropped. Fewer
    than two blocks of pairs cannot be resampled: then the size alone decides (the cautious side, "tested" False)."""
    new, old = np.asarray(new_err, dtype=float), np.asarray(old_err, dtype=float)
    ok = np.isfinite(new) & np.isfinite(old)
    new, old = np.abs(new[ok]), np.abs(old[ok])
    n = len(new)
    if n == 0:
        return {"rise": None, "low": None, "worse": False, "tested": False, "n": 0}
    m_new, m_old = float(_measure(new, metric)), float(_measure(old, metric))
    if m_old == 0:
        rise = 0.0 if m_new == 0 else float("inf")
        return {"rise": rise, "low": None, "worse": rise > min_rise, "tested": False, "n": n}
    rise = m_new / m_old - 1
    block = max(1, int(block))
    if n < 2 * block:
        return {"rise": rise, "low": None, "worse": rise > min_rise, "tested": False, "n": n}
    rng = np.random.default_rng(seed)
    k = -(-n // block)
    starts = rng.integers(0, n - block + 1, size=(n_boot, k))
    idx = (starts[:, :, None] + np.arange(block)).reshape(n_boot, -1)[:, :n]
    num, den = _measure(new[idx], metric), _measure(old[idx], metric)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(den > 0, num / den, np.where(num > 0, np.inf, 1.0))
    low = float(np.quantile(ratio, 1 - level)) - 1
    return {"rise": rise, "low": low, "worse": bool(rise > min_rise and low > 0), "tested": True, "n": n}
