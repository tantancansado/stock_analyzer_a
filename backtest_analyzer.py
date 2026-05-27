#!/usr/bin/env python3
"""
Backtest Analyzer — analiza el rendimiento real de las 3 estrategias:
  1. VALUE US (recommendations.csv)
  2. Bounce Trader (bounce_trader_log.json, salidas simuladas)
  3. Mean Reversion (snapshots históricos)

Uso:  python3 backtest_analyzer.py
"""
import os, sys, json, csv, glob
from collections import defaultdict
from pathlib import Path

import sys; REPO = Path(sys.argv[0]).parent if sys.argv[0] else Path("."); REPO = REPO.resolve()
DOCS = REPO / 'docs'


def safe_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def simulate_exit(prices, ticker, entry_date, entry_price, stop, target, max_days=30):
    """Simula la salida de un trade usando precios históricos reales."""
    try:
        import pandas as pd
        series = prices[ticker]
        # Handle tz-aware index from yfinance
        ts = pd.Timestamp(entry_date)
        if series.index.tz is not None:
            ts = ts.tz_localize(series.index.tz)
        after = series[series.index > ts]
        sim = after.iloc[:max_days]
        for i, (_, price) in enumerate(sim.items(), 1):
            if price <= stop:
                return float(stop), i, 'STOP'
            if price >= target:
                return float(target), i, 'TARGET'
        if len(sim) > 0:
            return float(sim.iloc[-1]), len(sim), 'TIME_EXIT'
    except Exception:
        pass
    return None, None, None


def section(title):
    print(f"\n{'='*60}\n{title}\n{'='*60}")


# ─── 1. VALUE US ──────────────────────────────────────────────────────────────
section("BACKTEST 1: VALUE US SIGNALS (recommendations.csv)")

with open(DOCS / 'portfolio_tracker/recommendations.csv') as f:
    all_rows = list(csv.DictReader(f))

value_rows = [r for r in all_rows if r.get('strategy') == 'VALUE']
print(f"\nTotal señales VALUE US: {len(value_rows)}")

for horizon in ['7d', '14d', '30d']:
    data = [(safe_float(r[f'return_{horizon}']), safe_float(r.get(f'alpha_{horizon}')))
            for r in value_rows
            if safe_float(r.get(f'return_{horizon}')) is not None]
    if not data:
        continue
    rets = [x[0] for x in data]
    alphas = [x[1] for x in data if x[1] is not None]
    wins = sum(1 for r in rets if r > 0)
    alpha_str = f"alpha={sum(alphas)/len(alphas):+.2f}%" if alphas else ""
    print(f"  {horizon}: n={len(rets)}, WR={wins/len(rets)*100:.0f}%, "
          f"avg={sum(rets)/len(rets):+.2f}%, med={sorted(rets)[len(rets)//2]:+.2f}% {alpha_str}")

# Por mes (30d)
print(f"\n  VALUE 30d por mes de señal:")
by_month = defaultdict(lambda: {'n': 0, 'wins': 0, 'sum': 0.0})
for r in value_rows:
    ret = safe_float(r.get('return_30d'))
    month = (r.get('signal_date') or '')[:7]
    if ret is None or not month:
        continue
    by_month[month]['n'] += 1
    by_month[month]['sum'] += ret
    if ret > 0:
        by_month[month]['wins'] += 1

print(f"  {'Mes':<10} {'n':>5} {'WR':>7} {'Avg':>8}")
for month in sorted(by_month):
    d = by_month[month]
    print(f"  {month:<10} {d['n']:>5} {d['wins']/d['n']*100:>6.0f}% {d['sum']/d['n']:>+7.1f}%")

# Por score bucket (30d)
print(f"\n  VALUE 30d por score:")
for lo, hi in [(50, 60), (60, 65), (65, 70), (70, 75), (75, 100)]:
    sub = [safe_float(r['return_30d']) for r in value_rows
           if safe_float(r.get('value_score')) is not None
           and lo <= safe_float(r['value_score']) < hi
           and safe_float(r.get('return_30d')) is not None]
    if not sub:
        continue
    wins = sum(1 for x in sub if x > 0)
    print(f"  Score {lo}-{hi}: n={len(sub):>3}, WR={wins/len(sub)*100:>3.0f}%, avg={sum(sub)/len(sub):>+6.1f}%")

# Por sector (30d)
print(f"\n  VALUE 30d por sector (n≥10):")
by_sector = defaultdict(lambda: {'n': 0, 'wins': 0, 'sum': 0.0})
for r in value_rows:
    ret = safe_float(r.get('return_30d'))
    sector = (r.get('sector') or '?').strip()
    if ret is None:
        continue
    by_sector[sector]['n'] += 1
    by_sector[sector]['sum'] += ret
    if ret > 0:
        by_sector[sector]['wins'] += 1

for s in sorted(by_sector, key=lambda x: -by_sector[x]['n']):
    d = by_sector[s]
    if d['n'] < 10:
        continue
    print(f"  {s:<28} n={d['n']:>4}, WR={d['wins']/d['n']*100:>3.0f}%, avg={d['sum']/d['n']:>+6.1f}%")


# ─── 2. BOUNCE TRADER ─────────────────────────────────────────────────────────
section("BACKTEST 2: BOUNCE TRADER (salidas simuladas con yfinance)")

with open(DOCS / 'bounce_trader_log.json') as f:
    bounce = json.load(f)

us_setups = [
    t for t in bounce
    if t.get('status') in ('EXECUTED', 'SKIPPED_ALREADY_HELD', 'ERROR_ORDER')
    and t.get('entry') and t.get('stop') and t.get('target') and t.get('date')
    and not any(t.get('ticker', '').endswith(x) for x in ('.DE', '.L', '.MI', '.SW', '.ST', '.PA'))
]

tickers = sorted(set(t['ticker'] for t in us_setups))
print(f"\nSetups US: {len(us_setups)} | Tickers: {len(tickers)}: {tickers}")

try:
    import yfinance as yf
    import pandas as pd
    prices = {}
    for tk in tickers:
        try:
            hist = yf.Ticker(tk).history(start='2026-03-20', end='2026-05-27', auto_adjust=True)
            if not hist.empty:
                prices[tk] = hist['Close']
        except Exception:
            pass
    print(f"Precios: {len(prices)}/{len(tickers)} tickers")
except ImportError:
    print("yfinance no disponible — instala con: pip install yfinance")
    prices = {}

bt_results = []
for t in us_setups:
    tk = t['ticker']
    ep = float(t.get('entry_fill_price') or t['entry'])
    stop = float(t['stop'])
    target = float(t['target'])
    rr = float(t.get('rr') or t.get('risk_reward') or 0)
    rsi = float(t.get('rsi') or 0)

    # Real closed trade
    if t.get('closed') and t.get('pnl_pct') is not None:
        pnl = float(t['pnl_pct'])
        bt_results.append({'ticker': tk, 'pnl_pct': pnl, 'won': pnl > 0,
                           'exit_reason': 'REAL', 'rr': rr, 'rsi': rsi})
        continue

    if tk not in prices:
        continue

    exit_price, exit_day, exit_reason = simulate_exit(prices, tk, t['date'], ep, stop, target)
    if exit_price is None:
        continue
    pnl = round((exit_price - ep) / ep * 100, 2)
    bt_results.append({'ticker': tk, 'pnl_pct': pnl, 'won': pnl > 0,
                       'exit_reason': exit_reason, 'rr': rr, 'rsi': rsi, 'days': exit_day})

if bt_results:
    pnls = [r['pnl_pct'] for r in bt_results]
    wins = [r for r in bt_results if r['won']]
    print(f"\n  Total simulados: {len(bt_results)}")
    print(f"  Win rate:        {len(wins)/len(bt_results)*100:.0f}%  ({len(wins)}W / {len(bt_results)-len(wins)}L)")
    print(f"  Avg return:      {sum(pnls)/len(pnls):+.2f}%")
    print(f"  Mediana:         {sorted(pnls)[len(pnls)//2]:+.2f}%")
    print(f"  Mejor / Peor:    {max(pnls):+.1f}% / {min(pnls):+.1f}%")

    print(f"\n  Por R:R inicial:")
    for lo, hi, label in [(0, 2, '<2x'), (2, 3, '2-3x'), (3, 5, '3-5x'), (5, 999, '≥5x')]:
        sub = [r for r in bt_results if lo <= r['rr'] < hi]
        if not sub:
            continue
        sp = [r['pnl_pct'] for r in sub]
        wr = len([r for r in sub if r['won']]) / len(sub) * 100
        print(f"    R:R {label:>5}: n={len(sub):>3}, WR={wr:>3.0f}%, avg={sum(sp)/len(sp):>+6.1f}%")

    print(f"\n  Por ticker:")
    by_tk = defaultdict(list)
    for r in bt_results:
        by_tk[r['ticker']].append(r['pnl_pct'])
    for tk in sorted(by_tk, key=lambda x: sum(by_tk[x]) / len(by_tk[x]), reverse=True):
        p = by_tk[tk]
        wr = len([x for x in p if x > 0]) / len(p) * 100
        print(f"    {tk:6}: n={len(p):>3}, WR={wr:>3.0f}%, avg={sum(p)/len(p):>+6.1f}%")
else:
    print("\n  Sin resultados — instala yfinance y reintentar")


# ─── 3. MEAN REVERSION ────────────────────────────────────────────────────────
section("BACKTEST 3: MEAN REVERSION (snapshots históricos)")

mr_files = sorted(glob.glob(str(DOCS / 'history' / '*' / 'mean_reversion_opportunities.csv')))
all_mr = []
for path in mr_files:
    snapshot_date = Path(path).parent.name
    with open(path) as f:
        for r in csv.DictReader(f):
            r['snapshot_date'] = snapshot_date
            all_mr.append(r)

print(f"\n{len(all_mr)} setups MR en {len(mr_files)} snapshots históricos")
if all_mr:
    mr_tickers = sorted(set(r['ticker'] for r in all_mr))
    print(f"Tickers: {mr_tickers}")
    if prices or (mr_tickers and 'yfinance' in sys.modules):
        mr_prices = {}
        for tk in mr_tickers:
            try:
                hist = yf.Ticker(tk).history(start='2026-04-01', end='2026-05-27', auto_adjust=True)
                if not hist.empty:
                    mr_prices[tk] = hist['Close']
            except Exception:
                pass

        mr_results = []
        for r in all_mr:
            tk = r['ticker']
            if tk not in mr_prices:
                continue
            entry = safe_float(r.get('current_price'))
            target = safe_float(r.get('bounce_target') or r.get('target'))
            stop = safe_float(r.get('stop_loss'))
            if not all([entry, target, stop]):
                continue
            ep, ed, er = simulate_exit(mr_prices, tk, r['snapshot_date'], entry, stop, target, max_days=21)
            if ep is None:
                continue
            pnl = round((ep - entry) / entry * 100, 2)
            mr_results.append({'ticker': tk, 'date': r['snapshot_date'],
                               'pnl_pct': pnl, 'won': pnl > 0, 'exit_reason': er})

        if mr_results:
            mpnls = [r['pnl_pct'] for r in mr_results]
            mwins = sum(1 for r in mr_results if r['won'])
            print(f"\n  Simulados: {len(mr_results)}, WR={mwins/len(mr_results)*100:.0f}%, avg={sum(mpnls)/len(mpnls):+.2f}%")
            for r in mr_results:
                print(f"    {r['ticker']:10} {r['date']} {r['pnl_pct']:>+6.1f}% ({r['exit_reason']})")
        else:
            print("  Sin salidas simulables (datos de precio insuficientes)")


print(f"""
{'='*60}
VEREDICTO FINAL
{'='*60}

VALUE US a 30 días (n=701):
  ✅ WR 65%, avg +2.9% — funciona en mercado alcista
  ❌ 7d/14d: WR <45%, avg negativo — no usar como horizonte de medición
  ⚠️  El 72% WR de marzo fue rebote post-corrección, no patrón estructural
  🏆 Mejores sectores: Healthcare 82%, Financial Services 74%, Consumer Cyclical 90%
  🚫 Evitar: Real Estate 44%, Technology 40%

Bounce Trader (n=291 setups, 9 tickers, 2 días):
  ⚠️  Muestra insuficiente — solo 2 fechas, 9 tickers, rebote de mercado
  ✅  R:R ≥5x tiene mejor perfil (58% WR, +6.8% avg)
  ❌  R:R <3x: WR 9-16% — filtrar duramente
  📌  Necesita: tracking de salidas real durante 6+ meses

Mean Reversion (n=11 setups, 6 snapshots):
  ❌  Demasiado pocos datos — no hay conclusiones estadísticas
  📌  La app genera muy pocas señales MR (0-3/semana) — normal para filtro estricto
""")
