"""V3: calibration of Polymarket economic-data markets (CPI/inflation, jobs, unemployment, GDP; US + international).
Price measured 1 and 7 days before the SCHEDULED end (skip markets already closed then: P2 look-ahead rule). Event-clustered."""
import json, os, subprocess, sys, time, numpy as np, pandas as pd, statsmodels.api as sm
R = sys.argv[1]; D = f"{R}/data/v3"; out = []
def get(u):
    for i in range(5):
        r = subprocess.run(['curl', '-s', '--max-time', '40', '-A', 'Mozilla/5.0', u], capture_output=True, text=True)
        try:
            d = json.loads(r.stdout)
            if isinstance(d, dict) and d.get('error'): raise ValueError
            return d
        except Exception: time.sleep(2 ** i)
fn = f"{D}/panel.csv"
if not os.path.exists(fn):
    seen = {}
    for q in ['CPI', 'inflation', 'jobs report', 'unemployment rate', 'nonfarm payrolls', 'GDP growth', 'PCE', 'payrolls']:
        for page in range(1, 6):
            d = get(f"https://gamma-api.polymarket.com/public-search?q={q.replace(' ', '%20')}&limit_per_type=50&events_status=closed&page={page}") or {}
            for e in d.get('events', []): seen[e['slug']] = e
    kw = ('inflation', 'cpi', 'unemployment', 'jobs', 'payroll', 'gdp', 'pce')
    rows = []
    for slug, e0 in seen.items():
        if not any(k in (e0['title'] + slug).lower() for k in kw): continue
        e = (get(f"https://gamma-api.polymarket.com/events?slug={slug}") or [None])[0]
        if not e: continue
        for m in e.get('markets', []):
            try: pr = [float(x) for x in json.loads(m['outcomePrices'])]; tok = json.loads(m['clobTokenIds'])[0]
            except Exception: continue
            if sorted(pr) != [0.0, 1.0] or not m.get('endDate'): continue
            h = (get(f"https://clob.polymarket.com/prices-history?market={tok}&interval=max&fidelity=60") or {}).get('history', [])
            if not h: h = (get(f"https://clob.polymarket.com/prices-history?market={tok}&interval=max&fidelity=1440") or {}).get('history', [])
            if not h: continue
            s = pd.Series({x['t']: x['p'] for x in h}).sort_index()
            end = pd.Timestamp(m['endDate']).timestamp(); ct = pd.Timestamp(m['closedTime']).timestamp() if m.get('closedTime') else end
            for dd in (1, 7):
                cut = end - dd * 86400
                if ct <= cut: continue
                ss = s[s.index <= cut]
                if len(ss): rows.append(dict(event=slug, title=e['title'], q=m['question'], days=dd, p=ss.iloc[-1], y=int(pr[0] == 1.0), vol=m.get('volumeNum')))
    pd.DataFrame(rows).to_csv(fn, index=False)
X = pd.read_csv(fn)
X['cat'] = np.select([X.title.str.contains('unemploy', case=False), X.title.str.contains('job|payroll', case=False), X.title.str.contains('gdp', case=False)], ['unemployment', 'jobs', 'gdp'], 'inflation')
X['us'] = ~X.title.str.contains('argentin|brazil|canada|china|japan|uk |u.k.|euro|germany|india|turkey|mexico|australia', case=False)
clip = lambda p: np.clip(p, 0.01, 0.99); lg = lambda p: np.log(clip(p) / (1 - clip(p)))
out.append(f"{X.event.nunique()} economic-data events, {X.q.nunique()} markets")
for dd, g in X.groupby('days'):
    g = g[(g.p > 0.01) & (g.p < 0.99)]
    f = sm.GLM(g.y, sm.add_constant(lg(g.p)), family=sm.families.Binomial()).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(g.event)[0]})
    bs = ((g.p - g.y) ** 2).mean(); unc = g.y.mean() * (1 - g.y.mean())
    out.append(f"\nT−{dd}d: n {len(g)} ({g.event.nunique()} events), Brier {bs:.4f}, skill {1-bs/unc:.1%}, logit slope {f.params.iloc[1]:.2f} ± {f.bse.iloc[1]:.2f}, intercept {f.params.iloc[0]:+.2f}")
    g = g.assign(bin=pd.cut(g.p, [0, .05, .15, .35, .65, .85, .95, 1]))
    t = g.groupby('bin', observed=True).agg(n=('y', 'size'), px=('p', 'mean'), won=('y', 'mean'))
    out.append("  " + "; ".join(f"{k}: n {r.n} px {r.px:.3f} won {r.won:.3f}" for k, r in t.iterrows()))
    for c, gc in g.groupby('cat'):
        if len(gc) > 40: out.append(f"  {c:<13} n {len(gc):4d}  mean price {gc.p.mean():.3f}  win rate {gc.y.mean():.3f}  (YES {'under' if gc.y.mean()>gc.p.mean() else 'over'}priced by {100*abs(gc.y.mean()-gc.p.mean()):.1f}¢)")
    for u, gu in g.groupby('us'): out.append(f"  {'US' if u else 'non-US':<13} n {len(gu):4d}  mean price {gu.p.mean():.3f}  win rate {gu.y.mean():.3f}")
txt = "\n".join(out); print(txt); open(f"{R}/notes/v3_out.txt", "w").write(txt)
# clustered test of YES overpricing (y − p) by category, T−1d
def ct(d):
    x = (d.y - d.p).values; g = pd.Series(x - x.mean()).groupby(d.event.values).sum(); return x.mean(), x.mean() / (np.sqrt((g ** 2).sum() * len(g) / (len(g) - 1)) / len(x)), d.event.nunique()
g1 = X[(X.days == 1) & (X.p > 0.01) & (X.p < 0.99)]
out.append("\nT−1d mean (outcome − price), event-clustered:")
for c, gc in list(g1.groupby('cat')) + [('ALL', g1)]:
    m, t, ne = ct(gc); out.append(f"  {c:<13} {100*m:+.2f}¢ (t {t:+.1f}, {ne} events)")
txt = "\n".join(out); print("\n".join(out[-6:])); open(f"{R}/notes/v3_out.txt", "w").write(txt)
