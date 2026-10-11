# Demo: reproduce the headline result in 60 seconds (record this for video/GIF)

# Option A — Docker (recommended for recordings: clean, identical everywhere)
docker compose up lab
# Expected tail output (real numbers, 2026-10-11 run):
#   qqq.us ... walks=7 oos_net=26498.58 WFE=0.228 robust=True
#   spy.us ... walks=7 oos_net=-1736.51 WFE=-0.032 robust=False

# Option B — bare metal
pip install -r requirements.txt
PYTHONPATH=src python experiments/run_all.py --basket spy.us,qqq.us --years 10 --out results

# What to show on camera (10-20 second flow):
# 1. `ls results/` -> full_report.json + per-market CSVs appear
# 2. `cat results/cross_market_patterns.csv` -> 1 robust of 5
# 3. Open docs/preview.html -> interactive lab + quiz
# 4. Open docs/assets/wf_verdict.png -> green QQQ bar vs red rest

# Recording guidance (keep assets fresh — re-record when results change):
# - GIF: `asciinema rec demo.cast` then `agg demo.cast demo.gif` (https://docs.asciinema.org/)
# - Video: upload MP4 via a GitHub issue attachment, then link a thumbnail:
#   [![Demo video](docs/assets/wf_verdict.png)](https://github.com/<you>/<repo>/assets/<id>)
#   (GitHub strips inline <video> tags in README — thumbnail-link is the supported workaround.)
