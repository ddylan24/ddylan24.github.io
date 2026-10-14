"""U4: proper-scoring tournament with Diebold–Mariano tests.
DM: d_t = L(model A)_t − L(benchmark)_t aggregated per event and ordered in time; DM = mean(d)/HAC-se(d) (Newey–West, lag 5).
Arena 1: Kalshi weather (second half of days, out-of-sample) — market (multiplicative / additive / Shin de-vig), recalibrated market
         (pooled logit slope from the first half, U3), market+MOS blend is in S8.
Arena 2: Kalshi BTC daily T−24h / T−6h — market vs DVOL lognormal vs recalibrated market (slope fit on first half)."""
import sys, numpy as np, pandas as pd, statsmodels.api as sm
from scipy.optimize import brentq
R = sys.argv[1]; out = []
clip = lambda p: np.clip(p, 1e-3, 1 - 1e-3); lg = lambda p: np.log(clip(p) / (1 - clip(p))); ilg = lambda z: 1 / (1 + np.exp(-z))
def dm(d):
    d = np.asarray(d, float); f = sm.OLS(d, np.ones(len(d))).fit(cov_type='HAC', cov_kwds={'maxlags': 5}); return f.params[0], f.tvalues[0]
# ---- Arena 1: weather
W = pd.read_csv(f"{R}/data/pm/kalshi_weather.csv"); W['date'] = pd.to_datetime(W.event.str.split('-').str[1], format='%y%b%d')
W = W.groupby('event').filter(lambda e: e.p.notna().all() and e.y.sum() == 1 and len(e) >= 5)
days = sorted(W.date.unique()); cut = days[len(days) // 2]; tr, te = W[W.date < cut], W[W.date >= cut].copy()
f = sm.GLM(tr.y, sm.add_constant(lg(tr.p)), family=sm.families.Binomial()).fit(); a, b = f.params
def shin(pi):
    S = pi.sum(); g = lambda z: (np.sqrt(z * z + 4 * (1 - z) * pi * pi / S) - z).sum() / (2 * (1 - z)) - 1
    z = brentq(g, 0, 0.99) if S > 1 else 0; return (np.sqrt(z * z + 4 * (1 - z) * pi * pi / S) - z) / (2 * (1 - z))
M = {}
for ev, e in te.groupby('event'):
    pi = e.p.values; n = len(pi); y = e.y.values
    rec = ilg(a + b * lg(pi)); rec = rec / rec.sum()
    for k, q in (('multiplicative', pi / pi.sum()), ('additive', np.clip(pi - (pi.sum() - 1) / n, 1e-3, 1)), ('shin', shin(pi)), ('recalibrated', rec)):
        q = q / q.sum(); M.setdefault(k, []).append((e.date.iloc[0], -np.log(clip(q[y == 1][0])), ((q - y) ** 2).sum()))
out.append(f"Arena 1 — Kalshi weather, out-of-sample {te.event.nunique()} city-days (recalibration slope fit on first half: b {b:.2f})")
base = pd.DataFrame(M['multiplicative'], columns=['d', 'll', 'br']).sort_values('d')
for k, v in M.items():
    x = pd.DataFrame(v, columns=['d', 'll', 'br']).sort_values('d'); mu, t = dm(x.ll.values - base.ll.values)
    out.append(f"  {k:<15} log loss {x.ll.mean():.4f}  Brier {x.br.mean():.4f}   DM vs multiplicative: {mu:+.4f} (t {t:+.1f})")
# ---- Arena 2: BTC
P = pd.read_csv(f"{R}/data/r1/panel.csv"); P['day'] = pd.to_datetime(P.event.str[7:14], format='%y%b%d')   # NOTE: string labels like 26AUG08 sort AUG<OCT<SEP — parse first
for h in (24, 6):
    x = P[P.h == h].copy(); ds = sorted(x.day.unique()); trd = set(ds[:len(ds) // 2]); A_, B_ = x[x.day.isin(trd)], x[~x.day.isin(trd)].copy()
    f = sm.GLM(A_.y, sm.add_constant(lg(A_.mid)), family=sm.families.Binomial()).fit(); B_['rec'] = ilg(f.params.iloc[0] + f.params.iloc[1] * lg(B_.mid))
    ll = lambda p, y: -(y * np.log(clip(p)) + (1 - y) * np.log(1 - clip(p)))
    E = B_.assign(l_m=ll(B_.mid, B_.y), l_v=ll(B_.model, B_.y), l_r=ll(B_.rec, B_.y)).groupby('day')[['l_m', 'l_v', 'l_r']].mean().sort_index()
    out.append(f"\nArena 2 — Kalshi BTC daily T−{h}h, out-of-sample {len(E)} days (recal slope {f.params.iloc[1]:.2f} fit on first {len(trd)} days)")
    for k, nm in (('l_m', 'market'), ('l_v', 'DVOL lognormal'), ('l_r', 'recalibrated market')):
        mu, t = dm(E[k] - E.l_m) if k != 'l_m' else (0, 0)
        out.append(f"  {nm:<20} log loss/contract {E[k].mean():.4f}   DM vs market {mu:+.4f} (t {t:+.1f})")
txt = "\n".join(out); print(txt); open(f"{R}/notes/u4_out.txt", "w").write(txt)
# ---- is the T−6h recalibration tradable out of sample? (cross the spread, pay Kalshi fee)
out.append("\nTrading the recalibrated T−6h probabilities out of sample (buy at ask / sell at bid when edge > e + fee):")
x = P[P.h == 6].copy(); ds = sorted(x.day.unique()); trd = set(ds[:len(ds) // 2]); A_, B_ = x[x.day.isin(trd)], x[~x.day.isin(trd)].copy()
f = sm.GLM(A_.y, sm.add_constant(lg(A_.mid)), family=sm.families.Binomial()).fit(); B_['rec'] = ilg(f.params.iloc[0] + f.params.iloc[1] * lg(B_.mid))
fee = lambda p: 0.07 * p * (1 - p)
for e in (0.0, 0.01, 0.02, 0.03):
    buy = B_.rec - B_.ask > e + fee(B_.ask); sell = B_.bid - B_.rec > e + fee(B_.bid)
    pnl = pd.concat([(B_.y - B_.ask - fee(B_.ask))[buy], (B_.bid - B_.y - fee(B_.bid))[sell]]); dd = pd.concat([B_.day[buy], B_.day[sell]])
    if len(pnl) < 5: out.append(f"  e={e:.2f}: {len(pnl)} trades"); continue
    g = pnl.groupby(dd.values).sum(); n_days = len(g)
    t = g.mean() / (g.std(ddof=1) / np.sqrt(n_days)) if n_days > 1 else np.nan
    out.append(f"  e={e:.2f}: {buy.sum()} buys / {sell.sum()} sells on {n_days} days, mean {100*pnl.mean():+.2f}¢/contract, daily-P&L t {t:+.1f}")
txt = "\n".join(out); print("\n".join(out[-5:])); open(f"{R}/notes/u4_out.txt", "w").write(txt)
# ---- robustness: is it calibration or BTC drift? intercept, BTC trend in each half, slope-only (no intercept) recalibration
perp = pd.read_csv(f"{R}/data/r1/btc_perp_1h.csv", index_col=0, parse_dates=True).iloc[:, 0]
td = sorted(trd); d0, d1 = td[0], td[-1] + pd.Timedelta(hours=21)
r1_ = np.log(perp[perp.index.tz_localize(None) <= d1].iloc[-1] / perp[perp.index.tz_localize(None) >= d0].iloc[0]); r2_ = np.log(perp.iloc[-1] / perp[perp.index.tz_localize(None) <= d1].iloc[-1])
out.append(f"\nRobustness: first-half fit intercept {f.params.iloc[0]:+.2f}, slope {f.params.iloc[1]:.2f}; YES rate first half {A_.y.mean():.3f} vs second {B_.y.mean():.3f}; BTC log-return first half {r1_:+.1%}, second {r2_:+.1%}")
f0 = sm.GLM(A_.y, lg(A_.mid).to_frame(), family=sm.families.Binomial()).fit(); B_['rec0'] = ilg(f0.params.iloc[0] * lg(B_.mid))
for e in (0.0, 0.01):
    buy = B_.rec0 - B_.ask > e + fee(B_.ask); sell = B_.bid - B_.rec0 > e + fee(B_.bid)
    pnl = pd.concat([(B_.y - B_.ask - fee(B_.ask))[buy], (B_.bid - B_.y - fee(B_.bid))[sell]]); dd = pd.concat([B_.day[buy], B_.day[sell]])
    g = pnl.groupby(dd.values).sum(); t = g.mean() / (g.std(ddof=1) / np.sqrt(len(g))) if len(g) > 1 else np.nan
    out.append(f"  slope-only recal (b {f0.params.iloc[0]:.2f}, no intercept), e={e:.2f}: {buy.sum()} buys / {sell.sum()} sells, mean {100*pnl.mean():+.2f}¢, daily t {t:+.1f}")
ll = lambda p, y: -(y * np.log(clip(p)) + (1 - y) * np.log(1 - clip(p)))
E0 = B_.assign(a=ll(B_.rec0, B_.y) - ll(B_.mid, B_.y)).groupby('day').a.mean().sort_index(); mu, t = dm(E0.values)
out.append(f"  slope-only recal log loss vs market: {mu:+.4f} (DM t {t:+.1f})")
txt = "\n".join(out); print("\n".join(out[-4:])); open(f"{R}/notes/u4_out.txt", "w").write(txt)
