"""READ-ONLY paper quoter for Kalshi's Liquidity Incentive Program (LIP).  Places NO orders.

Every --interval seconds, for each market with an active LIP program in --series:
  1. Read the public order book. Hypothetically rest Q contracts on each side: join the best YES bid and the best NO bid
     (or improve by 1 tick when the spread is >= --improve-at cents).
  2. Score the hypothetical quote with the official rules (pm_toolkit.lip_side_share: whole-level walk to Target,
     reference = level reaching Target/5, DF^ticks). Accrue reward = share/2 summed over sides x pool per second x interval,
     only when both sides reach Target (otherwise the snapshot is excluded).
  3. Simulate fills from the public trade feed since the last poll, conservatively: a resting YES bid at price b fills only
     when a taker SELLS yes (taker_side == 'no') at a YES price STRICTLY BELOW b, or at b with size larger than the queue
     ahead of us (book size at b when we joined). Same logic for the NO side. Positions are marked to settlement.
Outputs JSONL events to --out, and `python3 lip_paper.py --report` summarises reward vs fill P&L per series.

Run on the home PC/Pi:   python3 lip_paper.py --series KXEURUSD15M,KXTEMPMIAH,KXRT --size 100 --interval 30
See ../notes/LIP.md, X1.md, X2.md and ../PLAYBOOK.md §2.5.  Real orders require the user's explicit go-ahead (PLAYBOOK §4).
"""
import argparse, json, os, subprocess, sys, time
import datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'code'))
from pm_toolkit import lip_side_share

API = "https://api.elections.kalshi.com/trade-api/v2"
ap = argparse.ArgumentParser()
ap.add_argument('--series', default='KXEURUSD15M,KXTEMPMIAH,KXRT')
ap.add_argument('--size', type=float, default=100.0)
ap.add_argument('--interval', type=int, default=30)
ap.add_argument('--improve-at', type=int, default=3)
ap.add_argument('--out', default=os.path.expanduser('~/pmdata/lip_paper.jsonl'))
ap.add_argument('--report', action='store_true')
ap.add_argument('--cycles', type=int, default=0, help='stop after N cycles (0 = run forever)')
ap.add_argument('--max-markets', type=int, default=40, help='quote only the N richest live programs (by pool per second)')
a = ap.parse_args()


def get(u, tries=5):
    for i in range(tries):
        r = subprocess.run(['curl', '-s', '--max-time', '30', '-w', '\n%{http_code}', '-A', 'Mozilla/5.0', u], capture_output=True, text=True)
        body, _, code = r.stdout.rpartition('\n')
        if code == '200':
            try:
                return json.loads(body)
            except Exception:
                return None
        time.sleep(min(2 ** i, 20))


def log(kind, **kw):
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, 'a') as f:
        f.write(json.dumps({'ts': time.time(), 'kind': kind, **kw}) + '\n')


if a.report:
    import collections
    rew = collections.defaultdict(float); fills = collections.defaultdict(float); settled = collections.defaultdict(float); n = collections.Counter()
    for line in open(a.out):
        e = json.loads(line); s = e.get('series', '?')
        if e['kind'] == 'accrue': rew[s] += e['usd']
        elif e['kind'] == 'fill': fills[s] += e['qty']; n[s] += 1
        elif e['kind'] == 'settle': settled[s] += e['pnl']
    for s in sorted(set(rew) | set(settled)):
        print(f"{s:<16} reward ${rew[s]:9.2f}   fills {n[s]:5d} ({fills[s]:8.0f} contracts)   settled fill P&L ${settled[s]:+9.2f}   net ${rew[s] + settled[s]:+9.2f}")
    sys.exit(0)

series = set(a.series.split(','))
state = {}          # ticker -> {'yes': (price, queue_ahead), 'no': (...), 'pos_yes': contracts long YES, 'cash': $, 'last_trade_ts': iso}
cycle = 0
while True:
    cycle += 1; t0 = time.time()
    progs, cur = [], ''
    for _ in range(80):
        d = get(f"{API}/incentive_programs?status=active&type=liquidity&limit=10000" + (f"&cursor={cur}" if cur else "")) or {}
        progs += d.get('incentive_programs', []); cur = d.get('next_cursor') or ''
        if not cur or not d.get('incentive_programs'): break
    now = dt.datetime.now(dt.timezone.utc)
    live = [p for p in progs if p['market_ticker'].split('-')[0] in series]
    def rate(p):
        s0 = dt.datetime.fromisoformat(p['start_date'].replace('Z', '+00:00')); s1 = dt.datetime.fromisoformat(p['end_date'].replace('Z', '+00:00'))
        return p['period_reward'] / max((s1 - s0).total_seconds(), 1)
    live = sorted(live, key=rate, reverse=True)[:a.max_markets]
    for p in live:
        tk = p['market_ticker']; ser = tk.split('-')[0]
        T = float(p['target_size_fp']); DF = p['discount_factor_bps'] / 1e4
        s0 = dt.datetime.fromisoformat(p['start_date'].replace('Z', '+00:00')); s1 = dt.datetime.fromisoformat(p['end_date'].replace('Z', '+00:00'))
        pool_per_s = p['period_reward'] / 1e4 / max((s1 - s0).total_seconds(), 1)
        ob = (get(f"{API}/markets/{tk}/orderbook") or {}).get('orderbook_fp', {})
        yb = [(round(float(x) * 100), float(q)) for x, q in ob.get('yes_dollars', [])]
        nb = [(round(float(x) * 100), float(q)) for x, q in ob.get('no_dollars', [])]
        if not yb or not nb:
            continue
        by, bn = max(x for x, _ in yb), max(x for x, _ in nb)
        spread = 100 - by - bn
        my_y = by + 1 if spread >= a.improve_at else by
        my_n = bn + 1 if spread >= a.improve_at else bn
        st = state.setdefault(tk, {'pos_yes': 0.0, 'cash': 0.0, 'series': ser, 'last': now.isoformat(), 'acc': now.isoformat()})
        st['end'] = s1.isoformat()
        st['yes'] = (my_y, sum(q for x, q in yb if x == my_y)); st['no'] = (my_n, sum(q for x, q in nb if x == my_n))
        qy, sy = lip_side_share(yb, T, DF, my_y, a.size); qn, sn = lip_side_share(nb, T, DF, my_n, a.size)
        el = (now - dt.datetime.fromisoformat(st['acc'])).total_seconds() or a.interval; st['acc'] = now.isoformat()
        el = min(el, (s1 - max(s0, now - dt.timedelta(seconds=el))).total_seconds()) if now <= s1 else 0
        if qy and qn and el > 0:
            log('accrue', series=ser, ticker=tk, usd=(sy + sn) / 2 * pool_per_s * el, share=(sy + sn) / 2, my_yes=my_y, my_no=my_n, spread=spread, secs=el)
        # simulated fills from public trades since last poll
        since = int(dt.datetime.fromisoformat(st['last']).timestamp())
        tr = (get(f"{API}/markets/trades?ticker={tk}&limit=1000&min_ts={since}") or {}).get('trades', [])
        st['last'] = now.isoformat()
        for x in tr:
            yp = round(float(x['yes_price_dollars']) * 100); q = float(x['count_fp'])
            if x['taker_side'] == 'no':          # taker sells YES → could hit our YES bid
                b, ahead = st['yes']
                if yp < b or (yp == b and q > ahead):
                    fq = min(a.size, q if yp < b else q - ahead); st['pos_yes'] += fq; st['cash'] -= fq * b / 100
                    log('fill', series=ser, ticker=tk, side='buy_yes', price=b, qty=fq)
            else:                                # taker buys YES = sells NO → could hit our NO bid
                b, ahead = st['no']
                if (100 - yp) < b or ((100 - yp) == b and q > ahead):
                    fq = min(a.size, q if (100 - yp) < b else q - ahead); st['pos_yes'] -= fq; st['cash'] -= fq * b / 100
                    log('fill', series=ser, ticker=tk, side='buy_no', price=b, qty=fq)
        time.sleep(0.1)
    # settle finished markets
    for tk, st in list(state.items()):
        if dt.datetime.now(dt.timezone.utc) < dt.datetime.fromisoformat(st['end']) + dt.timedelta(minutes=1):
            continue
        m = (get(f"{API}/markets/{tk}") or {}).get('market', {})
        if m.get('result') in ('yes', 'no'):
            y = 1.0 if m['result'] == 'yes' else 0.0
            long_y = max(st['pos_yes'], 0); long_n = max(-st['pos_yes'], 0)
            pnl = st['cash'] + long_y * y + long_n * (1 - y)
            log('settle', series=st['series'], ticker=tk, result=m['result'], pnl=pnl)
            del state[tk]
    print(dt.datetime.now(dt.timezone.utc).strftime('%H:%M:%S'), f'cycle {cycle}: {len(live)} live programs in {sorted(series)}; open markets {len(state)}', flush=True)
    if a.cycles and cycle >= a.cycles:
        break
    time.sleep(max(1, a.interval - (time.time() - t0)))
