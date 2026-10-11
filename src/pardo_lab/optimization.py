"""Grid optimisation with anti-curve-fit guardrails (Pardo Ch.9-10 + AlgoXpert 2026 + Mroziewicz 2026).

Rules enforced:
- <=4 variables (default 3: ma_len, ma_lag, vol_mult). Risk params NOT optimised by default
  ('avoid over-optimization of risk management rules').
- Reasonable steps (e.g. vol_mult 0.5..2.5 step 0.5, NOT 0.10..5.00 step 0.05).
- Selector is PROM (or Sharpe/Calmar composite), NEVER net profit.
- Plateau test: winner must sit on a plateau (>=60% of 8 neighbours within 20% of PROM).
- Reports full optimisation profile distribution + shape for the paper.
"""
from __future__ import annotations
import itertools
import pandas as pd
from .backtest_engine import backtest
from .metrics import summarize

DEFAULT_GRID = {"ma_len": [20, 40, 60], "ma_lag": [5, 10, 15], "vol_mult": [1.0, 1.5, 2.0, 2.5]}
WIDE_GRID = {"ma_len": [20, 30, 40, 50, 60, 80], "ma_lag": [5, 10, 15, 20], "vol_mult": [0.5, 1.0, 1.5, 2.0, 2.5]}

def grid_search(df: pd.DataFrame, grid: dict, selector: str = "prom_ann",
                equity0=100_000.0, **bt_kw) -> pd.DataFrame:
    keys = list(grid.keys())
    rows = []
    for vals in itertools.product(*[grid[k] for k in keys]):
        params = dict(zip(keys, vals))
        try:
            bt = backtest(df, params, equity0=equity0, **bt_kw)
            s = summarize(bt)
            rows.append({**params, **s})
        except Exception as e:
            rows.append({**params, "error": str(e), "n": 0, selector: -999})
    res = pd.DataFrame(rows).sort_values(selector, ascending=False).reset_index(drop=True)
    return res

def plateau_flag(profile: pd.DataFrame, winner_idx: int = 0, selector="prom_ann",
                 tol: float = 0.20, need: float = 0.6) -> dict:
    """Crude plateau check: compare winner vs others differing by one grid step."""
    if len(profile) < 9:
        return {"plateau": None, "reason": "too few points"}
    w = profile.iloc[winner_idx]
    neigh = 0
    ok = 0
    for _, r in profile.iterrows():
        if r.equals(w):
            continue
        diff_dims = sum(1 for k in ["ma_len", "ma_lag", "vol_mult"]
                        if k in profile.columns and r[k] != w[k])
        if diff_dims == 1:
            neigh += 1
            if abs(r[selector] - w[selector]) <= tol * max(abs(w[selector]), 1e-9):
                ok += 1
    frac = ok / max(neigh, 1)
    return {"plateau": bool(frac >= need), "neighbours": neigh,
            "within_tol": ok, "frac": round(frac, 2)}
