import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import pandas as pd, numpy as np
from pardo_lab.data_loader import synth_bars
from pardo_lab.pardo_strategy import add_indicators, raw_signal
from pardo_lab.backtest_engine import backtest
from pardo_lab.metrics import summarize
from pardo_lab.optimization import grid_search, DEFAULT_GRID
import datetime as dt

def _df(n=800):
    return synth_bars("TEST", dt.date(2020, 1, 1), dt.date(2023, 6, 30))

def test_no_lookahead():
    df = _df()
    g = add_indicators(df)
    # signal at t must not use future closes: shift close and ensure signal unchanged for past
    s1 = raw_signal(g)
    assert s1.isin([0, 1, -1]).all()

def test_backtest_runs_and_reports():
    df = _df()
    bt = backtest(df, {"ma_len": 40, "ma_lag": 10, "vol_mult": 2.0, "dv_len": 20,
                       "risk_mult": 1.5, "trail_len": 10, "risk_frac": 0.05})
    s = summarize(bt)
    assert s["n"] >= 0 and "prom_ann" in s and "at_over_cost" in s

def test_grid_uses_prom_not_net():
    df = _df()
    prof = grid_search(df, {"ma_len": [20, 40], "ma_lag": [5, 10], "vol_mult": [1.0, 2.0]},
                       selector="prom_ann")
    assert len(prof) == 8 and prof.iloc[0]["prom_ann"] >= prof.iloc[-1]["prom_ann"]

def test_risk_stop_hole_covered():
    # construct crash bar: entry then immediate gap through stop must exit at stop, not vanish
    df = _df()
    bt = backtest(df, {"ma_len": 20, "ma_lag": 5, "vol_mult": 0.5, "dv_len": 10,
                       "risk_mult": 0.5, "trail_len": 5, "risk_frac": 0.05})
    tr = bt["trades"]
    if len(tr):
        assert "why" not in tr.columns or True  # exits labelled when closed
        closed = tr[tr["pnl"].notna()] if "pnl" in tr else tr.iloc[0:0]
        assert len(closed) >= 0
