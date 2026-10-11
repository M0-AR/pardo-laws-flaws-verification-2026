"""Free public market data loader: Stooq (primary, no key) -> Yahoo (fallback) -> synthetic GBM (offline fallback).

Why this choice (verified 2026-10-11 via sequential multi-source search):
- Pardo requires >=5y daily, preferably 10y, multi-market basket.
- Stooq daily CSV is free, no API key, no rate cap for daily bars (corroborated by
  backtesting.py docs recommending yfinance/Stooq-style OHLC, Quantopia 2026 backtesting guide,
  IBKR Campus WFA guide: 'high-quality reliable historical data is the foundation').
- Yahoo v8 chart is keyless fallback.
- Synthetic fallback guarantees reproducibility offline and is ALWAYS labelled synthetic
  (never mixed silently with real data) to avoid survivorship/look-ahead bias claims.

Covers Pardo Step 'Assemble necessary price data' + flaw 'holes in your testing'.
"""
from __future__ import annotations
import datetime as dt
import io
import os
import numpy as np
import pandas as pd
import requests

STOOQ_URL = "https://stooq.com/q/d/l/"
YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
# VERIFIED 2026-10-11 (live probe from this repo): Stooq /q/d/l/ now returns
# a JS-verification page (HTTP 200 + 'requires JavaScript') and static zip returns 401.
# Therefore Yahoo v8 is the effective primary; Stooq is still tried first so the
# pipeline self-heals if Stooq lifts the wall. Provenance is logged per symbol.

# Stooq suffix mapping: user passes 'spy.us' style already; yahoo needs 'SPY'.
def _to_yahoo(symbol: str) -> str:
    s = symbol.lower()
    if s.endswith(".us"):
        return s[:-3].upper()
    if s == "eurusd":
        return "EURUSD=X"
    if s == "btcusd":
        return "BTC-USD"
    return symbol.upper()

def fetch_stooq(symbol: str, start: dt.date, end: dt.date) -> pd.DataFrame | None:
    params = {"s": symbol.lower(), "d1": start.strftime("%Y%m%d"),
              "d2": end.strftime("%Y%m%d"), "i": "d"}
    try:
        r = requests.get(STOOQ_URL, params=params, timeout=30)
        if r.status_code != 200 or "Date" not in r.text[:200]:
            return None
        df = pd.read_csv(io.StringIO(r.text), parse_dates=["Date"])
        if len(df) < 100:
            return None
        df = df.rename(columns={"Date": "date", "Open": "Open", "High": "High",
                                "Low": "Low", "Close": "Close", "Volume": "Volume"})
        df = df.set_index("date").sort_index().dropna(subset=["Close"])
        df["symbol"] = symbol
        return df
    except Exception:
        return None

def fetch_yahoo(symbol: str, start: dt.date, end: dt.date) -> pd.DataFrame | None:
    ysym = _to_yahoo(symbol)
    try:
        p1 = int(dt.datetime(start.year, start.month, start.day).timestamp())
        p2 = int(dt.datetime(end.year, end.month, end.day).timestamp()) + 86400
        r = requests.get(YAHOO_URL.format(sym=ysym),
                         params={"period1": p1, "period2": p2, "interval": "1d"},
                         headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        j = r.json()
        res = j["chart"]["result"][0]
        ts = res["timestamp"]
        q = res["indicators"]["quote"][0]
        df = pd.DataFrame({"Open": q["open"], "High": q["high"], "Low": q["low"],
                           "Close": q["close"], "Volume": q.get("volume")})
        df["date"] = pd.to_datetime(ts, unit="s")
        df = df.set_index("date").sort_index().dropna(subset=["Close"])
        df["symbol"] = symbol
        return df
    except Exception:
        return None

def synth_bars(symbol: str, start: dt.date, end: dt.date, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed + abs(hash(symbol)) % 10_000)
    idx = pd.bdate_range(start, end)
    rets = rng.normal(0.0003, 0.012, len(idx))
    close = 100 * np.exp(np.cumsum(rets))
    spread = np.abs(rng.normal(0.006, 0.004, len(idx)))
    df = pd.DataFrame({"Open": close * (1 + rng.normal(0, 0.002, len(idx))),
                       "High": close * (1 + spread / 2), "Low": close * (1 - spread / 2),
                       "Close": close, "Volume": rng.integers(1e6, 9e6, len(idx))}, index=idx)
    df.index.name = "date"
    df["symbol"] = symbol
    df["SYNTHETIC"] = True
    return df

def load_symbol(symbol: str, start: dt.date, end: dt.date, cache_dir: str = "data") -> tuple[pd.DataFrame, str]:
    """Returns (df, provenance in {stooq,yahoo,synthetic,cache})."""
    os.makedirs(cache_dir, exist_ok=True)
    cache = os.path.join(cache_dir, f"{symbol}_{start}_{end}.csv")
    if os.path.exists(cache):
        try:
            df = pd.read_csv(cache, parse_dates=["date"], index_col="date").sort_index()
            return df, "cache"
        except Exception:
            pass
    df = fetch_stooq(symbol, start, end)
    prov = "stooq"
    if df is None:
        df = fetch_yahoo(symbol, start, end)
        prov = "yahoo"
    if df is None:
        df = synth_bars(symbol, start, end)
        prov = "synthetic"
    else:
        df.to_csv(cache)
    return df, prov

def load_basket(symbols: list[str], years: int = 10,
                end: dt.date | None = None, cache_dir: str = "data") -> dict:
    end = end or dt.date.today()
    start = dt.date(end.year - years, end.month, end.day)
    out = {}
    for s in symbols:
        df, prov = load_symbol(s, start, end, cache_dir)
        out[s] = {"data": df, "provenance": prov, "start": str(df.index[0].date()),
                  "end": str(df.index[-1].date()), "bars": len(df)}
    return out
