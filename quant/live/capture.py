"""Continuous prediction-market data capture for the home PC / Pi (see ../PLAYBOOK.md).
Every INTERVAL seconds, append snapshots to dated JSONL files under OUT:
  * Polymarket: top-N active markets by 24h volume, with best bid/ask (gamma) and the merged CLOB book top 5 levels
  * Kalshi: open KXBTCD + KXHIGH* events with yes bid/ask per market (batch, public API)
  * Deribit: BTC index + option book summary (for Q3/T3 digital comparisons)
  * Kalshi Liquidity Incentive Programs (hourly; notes/LIP.md)
No API keys, read-only. Run:  python3 capture.py --out ~/pmdata --interval 300
Lessons baked in: curl with hard timeouts (urllib can hang); back off on 429; timestamps recorded at capture time in UTC."""
import argparse, json, os, subprocess, time, datetime as dt
p = argparse.ArgumentParser(); p.add_argument('--out', default=os.path.expanduser('~/pmdata')); p.add_argument('--interval', type=int, default=300)
p.add_argument('--top', type=int, default=200); p.add_argument('--deribit-every', type=int, default=12, help='cycles between Deribit option snapshots (~400KB each)'); a = p.parse_args(); os.makedirs(a.out, exist_ok=True)
def get(u, tries=5):
    for i in range(tries):
        r = subprocess.run(['curl', '-s', '--max-time', '30', '-w', '\n%{http_code}', '-A', 'Mozilla/5.0', u], capture_output=True, text=True)
        body, _, code = r.stdout.rpartition('\n')
        if code == '200':
            try: return json.loads(body)
            except Exception: return None
        time.sleep(min(2 ** i, 30))
def dump(name, obj):
    day = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d')
    with open(f"{a.out}/{name}_{day}.jsonl", 'a') as f: f.write(json.dumps({'ts': time.time(), 'data': obj}) + '\n')
cycle = 0
while True:
    t0 = time.time(); cycle += 1
    try:
        ms = []
        for off in range(0, a.top, 100):
            ms += get(f"https://gamma-api.polymarket.com/markets?closed=false&limit=100&offset={off}&order=volume24hr&ascending=false") or []
        dump('poly_markets', [{k: m.get(k) for k in ('id', 'conditionId', 'question', 'clobTokenIds', 'bestBid', 'bestAsk', 'lastTradePrice', 'volume24hr', 'endDate', 'negRisk')} for m in ms])
        books = {}
        for m in ms[:50]:
            toks = json.loads(m.get('clobTokenIds') or '[]')
            if len(toks) == 2:
                b, n = get(f"https://clob.polymarket.com/book?token_id={toks[0]}"), get(f"https://clob.polymarket.com/book?token_id={toks[1]}")
                if b and n: books[m['conditionId']] = {'yes': {'bids': b.get('bids', [])[-5:], 'asks': b.get('asks', [])[-5:]}, 'no': {'bids': n.get('bids', [])[-5:], 'asks': n.get('asks', [])[-5:]}}
        dump('poly_books', books)
        for series in ('KXBTCD', 'KXHIGHNY', 'KXHIGHCHI', 'KXHIGHMIA', 'KXHIGHLAX', 'KXHIGHAUS', 'KXHIGHDEN'):
            d = get(f"https://api.elections.kalshi.com/trade-api/v2/events?series_ticker={series}&status=open&with_nested_markets=true&limit=50") or {}
            dump(f'kalshi_{series}', [{'event': e['event_ticker'], 'markets': [{k: m.get(k) for k in ('ticker', 'floor_strike', 'cap_strike', 'yes_bid_dollars', 'yes_ask_dollars', 'close_time', 'volume')} for m in e.get('markets', [])]} for e in d.get('events', [])])
        if cycle % a.deribit_every == 1 or a.deribit_every == 1:
            lip, cur = [], ''
            for _ in range(80):
                d = get('https://api.elections.kalshi.com/trade-api/v2/incentive_programs?status=active&limit=100' + (f'&cursor={cur}' if cur else '')) or {}
                lip += d.get('incentive_programs', []); cur = d.get('next_cursor') or ''
                if not cur: break
            dump('kalshi_incentive_programs', lip)
        if cycle % a.deribit_every == 1 or a.deribit_every == 1: dump('deribit_btc', {'index': (get("https://www.deribit.com/api/v2/public/get_index_price?index_name=btc_usd") or {}).get('result'),
                              'options': (get("https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency=BTC&kind=option") or {}).get('result')})
    except Exception as e:
        print(dt.datetime.now(dt.timezone.utc), 'error', e, flush=True)
    time.sleep(max(5, a.interval - (time.time() - t0)))
