"""Generate docs/assets charts from REAL results (no invented numbers)."""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(BASE, "results")
OUT = os.path.join(BASE, "docs", "assets")
os.makedirs(OUT, exist_ok=True)

rep = json.load(open(os.path.join(RES, "full_report.json")))
markets = list(rep["markets"].keys())

# 1. OOS net + WF efficiency bar chart (cross-market verdict)
fig, ax1 = plt.subplots(figsize=(9, 4.5))
oos = [rep["markets"][m]["wf"]["oos_net"] for m in markets]
wfe = [rep["markets"][m]["wf"]["wf_efficiency"] for m in markets]
cols = ["#16a34a" if v > 0 else "#dc2626" for v in oos]
ax1.bar(markets, oos, color=cols, alpha=0.85)
ax1.axhline(0, color="black", linewidth=0.8)
ax1.set_title("Walk-forward out-of-sample net profit per $100k (10y, IS4/OOS1, OOS-only)")
ax1.set_ylabel("OOS net ($)")
for i, v in enumerate(oos):
    ax1.text(i, v + (800 if v > 0 else -1800), f"${v:,.0f}", ha="center", fontsize=9)
ax2 = ax1.twinx()
ax2.plot(markets, wfe, color="#1d4ed8", marker="o", linewidth=2, label="WF efficiency")
ax2.set_ylabel("WF efficiency (OOS/IS)")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "wf_verdict.png"), dpi=150)
print("wrote wf_verdict.png")

# 2. Equity snapshots: rebuild full-sample equity for best params per market
from pardo_lab.data_loader import load_symbol
from pardo_lab.backtest_engine import backtest
import datetime as dt
fig, axes = plt.subplots(2, 3, figsize=(12, 6), sharex=False)
axes = axes.ravel()
start, end = dt.date(2016, 10, 10), dt.date(2026, 10, 9)
for ax, m in zip(axes, markets):
    df, _ = load_symbol(m, start, end, os.path.join(BASE, "data"))
    best = rep["markets"][m]["best_params"]
    bt = backtest(df, best)
    eq = bt["equity"]
    ax.plot(eq.index, eq.values, linewidth=1.2)
    ax.axhline(bt["equity0"], color="gray", linestyle="--", linewidth=0.8)
    ax.set_title(f"{m}  best={best}  net=${rep['markets'][m]['best_stats']['net']:,.0f}")
    ax.tick_params(labelsize=7)
axes[-1].axis("off")
fig.suptitle("Full-sample equity curves at PROM-optimal params (frictions included, $100k start)")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "equity_curves.png"), dpi=150)
print("wrote equity_curves.png")

# 3. WF matrix heat table for QQQ vs SPY
fig, axes = plt.subplots(1, 2, figsize=(10, 3.5))
for ax, m in zip(axes, ["spy.us", "qqq.us"]):
    mat = pd.read_csv(os.path.join(RES, f"wf_matrix_{m}.csv"))
    ax.bar([f"IS{r.IS}/OOS{r.OOS}" for r in mat.itertuples()], mat.oos_net,
           color=["#16a34a" if v > 0 else "#dc2626" for v in mat.oos_net])
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title(f"WF matrix: {m}")
    ax.tick_params(axis="x", labelsize=8)
fig.suptitle("Walk-forward matrix: verdicts are structural, not window-picked")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "wf_matrix.png"), dpi=150)
print("wrote wf_matrix.png")

# 4. Regime split grouped bars
import numpy as np
regs = ["uptrend", "downtrend", "range"]
x = np.arange(len(markets))
w = 0.22
fig, ax = plt.subplots(figsize=(10, 4.2))
for i, r in enumerate(regs):
    vals = [rep["markets"][m]["audit"]["regimes"]["regimes"][r]["net"] for m in markets]
    ax.bar(x + (i - 1) * w, vals, w, label=r)
ax.set_xticks(x)
ax.set_xticklabels(markets)
ax.axhline(0, color="black", linewidth=0.8)
ax.set_title("Regime split: same rule, wildly different legs (hidden pattern #3)")
ax.set_ylabel("Net ($)")
ax.legend()
fig.tight_layout()
fig.savefig(os.path.join(OUT, "regimes.png"), dpi=150)
print("wrote regimes.png")
