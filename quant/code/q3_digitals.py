"""Q3: binary (digital) options math vs crypto threshold prediction markets.
Risk-neutral P(S_T > K) from the Deribit BTC option surface (smile + time interpolation, Breeden-Litzenberger
digital = -dC/dK) compared with live Polymarket 'Bitcoin above X' (Binance BTCUSDT noon ET) and Kalshi KXBTCD (BRTI 5pm ET)."""
import json, sys, time, urllib.request, numpy as np, pandas as pd
from scipy.stats import norm
R = sys.argv[1]; out = []
def get(u):
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=60) as r: return json.load(r)
        except Exception: time.sleep(2 ** i)
NOW = pd.Timestamp.now(tz='UTC'); YR = 365.25 * 86400
# ---------------- Deribit surface
chain = get("https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency=BTC&kind=option")['result']
idx = get("https://www.deribit.com/api/v2/public/get_index_price?index_name=btc_usd")['result']['index_price']
rows = []
for x in chain:
    _, e, k, cp = x['instrument_name'].split('-')
    T = (pd.Timestamp(pd.to_datetime(e, format='%d%b%y').strftime('%Y-%m-%d') + ' 08:00', tz='UTC') - NOW).total_seconds() / YR
    if x.get('mark_iv') and T > 0:
        rows.append(dict(exp=e, T=T, K=float(k), cp=cp, iv=x['mark_iv'] / 100, F=x['underlying_price']))
O = pd.DataFrame(rows)
O = O[((O.cp == 'C') & (O.K >= O.F)) | ((O.cp == 'P') & (O.K < O.F))]   # out-of-the-money side of the smile
S = {}
for e, g in O.groupby('exp'):
    g = g.sort_values('K'); F = g.F.median(); T = g['T'].iloc[0]
    S[T] = (F, np.log(g.K.values / F), g.iv.values ** 2 * T)       # total variance w(k)
Ts = sorted(S)
SMOOTH = '--smooth' in sys.argv
POLY = {}
for t_, (F_, ks_, ws_) in S.items():
    m_ = np.abs(ks_) < 0.3
    POLY[t_] = np.polyfit(ks_[m_], ws_[m_], 4) if m_.sum() >= 8 else None
def w_at(k, T):
    """total implied variance at log-moneyness k and horizon T: linear in k within an expiry, linear in T across expiries"""
    def w1(Te):
        F, ks, ws = S[Te]
        if SMOOTH and POLY[Te] is not None and abs(k) < 0.3: return max(np.polyval(POLY[Te], k), 1e-8)
        return np.interp(k, ks, ws)
    if T <= Ts[0]: return w1(Ts[0]) * T / Ts[0]
    j = np.searchsorted(Ts, T); a, b = Ts[j - 1], Ts[min(j, len(Ts) - 1)]
    return w1(a) + (w1(b) - w1(a)) * (T - a) / (b - a) if b > a else w1(a)
def fwd(T):
    Fs = [S[t][0] for t in Ts]; return np.interp(T, Ts, Fs, left=Fs[0])
def call(F, K, w):
    s = np.sqrt(w); d1 = (np.log(F / K) + w / 2) / s; return F * norm.cdf(d1) - K * norm.cdf(d1 - s)
def digital(K, T, scale=1.0, dF=0.0):
    F = fwd(T) * scale + dF; h = 0.002 * K
    c = lambda KK: call(F, KK, w_at(np.log(KK / F), T))
    p_smile = -(c(K + h) - c(K - h)) / (2 * h)
    w = w_at(np.log(K / F), T); p_flat = norm.cdf((np.log(F / K) - w / 2) / np.sqrt(w))
    return p_smile, p_flat, np.sqrt(w / T)
out.append(f"Snapshot {NOW:%Y-%m-%d %H:%M} UTC; Deribit BTC index {idx:,.0f}; {len(O)} OTM options across {len(Ts)} expiries")
out.append("  ATM implied vol by expiry: " + ", ".join(f"{e} {np.sqrt(np.interp(0, S[t][1], S[t][2]) / t):.0%}" for e, t in sorted(((e, g['T'].iloc[0]) for e, g in O.groupby('exp')), key=lambda z: z[1])[:7]))
def index_now(): return get("https://www.deribit.com/api/v2/public/get_index_price?index_name=btc_usd")['result']['index_price']
kr = get("https://api.kraken.com/0/public/Ticker?pair=USDTUSD")['result']; USDT = float(list(kr.values())[0]['c'][0])
out.append(f"  USDT/USD (Kraken) {USDT:.5f} -> Binance BTCUSDT strikes are K*{USDT:.5f} in USD")
# ---------------- Polymarket
pm = []; i0 = index_now()
for d in pd.date_range(NOW.normalize(), periods=8, freq='D'):
    for slug in [f"bitcoin-above-on-{d:%B}-{d.day}-{d:%Y}".lower()]:
        ev = get(f"https://gamma-api.polymarket.com/events?slug={slug}")
        if not ev: continue
        for m in ev[0]['markets']:
            if m.get('closed') or m.get('bestAsk') is None: continue
            end = pd.Timestamp(m['endDate']); T = (end - NOW).total_seconds() / YR
            if T <= 0: continue
            pm.append(dict(venue='Polymarket', expiry=end, T=T, K=float(m['groupItemTitle'].replace(',', '')), bid=float(m.get('bestBid') or 0), ask=float(m['bestAsk'])))
IDX = {'Polymarket': (i0 + index_now()) / 2}
# ---------------- Kalshi
ks = []; i0 = index_now()
kd = get("https://api.elections.kalshi.com/trade-api/v2/events?series_ticker=KXBTCD&status=open&with_nested_markets=true&limit=20") or {}
for ev in kd.get('events', []):
    for m in ev['markets']:
        end = pd.Timestamp(m['close_time']); T = (end - NOW).total_seconds() / YR
        b, a = m.get('yes_bid_dollars'), m.get('yes_ask_dollars')
        if T <= 2 / 24 / 365.25 or b is None or a is None: continue
        if not m.get('floor_strike'): continue
        ks.append(dict(venue='Kalshi', expiry=end, T=T, K=float(m['floor_strike']), bid=float(b), ask=float(a)))
IDX['Kalshi'] = (i0 + index_now()) / 2
out.append("  Deribit index during venue fetches: " + ", ".join(f"{k} {v:,.0f}" for k, v in IDX.items()) + f" (chain snapshot {idx:,.0f})")
D = pd.DataFrame(pm + ks)
D['K_usd'] = np.where(D.venue == 'Polymarket', D.K * USDT, D.K)
D['scale'] = D.venue.map(IDX) / idx            # move the forward with spot between snapshots
D['mid'] = (D.bid + D.ask) / 2; D['spread'] = D.ask - D.bid
D[['p_opt', 'p_flat', 'iv']] = D.apply(lambda r: pd.Series(digital(r.K_usd, r['T'], r.scale)), axis=1)
D[['p_naive']] = D.apply(lambda r: pd.Series(digital(r.K, r['T'])[0]), axis=1)   # no USDT / timing adjustment
D = D[(D.ask - D.bid <= 0.10)]                     # quoted two-sided
D['diff'] = D.mid - D.p_opt
D['inside'] = (D.p_opt >= D.bid) & (D.p_opt <= D.ask)
D['edge_buy'] = D.p_opt - D.ask; D['edge_sell'] = D.bid - D.p_opt
D.to_csv(f"{R}/data/q3/compare{'_smooth' if SMOOTH else ''}.csv", index=False)
for v, g in D.groupby('venue'):
    mid = g[(g.p_opt > .03) & (g.p_opt < .97)]
    out.append(f"\n{v}: {len(g)} strikes with two-sided quotes across {g.expiry.nunique()} expiries; {len(mid)} with 3%<p<97%")
    out.append(f"  mid − options prob: mean {100*mid['diff'].mean():+.2f}¢, mean |diff| {100*mid['diff'].abs().mean():.2f}¢, max |diff| {100*mid['diff'].abs().max():.2f}¢; median spread {100*g.spread.median():.1f}¢")
    out.append(f"  options prob inside the bid–ask: {mid.inside.mean():.0%};  executable vs options (ask < p_opt or bid > p_opt): {((mid.edge_buy>0)|(mid.edge_sell>0)).sum()} strikes, best {100*max(mid.edge_buy.max(), mid.edge_sell.max()):.2f}¢")
    sk = mid.assign(z=np.log(mid.K / fwd(mid['T'].mean())))
    lo, hi = sk[sk.p_opt < .3], sk[sk.p_opt > .7]
    out.append(f"  by moneyness: p_opt<30% mean diff {100*lo['diff'].mean():+.2f}¢ (n={len(lo)}), 30–70% {100*sk[(sk.p_opt>=.3)&(sk.p_opt<=.7)]['diff'].mean():+.2f}¢, >70% {100*hi['diff'].mean():+.2f}¢ (n={len(hi)})")
    out.append(f"  skew correction (smile digital − flat N(d2)): mean {100*(g.p_opt-g.p_flat).mean():+.2f}¢, max |·| {100*(g.p_opt-g.p_flat).abs().max():.2f}¢")
# implied forward: shift dF that best fits each venue+expiry's mids (10%<p<90%)
from scipy.optimize import minimize_scalar
fits = []
for (v, e), g in D[(D.p_opt > .1) & (D.p_opt < .9)].groupby(['venue', 'expiry']):
    if len(g) < 3: continue
    f = lambda dF: sum((r.mid - digital(r.K_usd, r.T, r.scale, dF)[0]) ** 2 for r in g.itertuples())
    res = minimize_scalar(f, bounds=(-1500, 1500), method='bounded')
    rmse0, rmse1 = np.sqrt(f(0) / len(g)), np.sqrt(res.fun / len(g))
    fits.append((v, e, len(g), res.x, rmse0, rmse1, fwd(g['T'].iloc[0]) * g.scale.iloc[0] - D.venue.map(IDX)[g.index[0]]))
out.append("\nImplied forward shift (venue mids vs Deribit forward), USD; 'carry' = Deribit forward − index:")
for v, e, n, dF, r0, r1, carry in fits:
    out.append(f"  {v:<10} {pd.Timestamp(e):%m-%d %H:%M}  n={n:2d}  dF {dF:+6.0f}  carry {carry:+5.0f}  RMSE {100*r0:.2f}¢ → {100*r1:.2f}¢")
out.append(f"  naive (no USDT, no timing) mean diff Polymarket {100*(D[D.venue=='Polymarket'].mid-D[D.venue=='Polymarket'].p_naive)[(D.p_opt>.03)&(D.p_opt<.97)].mean():+.2f}¢")
for v, g in D[(D.p_opt > .03) & (D.p_opt < .97)].groupby('venue'):
    out.append(f"  {v}: RMSE of mids vs smile digital {100*np.sqrt(((g.mid-g.p_opt)**2).mean()):.2f}¢ vs flat ATM-vol N(d2) {100*np.sqrt(((g.mid-g.p_flat)**2).mean()):.2f}¢ (venues price the skew)")
# show one expiry table per venue
for v in ['Polymarket', 'Kalshi']:
    g = D[(D.venue == v)]
    if not len(g): continue
    e = sorted(g.expiry.unique())[min(1, g.expiry.nunique() - 1)]
    t = g[(g.expiry == e) & (g.p_opt > .02) & (g.p_opt < .98)].sort_values('K')
    out.append(f"\n{v} expiry {pd.Timestamp(e):%m-%d %H:%M} UTC (fwd {fwd(t['T'].iloc[0]):,.0f}, vol {t.iv.median():.0%}):")
    for r in t.itertuples():
        out.append(f"  K {r.K:>8,.0f}  bid/ask {r.bid:.3f}/{r.ask:.3f}  options {r.p_opt:.3f} (flat N(d2) {r.p_flat:.3f})  diff {100*r.diff:+.1f}¢")
txt = "\n".join(out); print(txt); open(f"{R}/notes/q3_out{'_smooth' if SMOOTH else ''}.txt", "w").write(txt)
