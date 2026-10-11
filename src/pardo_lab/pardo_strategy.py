"""Faithful encoding of the slide-deck strategy (Pardo Steps 1-2).

Theory: 'the trend is my friend' -> trade in direction of dominant trend.
Mechanism:
  MA(n)  = simple moving average of Close, length ma_len
  DV     = daily volatility = SMA of True Range over dv_len (default 20)
  3DV    = 3 * DV  (slide: 'Set non-volatile risk stop at 1.5 x 3DV')
Signal (evaluated at close t, traded at next open t+1 — no look-ahead):
  LONG  if MA(t) > MA(t - ma_lag) + vol_mult * DV(t)
  SHORT if MA(t) < MA(t - ma_lag) - vol_mult * DV(t)
  else FLAT/exit-on-opposite-signal.
Slides default: ma_lag=10, vol_mult=2.0.

Exits: opposite signal | hard risk stop (entry +/- risk_mult * 3DV, risk_mult default 1.5)
       | shorter-MA trailing stop (optional, trail_len < ma_len).
Position sizing: contracts/shares = floor((equity * risk_frac) / stop_distance),
  risk_frac default 0.05 ('5% of account equity'), floored at 1, capped by equity
  (no leverage). Fully invested equity curve is computed on next-open execution.

All formulae are pure functions of past bars only; unit-tested for look-ahead freedom.
"""
from __future__ import annotations
import pandas as pd
import numpy as np

DEFAULTS = dict(ma_len=40, ma_lag=10, vol_mult=2.0, dv_len=20,
                risk_mult=1.5, trail_len=10, risk_frac=0.05)

def true_range(df: pd.DataFrame) -> pd.Series:
    pc = df["Close"].shift(1)
    return pd.concat([df["High"] - df["Low"], (df["High"] - pc).abs(),
                      (df["Low"] - pc).abs()], axis=1).max(axis=1)

def add_indicators(df: pd.DataFrame, ma_len=40, dv_len=20, trail_len=10) -> pd.DataFrame:
    ma_len, dv_len, trail_len = int(ma_len), int(dv_len), int(trail_len)
    out = df.copy()
    out["MA"] = out["Close"].rolling(ma_len).mean()
    out["DV"] = true_range(out).rolling(dv_len).mean()
    out["3DV"] = 3.0 * out["DV"]
    out["TRAIL_MA"] = out["Close"].rolling(trail_len).mean()
    return out

def raw_signal(df: pd.DataFrame, ma_lag=10, vol_mult=2.0) -> pd.Series:
    """+1 long, -1 short, 0 flat. Uses only closed bars."""
    ma_past = df["MA"].shift(ma_lag)
    thresh = vol_mult * df["DV"]
    sig = pd.Series(0, index=df.index)
    long_cond = (df["MA"] > ma_past + thresh)
    short_cond = (df["MA"] < ma_past - thresh)
    sig[long_cond] = 1
    sig[short_cond] = -1
    return sig.fillna(0).astype(int)
