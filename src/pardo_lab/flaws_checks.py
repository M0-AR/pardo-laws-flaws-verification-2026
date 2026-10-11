"""Fatal-flaw audit gates. Every gate returns PASS/FAIL + evidence; the paper reports all.

G1 S&C caution: strategy must survive 2x costs with AT>=3x cost at 1x (Pardo: overstate!).
G2 AT robustness: avg trade >= 3x round-trip cost.
G3 Sample size: >=30 trades in every evaluation that matters (IS, OOS-aggregate, full).
G4 Selector hygiene: PROM-selected params must differ-check vs net-profit-selected (demonstrates
   why net profit is 'one of the very worst' — it picks fragile spikes).
G5 Balance: long/short contribution + up/down/range regime split must not be one-legged,
   unless strategy is declared single-market (then flagged as conditional).
G6 Plateau: winner sits on optimisation plateau (not a spike).
G7 Single-OOS-once: final lock evaluated once on held-out tail (Mroziewicz 2026) — re-touching
   the tail converts OOS into IS (Pardo/LinkedIn 2026 discussion).
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from .backtest_engine import backtest
from .metrics import summarize
from .optimization import grid_search

def cost_stress(df, params, equity0=100_000.0):
    outs = {}
    for mult, (c, s) in {"0x": (0.0, 0.0), "1x": (0.005, 0.0005), "2x": (0.01, 0.001)}.items():
        bt = backtest(df, params, equity0=equity0, commission_ps=c, slippage_pct=s)
        outs[mult] = summarize(bt)
    at1 = outs["1x"]["avg_trade"]
    rt1 = outs["1x"]["rt_per_trade"]
    return {"table": outs,
            "pass": bool(outs["1x"]["n"] >= 30 and at1 >= 3 * max(rt1, 1e-9) and outs["2x"]["net"] > 0),
            "detail": f"AT={at1} vs 3xRT={3*rt1:.2f}; 2x-costs net={outs['2x']['net']}"}

def regime_split(df, params, **kw):
    bt_all = backtest(df, params, **kw)
    px = df["Close"]
    mom = px.pct_change(60)
    vols = px.pct_change().rolling(60).std()
    out = {}
    for name, mask in {"uptrend": mom > 0.05, "downtrend": mom < -0.05,
                       "range": mom.abs() <= 0.05}.items():
        sub = df[mask.reindex(df.index).fillna(False)]
        if len(sub) < 120:
            out[name] = {"n": 0, "net": 0.0}
            continue
        try:
            out[name] = {"n": summarize(backtest(sub, params, **kw))["n"],
                         "net": summarize(backtest(sub, params, **kw))["net"]}
        except Exception:
            out[name] = {"n": 0, "net": 0.0}
    pos_legs = sum(1 for v in out.values() if v["net"] > 0)
    return {"regimes": out, "pass": bool(pos_legs >= 2),
            "detail": f"{pos_legs}/3 regimes positive"}

def selector_hygiene(df, grid, **kw):
    by_prom = grid_search(df, grid, selector="prom_ann", **kw).iloc[0]
    by_net = grid_search(df, grid, selector="net", **kw).iloc[0]
    same = all(by_prom[k] == by_net[k] for k in grid.keys())
    return {"prom_params": {k: by_prom[k] for k in grid.keys()},
            "net_params": {k: by_net[k] for k in grid.keys()},
            "prom_prom": float(by_prom["prom_ann"]), "net_prom": float(by_net["prom_ann"]),
            "same": bool(same),
            "pass": True,  # informative gate: documents divergence
            "detail": "SAME" if same else
                      f"net-profit picks spike with PROM {by_net['prom_ann']} vs PROM-opt {by_prom['prom_ann']}"}
