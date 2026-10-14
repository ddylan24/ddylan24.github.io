import json, sys, re, numpy as np, pandas as pd, statsmodels.api as sm
R=sys.argv[1]; out=[]
m=pd.read_csv(f'{R}/data/pm/markets.csv',dtype={'tok':str})
def cat(r):
    t=(str(r.q)+' '+str(r.event)).lower()
    if re.search(r'\b(nba|nfl|mlb|nhl|ufc|premier league|champions league|world series|super bowl|win on|vs\.?|grand prix|f1|tennis|open|masters|fifa|world cup|stanley cup|finals|match|game \d|playoff|mvp|heisman|draft)\b',t): return 'sports'
    if re.search(r'\b(bitcoin|btc|eth|ethereum|solana|crypto|token|coin|doge|xrp|airdrop|fdv|etf)\b',t): return 'crypto'
    if re.search(r'\b(election|president|presidential|senate|house|governor|nominee|primary|parliament|prime minister|vote|electoral|mayor|party|trump|biden|harris|cabinet|impeach|congress)\b',t): return 'politics'
    if re.search(r'\b(fed|rate|cpi|inflation|gdp|recession|unemployment|tariff|interest)\b',t): return 'economics'
    return 'other'
m['category']=m.apply(cat,axis=1)
out.append("M1 Polymarket calibration by category (scheduled-end design, 7 days before, 1¢<p<99¢); category by keyword rules on question/event title")
out.append("  market counts: "+", ".join(f"{k} {v}" for k,v in m.category.value_counts().items()))
d=pd.read_csv(f'{R}/data/pm/calib_sched_h7.csv'); 
# re-derive categories by joining on event (calib file has event only) — map event→category by majority
evcat=m.groupby('event').category.agg(lambda s:s.mode().iloc[0])
d['category']=d.event.map(evcat).fillna('other'); d=d[(d.p>0.01)&(d.p<0.99)]
for c,g in d.groupby('category'):
    if len(g)<40: out.append(f"  {c:<10} n={len(g)} (too few)"); continue
    X=sm.add_constant(np.log(g.p/(1-g.p)))
    try: f=sm.Logit(g.y,X).fit(disp=0,cov_type='cluster',cov_kwds={'groups':pd.factorize(g.event)[0]}); b=f'{f.params.iloc[1]:.2f} ± {f.bse.iloc[1]:.2f}'
    except Exception: b='n/a'
    mid=g[(g.p>=.05)&(g.p<=.95)]; e=(mid.y-mid.p); gg=e.groupby(mid.event).mean()
    t=gg.mean()/(gg.std()/np.sqrt(len(gg))) if len(gg)>2 else np.nan
    out.append(f"  {c:<10} n={len(g):4d} ({g.event.nunique()} events): Brier {np.mean((g.p-g.y)**2):.4f}, slope b {b}; mid-priced outcome−price {e.mean():+.3f} (clustered t {t:+.2f}, n {len(mid)})")
txt="\n".join(out); print(txt); open(f'{R}/notes/m1_out.txt','w').write(txt)
