"""READ-ONLY paper market-maker for Kalshi hourly Miami temperature (KXTEMPMIAH) + LIP rewards.  Places NO orders.

Two shadow policies are run side by side on the same live data so their economics can be compared:
  JOIN  : always rest --size contracts at the best YES bid and the best NO bid of every open market.
  SMART : same, but uses Kalshi's own settlement index (GET /live_data/weather/miami, public, 1-minute, 0.01°F) to PULL
          both sides of a strike when the hour is close and the index is near the strike
          (minutes_left <= --risk-min and |index - K| <= --risk-band), and pulls everything in the final --final-min minutes.
Each cycle (--interval s):
  * reward: official LIP scoring (pm_toolkit.lip_side_share) on the live book, accrued only while BOTH sides are quoted and
    both sides reach Target (snapshot rule), pro-rated by elapsed time and the program's pool per second.
  * fills: public trades since the previous cycle are matched against the quotes that were resting at the previous cycle
    (so the effective cancel latency is one cycle: conservative). A YES bid at b fills on taker NO trades at YES price < b,
    or at b beyond the queue ahead; a NO bid symmetrically.
  * settlement: when a market settles, positions are marked to the result.
Output JSONL (--out); `--report` prints reward, fill P&L and net per policy.

Run (home PC/VPS):  python3 tempmiah_paper.py --size 100 --interval 10
Real orders require the user's explicit go-ahead (PLAYBOOK §4). See notes/AA1.md, Z1.md, Z2.md, SPEED.md.
"""
import argparse, json, os, subprocess, sys, time
import datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'code'))
from pm_toolkit import lip_side_share

API = "https://api.elections.kalshi.com/trade-api/v2"
ap = argparse.ArgumentParser()
ap.add_argument('--size', type=float, default=100.0)
ap.add_argument('--interval', type=int, default=10)
ap.add_argument('--risk-min', type=float, default=20.0)
ap.add_argument('--risk-band', type=float, default=1.0)
ap.add_argument('--final-min', type=float, default=3.0)
ap.add_argument('--out', default=os.path.expanduser('~/pmdata/tempmiah_paper.jsonl'))
ap.add_argument('--hours', type=float, default=0, help='stop after N hours (0 = forever)')
ap.add_argument('--report', action='store_true')
a = ap.parse_args()
POL = ('JOIN', 'SMART')


def get(u, tries=4):
    for i in range(tries):
        r = subprocess.run(['curl', '-s', '--max-time', '20', '-w', '\n%{http_code}', '-A', 'Mozilla/5.0', u], capture_output=True, text=True)
        b, _, c = r.stdout.rpartition('\n')
        if c == '200':
            try: return json.loads(b)
            except Exception: return None
        time.sleep(min(2 ** i, 10))


def log(kind, **kw):
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, 'a') as f: f.write(json.dumps({'ts': time.time(), 'kind': kind, **kw}) + '\n')


if a.report:
    import collections
    agg = collections.defaultdict(lambda: collections.Counter())
    for line in open(a.out):
        e = json.loads(line); p = e.get('policy')
        if not p: continue
        if e['kind'] == 'accrue': agg[p]['reward'] += e['usd']
        elif e['kind'] == 'fill': agg[p]['fills'] += 1; agg[p]['contracts'] += e['qty']
        elif e['kind'] == 'settle': agg[p]['fill_pnl'] += e['pnl']; agg[p]['settled'] += 1
    for p in POL:
        g = agg[p]
        print(f"{p:<6} reward ${g['reward']:8.2f}  fills {g['fills']:4d} ({g['contracts']:7.0f} ct)  settled mkts {g['settled']:3d}  "
              f"fill P&L ${g['fill_pnl']:+8.2f}  NET ${g['reward'] + g['fill_pnl']:+8.2f}")
    sys.exit(0)

progs, progs_t = {}, 0
st = {p: {} for p in POL}                    # policy -> ticker -> {'pos': yes contracts, 'cash', 'yes': (px, ahead) | None, 'no': ...}
last_poll = {}
t_start = time.time()
while True:
    t0 = time.time(); now = dt.datetime.now(dt.timezone.utc)
    if time.time() - progs_t > 300:          # refresh LIP programs every 5 min
        d = get(f"{API}/incentive_programs?status=active&type=liquidity&limit=10000") or {}
        progs = {p['market_ticker']: p for p in d.get('incentive_programs', []) if p['market_ticker'].startswith('KXTEMPMIAH')}
        progs_t = time.time()
    wx = get(f"{API}/live_data/weather/miami?last_sec=600") or {}
    pts = [p for p in wx.get('timeseries', []) if p.get('v') is not None]
    idx = pts[-1]['v'] if pts else None
    mk = (get(f"{API}/markets?series_ticker=KXTEMPMIAH&status=open&limit=100") or {}).get('markets', [])
    for m in mk:
        tk = m['ticker']; K = m.get('floor_strike'); close = dt.datetime.fromisoformat(m['close_time'].replace('Z', '+00:00'))
        mins_left = (close - now).total_seconds() / 60
        ob = (get(f"{API}/markets/{tk}/orderbook") or {}).get('orderbook_fp', {})
        yb = [(round(float(x) * 100), float(q)) for x, q in ob.get('yes_dollars', [])]
        nb = [(round(float(x) * 100), float(q)) for x, q in ob.get('no_dollars', [])]
        # fills against the quotes that were resting during the last interval
        since = last_poll.get(tk, int(t0) - a.interval)
        tr = (get(f"{API}/markets/trades?ticker={tk}&limit=1000&min_ts={since}") or {}).get('trades', []); last_poll[tk] = int(t0)
        for p in POL:
            s = st[p].setdefault(tk, {'pos': 0.0, 'cash': 0.0, 'yes': None, 'no': None, 'close': m['close_time']})
            for x in tr:
                yp = round(float(x['yes_price_dollars']) * 100); q = float(x['count_fp'])
                if x['taker_side'] == 'no' and s['yes']:
                    b, ahead = s['yes']
                    if yp < b or (yp == b and q > ahead):
                        fq = min(a.size, q if yp < b else q - ahead); s['pos'] += fq; s['cash'] -= fq * b / 100
                        log('fill', policy=p, ticker=tk, side='buy_yes', price=b, qty=fq, mins_left=round(mins_left, 1), idx=idx, K=K)
                elif x['taker_side'] == 'yes' and s['no']:
                    b, ahead = s['no']
                    if (100 - yp) < b or ((100 - yp) == b and q > ahead):
                        fq = min(a.size, q if (100 - yp) < b else q - ahead); s['pos'] -= fq; s['cash'] -= fq * b / 100
                        log('fill', policy=p, ticker=tk, side='buy_no', price=b, qty=fq, mins_left=round(mins_left, 1), idx=idx, K=K)
            # new quotes for the next interval
            if not yb or not nb or mins_left <= 0:
                s['yes'] = s['no'] = None; continue
            by, bn = max(x for x, _ in yb), max(x for x, _ in nb)
            quote = True
            if p == 'SMART':
                if mins_left <= a.final_min: quote = False
                elif idx is not None and K is not None and mins_left <= a.risk_min and abs(idx - K) <= a.risk_band: quote = False
            s['yes'] = (by, sum(q for x, q in yb if x == by)) if quote else None
            s['no'] = (bn, sum(q for x, q in nb if x == bn)) if quote else None
            pr = progs.get(tk)
            if quote and pr:
                T = float(pr['target_size_fp']); DF = pr['discount_factor_bps'] / 1e4
                s0 = dt.datetime.fromisoformat(pr['start_date'].replace('Z', '+00:00')); s1 = dt.datetime.fromisoformat(pr['end_date'].replace('Z', '+00:00'))
                if s0 <= now <= s1:
                    qy, sy = lip_side_share(yb, T, DF, by, a.size); qn, sn = lip_side_share(nb, T, DF, bn, a.size)
                    if qy and qn:
                        log('accrue', policy=p, ticker=tk, usd=(sy + sn) / 2 * pr['period_reward'] / 1e4 / max((s1 - s0).total_seconds(), 1) * a.interval,
                            share=round((sy + sn) / 2, 4), mins_left=round(mins_left, 1), idx=idx, K=K)
        time.sleep(0.05)
    # settlement
    for p in POL:
        for tk, s in list(st[p].items()):
            if dt.datetime.now(dt.timezone.utc) < dt.datetime.fromisoformat(s['close'].replace('Z', '+00:00')) + dt.timedelta(minutes=2): continue
            m = (get(f"{API}/markets/{tk}") or {}).get('market', {})
            if m.get('result') in ('yes', 'no'):
                y = 1.0 if m['result'] == 'yes' else 0.0
                pnl = s['cash'] + max(s['pos'], 0) * y + max(-s['pos'], 0) * (1 - y)
                log('settle', policy=p, ticker=tk, result=m['result'], pnl=pnl, pos=s['pos']); del st[p][tk]
    print(now.strftime('%H:%M:%S'), f"index {idx}  open markets {len(mk)}  programs {len(progs)}", flush=True)
    if a.hours and time.time() - t_start > a.hours * 3600: break
    time.sleep(max(1, a.interval - (time.time() - t0)))
