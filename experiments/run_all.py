"""End-to-end Pardo verification: preliminary -> optimisation -> WFA -> WFA matrix ->
double-OOS lock -> flaw audit -> hidden-pattern mining. All on REAL public data.

Usage:
  python experiments/run_all.py --basket spy.us,qqq.us,dia.us,iwm.us,gld.us --years 10 --out results
"""
from __future__ import annotations
import argparse, json, os, sys, datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import pandas as pd
from pardo_lab.data_loader import load_basket
from pardo_lab.backtest_engine import backtest
from pardo_lab.metrics import summarize
from pardo_lab.optimization import grid_search, plateau_flag, DEFAULT_GRID
from pardo_lab.walkforward import walk_forward, wf_matrix
from pardo_lab.flaws_checks import cost_stress, regime_split, selector_hygiene
from pardo_lab.pardo_strategy import DEFAULTS

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--basket", default="spy.us,qqq.us,dia.us,iwm.us,gld.us")
    ap.add_argument("--years", type=int, default=10)
    ap.add_argument("--out", default="results")
    ap.add_argument("--data-dir", default="data")
    a = ap.parse_args()
    syms = [s.strip() for s in a.basket.split(",")]
    os.makedirs(a.out, exist_ok=True)
    print(f"[1/7] loading {syms} x {a.years}y of REAL public data (Stooq->Yahoo->synthetic-labelled)...")
    basket = load_basket(syms, years=a.years, cache_dir=a.data_dir)
    for s, m in basket.items():
        print(f"  {s}: {m['provenance']} {m['start']}->{m['end']} bars={m['bars']}")
    report = {"generated": dt.datetime.utcnow().isoformat() + "Z",
              "basket": {s: {k: v for k, v in m.items() if k != 'data'} for s, m in basket.items()},
              "defaults": DEFAULTS, "markets": {}}
    for sym, m in basket.items():
        df = m["data"]
        print(f"[2/7] {sym} preliminary test with guesstimated defaults {DEFAULTS}...")
        pre = summarize(backtest(df, dict(DEFAULTS)))
        print(f"  prelim: net={pre['net']} n={pre['n']} AT/cost={pre['at_over_cost']} prom={pre['prom_ann']}")
        print(f"[3/7] {sym} optimisation (PROM selector, {len(DEFAULT_GRID)} vars, coarse steps)...")
        prof = grid_search(df, DEFAULT_GRID, selector="prom_ann")
        best = {k: prof.iloc[0][k] for k in DEFAULT_GRID.keys()}
        plat = plateau_flag(prof)
        print(f"  best={best} prom={prof.iloc[0]['prom_ann']} plateau={plat}")
        print(f"[4/7] {sym} walk-forward (IS4/OOS1 rolling, purge=5d)...")
        wf = walk_forward(df, DEFAULT_GRID)
        print(f"  walks={wf['n_walks']} oos_net={wf['oos_net']} WFE={wf['wf_efficiency']} robust={wf['robust']}")
        print(f"[5/7] {sym} WF matrix + double-OOS lock...")
        mat = wf_matrix(df, DEFAULT_GRID)
        # double-OOS: hold out last 365 bars, run locked best ONCE
        tail = df.iloc[-365:]
        head = df.iloc[:-365]
        head_prof = grid_search(head, DEFAULT_GRID, selector="prom_ann")
        locked = {k: head_prof.iloc[0][k] for k in DEFAULT_GRID.keys()}
        lock_stats = summarize(backtest(tail, locked))
        print(f"  locked={locked} tail-once net={lock_stats['net']} n={lock_stats['n']}")
        print(f"[6/7] {sym} flaw audit (S&C stress, regimes, selector hygiene)...")
        audit = {"costs": cost_stress(df, best), "regimes": regime_split(df, best),
                 "selector": selector_hygiene(df, DEFAULT_GRID)}
        for k, v in audit.items():
            print(f"  {k}: pass={v['pass']} :: {v['detail']}")
        report["markets"][sym] = {
            "preliminary": pre, "best_params": {k: float(best[k]) for k in best},
            "best_stats": {k: (float(prof.iloc[0][k]) if isinstance(prof.iloc[0][k], (int, float)) else str(prof.iloc[0][k])) for k in ["net", "prom_ann", "sharpe", "calmar", "maxdd_pct", "n", "at_over_cost", "win_rate", "long_n", "short_n", "long_pnl", "short_pnl"]},
            "plateau": plat, "wf": {k: v for k, v in wf.items() if k != "all_oos_trades"},
            "wf_matrix": mat.to_dict(orient="records"),
            "double_oos": {"locked": {k: float(v) for k, v in locked.items()}, "tail_stats": lock_stats},
            "audit": audit,
            "optim_profile_head": prof.head(10).to_dict(orient="records")}
        prof.to_csv(os.path.join(a.out, f"optim_profile_{sym}.csv"), index=False)
        mat.to_csv(os.path.join(a.out, f"wf_matrix_{sym}.csv"), index=False)
        if len(wf["all_oos_trades"]):
            wf["all_oos_trades"].to_csv(os.path.join(a.out, f"oos_trades_{sym}.csv"), index=False)
    # [7/7] hidden-pattern mining across markets
    pats = []
    for sym, m in report["markets"].items():
        pats.append({"market": sym, "prelim_n": m["preliminary"]["n"],
                     "best": m["best_params"], "oos_net": m["wf"]["oos_net"],
                     "wfe": m["wf"]["wf_efficiency"], "robust": m["wf"]["robust"],
                     "tail_net": m["double_oos"]["tail_stats"]["net"],
                     "at_over_cost": m["best_stats"]["at_over_cost"],
                     "regimes": m["audit"]["regimes"]["regimes"]})
    df_p = pd.DataFrame(pats)
    df_p.to_csv(os.path.join(a.out, "cross_market_patterns.csv"), index=False)
    report["hidden_patterns"] = pats
    with open(os.path.join(a.out, "full_report.json"), "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"[7/7] wrote {a.out}/full_report.json + per-market CSVs")
    print("CROSS-MARKET:")
    print(df_p.to_string(index=False))

if __name__ == "__main__":
    main()
