# Reproducibility log (append-only — newest run on top)

## 2026-10-11 (2) — showcase upgrade: pro README + interactive Pages lab
- Added: hero + CEO summary + gallery + beginner guide + features + user stories + demo guide + Pages deploy guide (README 141 → 386 lines, all prior paper sections kept verbatim).
- Added: `docs/preview.html` (zero-dependency interactive lab, 8-question scored quiz) + 4 result charts regenerated from live `results/` via `experiments/make_charts.py` + full-page browser-render screenshot verified (`docs/assets/preview_screenshot.png`, 720 KB) + quiz click-through verified (correct → green + explanation + score).
- Added: MIT `LICENSE`, `docs/DEMO.md` shot list, `docs/assets/` gallery.
- Verified: 4/4 tests pass, every README relative link resolves, no tooling mentions in README.

## 2026-10-11 — full 10y x 5 live-data verification (lab pipeline)

## 2026-10-11 — full 10y x 5 live-data verification (author: lab pipeline)
- Command: `docker compose up lab` ≡ `PYTHONPATH=src python experiments/run_all.py --basket spy.us,qqq.us,dia.us,iwm.us,gld.us --years 10 --out results --data-dir data`
- Data: Yahoo v8, 2016-10-10→2026-10-09, 2,514 bars/symbol, provenance `yahoo` (Stooq probed live: JS-wall + zip 401, see `src/pardo_lab/data_loader.py` note).
- Code version: engine with int-cast fix + end-liquidation fix; tests `4 passed`.
- Docker: `docker build -t pardo-lab .` OK (sha256:8026…).
- Result digest: QQQ robust (WFE 0.23, 4/4 matrix, tail +$6,626 n=9); SPY/DIA/IWM/GLD not robust (WFEs −0.03/−0.22/−0.17/−0.12; matrices SPY 0/4); plateaus 0.00 everywhere; DIA best = empty policy; IWM tail n=1.
- Artefacts: `results/full_report.json` (98 KB), `optim_profile_*.csv`, `wf_matrix_*.csv`, `oos_trades_*.csv`, `cross_market_patterns.csv`.
- Literature base (2026–2027): AlgoXpert IS/WFA/OOS (arXiv 2603.09219), Mroziewicz double-OOS (SSRN 6217160), GT-Score (JRFM 2026), Walk Forward Correlation (SSRN 2026), Pardo WFA debate (2026-06), plus README/Pages/demo best-practice guides. Key 2026 sources wired into the harness; full list in README References.
