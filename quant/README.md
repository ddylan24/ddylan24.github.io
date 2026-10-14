# quant/

Research notes, code and course material on quantitative trading, built in Claude Code sessions starting October 2026.

**Start here:** read [`CONTEXT.md`](CONTEXT.md). It's a self-contained briefing of everything learned, written so a new session can pick up where the last one left off. To continue the research in a new session, say something like:

> Read `quant/CONTEXT.md` and `quant/agenda.md`, then continue the next unfinished topic. Keep adding notes to `quant/notes/` and update `CONTEXT.md` with any new findings.

| Path | What's in it |
|---|---|
| `CONTEXT.md` | Condensed findings, formulas, pitfalls, data sources |
| `agenda.md` | All research topics with done/todo status |
| `notes/` | One file per topic: the math, the method, exact numbers, lessons |
| `code/` | The Python script behind each topic |
| `course/quant-field-manual.html` | The full course (open in a browser) |
| `data/` | Small derived datasets; `fetch_data.sh` re-downloads the raw data |
| `sims/` | Standalone simulation demos |

## Re-running anything

```bash
cd quant
pip install numpy pandas scipy statsmodels arch hmmlearn scikit-learn yfinance openpyxl
bash data/fetch_data.sh            # Ken French, FRED and AQR data
python3 -I code/a1_sweeps.py .     # also writes data/spy.csv
python3 -I code/verify_data.py .   # also writes data/ff3_daily.csv
python3 -I code/<topic>.py .       # any other topic
```

This folder is excluded from the Jekyll site build (`_config.yml` → `exclude`), so it won't be published on the website.
