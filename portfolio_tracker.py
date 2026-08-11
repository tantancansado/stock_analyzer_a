#!/usr/bin/env python3
"""
PORTFOLIO TRACKER — Track recommendations and measure real performance
Records each VALUE/MOMENTUM recommendation with price at signal date.
Checks 7d, 14d, 30d returns to calculate real win rate.
Learns which signals actually work.
"""
import pandas as pd
import numpy as np
import yfinance as yf
from pathlib import Path
from datetime import datetime, timedelta
import json
import time
import argparse
from value_bands import UPSIDE_MIN, UPSIDE_GOLDEN_MAX, UPSIDE_HARD_REJECT


TRACKER_DIR = Path('docs/portfolio_tracker')

# Señales vencidas mínimas para dar por bueno el periodo limpio en un horizonte.
# Por debajo de esto el win rate es ruido y sale peor que usar el histórico.
MIN_MUESTRA_LIMPIA = 30


def _mejor_base(horizonte: str, limpio: pd.DataFrame, historico: pd.DataFrame,
                win_stats) -> dict:
    """Estadísticas de un horizonte, prefiriendo SIEMPRE el periodo limpio.

    El histórico (golden_zone_hist) incluye el tramo contaminado y describe otra
    población: a 30d daba 76,9% de acierto y +5,05% cuando las señales que el
    sistema emite hoy van al 21,0% y −4,68%. Se eligió como base porque cuando se
    montó el tracker el periodo limpio aún no tenía señales vencidas a 30d; ya
    tiene 100, así que la sustitución dejó de estar justificada y solo quedaba el
    titular inflado. El respaldo está en `stats_basis`, pero nadie lee la letra
    pequeña de un 76,9%.

    Se cae al histórico únicamente mientras el limpio no llegue a
    MIN_MUESTRA_LIMPIA, y en ese caso `basis` lo dice.
    """
    ret, win = f'return_{horizonte}', f'win_{horizonte}'
    n_limpio = int(limpio[ret].notna().sum()) if (not limpio.empty and ret in limpio) else 0
    if n_limpio >= MIN_MUESTRA_LIMPIA:
        return {**win_stats(ret, win, limpio), 'basis': 'clean_period'}
    if historico.empty:
        return {}
    return {**win_stats(ret, win, historico), 'basis': 'golden_zone_hist',
            'nota': (f'periodo limpio aún sin muestra a {horizonte} '
                     f'({n_limpio} de {MIN_MUESTRA_LIMPIA} necesarias) — '
                     f'este dato viene del histórico, que incluye el tramo '
                     f'contaminado y describe otra población')}


def _alpha_stats(df: pd.DataFrame, alpha_col: str, return_col: str) -> dict:
    """Alpha = señal return - benchmark return en el mismo período."""
    if alpha_col not in df.columns or return_col not in df.columns:
        return {'count': 0, 'avg_alpha': None, 'positive_alpha_rate': None,
                'avg_signal_return': None, 'avg_benchmark_return': None}
    valid = df[df[alpha_col].notna() & (df[return_col] > -95) & (df[return_col] < 500)]
    if len(valid) < 3:
        return {'count': 0, 'avg_alpha': None, 'positive_alpha_rate': None,
                'avg_signal_return': None, 'avg_benchmark_return': None}
    bench_col = alpha_col.replace('alpha_', 'benchmark_return_')
    return {
        'count': int(len(valid)),
        'avg_alpha': round(float(valid[alpha_col].mean()), 2),
        'avg_signal_return': round(float(valid[return_col].mean()), 2),
        'avg_benchmark_return': round(float(valid[bench_col].mean()), 2) if bench_col in valid.columns else None,
        'positive_alpha_rate': round(float((valid[alpha_col] > 0).mean() * 100), 1),
        'best_alpha': round(float(valid[alpha_col].max()), 2),
        'worst_alpha': round(float(valid[alpha_col].min()), 2),
    }
RECOMMENDATIONS_FILE = TRACKER_DIR / 'recommendations.csv'
PERFORMANCE_FILE = TRACKER_DIR / 'performance.csv'
SUMMARY_FILE = TRACKER_DIR / 'summary.json'
CALIBRATION_FILE = TRACKER_DIR / 'calibration.json'


class PortfolioTracker:
    """Track recommendations and measure real-world results"""

    def __init__(self):
        TRACKER_DIR.mkdir(parents=True, exist_ok=True)
        self.recommendations = self._load_recommendations()

    def _load_recommendations(self) -> pd.DataFrame:
        """Load existing recommendations history"""
        if RECOMMENDATIONS_FILE.exists():
            return pd.read_csv(RECOMMENDATIONS_FILE, parse_dates=['signal_date'])
        return pd.DataFrame(columns=[
            'ticker', 'company_name', 'strategy', 'signal_date', 'signal_price',
            'value_score', 'momentum_score', 'fcf_yield_pct', 'risk_reward_ratio',
            'analyst_upside_pct', 'short_percent_float', 'sector', 'market_regime',
            'entry_readiness', 'entry_readiness_reason',
            'return_7d', 'return_14d', 'return_30d', 'return_90d', 'return_180d', 'return_365d',
            'price_7d', 'price_14d', 'price_30d', 'price_90d', 'price_180d', 'price_365d',
            'win_7d', 'win_14d', 'win_30d', 'win_90d', 'win_180d', 'win_365d',
            'max_drawdown_30d', 'status',
            'stop_loss', 'target_price', 'exit_price', 'exit_day', 'exit_reason',
            'benchmark_return_7d', 'benchmark_return_14d', 'benchmark_return_30d',
            'benchmark_return_90d', 'benchmark_return_180d', 'benchmark_return_365d',
            'alpha_7d', 'alpha_14d', 'alpha_30d', 'alpha_90d', 'alpha_180d', 'alpha_365d',
        ])

    def record_signals(self):
        """Record today's VALUE + MOMENTUM recommendations"""
        today = pd.Timestamp.now().normalize()

        # Check if already recorded today
        if not self.recommendations.empty:
            existing_today = self.recommendations[
                self.recommendations['signal_date'] == today
            ]
            if len(existing_today) > 0:
                print(f"  Already recorded {len(existing_today)} signals for {today.date()}")
                return

        signals_recorded = 0

        # Build cooldown set: tickers signalled in the last 21 days — skip re-entry
        # Prevents same ticker appearing 15+ consecutive days, which inflates win rate stats
        COOLDOWN_DAYS = 21
        cooldown_cutoff = today - pd.Timedelta(days=COOLDOWN_DAYS)
        if not self.recommendations.empty:
            recent = self.recommendations[self.recommendations['signal_date'] >= cooldown_cutoff]
            cooldown_tickers = set(recent['ticker'].str.upper().str.strip())
        else:
            cooldown_tickers = set()
        if cooldown_tickers:
            print(f"  Cooldown active for {len(cooldown_tickers)} tickers (signalled in last {COOLDOWN_DAYS}d)")

        # Record VALUE opportunities
        # Filtros calibrados con 767 señales reales (feb-may 2026):
        #   score 50-65: WR 62-67%, avg +2-3% — score >65 es peor (34% WR, -1.7%)
        #   Sectores excluidos: Technology (WR 25%, -3.6%), Real Estate (WR 44%, -3.9%)
        #   Solo CONFIRMED_UPTREND: WR 56% vs 44% en CORRECTION
        #   Upside: banda dorada de value_bands.py, fuente única (ver abajo por
        #   qué se quitó el filtro de R:R que la pisaba)
        _EXCLUDED_SECTORS_VALUE = {'Technology', 'Real Estate'}
        value_path = Path('docs/value_opportunities.csv')
        if value_path.exists():
            vdf = pd.read_csv(value_path)
            if not vdf.empty:
                _score = pd.to_numeric(vdf.get('value_score', pd.Series(dtype=float)), errors='coerce')
                vdf = vdf[_score.between(50.0, 65.0)]
                # OJO: `risk_reward_ratio` NO es un factor independiente —
                # super_score_integrator.py:1264 lo calcula como
                # `analyst_upside_pct / 8.0` (el stop estándar del 8%). Medido
                # sobre 1479 señales reales: corr(RR, upside) = +1.0000 exacto.
                # El filtro `_rr.between(2.0, 3.5)` que había aquí era, por
                # tanto, una banda de upside [16, 28] hardcodeada inline y
                # disfrazada de otra variable — justo lo que CLAUDE.md prohíbe
                # ("las bandas viven en value_bands.py, NUNCA inline").
                #
                # Y pisaba a la banda declarada: las 12 últimas señales US van
                # todas de 16,6 a 26,5 de upside. Nada por debajo de 16 llegaba
                # a registrarse pese a estar en zona dorada, y WMT (26,5),
                # OTIS (26,3) y SPGI (25,3) entraron estando FUERA de ella.
                # En el periodo limpio el alfa decae de forma monótona según
                # sube el upside, así que se estaba tirando lo mejor de la banda
                # y quedándose con lo peor. Fuente única, sin doble conteo:
                if 'analyst_upside_pct' in vdf.columns:
                    _up = pd.to_numeric(vdf['analyst_upside_pct'], errors='coerce')
                    vdf = vdf[(_up >= UPSIDE_MIN) & (_up < UPSIDE_GOLDEN_MAX)]
                if 'sector' in vdf.columns:
                    vdf = vdf[~vdf['sector'].isin(_EXCLUDED_SECTORS_VALUE)]
                if 'market_regime' in vdf.columns:
                    vdf = vdf[vdf['market_regime'] == 'CONFIRMED_UPTREND']
                # No se recomienda un cuchillo cayendo. `entry_readiness` es
                # ESPERAR cuando el ticker está bajo una MA200 descendente, y
                # entry_timing_backtest.py lo midió reconstruyendo el timing
                # histórico de cada señal con precios ANTERIORES a su fecha:
                #     30d limpio  ESPERAR 10,3% acierto vs 32,5% el resto
                #     90d limpio  ESPERAR 20,8%          vs 54,5%
                #     90d todo    ESPERAR 48,4%          vs 74,8%
                # El alfa de ESPERAR es ~-10% en los tres cortes. Se sostiene en
                # ambos periodos y ambos horizontes, que es el test que separa
                # una señal real del ruido. Y eran el 62% de lo que se
                # registraba: es la mayor fuga de rendimiento medida hasta ahora.
                # No se exige ENTRADA porque VIGILAR rinde igual o mejor
                # (76,0% vs 70,2% en la muestra grande) y exigirla dejaría el
                # sistema en 0 señales — el screen encuentra los valores
                # mientras caen, no cuando ya han confirmado.
                if 'entry_readiness' in vdf.columns:
                    vdf = vdf[vdf['entry_readiness'] != 'ESPERAR']
                # Suelo de caída: lo que ya ha caído demasiado sigue cayendo.
                # Reconstruidas las ~150 columnas de las 767 señales US con
                # retorno a 90d (desde los snapshots diarios de git), la
                # distancia al máximo de 52 semanas es el factor con MÁS señal
                # de todos, y del mismo signo en ambos periodos (corr con alpha
                # +0,201 contaminado / +0,478 limpio). Por tramos, en limpio:
                #     caída >40%   n=38   7,9% acierto   alpha -12,46
                #     caída 10-20% n= 9    100% acierto   alpha  -1,51
                # Barrido de umbrales: el suelo en -30% es donde el alpha de lo
                # que queda toca fondo (-2,81 vs -5,32 con suelo en -40), y lo
                # que se descarta rinde -11,83 con 14,8% de acierto.
                # No es el upside disfrazado: corr(distancia, upside) = -0,44, y
                # controlando por banda dorada la señal sigue viva (+0,143).
                # OJO, no es monótono: pegado al máximo (0-10%) también es malo
                # (alpha -5,35, 20,2% acierto). La zona buena es 10-30% de
                # caída — por eso esto es un SUELO, no un "cuanto más cerca del
                # máximo mejor".
                _CAIDA_MAX_PCT = -30.0
                if 'proximity_to_52w_high' in vdf.columns:
                    _prox = pd.to_numeric(vdf['proximity_to_52w_high'], errors='coerce')
                    vdf = vdf[_prox.isna() | (_prox >= _CAIDA_MAX_PCT)]
                vdf = vdf.head(5)  # max 5 picks/día — calidad > cantidad
                for _, row in vdf.iterrows():
                    ticker = str(row['ticker']).upper().strip()
                    if ticker in cooldown_tickers:
                        continue
                    price = row.get('current_price', 0)
                    if not price or pd.isna(price) or float(price) <= 0:
                        continue
                    rec = {
                        'ticker': row['ticker'],
                        'company_name': str(row.get('company_name') or row['ticker']),
                        'strategy': 'VALUE',
                        'signal_date': today,
                        'signal_price': float(price),
                        'value_score': row.get('value_score'),
                        'momentum_score': None,
                        'stop_loss': float(price) * 0.92 if price else None,  # 8% standard stop
                        'target_price': float(row.get('target_price_analyst') or (float(price) * (1 + float(row.get('analyst_upside_pct', 0) or 0) / 100))),
                        'fcf_yield_pct': row.get('fcf_yield_pct'),
                        'risk_reward_ratio': row.get('risk_reward_ratio'),
                        'analyst_upside_pct': row.get('analyst_upside_pct'),
                        # Capturado desde 11-ago-2026 para poder decidir CON NUESTRAS
                        # señales si el interés corto predice algo. Hoy no se puede:
                        # solo hay 31 snapshots de docs/history y dan n=20 a 7 días.
                        # El estudio transversal sobre el universo (6265 obs) no
                        # encuentra efecto — si acaso el contrario — pero cubre 6
                        # semanas de mercado alcista y no basta para fijar un umbral.
                        'short_percent_float': row.get('short_percent_float'),
                        'sector': row.get('sector', 'N/A'),
                        'market_regime': row.get('market_regime', 'N/A'),
                        # Capturado desde 6-ago-2026: hace falta para responder la pregunta
                        # pendiente del plan de recalibración VALUE — si comprar solo en
                        # ENTRADA (vs VIGILAR/ESPERAR) mejora el alpha de entrada frente a
                        # comprar el día del screen. Sin este dato en el momento de la señal
                        # no se puede reconstruir después (el timing técnico cambia a diario).
                        'entry_readiness': row.get('entry_readiness'),
                        'entry_readiness_reason': row.get('entry_readiness_reason'),
                        'return_7d': None, 'return_14d': None, 'return_30d': None,
                        'price_7d': None, 'price_14d': None, 'price_30d': None,
                        'win_7d': None, 'win_14d': None, 'win_30d': None,
                        'max_drawdown_30d': None,
                        'status': 'ACTIVE'
                    }
                    self.recommendations = pd.concat(
                        [self.recommendations, pd.DataFrame([rec])],
                        ignore_index=True
                    )
                    cooldown_tickers.add(ticker)
                    signals_recorded += 1
                print(f"  Recorded {signals_recorded} VALUE signals")

        # Record MOMENTUM opportunities
        mom_recorded = 0
        momentum_path = Path('docs/momentum_opportunities_filtered.csv')
        if momentum_path.exists():
            mdf = pd.read_csv(momentum_path)
            if not mdf.empty:
                for _, row in mdf.iterrows():
                    ticker = str(row['ticker']).upper().strip()
                    if ticker in cooldown_tickers:
                        continue
                    price = row.get('current_price', 0)
                    if not price or pd.isna(price) or float(price) <= 0:
                        continue
                    rec = {
                        'ticker': row['ticker'],
                        'company_name': str(row.get('company_name') or row['ticker']),
                        'strategy': 'MOMENTUM',
                        'signal_date': today,
                        'signal_price': float(price),
                        'value_score': None,
                        'momentum_score': row.get('momentum_score'),
                        'fcf_yield_pct': row.get('fcf_yield_pct'),
                        'risk_reward_ratio': row.get('risk_reward_ratio'),
                        'analyst_upside_pct': row.get('analyst_upside_pct'),
                        # Capturado desde 11-ago-2026 para poder decidir CON NUESTRAS
                        # señales si el interés corto predice algo. Hoy no se puede:
                        # solo hay 31 snapshots de docs/history y dan n=20 a 7 días.
                        # El estudio transversal sobre el universo (6265 obs) no
                        # encuentra efecto — si acaso el contrario — pero cubre 6
                        # semanas de mercado alcista y no basta para fijar un umbral.
                        'short_percent_float': row.get('short_percent_float'),
                        'sector': row.get('sector', 'N/A'),
                        'market_regime': row.get('market_regime', 'N/A'),
                        'entry_readiness': row.get('entry_readiness'),
                        'entry_readiness_reason': row.get('entry_readiness_reason'),
                        'return_7d': None, 'return_14d': None, 'return_30d': None,
                        'price_7d': None, 'price_14d': None, 'price_30d': None,
                        'win_7d': None, 'win_14d': None, 'win_30d': None,
                        'max_drawdown_30d': None,
                        'status': 'ACTIVE'
                    }
                    self.recommendations = pd.concat(
                        [self.recommendations, pd.DataFrame([rec])],
                        ignore_index=True
                    )
                    cooldown_tickers.add(ticker)
                    mom_recorded += 1
                print(f"  Recorded {mom_recorded} MOMENTUM signals")

        # EU_VALUE pausado: WR 16%, avg -5.9%, alpha -6.6% en 738 señales (feb-may 2026)
        # El modelo europeo no tiene edge real — requiere revisión de scoring antes de reactivar
        # Para reactivar: cambiar EU_VALUE_PAUSED = False
        EU_VALUE_PAUSED = True
        if not EU_VALUE_PAUSED:
            pass  # reactivar aquí cuando el scoring EU esté calibrado
        print("  EU_VALUE pausado (WR 16% en backtest — sin edge)")

        total = signals_recorded + mom_recorded
        print(f"  Total new signals recorded: {total}")
        self._save_recommendations()

    def update_performance(self):
        """Check actual returns for past recommendations"""
        if self.recommendations.empty:
            print("  No recommendations to update")
            return

        today = pd.Timestamp.now().normalize()
        updated = 0

        # ── Download benchmarks once for the full date range ──────────────────
        # SPY = benchmark for VALUE US / MOMENTUM
        # VGK = benchmark for EU_VALUE (Vanguard FTSE Europe)
        bench_hists: dict[str, pd.DataFrame] = {}
        # Además de las ACTIVE, backfillea horizontes largos (90/180d) en las
        # COMPLETED: una tesis value se juzga a trimestres, no a 30 días —
        # medir solo 7/14/30d es puntuar value picks con regla de trader.
        # SOLO filas con edad suficiente para llenar el checkpoint que les
        # falta — sin este gate se re-escaneaban ~190 tickers/día esperando
        # su 180d y el job core-scoring reventó su timeout de 60 min
        # (run 28682078892, cancelado a los 60:00 exactos el 3-jul).
        _recs = self.recommendations
        _age_days = (today - pd.to_datetime(_recs['signal_date'])).dt.days
        _needs_long = pd.Series(False, index=_recs.index)
        for _col, _min_age in (('return_90d', 90), ('return_180d', 180), ('return_365d', 365)):
            _missing = (pd.to_numeric(_recs[_col], errors='coerce').isna()
                        if _col in _recs.columns
                        else pd.Series(True, index=_recs.index))
            _needs_long |= _missing & (_age_days >= _min_age)
        active_all = _recs[(_recs['status'] == 'ACTIVE') | _needs_long].copy()
        if not active_all.empty:
            earliest = pd.Timestamp(active_all['signal_date'].min()) - timedelta(days=1)
            bench_end = (today + timedelta(days=1)).strftime('%Y-%m-%d')
            bench_start = earliest.strftime('%Y-%m-%d')
            for bench in ['SPY', 'VGK']:
                try:
                    h = yf.Ticker(bench).history(start=bench_start, end=bench_end)
                    if not h.empty:
                        if h.index.tz is not None:
                            h.index = h.index.tz_localize(None)
                        bench_hists[bench] = h
                except Exception as e:
                    print(f"    Warning: could not download {bench}: {e}")
        # ──────────────────────────────────────────────────────────────────────

        # Group by ticker to batch yfinance calls
        active = active_all.copy()
        tickers_to_check = active['ticker'].unique()

        print(f"  Checking {len(tickers_to_check)} tickers for performance updates...")

        for ticker in tickers_to_check:
            ticker_recs = active_all[active_all['ticker'] == ticker]

            # Fetch price history
            try:
                stock = yf.Ticker(ticker)
                earliest_date = ticker_recs['signal_date'].min()
                start_date = pd.Timestamp(earliest_date) - timedelta(days=1)
                hist = stock.history(
                    start=start_date.strftime('%Y-%m-%d'),
                    end=(today + timedelta(days=1)).strftime('%Y-%m-%d')
                )
                if hist.empty:
                    continue

                # yfinance returns tz-aware index; strip tz to allow naive comparisons
                if hist.index.tz is not None:
                    hist.index = hist.index.tz_localize(None)

                for idx, rec in ticker_recs.iterrows():
                    signal_date = pd.Timestamp(rec['signal_date'])
                    signal_price = float(rec['signal_price'])
                    days_since = (today - signal_date).days

                    # Get prices at 7d..365d checkpoints (90/180/365d = horizonte
                    # real de una tesis value; 7-30d mide ruido/momentum)
                    for period, col_return, col_price, col_win in [
                        (7, 'return_7d', 'price_7d', 'win_7d'),
                        (14, 'return_14d', 'price_14d', 'win_14d'),
                        (30, 'return_30d', 'price_30d', 'win_30d'),
                        (90, 'return_90d', 'price_90d', 'win_90d'),
                        (180, 'return_180d', 'price_180d', 'win_180d'),
                        (365, 'return_365d', 'price_365d', 'win_365d'),
                    ]:
                        if days_since >= period and pd.isna(rec.get(col_return)):
                            check_date = signal_date + timedelta(days=period)
                            # Find closest trading day
                            mask = hist.index >= check_date
                            if mask.any():
                                check_price = float(hist.loc[mask, 'Close'].iloc[0])
                                # LSE GBp/GBP sanity: if prices differ by ~100x, correct
                                if signal_price > 0 and check_price > 0:
                                    ratio = check_price / signal_price
                                    if ratio < 0.02:   # signal in GBp, fetch in GBP
                                        check_price = check_price * 100
                                    elif ratio > 50:   # signal in GBP, fetch in GBp
                                        check_price = check_price / 100
                                pct_return = ((check_price - signal_price) / signal_price) * 100
                                self.recommendations.at[idx, col_return] = round(pct_return, 2)
                                self.recommendations.at[idx, col_price] = round(check_price, 2)
                                self.recommendations.at[idx, col_win] = pct_return > 0
                                updated += 1

                                # ── Alpha vs benchmark ────────────────────────
                                strategy = rec.get('strategy', 'VALUE')
                                bench_key = 'VGK' if strategy == 'EU_VALUE' else 'SPY'
                                bench_col_ret  = f'benchmark_return_{period}d'
                                bench_col_alpha = f'alpha_{period}d'
                                if bench_key in bench_hists and pd.isna(rec.get(bench_col_ret)):
                                    bh = bench_hists[bench_key]
                                    b_signal_mask = bh.index >= signal_date
                                    b_check_mask  = bh.index >= check_date
                                    if b_signal_mask.any() and b_check_mask.any():
                                        b_signal_price = float(bh.loc[b_signal_mask, 'Close'].iloc[0])
                                        b_check_price  = float(bh.loc[b_check_mask,  'Close'].iloc[0])
                                        if b_signal_price > 0:
                                            bench_ret = ((b_check_price - b_signal_price) / b_signal_price) * 100
                                            alpha     = pct_return - bench_ret
                                            self.recommendations.at[idx, bench_col_ret]   = round(bench_ret, 2)
                                            self.recommendations.at[idx, bench_col_alpha] = round(alpha, 2)
                                # ─────────────────────────────────────────────

                    # Max drawdown over 30 days
                    if days_since >= 7 and pd.isna(rec.get('max_drawdown_30d')):
                        window_end = min(signal_date + timedelta(days=30), today)
                        window = hist[(hist.index >= signal_date) & (hist.index <= window_end)]
                        if not window.empty:
                            min_price = float(window['Low'].min())
                            drawdown = ((min_price - signal_price) / signal_price) * 100
                            self.recommendations.at[idx, 'max_drawdown_30d'] = round(drawdown, 2)

                    # Simulate stop/target exit (daily check for active signals)
                    stop = rec.get('stop_loss')
                    target = rec.get('target_price')
                    if (pd.isna(rec.get('exit_reason')) and
                            stop and target and not pd.isna(stop) and not pd.isna(target)):
                        stop_f = float(stop)
                        target_f = float(target)
                        sim_end = min(signal_date + timedelta(days=45), today)
                        sim_window = hist[(hist.index > signal_date) & (hist.index <= sim_end)]
                        for sim_day, (sim_dt, sim_row) in enumerate(sim_window.iterrows(), 1):
                            if sim_row['Low'] <= stop_f:
                                self.recommendations.at[idx, 'exit_price'] = round(stop_f, 2)
                                self.recommendations.at[idx, 'exit_day'] = sim_day
                                self.recommendations.at[idx, 'exit_reason'] = 'STOP'
                                break
                            elif sim_row['High'] >= target_f:
                                self.recommendations.at[idx, 'exit_price'] = round(target_f, 2)
                                self.recommendations.at[idx, 'exit_day'] = sim_day
                                self.recommendations.at[idx, 'exit_reason'] = 'TARGET'
                                break
                        else:
                            if sim_day >= 30:
                                last_p = float(sim_window['Close'].iloc[-1]) if not sim_window.empty else signal_price
                                self.recommendations.at[idx, 'exit_price'] = round(last_p, 2)
                                self.recommendations.at[idx, 'exit_day'] = sim_day
                                self.recommendations.at[idx, 'exit_reason'] = 'TIME_30D'

                    # Mark completed if 30d has passed
                    if days_since >= 30 and not pd.isna(self.recommendations.at[idx, 'return_30d']):
                        self.recommendations.at[idx, 'status'] = 'COMPLETED'

                time.sleep(1.0)  # Rate limiting

            except Exception as e:
                print(f"    Error checking {ticker}: {e}")
                continue

        print(f"  Updated {updated} performance checkpoints")
        self._save_recommendations()

    def generate_summary(self) -> dict:
        """Generate performance summary statistics"""
        if self.recommendations.empty:
            summary = {
                'total_signals': 0,
                'message': 'No recommendations tracked yet',
                'generated_at': datetime.now().isoformat()
            }
            self._save_summary(summary)
            return summary

        df = self.recommendations

        # Core VALUE strategies only — exclude MOMENTUM/Bounce/Entry (different logic, distorts stats)
        VALUE_STRATEGIES = {'VALUE', 'EU_VALUE'}
        value_core_all = df[df['strategy'].isin(VALUE_STRATEGIES)]

        # ── Clean data cut: ignore contaminated signals before 2026-04-08 ──────
        # Before Apr-8: EU recorded full universe (50/day), US recorded unfiltered (30-80/day).
        # From Apr-8: proper 4-6 filtered signals/day. Stats use clean data only.
        CLEAN_FROM = pd.Timestamp('2026-04-08')
        value_core = value_core_all[value_core_all['signal_date'] >= CLEAN_FROM].copy()

        # For 30d completed stats, clean signals don't have 30d yet (too recent).
        # Golden zone retroactiva: score>=60 y la banda dorada de value_bands,
        # para que el histórico mida la MISMA población que se emite hoy.
        #
        # Dos correcciones (7-ago-2026), ambas medidas:
        #  · El tope pasa de UPSIDE_HARD_REJECT (30) a UPSIDE_GOLDEN_MAX (25),
        #    que es lo que `record_signals` registra desde hoy. Además el tramo
        #    25-30 es el que destruye el retorno: con datos LIMPIOS a 90d,
        #    [10,25) da alpha +4,55% y [10,30) da -2,60% (sin filtro: -8,48%).
        #    El orden se repite en el contaminado (+4,54 vs +1,48), así que no
        #    es un artefacto de la muestra pequeña del periodo limpio.
        #  · Fuera el filtro `_rr >= 2.0`: R:R es `analyst_upside_pct / 8.0`
        #    (corr +1.0000 sobre 1479 señales), así que sólo recortaba la banda
        #    a upside>=16 por la puerta de atrás, tirando el tramo 10-16.
        _hist_us = value_core_all[value_core_all['strategy'] == 'VALUE'].copy()
        _score = pd.to_numeric(_hist_us['value_score'], errors='coerce')
        _up    = pd.to_numeric(_hist_us['analyst_upside_pct'], errors='coerce')
        golden_hist = _hist_us[(_score >= 60)
                               & (_up >= UPSIDE_MIN) & (_up < UPSIDE_GOLDEN_MAX)].copy()

        # EU: mismo problema con los horizontes largos — las señales del clean
        # period aún no cumplen 90d. Usamos TODO el histórico EU (no hay zona
        # dorada definida para EU) para que 90d tenga base real ya (~674
        # señales); 180/365d se llenan al envejecer.
        eu_hist = value_core_all[value_core_all['strategy'] == 'EU_VALUE'].copy()

        # Combinado para el win rate global a horizonte largo (overall 90d+)
        long_hist = pd.concat([golden_hist, eu_hist], ignore_index=True)

        # Overall stats (VALUE core only)
        total = len(value_core)
        unique_tickers = value_core['ticker'].nunique()
        date_range = f"{CLEAN_FROM.date()} to {value_core['signal_date'].max().date()}" if not value_core.empty else ''

        # Win rates by period
        def win_stats(col_return, col_win, subset=None):
            d = subset if subset is not None else value_core
            if col_return not in d.columns:   # 90/180d aún sin backfillear
                return {'count': 0, 'win_rate': None, 'avg_return': None,
                        'median_return': None, 'best': None, 'worst': None}
            valid = d[d[col_return].notna()]
            if valid.empty:
                return {'count': 0, 'win_rate': None, 'avg_return': None,
                        'median_return': None, 'best': None, 'worst': None}
            wins = valid[valid[col_win] == True]
            return {
                'count': len(valid),
                'win_rate': round(len(wins) / len(valid) * 100, 1),
                'avg_return': round(valid[col_return].mean(), 2),
                'median_return': round(valid[col_return].median(), 2),
                'best': round(valid[col_return].max(), 2),
                'worst': round(valid[col_return].min(), 2),
            }

        # By strategy (VALUE core only — clean period)
        value_df  = value_core[value_core['strategy'] == 'VALUE']
        eu_df     = value_core[value_core['strategy'] == 'EU_VALUE']
        mom_df    = df[df['strategy'] == 'MOMENTUM']  # kept separate, not mixed in

        # Conviction slice: golden zone historical (126 signals, 73% win rate, +5.1% avg 30d)
        conviction_df = golden_hist

        # Sector analysis — PERIODO LIMPIO, US VALUE.
        #
        # Antes salía de `golden_hist`, que es todo el histórico (79 señales
        # contaminadas + 24 limpias). No es un matiz académico: este dict lo
        # consume `super_score_integrator.py` para sumar o restar hasta 12
        # puntos al value_score de cada ticker, así que un sesgo aquí mueve
        # la lista publicada.
        #
        # Contrastado sector a sector, el periodo contaminado NO predice al
        # limpio: correlación de win-rate entre ambos +0,26 (30d) y +0,41
        # (90d) sobre los únicos 4 sectores con n>=15 en los dos — nada con
        # esa muestra. Y el sesgo es sistemático, no ruido: TODOS los sectores
        # rinden peor en limpio (Communication Services 65,3%→12,5%,
        # Technology 63,0%→24,1% a 90d), porque el periodo contaminado
        # registraba 30-80 señales sin filtrar al día, otra población.
        # Con eso, Financial Services cobraba +5 puntos por un 74,6% que en
        # datos limpios es 42,9%.
        #
        # US VALUE porque es a lo que el integrator aplica el ajuste, y sin el
        # corte golden porque con él ningún sector llega a muestra mínima.
        # Donde no haya muestra limpia suficiente no habrá ajuste, que es la
        # respuesta correcta a "no lo sé".
        sector_perf = {}
        _sector_base = value_core[value_core['strategy'] == 'VALUE']
        for sector in _sector_base['sector'].unique():
            sdf = _sector_base[(_sector_base['sector'] == sector) & _sector_base['return_30d'].notna()]
            if len(sdf) >= 2:
                sector_perf[sector] = {
                    'count': len(sdf),
                    'avg_30d': round(sdf['return_30d'].mean(), 2),
                    'win_rate_30d': round((sdf['return_30d'] > 0).sum() / len(sdf) * 100, 1)
                }

        # Score correlation — golden zone historical (score variance is meaningful here)
        score_corr = None
        if not golden_hist.empty and golden_hist['return_30d'].notna().sum() >= 5:
            valid = golden_hist[golden_hist['return_30d'].notna() & golden_hist['value_score'].notna()]
            if len(valid) >= 5:
                score_corr = round(valid['value_score'].corr(valid['return_30d']), 3)

        # Ensure company_name column exists (backfill from ticker for old rows)
        if 'company_name' not in value_core.columns:
            value_core = value_core.copy()
            value_core['company_name'] = value_core['ticker']
        else:
            value_core = value_core.copy()
            value_core['company_name'] = value_core['company_name'].fillna(value_core['ticker'])

        # Top/Bottom performers — VALUE core only, extreme returns excluded
        perf_cols = ['ticker', 'company_name', 'strategy', 'signal_date', 'signal_price', 'return_14d']
        valid_ret = value_core[value_core['return_14d'].notna() & (value_core['return_14d'] > -95) & (value_core['return_14d'] < 500)]
        if not valid_ret.empty:
            top_by_ticker = valid_ret.loc[valid_ret.groupby('ticker')['return_14d'].idxmax()]
            bot_by_ticker = valid_ret.loc[valid_ret.groupby('ticker')['return_14d'].idxmin()]
            top5 = top_by_ticker.sort_values('return_14d', ascending=False).head(5)[perf_cols].to_dict('records')
            bottom5 = bot_by_ticker.sort_values('return_14d').head(5)[perf_cols].to_dict('records')
        else:
            top5 = []
            bottom5 = []

        # Recent active signals — VALUE core only
        active_df = value_core[value_core['status'] == 'ACTIVE'].sort_values('signal_date', ascending=False)
        signal_cols = ['ticker', 'company_name', 'strategy', 'signal_date', 'signal_price', 'sector', 'value_score']
        recent_signals = active_df.head(20)[
            [c for c in signal_cols if c in active_df.columns]
        ].to_dict('records')
        today_ts = pd.Timestamp.now().normalize()
        for s in recent_signals:
            sig_dt = pd.Timestamp(s['signal_date'])
            s['days_active'] = int((today_ts - sig_dt).days)
            s['first_result_date'] = (sig_dt + pd.Timedelta(days=7)).strftime('%Y-%m-%d')
            s['signal_date'] = sig_dt.strftime('%Y-%m-%d')

        summary = {
            'total_signals': total,
            'unique_tickers': unique_tickers,
            'date_range': date_range,
            'active_signals': int((value_core['status'] == 'ACTIVE').sum()),
            'completed_signals': int((value_core['status'] == 'COMPLETED').sum()),

            # Una sola población: las señales que el filtro de hoy sí emite.
            # Antes 90/180/365d salían de long_hist (golden US + TODO el EU
            # pre-abril, sin filtrar) mientras 7/14/30d salían del clean period:
            # el salto de 30d (23.7%) a 90d (46.6%) no era la tesis madurando,
            # era el gráfico cambiando de muestra por debajo. El histórico sigue
            # publicado aparte, en 'long_hist_reference'.
            'overall': {
                '7d': win_stats('return_7d', 'win_7d'),
                '14d': win_stats('return_14d', 'win_14d'),
                '30d': win_stats('return_30d', 'win_30d'),
                '90d': win_stats('return_90d', 'win_90d'),
                '180d': win_stats('return_180d', 'win_180d'),
                '365d': win_stats('return_365d', 'win_365d'),
            },

            # Histórico largo (golden zone US + EU completo, incluye el periodo
            # contaminado): más muestra, otra población. Sirve de contraste, NO
            # de titular — no es comparable con 'overall'.
            'long_hist_reference': {
                '90d':  win_stats('return_90d', 'win_90d', long_hist),
                '180d': win_stats('return_180d', 'win_180d', long_hist),
                '365d': win_stats('return_365d', 'win_365d', long_hist),
            },

            # Mixed bases below — legend for JSON consumers (counts differ on purpose)
            'stats_basis': {
                'clean_period': f'señales VALUE+EU_VALUE desde {CLEAN_FROM.date()} (filtrado correcto)',
                'clean_period_us_value': (
                    f'US VALUE desde {CLEAN_FROM.date()} — base del ajuste sectorial del '
                    'integrator. Antes usaba golden_zone_hist (contaminado): su win-rate '
                    'sectorial no predice al limpio (corr +0,26 a 30d) y lo infla en bloque'),
                'golden_zone_hist': (
                    f'histórico US VALUE retroactivo: score>=60 y upside en '
                    f'[{UPSIDE_MIN:.0f}, {UPSIDE_GOLDEN_MAX:.0f}) — misma población que se emite hoy. '
                    f'Incluye el periodo contaminado: es el único con datos 30d/90d suficientes'),
                'long_hist': 'golden zone US + histórico EU completo — incluye el periodo contaminado; más muestra, otra población',
                'sections': {
                    'overall': 'clean_period',
                    'long_hist_reference': 'long_hist',
                    'conviction': 'golden_zone_hist',
                    'value_strategy.7d/14d': 'clean_period',
                    'value_strategy.30d+': (
                        'clean_period en cuanto hay >=30 señales vencidas; '
                        'golden_zone_hist solo mientras no las haya, y entonces '
                        'la propia sección lo dice en "nota"'),
                    'sector_performance': 'clean_period_us_value',
                    'score_correlation': 'golden_zone_hist',
                },
            },

            # Golden zone historical slice (see stats_basis)
            'conviction': {
                '7d': (lambda d: {
                    'count': 0, 'win_rate': None, 'avg_return': None
                } if d.empty or d['return_7d'].notna().sum() == 0 else {
                    'count': int(d['return_7d'].notna().sum()),
                    'win_rate': round((d[d['win_7d'] == True]['return_7d'].notna().sum()) / d['return_7d'].notna().sum() * 100, 1),
                    'avg_return': round(d['return_7d'].dropna().mean(), 2),
                    'basis': 'golden_zone_hist',
                })(conviction_df),
            },

            'value_strategy': {
                'count': len(value_df),
                # 7d/14d siempre del periodo limpio. Para 30d+ se prefiere TAMBIÉN
                # el limpio en cuanto tiene muestra, y solo se cae al histórico
                # cuando no la hay — ver _mejor_base.
                '7d':  {**win_stats('return_7d',  'win_7d',  value_df), 'basis': 'clean_period'} if not value_df.empty else {},
                '14d': {**win_stats('return_14d', 'win_14d', value_df), 'basis': 'clean_period'} if not value_df.empty else {},
                **{h: _mejor_base(h, value_df, golden_hist, win_stats)
                   for h in ('30d', '90d', '180d', '365d')},
            },

            'eu_value_strategy': {
                'count': len(eu_df),
                # 7d/14d: clean period. 30d+: histórico EU completo (como US con
                # golden_hist) para tener base a horizonte largo desde ya.
                '7d':  {**win_stats('return_7d',  'win_7d',  eu_df), 'basis': 'clean_period'} if not eu_df.empty else {},
                '14d': {**win_stats('return_14d', 'win_14d', eu_df), 'basis': 'clean_period'} if not eu_df.empty else {},
                '30d': {**win_stats('return_30d', 'win_30d', eu_hist), 'basis': 'eu_full_hist'} if not eu_hist.empty else {},
                '90d': {**win_stats('return_90d', 'win_90d', eu_hist), 'basis': 'eu_full_hist'} if not eu_hist.empty else {},
                '180d': {**win_stats('return_180d', 'win_180d', eu_hist), 'basis': 'eu_full_hist'} if not eu_hist.empty else {},
                '365d': {**win_stats('return_365d', 'win_365d', eu_hist), 'basis': 'eu_full_hist'} if not eu_hist.empty else {},
            },

            'momentum_strategy': {
                'count': len(mom_df),
            },

            'sector_performance': sector_perf,
            'score_correlation': score_corr,
            'top_performers': top5,
            'worst_performers': bottom5,
            'recent_signals': recent_signals,

            'avg_max_drawdown': round(value_core['max_drawdown_30d'].mean(), 2) if value_core['max_drawdown_30d'].notna().sum() > 0 else None,

            # ── Alpha vs benchmark (SPY for VALUE US, VGK for EU_VALUE) ──────
            'alpha': {
                '365d': _alpha_stats(value_core, 'alpha_365d', 'return_365d'),
                '180d': _alpha_stats(value_core, 'alpha_180d', 'return_180d'),
                '90d': _alpha_stats(value_core, 'alpha_90d', 'return_90d'),
                '30d': _alpha_stats(value_core, 'alpha_30d', 'return_30d'),
                '14d': _alpha_stats(value_core, 'alpha_14d', 'return_14d'),
                '7d':  _alpha_stats(value_core, 'alpha_7d',  'return_7d'),
            },
            # Horizontes largos (90/180/365) desde el histórico completo
            # (golden_hist US / eu_hist EU), igual que value_strategy — el clean
            # period aún no cumple 90d. 14/30d desde el clean period (más limpio).
            'alpha_us': {
                '365d': _alpha_stats(golden_hist, 'alpha_365d', 'return_365d'),
                '180d': _alpha_stats(golden_hist, 'alpha_180d', 'return_180d'),
                '90d': _alpha_stats(golden_hist, 'alpha_90d', 'return_90d'),
                '30d': _alpha_stats(value_df, 'alpha_30d', 'return_30d'),
                '14d': _alpha_stats(value_df, 'alpha_14d', 'return_14d'),
            },
            'alpha_eu': {
                '365d': _alpha_stats(eu_hist, 'alpha_365d', 'return_365d'),
                '180d': _alpha_stats(eu_hist, 'alpha_180d', 'return_180d'),
                '90d': _alpha_stats(eu_hist, 'alpha_90d', 'return_90d'),
                '30d': _alpha_stats(eu_df, 'alpha_30d', 'return_30d'),
                '14d': _alpha_stats(eu_df, 'alpha_14d', 'return_14d'),
            },

            'generated_at': datetime.now().isoformat()
        }

        self._save_summary(summary)
        self.generate_calibration()
        return summary

    def generate_exit_stats(self) -> dict:
        """Compute stop/target/time-exit statistics for all completed signals with exit data."""
        df = self.recommendations.copy()
        has_exit = df[df['exit_reason'].notna() & df['exit_price'].notna()].copy()
        if has_exit.empty:
            return {'total': 0, 'note': 'No exit data yet — runs after 30d'}

        has_exit['exit_pnl_pct'] = (
            (has_exit['exit_price'].astype(float) - has_exit['signal_price'].astype(float))
            / has_exit['signal_price'].astype(float) * 100
        )

        def bucket(subset, label):
            if subset.empty:
                return {}
            p = subset['exit_pnl_pct']
            wins = (p > 0).sum()
            return {
                'n': int(len(subset)),
                'win_rate': round(float(wins / len(subset) * 100), 1),
                'avg_pnl': round(float(p.mean()), 2),
                'median_pnl': round(float(p.median()), 2),
                'avg_days': round(float(subset['exit_day'].mean()), 1) if 'exit_day' in subset.columns else None,
            }

        by_reason = {}
        for reason in ['STOP', 'TARGET', 'TIME_30D']:
            sub = has_exit[has_exit['exit_reason'] == reason]
            by_reason[reason] = bucket(sub, reason)

        by_strategy = {}
        for strat in has_exit['strategy'].unique():
            sub = has_exit[has_exit['strategy'] == strat]
            by_strategy[strat] = bucket(sub, strat)

        # R:R buckets
        rr_buckets = {}
        if 'risk_reward_ratio' in has_exit.columns:
            for lo, hi, label in [(0, 2, '<2x'), (2, 3, '2-3x'), (3, 5, '3-5x'), (5, 99, '>=5x')]:
                sub = has_exit[
                    has_exit['risk_reward_ratio'].apply(lambda x: lo <= (float(x) if x and str(x) != 'nan' else -1) < hi)
                ]
                if not sub.empty:
                    rr_buckets[label] = bucket(sub, label)

        return {
            'total': int(len(has_exit)),
            'by_exit_reason': by_reason,
            'by_strategy': by_strategy,
            'by_rr': rr_buckets,
            'generated_at': pd.Timestamp.now().isoformat(),
        }

    def generate_calibration(self):
        """Compute score/regime/sector calibration — does a higher score actually predict better returns?"""
        VALUE_STRATEGIES = {'VALUE', 'EU_VALUE'}
        df = self.recommendations[self.recommendations['strategy'].isin(VALUE_STRATEGIES)]
        completed = df[df['return_14d'].notna() & (df['return_14d'] > -95) & (df['return_14d'] < 500)]
        if len(completed) < 10:
            return

        def bucket_stats(subset):
            if subset.empty:
                return None
            wins = (subset['win_14d'] == True).sum()
            return {
                'count': int(len(subset)),
                'win_rate_14d': round(wins / len(subset) * 100, 1),
                'avg_return_14d': round(subset['return_14d'].mean(), 2),
                'median_return_14d': round(subset['return_14d'].median(), 2),
            }

        # Score buckets
        score_buckets = []
        breaks = [(50, 55), (55, 60), (60, 65), (65, 70), (70, 75), (75, 200)]
        for lo, hi in breaks:
            sub = completed[completed['value_score'].notna() &
                            (completed['value_score'] >= lo) & (completed['value_score'] < hi)]
            stats = bucket_stats(sub)
            if stats:
                stats['range'] = f'{lo}-{hi}' if hi < 200 else f'{lo}+'
                score_buckets.append(stats)

        # Market regime
        regime_rows = []
        for regime in completed['market_regime'].dropna().unique():
            sub = completed[completed['market_regime'] == regime]
            stats = bucket_stats(sub)
            if stats:
                stats['regime'] = regime
                regime_rows.append(stats)
        regime_rows.sort(key=lambda x: -x['count'])

        # Sector calibration (min 5 signals)
        sector_rows = []
        for sector in completed['sector'].dropna().unique():
            sub = completed[completed['sector'] == sector]
            if len(sub) < 5:
                continue
            stats = bucket_stats(sub)
            if stats:
                stats['sector'] = sector
                sector_rows.append(stats)
        sector_rows.sort(key=lambda x: -x['win_rate_14d'])

        # FCF yield buckets (only where available)
        fcf_df = completed[completed['fcf_yield_pct'].notna()].copy()
        fcf_buckets = []
        fcf_breaks = [(-99, 0, 'Negative'), (0, 3, '0-3%'), (3, 6, '3-6%'), (6, 12, '6-12%'), (12, 999, '12%+')]
        for lo, hi, label in fcf_breaks:
            sub = fcf_df[(fcf_df['fcf_yield_pct'] >= lo) & (fcf_df['fcf_yield_pct'] < hi)]
            stats = bucket_stats(sub)
            if stats:
                stats['range'] = label
                fcf_buckets.append(stats)

        calibration = {
            'score_buckets': score_buckets,
            'regime_analysis': regime_rows,
            'sector_calibration': sector_rows,
            'fcf_yield_buckets': fcf_buckets,
            'total_completed': int(len(completed)),
            'generated_at': datetime.now().isoformat(),
        }

        def convert(obj):
            if isinstance(obj, (np.integer, np.floating)):
                return float(obj)
            if isinstance(obj, np.bool_):
                return bool(obj)
            if isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [convert(i) for i in obj]
            return obj

        with open(CALIBRATION_FILE, 'w') as f:
            json.dump(convert(calibration), f, indent=2)
        print(f'  Calibration saved: {CALIBRATION_FILE}')

    def print_report(self, summary: dict):
        """Print formatted performance report"""
        print("\n" + "=" * 80)
        print("PORTFOLIO TRACKER — PERFORMANCE REPORT")
        print("=" * 80)

        print(f"\n  Total signals tracked: {summary['total_signals']}")
        print(f"  Unique tickers: {summary.get('unique_tickers', 'N/A')}")
        print(f"  Period: {summary.get('date_range', 'N/A')}")
        print(f"  Active: {summary.get('active_signals', 0)} | Completed: {summary.get('completed_signals', 0)}")

        for label, key in [('OVERALL', 'overall'), ('VALUE', 'value_strategy'), ('MOMENTUM', 'momentum_strategy')]:
            data = summary.get(key, {})
            if not data:
                continue
            print(f"\n  --- {label} ---")
            for period in ['7d', '14d', '30d', '90d', '180d']:
                stats = data.get(period, {})
                if not stats or stats.get('count', 0) == 0:
                    continue
                wr = stats.get('win_rate')
                avg = stats.get('avg_return')
                n = stats.get('count')
                wr_str = f"{wr}%" if wr is not None else "N/A"
                avg_str = f"{avg:+.2f}%" if avg is not None else "N/A"
                print(f"    {period}: Win Rate {wr_str} | Avg {avg_str} | n={n}")

        # Score correlation
        corr = summary.get('score_correlation')
        if corr is not None:
            direction = "POSITIVE" if corr > 0.1 else ("NEGATIVE" if corr < -0.1 else "WEAK")
            print(f"\n  Score → Return correlation: {corr} ({direction})")
            if corr > 0.1:
                print("    Higher scores DO predict better returns")
            elif corr < -0.1:
                print("    WARNING: Higher scores predict WORSE returns!")

        # Top/Bottom
        top = summary.get('top_performers', [])
        if top:
            print(f"\n  TOP 5 PERFORMERS:")
            for t in top:
                sig_date = str(t.get('signal_date', ''))[:10]
                print(f"    {t['ticker']:6} {t['strategy']:8} {sig_date} ${t.get('signal_price', 0):>8.2f} → {t['return_14d']:+.1f}%")

        bottom = summary.get('worst_performers', [])
        if bottom:
            print(f"\n  WORST 5 PERFORMERS:")
            for t in bottom:
                sig_date = str(t.get('signal_date', ''))[:10]
                print(f"    {t['ticker']:6} {t['strategy']:8} {sig_date} ${t.get('signal_price', 0):>8.2f} → {t['return_14d']:+.1f}%")

        dd = summary.get('avg_max_drawdown')
        if dd is not None:
            print(f"\n  Average Max Drawdown (30d): {dd:.1f}%")

        print("\n" + "=" * 80)

    def _save_recommendations(self):
        """Save recommendations to CSV"""
        self.recommendations.to_csv(RECOMMENDATIONS_FILE, index=False)

    def _save_summary(self, summary: dict):
        """Save summary to JSON"""
        # Convert Timestamps to strings for JSON
        def convert(obj):
            if isinstance(obj, (pd.Timestamp, datetime)):
                return str(obj)
            if isinstance(obj, (np.integer, np.floating)):
                return float(obj)
            if isinstance(obj, np.bool_):
                return bool(obj)
            if isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [convert(i) for i in obj]
            if pd.isna(obj) if isinstance(obj, float) else False:
                return None
            return obj

        with open(SUMMARY_FILE, 'w') as f:
            json.dump(convert(summary), f, indent=2, default=str)
        print(f"  Summary saved: {SUMMARY_FILE}")


def backfill_alpha(tracker: 'PortfolioTracker') -> int:
    """
    Backfill alpha_7d / alpha_14d / alpha_30d for COMPLETED signals that have
    return data but no benchmark comparison.

    Downloads SPY (US/MOMENTUM) and VGK (EU_VALUE) history once for the full
    date range, then computes alpha for every row missing it.
    Returns count of rows updated.
    """
    df = tracker.recommendations
    if df.empty:
        return 0

    # Rows that have a return but no alpha yet — en CUALQUIER horizonte
    # (antes solo miraba alpha_7d, así que las filas con alpha corto pero sin
    # alpha_90d/180d/365d no se rellenaban nunca → alpha largo siempre vacío)
    _missing_any = pd.Series(False, index=df.index)
    for _h in ('7d', '14d', '30d', '90d', '180d', '365d'):
        _rc, _ac = f'return_{_h}', f'alpha_{_h}'
        if _rc in df.columns:
            _has_ret = df[_rc].notna()
            _no_alpha = df[_ac].isna() if _ac in df.columns else True
            _missing_any |= _has_ret & _no_alpha
    needs = df[_missing_any].copy()

    if needs.empty:
        print("  No rows need alpha backfill.")
        return 0

    print(f"  Backfilling alpha for {len(needs)} rows…")

    # Date range: earliest signal to today
    earliest = pd.Timestamp(needs['signal_date'].min()) - timedelta(days=1)
    end_str   = (pd.Timestamp.now() + timedelta(days=2)).strftime('%Y-%m-%d')
    start_str = earliest.strftime('%Y-%m-%d')

    bench_hists: dict[str, pd.DataFrame] = {}
    for bench in ['SPY', 'VGK']:
        try:
            h = yf.Ticker(bench).history(start=start_str, end=end_str)
            if not h.empty:
                if h.index.tz is not None:
                    h.index = h.index.tz_localize(None)
                bench_hists[bench] = h
                print(f"  Downloaded {bench}: {len(h)} days")
        except Exception as e:
            print(f"  Warning: could not download {bench}: {e}")

    if not bench_hists:
        print("  No benchmark data available — skipping backfill.")
        return 0

    updated = 0
    for idx, row in needs.iterrows():
        signal_date = pd.Timestamp(row['signal_date'])
        strategy    = str(row.get('strategy', 'VALUE'))
        bench_key   = 'VGK' if strategy == 'EU_VALUE' else 'SPY'
        bh = bench_hists.get(bench_key)
        if bh is None:
            continue

        for period, col_ret, col_bench, col_alpha in [
            (7,  'return_7d',  'benchmark_return_7d',  'alpha_7d'),
            (14, 'return_14d', 'benchmark_return_14d', 'alpha_14d'),
            (30, 'return_30d', 'benchmark_return_30d', 'alpha_30d'),
            (90, 'return_90d', 'benchmark_return_90d', 'alpha_90d'),
            (180, 'return_180d', 'benchmark_return_180d', 'alpha_180d'),
            (365, 'return_365d', 'benchmark_return_365d', 'alpha_365d'),
        ]:
            sig_return = row.get(col_ret)
            if pd.isna(sig_return):
                continue
            # Only backfill if not already set
            existing = row.get(col_alpha)
            if not pd.isna(existing) and existing != '':
                continue

            check_date = signal_date + timedelta(days=period)
            b_sig_mask   = bh.index >= signal_date
            b_check_mask = bh.index >= check_date
            if not b_sig_mask.any() or not b_check_mask.any():
                continue

            b_sig_price   = float(bh.loc[b_sig_mask,   'Close'].iloc[0])
            b_check_price = float(bh.loc[b_check_mask, 'Close'].iloc[0])
            if b_sig_price <= 0:
                continue

            bench_ret = (b_check_price - b_sig_price) / b_sig_price * 100
            alpha     = float(sig_return) - bench_ret

            df.at[idx, col_bench] = round(bench_ret, 2)
            df.at[idx, col_alpha] = round(alpha, 2)
            updated += 1

    tracker._save_recommendations()
    print(f"  ✓ Backfilled {updated} alpha values across {len(needs)} rows.")
    return updated


def main():
    parser = argparse.ArgumentParser(description='Portfolio Tracker')
    parser.add_argument('--record',         action='store_true', help='Record today\'s signals')
    parser.add_argument('--update',         action='store_true', help='Update performance for past signals')
    parser.add_argument('--report',         action='store_true', help='Generate and print performance report')
    parser.add_argument('--all',            action='store_true', help='Record + Update + Report')
    parser.add_argument('--backfill-alpha', action='store_true', help='Backfill alpha vs SPY/VGK for completed signals')
    args = parser.parse_args()

    if not any([args.record, args.update, args.report, args.all, args.backfill_alpha]):
        args.all = True

    tracker = PortfolioTracker()

    print("\n" + "=" * 80)
    print("PORTFOLIO TRACKER")
    print("=" * 80)

    if args.record or args.all:
        print("\n1. RECORDING TODAY'S SIGNALS")
        print("-" * 40)
        tracker.record_signals()

    if args.update or args.all:
        print("\n2. UPDATING PERFORMANCE")
        print("-" * 40)
        tracker.update_performance()

    if args.backfill_alpha:
        print("\n[BACKFILL] ALPHA VS BENCHMARK")
        print("-" * 40)
        backfill_alpha(tracker)

    if args.report or args.all:
        print("\n3. GENERATING REPORT")
        print("-" * 40)
        summary = tracker.generate_summary()
        tracker.print_report(summary)

    print("\nDone!")


if __name__ == '__main__':
    main()
