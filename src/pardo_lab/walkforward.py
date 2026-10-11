"""Walk-forward analysis (Pardo Ch.11) + 2026 extensions.

- Rolling WFA: IS window optimised by PROM, best params locked, tested on next OOS window.
  IS=4y/OOS=1y default for 10y daily (6 walks). Anchored option available.
- WF Matrix (Pardo Masterclass 2026): run several IS/OOS combos to test 'positive by chance'.
- Double-OOS discipline (Mroziewicz et al. 2026): final locked params run ONCE on held-out tail.
- WF efficiency = sum(OOS net)/sum(IS net). Robust iff OOS summary positive AND efficient.
- Purge gap (AlgoXpert 2026): 5-day embargo between IS end and OOS start to cut leakage.
"""
from __future__ import annotations
import pandas as pd
from .optimization import grid_search
from .backtest_engine import backtest
from .metrics import summarize

def _years(df: pd.DataFrame) -> sorted:
    return sorted(set(df.index.year))

def walk_forward(df: pd.DataFrame, grid: dict, is_years=4, oos_years=1,
                 anchored=False, purge_days=5, selector="prom_ann",
                 equity0=100_000.0, **bt_kw) -> dict:
    yrs = _years(df)
    walks = []
    oos_equity_parts, oos_trades = [], []
    for i in range(len(yrs)):
        is_end_y = yrs[i] + is_years - 1
        oos_end_y = is_end_y + oos_years
        is_start_y = yrs[0] if anchored else yrs[i]
        if oos_end_y > yrs[-1]:
            break
        is_df = df[(df.index.year >= is_start_y) & (df.index.year <= is_end_y)]
        oos_df = df[(df.index.year > is_end_y) & (df.index.year <= oos_end_y)]
        if len(is_df) < 500 or len(oos_df) < 120:
            continue
        prof = grid_search(is_df, grid, selector=selector, equity0=equity0, **bt_kw)
        best = {k: prof.iloc[0][k] for k in grid.keys()}
        is_stats = {k: float(prof.iloc[0][k]) for k in
                    ["net", "prom_ann", "sharpe", "maxdd_pct", "n"] if k in prof.columns}
        if purge_days:
            oos_df = oos_df.iloc[min(purge_days, len(oos_df) - 1):]
        bt = backtest(oos_df, best, equity0=equity0, **bt_kw)
        st = summarize(bt)
        walks.append({"is": f"{is_start_y}-{is_end_y}", "oos": f"{is_end_y+1}-{oos_end_y}",
                      "params": best, "is_stats": is_stats, "oos_stats": st})
        oos_equity_parts.append(bt["equity"])
        if len(bt["trades"]):
            t = bt["trades"].copy()
            t["walk"] = f"{is_end_y+1}-{oos_end_y}"
            oos_trades.append(t)
    is_net = sum(w["is_stats"].get("net", 0) for w in walks)
    oos_net = sum(w["oos_stats"].get("net", 0) for w in walks)
    wfe = float(oos_net / (is_net + 1e-9))
    oos_n = sum(w["oos_stats"].get("n", 0) for w in walks)
    pos_walks = sum(1 for w in walks if w["oos_stats"].get("net", 0) > 0)
    all_oos = pd.concat(oos_trades) if oos_trades else pd.DataFrame()
    return {"walks": walks, "n_walks": len(walks), "is_net": round(is_net, 2),
            "oos_net": round(oos_net, 2), "wf_efficiency": round(wfe, 3),
            "oos_trades": int(oos_n), "pos_walks": pos_walks,
            "robust": bool(oos_net > 0 and oos_n >= 30 and pos_walks >= len(walks) / 2),
            "all_oos_trades": all_oos}

def wf_matrix(df: pd.DataFrame, grid: dict, combos=((4, 1), (3, 1), (5, 1), (2, 1)), **kw) -> pd.DataFrame:
    rows = []
    for is_y, oos_y in combos:
        r = walk_forward(df, grid, is_years=is_y, oos_years=oos_y, **kw)
        rows.append({"IS": is_y, "OOS": oos_y, "walks": r["n_walks"],
                     "oos_net": r["oos_net"], "wf_eff": r["wf_efficiency"],
                     "oos_trades": r["oos_trades"], "pos_walks": r["pos_walks"],
                     "robust": r["robust"]})
    return pd.DataFrame(rows)
