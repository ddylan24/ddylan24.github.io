"""Kalshi Liquidity Incentive Program (LIP): census of live programs + what a new liquidity provider would earn.
Scoring (CFTC filing Feb 2026 / help.kalshi.com, Oct 2026):
  Reference price per side: help-center (current) = first bid level, walking down from the best bid, where cumulative size ≥ Target/5;
     (Feb-2026 filing: = best bid). Qualifying bids: walk down from the best bid until cumulative size ≥ Target (else side fails).
  Score(bid) = DF^(ticks below reference) · size (bids at/above reference: DF^0 = 1); normalised within side.
  Snapshot user score = yes-share + no-share (≤ 2 across users); snapshot excluded unless BOTH sides reach Target.
  Payout = user's Σ snapshot scores / all users' Σ × Period Reward × (non-excluded snapshots / all snapshots).
API: GET /trade-api/v2/incentive_programs?status=active (cursor paging); period_reward in 1/10,000 $ ; discount_factor_bps/1e4.
Simulation: add Q contracts at the best bid on BOTH sides of the current book; share = my normalised score; $/day assuming the
current book persists (two-sided ⇒ snapshot counts). Return on capital = $/day ÷ (Q·yes_bid + Q·no_bid)."""
import json, subprocess, sys, time, numpy as np, pandas as pd
R = sys.argv[1]; D = f"{R}/data/lip"; out = []
def get(u):
    for i in range(6):
        r = subprocess.run(['curl', '-s', '--max-time', '30', '-w', '\n%{http_code}', '-A', 'Mozilla/5.0', u], capture_output=True, text=True)
        b, _, c = r.stdout.rpartition('\n')
        if c == '200': return json.loads(b)
        time.sleep(min(2 ** i, 20))
API = "https://api.elections.kalshi.com/trade-api/v2"
P, cur = [], ""
for _ in range(100):
    d = get(f"{API}/incentive_programs?status=active&limit=100" + (f"&cursor={cur}" if cur else "")) or {}
    P += d.get('incentive_programs', []); cur = d.get('next_cursor') or ""
    if not cur or not d.get('incentive_programs'): break
L = pd.DataFrame(P); L.to_csv(f"{D}/programs_active.csv", index=False)
L['start'] = pd.to_datetime(L.start_date, utc=True, format='mixed'); L['end'] = pd.to_datetime(L.end_date, utc=True, format='mixed')
L['days'] = (L.end - L.start).dt.total_seconds() / 86400; L['reward'] = L.period_reward / 1e4; L['per_day'] = L.reward / L.days.clip(lower=1 / 24)
L['df'] = L.discount_factor_bps / 1e4; L['target'] = L.target_size_fp.astype(float); L['series'] = L.market_ticker.str.split('-').str[0]
now = pd.Timestamp.now(tz='UTC'); A = L[(L.start <= now) & (L.end > now) & (L.incentive_type == 'liquidity')].copy()
out.append(f"Active liquidity programs now ({now:%Y-%m-%d %H:%M} UTC): {len(A)} markets in {A.series.nunique()} series; listed incl. upcoming: {len(L)}")
out.append(f"  reward per market-day: median ${A.per_day.median():,.0f}, mean ${A.per_day.mean():,.0f}, max ${A.per_day.max():,.0f}; total ≈ ${A.per_day.sum():,.0f}/day across live programs")
out.append(f"  period length: median {A.days.median():.2f} days; discount factor values {sorted(A.df.unique().round(2).tolist())}; target sizes {sorted(A.target.unique().astype(int).tolist())[:8]}")
out.append(f"  types: {A.incentive_description.value_counts().to_dict()}")
out.append("  top series by $/day: " + ", ".join(f"{s} ${v:,.0f}" for s, v in A.groupby('series').per_day.sum().sort_values(ascending=False).head(8).items()))
def side_score(bids, target, df, me=None):
    """bids: list of (price_cents, size, owner). Walk whole PRICE LEVELS from the best bid (the filing adds all bids at a level),
    until cumulative size ≥ target. Returns (qualifies, my normalised share, reference price)."""
    if me: bids = bids + [me]
    levels = sorted({p for p, s, o in bids}, reverse=True); cum, q = 0.0, []
    for lv in levels:
        at = [(p, s, o) for p, s, o in bids if p == lv]; q += at; cum += sum(s for _, s, _ in at)
        if cum >= target: break
    if cum < target: return False, 0.0, None
    c2, ref = 0.0, levels[0]
    for lv in levels:                                   # help-center rule: first level where cumulative ≥ target/5
        c2 += sum(s for p, s, o in q if p == lv)
        if c2 >= target / 5: ref = lv; break
    sc = [(df ** max(0, ref - p)) * s for p, s, o in q]; tot = sum(sc)
    mine = sum(x for x, (p, s, o) in zip(sc, q) if o == 'me')
    return True, (mine / tot if tot else 0.0), ref
rows = []
samp = A.sort_values('per_day', ascending=False).head(250)
for r in samp.itertuples():
    ob = (get(f"{API}/markets/{r.market_ticker}/orderbook") or {}).get('orderbook_fp', {})
    yb = sorted([(round(float(p) * 100), float(s), 'x') for p, s in ob.get('yes_dollars', [])], key=lambda x: -x[0])
    nb = sorted([(round(float(p) * 100), float(s), 'x') for p, s in ob.get('no_dollars', [])], key=lambda x: -x[0])
    if not yb or not nb: rows.append(dict(t=r.market_ticker, per_day=r.per_day, both=False)); continue
    qy0, _, _ = side_score(yb, r.target, r.df); qn0, _, _ = side_score(nb, r.target, r.df)
    res = dict(t=r.market_ticker, series=r.series, per_day=r.per_day, target=r.target, df=r.df, yes_bid=yb[0][0], no_bid=nb[0][0],
               spread=100 - yb[0][0] - nb[0][0], both_now=qy0 and qn0, depth_y=sum(s for _, s, _ in yb), depth_n=sum(s for _, s, _ in nb))
    for Q in (100, 500, int(r.target)):
        qy, sy, _ = side_score(yb, r.target, r.df, me=(yb[0][0], Q, 'me')); qn, sn, _ = side_score(nb, r.target, r.df, me=(nb[0][0], Q, 'me'))
        share = (sy + sn) / 2 if (qy and qn) else 0.0
        cap = Q * (yb[0][0] + nb[0][0]) / 100
        res[f'share_{Q if Q in (100,500) else "T"}'] = share; res[f'usd_{Q if Q in (100,500) else "T"}'] = share * r.per_day; res[f'cap_{Q if Q in (100,500) else "T"}'] = cap
    rows.append(res); time.sleep(0.15)
B = pd.DataFrame(rows); B.to_csv(f"{D}/sim.csv", index=False)
ok = B[B.get('both_now', False) == True]
out.append(f"\nOrder books of the {len(B)} richest live programs: two-sided at Target now: {len(ok)} ({len(ok)/len(B):.0%}); "
           f"empty/one-sided books: {(B.both_now != True).sum()}")
if len(ok):
    for Q in ('100', '500', 'T'):
        u, c = ok[f'usd_{Q}'], ok[f'cap_{Q}']
        roc = (u / c).replace([np.inf], np.nan)
        out.append(f"  add {Q if Q!='T' else 'Target-size'} contracts at best bid on both sides: median share {ok[f'share_{Q}'].median():.1%}, "
                   f"median ${u.median():.2f}/day on ${c.median():,.0f} capital → median {100*roc.median():.2f}%/day (simple, ignores fills)")
    out.append(f"  median quoted spread in these markets {ok.spread.median():.0f}¢; median reward ${ok.per_day.median():,.0f}/day")
# markets where the book does NOT reach target on both sides: whoever completes it gets the whole snapshot pool
thin = B[B.both_now != True]
out.append(f"  one-sided/thin books with live rewards: {len(thin)}, reward ${thin.per_day.sum():,.0f}/day — the first LP to make them two-sided at Target collects (nearly) all of it, but must post Target size on BOTH sides")
txt = "\n".join(out); print(txt); open(f"{R}/notes/lip_out.txt", "w").write(txt)
# robustness: only programs lasting ≥ 1 day (short programs inflate a per-day rate), and spread structure
B2 = B.merge(A[['market_ticker', 'days']].rename(columns={'market_ticker': 't'}), on='t', how='left')
ok2 = B2[(B2.both_now == True) & (B2.days >= 1)]
out.append(f"\nPrograms lasting ≥1 day among those: n {len(ok2)}, median reward ${ok2.per_day.median():,.0f}/day")
for Q in ('100', '500', 'T'):
    u, c = ok2[f'usd_{Q}'], ok2[f'cap_{Q}']
    out.append(f"  add {Q if Q!='T' else 'Target'}: median share {ok2[f'share_{Q}'].median():.1%}, ${u.median():.2f}/day on ${c.median():,.0f} → {100*(u/c).median():.2f}%/day; 25th pct {100*(u/c).quantile(.25):.2f}%/day")
out.append(f"  quoted spread (100 − yes_bid − no_bid) in these: median {ok2.spread.median():.0f}¢, share of markets with spread ≥ 10¢: {(ok2.spread>=10).mean():.0%}")
out.append(f"  across ALL {len(A)} live programs the median pool is ${A.per_day.median():.0f}/day — the rich pools above are the top 250 by $/day")
txt = "\n".join(out); print("\n".join(out[-6:])); open(f"{R}/notes/lip_out.txt", "w").write(txt)
