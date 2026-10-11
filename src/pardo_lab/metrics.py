"""Risk-adjusted metrics. Net profit is BANNED as a search function (Pardo: 'one of the very worst').

- PROM (Pessimistic Return on Margin, Pardo's 'best publicly available' measure):
    PROM = (NetProfit - LargestWin) / MaxMarginRequired, annualised.
  We use MaxMarginRequired = max notional deployed (shares*price). This penalises
  one-lucky-trade systems, exactly Pardo's intent.
- Sharpe (daily, ann=252), Calmar = annReturn/|MaxDD|, MAR, profit factor,
  avg trade (AT) + AT/(S&C) gate, win rate, long/short split.
- WF efficiency = sum(OOS net) / sum(IS net) (Pardo Ch.11).
- GT-Score-lite (Sheppert 2026 composite spirit): z-scored blend of Sharpe, Calmar,
  consistency (frac of profitable OOS windows), -drawdown. Used only as selector, reported raw.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

def max_drawdown(equity: pd.Series) -> tuple[float, float]:
    peak = equity.cummax()
    dd = (equity - peak) / peak
    return float(dd.min()), float((peak - equity).max())

def annualised_return(equity: pd.Series) -> float:
    if len(equity) < 2:
        return 0.0
    yrs = max((equity.index[-1] - equity.index[0]).days / 365.25, 1e-9)
    return float((equity.iloc[-1] / equity.iloc[0]) ** (1 / yrs) - 1)

def summarize(bt: dict) -> dict:
    tr = bt["trades"].copy()
    eq = bt["equity"]
    eq0 = bt["equity0"]
    if "pnl" not in tr.columns:
        tr["pnl"] = pd.Series(dtype=float)
    tr = tr[tr["pnl"].notna()] if len(tr) else tr
    net = float(eq.iloc[-1] - eq0) if len(eq) else 0.0
    mdd_pct, mdd_abs = max_drawdown(eq) if len(eq) else (0.0, 0.0)
    ann = annualised_return(eq) if len(eq) else 0.0
    rets = eq.pct_change().dropna()
    sharpe = float(rets.mean() / (rets.std() + 1e-12) * np.sqrt(252)) if len(rets) > 2 else 0.0
    calmar = float(ann / (abs(mdd_pct) + 1e-9)) if mdd_pct < 0 else 0.0
    n = len(tr)
    wins = tr[tr["pnl"] > 0] if n and "pnl" in tr else tr.iloc[0:0]
    nw = len(wins)
    gross_p = float(wins["pnl"].sum()) if nw else 0.0
    gross_l = float(tr[tr["pnl"] <= 0]["pnl"].sum()) if n else 0.0
    pf = float(gross_p / (abs(gross_l) + 1e-9)) if gross_l else (np.inf if gross_p > 0 else 0.0)
    avg_trade = float(tr["pnl"].mean()) if n and "pnl" in tr else 0.0
    largest_win = float(tr["pnl"].max()) if n and "pnl" in tr else 0.0
    # avg round-trip cost per TRADE (not per share): infer from diag + mean shares
    mean_sh = float(tr["shares"].mean()) if n and "shares" in tr else 0.0
    rt_per_trade = bt["diag"]["rt_cost_per_share"] * mean_sh
    at_over_cost = float(avg_trade / (rt_per_trade + 1e-9)) if rt_per_trade else np.inf
    # PROM
    max_margin = float((tr["shares"] * tr["entry_px"]).max()) if n and "shares" in tr else eq0
    prom_raw = (net - largest_win) / (max_margin + 1e-9)
    yrs = max((eq.index[-1] - eq.index[0]).days / 365.25, 1e-9) if len(eq) else 1.0
    prom_ann = float(((1 + prom_raw) ** (1 / yrs) - 1)) if prom_raw > -1 else float(prom_raw / yrs)
    longs = tr[tr["side"] == 1] if n and "side" in tr else tr.iloc[0:0]
    shorts = tr[tr["side"] == -1] if n and "side" in tr else tr.iloc[0:0]
    return {"net": round(net, 2), "ann_ret": round(ann, 4), "maxdd_pct": round(mdd_pct, 4),
            "sharpe": round(sharpe, 3), "calmar": round(calmar, 3),
            "n": n, "win_rate": round(nw / n, 3) if n else 0.0,
            "profit_factor": round(min(pf, 999), 3), "avg_trade": round(avg_trade, 2),
            "largest_win": round(largest_win, 2), "rt_per_trade": round(rt_per_trade, 2),
            "at_over_cost": round(min(at_over_cost, 999), 2),
            "prom_ann": round(prom_ann, 4), "max_margin": round(max_margin, 2),
            "long_n": len(longs), "short_n": len(shorts),
            "long_pnl": round(float(longs["pnl"].sum()) if len(longs) and "pnl" in longs else 0.0, 2),
            "short_pnl": round(float(shorts["pnl"].sum()) if len(shorts) and "pnl" in shorts else 0.0, 2)}
