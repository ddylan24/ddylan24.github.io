"""R2: skill vs luck among Polymarket takers.
Null (efficient prices): a taker's P&L on a position has mean 0 and variance n²·p̄(1−p̄), where n = net YES shares and p̄ the
share-weighted price (all of a wallet's trades in one market share one outcome, so aggregate per wallet-market first).
Then: (1) z-scores across wallets vs N(0,1); BH-FDR count of 'skilled' wallets; (2) persistence: early-half vs late-half markets."""
import sys, numpy as np, pandas as pd
from scipy import stats
R = sys.argv[1]; out = []
M = pd.read_csv(f"{R}/data/r2/markets.csv"); M['closed'] = pd.to_datetime(M.closed, utc=True, format='mixed')
T = pd.read_csv(f"{R}/data/r2/trades.csv.gz")
T = T.merge(M[['cid', 'y', 'closed']], on='cid')
T['ts'] = pd.to_datetime(T.ts, unit='s', utc=True)
T = T[T.ts < T.closed - pd.Timedelta(hours=1)]               # drop trades in the final hour (often after the outcome is known)
T['p_yes'] = np.where(T.is_yes, T.price, 1 - T.price)
T['n_yes'] = np.where(T.is_yes == (T.side == 'BUY'), 1, -1) * T['size']     # YES-equivalent shares bought by the taker
T['cost'] = T.n_yes * T.p_yes
out.append(f"{T.cid.nunique()} resolved 2026 markets, {len(T):,} taker trades (excluding final hour), {T.wallet.nunique():,} wallets, ${(T['size']*T.price).sum()/1e6:,.1f}M")
W = T.groupby(['wallet', 'cid']).agg(n=('n_yes', 'sum'), cost=('cost', 'sum'), gross=('n_yes', lambda s: s.abs().sum()), y=('y', 'first'), closed=('closed', 'first')).reset_index()
W['pnl'] = W.n * W.y - W.cost                                   # payoff of net position minus net cost
W['pbar'] = np.clip(np.where(W.n != 0, W.cost / W.n.replace(0, np.nan), 0.5), 0.01, 0.99)
W['var'] = (W.n ** 2) * W.pbar * (1 - W.pbar)
# ---- null: each market's outcome drawn ONCE for everyone, y ~ Bernoulli(volume-weighted YES price of all taker trades in it)
import scipy.sparse as sp
ref = T.assign(usd=T['size'] * T.price).groupby('cid').apply(lambda g: np.average(g.p_yes, weights=g['size']), include_groups=False)
wl = W.wallet.astype('category'); ml = W.cid.astype('category')
Nm = sp.csr_matrix((W.n.values, (wl.cat.codes, ml.cat.codes)), shape=(len(wl.cat.categories), len(ml.cat.categories)))
cost = W.groupby(wl.cat.codes).cost.sum().reindex(range(Nm.shape[0])).values
gross = W.groupby(wl.cat.codes).apply(lambda g: (g.gross * g.pbar).sum(), include_groups=False).reindex(range(Nm.shape[0])).values
nmk = W.groupby(wl.cat.codes).cid.nunique().reindex(range(Nm.shape[0])).values
yreal = M.set_index('cid').y.reindex(ml.cat.categories).values
pref = ref.reindex(ml.cat.categories).values
real = Nm @ yreal - cost
rng = np.random.default_rng(0); B = 500
Ys = (rng.random((len(pref), B)) < pref[:, None]).astype(float)
sims = (Nm @ Ys) - cost[:, None]
pval = ((sims >= real[:, None]).sum(1) + 1) / (B + 1)
keep = nmk >= 3
out.append(f"\nNull: outcomes ~ Bernoulli(volume-weighted price), drawn once per market for all wallets ({B} sims). Wallets with ≥3 markets: {keep.sum():,}")
out.append(f"  takers' total P&L real ${real.sum():,.0f} vs null mean ${sims.sum(0).mean():,.0f} ± {sims.sum(0).std():,.0f}")
pv = pval[keep]
out.append(f"  wallets with p<0.05: {(pv<0.05).mean():.2%} (null 5%); p<0.01: {(pv<0.01).mean():.2%} (null 1%)")
from statsmodels.stats.multitest import multipletests
rej = multipletests(pv, alpha=0.05, method='fdr_bh')[0]
out.append(f"  BH-FDR 5% 'skilled' wallets: {rej.sum()} of {keep.sum():,}")
top = np.argsort(-np.where(keep, real, -np.inf))[:10]
out.append("  top-10 by P&L: " + "; ".join(f"${real[i]:,.0f} (p {pval[i]:.3f}, {nmk[i]} mkts)" for i in top))
roi = real / np.maximum(gross, 1)
out.append(f"  ROI on traded notional, wallets ≥3 mkts: median {np.median(roi[keep]):+.2%}, share positive {(real[keep]>0).mean():.1%}")
# placebo of the whole procedure: replace real outcomes by one simulated draw
yfake = (rng.random(len(pref)) < pref).astype(float); fake = Nm @ yfake - cost
pf = ((sims >= fake[:, None]).sum(1) + 1) / (B + 1)
out.append(f"  placebo (fake outcomes): wallets with p<0.05 {(pf[keep]<0.05).mean():.2%}; BH 'skilled' {multipletests(pf[keep], alpha=0.05, method='fdr_bh')[0].sum()}")
# ---- persistence on ROI: markets closing before vs after the median close date
med = W.closed.median()
def half(sub):
    g = sub.groupby('wallet'); return pd.DataFrame({'pnl': g.pnl.sum(), 'vol': g.apply(lambda x: (x.gross * x.pbar).sum(), include_groups=False), 'k': g.cid.nunique()})
E, L = half(W[W.closed <= med]), half(W[W.closed > med])
Bq = E.join(L, lsuffix='_e', rsuffix='_l', how='inner'); Bq = Bq[(Bq.k_e >= 3) & (Bq.k_l >= 3) & (Bq.vol_e > 100) & (Bq.vol_l > 100)]
Bq['roi_e'] = Bq.pnl_e / Bq.vol_e; Bq['roi_l'] = Bq.pnl_l / Bq.vol_l
from scipy import stats as st
r, p = st.spearmanr(Bq.roi_e, Bq.roi_l)
Bq['q'] = pd.qcut(Bq.roi_e.rank(method='first'), 5, labels=False)
out.append(f"\nPersistence (close ≤ vs > {med:%Y-%m-%d}), {len(Bq)} wallets with ≥3 markets and >$100 in each half: Spearman(ROI early, ROI late) {r:+.3f} (p {p:.3f})")
for q, g in Bq.groupby('q'): out.append(f"  early-ROI quintile {q+1}: early ROI {g.roi_e.median():+.1%}, late median ROI {g.roi_l.median():+.2%}, late total P&L ${g.pnl_l.sum():,.0f}, share late>0 {(g.pnl_l>0).mean():.0%}")
txt = "\n".join(out); print(txt); open(f"{R}/notes/r2_out.txt", "w").write(txt)
