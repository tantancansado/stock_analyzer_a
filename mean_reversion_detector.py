#!/usr/bin/env python3
"""
MEAN REVERSION DETECTOR
Identifica oportunidades de reversión a la media - compra dips en stocks de calidad

Estrategias detectadas:
1. Oversold Bounces - RSI < 30 en stocks fundamentalmente sólidos
2. Bull Flag Pullbacks - Retrocesos 10-15% en tendencias alcistas
3. Support Zone Bounces - Rebotes desde niveles técnicos clave
4. Insider Dip Buying - Insiders comprando durante caídas
"""
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from pathlib import Path
from datetime import datetime, timedelta, date
from typing import List, Dict, Tuple, Optional
import json
import math


# Suelo de risk/reward para publicar un setup. Ver el bloque de setup_coherente
# que lo aplica: es la frontera aritmética (ganar al menos lo que arriesgas),
# no un parámetro calibrado con resultados propios.
RR_MINIMO = 1.0


def setup_coherente(setup: dict) -> tuple[bool, str]:
    """¿Esta señal es operable, o pide algo imposible?

    Puerta única antes de publicar. Los detectores calculan stop y target a
    partir de niveles técnicos (soporte, resistencia, SMA50, máximo de 60d) sin
    comprobar que queden del lado correcto del precio, y el 20-ago-2026 se
    publicaron dos señales pidiendo comprar a 177 para vender a 156, y otra con
    el stop un 3,5% POR ENCIMA del precio de entrada.

    Cada guard suelto arregla un setup; esto ataja también los que se añadan
    después. Devuelve (ok, motivo) para poder registrar POR QUÉ se descarta.
    """
    precio = setup.get('current_price')
    if not precio or precio <= 0:
        return False, 'sin precio'

    for campo in ('bounce_target', 'target'):
        t = setup.get(campo)
        if t is not None and t <= precio:
            return False, f'{campo} {t} <= precio {precio} (pide comprar caro para vender barato)'

    stop = setup.get('stop_loss')
    if stop is not None and stop >= precio:
        return False, f'stop {stop} >= precio {precio} (stop por encima de la entrada)'

    # Un R:R de 0 significa que el cálculo se fue a la rama de fallback porque
    # la aritmética era imposible: publicarlo es esconder el problema.
    rr = setup.get('risk_reward')
    if rr is not None and rr <= 0:
        return False, f'risk_reward {rr}: el cálculo no da un número válido'

    # Suelo de riesgo. No es un umbral calibrado —no hay histórico de rebotes,
    # el registro en el tracker empezó el 20-ago-2026— sino aritmética: con
    # R:R < 1 arriesgas más de lo que puedes ganar, así que necesitas acertar
    # más de la mitad de las veces solo para empatar, y nadie ha medido si este
    # detector acierta la mitad de las veces. El escáner amplio ya exige 1.5
    # (bounce_scanner_broad.MIN_RR) desde hace meses; que el detector hermano
    # no exigiera NADA y publicara AJG con 0,51 —arriesgar 22$ para ganar 11$—
    # marcado "⭐⭐ MUY BUENA" es la incoherencia, no el valor concreto.
    #
    # Se queda en 1.0 y no en 1.5 a propósito: 1.0 es la frontera aritmética y
    # no requiere calibración. Subirlo a 1.5 SÍ la requiere, y el tracker ya
    # guarda risk_reward_ratio de cada señal para poder decidirlo con datos
    # propios dentro de unos meses.
    if rr is not None and rr < RR_MINIMO:
        return False, f'risk_reward {rr} < {RR_MINIMO} (arriesga más de lo que puede ganar)'

    # El R:R tiene que salir del objetivo que se publica y del precio de
    # entrada que se pide. Parece obvio; durante meses no fue así: se publicaba
    # `target` = resistencia y se calculaba el R:R contra el objetivo de rebote
    # (+7% fijo). El 16-sep-2026 no cuadraba NINGUNA de las 12 fichas. Nada
    # fallaba: los dos números eran correctos por separado y juntos mentían.
    entrada = setup.get('entry_ref') or precio
    objetivo = setup.get('target')

    # La zona de entrada tiene que ser alcanzable. Si te dice «entra a 311»
    # cuando cotiza a 296,85 no es una zona de entrada, es un precio que hoy no
    # existe — y ocurría cuando el soporte del que colgaba la zona ya estaba
    # roto. Se admite hasta un 2% por encima porque el Bull Flag Pullback
    # define su zona como el precio ±2%.
    if entrada > precio * 1.02:
        return False, (f'la zona de entrada llega a {entrada} con el precio en {precio} '
                       f'(+{100 * (entrada / precio - 1):.1f}%): no es alcanzable')

    if None not in (rr, objetivo, stop) and entrada > stop:
        rr_real = (objetivo - entrada) / (entrada - stop)
        if abs(rr_real - rr) > 0.05:
            return False, (f'R:R {rr} no sale de sus propios números '
                           f'(objetivo {objetivo}, entrada {entrada}, stop {stop} → {rr_real:.2f})')

    # El techo técnico es hasta dónde PODRÍA llegar. Si queda por debajo del
    # objetivo, uno de los dos está mal calculado.
    techo = setup.get('techo_tecnico')
    if techo is not None and objetivo is not None and techo < objetivo:
        return False, f'techo técnico {techo} por debajo del objetivo {objetivo}'

    return True, ''


class MeanReversionDetector:
    """Detector de oportunidades de reversión a la media"""

    def __init__(self):
        # 300 días de calendario ≈ 205 sesiones — necesario para SMA200 real.
        # Con 180 (el valor anterior) solo había ~124 sesiones y la SMA200 del
        # bull-flag caía SIEMPRE a SMA50: el criterio de tendencia mayor (lo que
        # DEFINE un bull flag) nunca se evaluaba y el trend salía siempre Bearish.
        self.lookback_days = 300
        self.results = []
        self._market_regime_cache: Dict = {}  # caché para no repetir llamadas

    def get_market_regime(self) -> Dict:
        """
        Calcula el régimen de mercado actual usando SPY.
        Devuelve dict con spy_above_ma50 (bool), spy_above_ma200 (bool),
        spy_price, spy_ma50, spy_ma200 y regime_label.
        Resultado cacheado en memoria para el ciclo de scan.
        """
        if self._market_regime_cache:
            return self._market_regime_cache

        try:
            import yfinance as yf
            spy = yf.Ticker('SPY')
            hist = spy.history(period='1y')
            if len(hist) < 50:
                raise ValueError("Datos insuficientes SPY")

            spy_price = float(hist['Close'].iloc[-1])
            ma50  = float(hist['Close'].rolling(50).mean().iloc[-1])
            ma200 = float(hist['Close'].rolling(200).mean().iloc[-1])

            above_50  = spy_price > ma50
            above_200 = spy_price > ma200

            if above_50 and above_200:
                label = 'ALCISTA'
            elif above_200 and not above_50:
                label = 'CORRECCIÓN'
            elif not above_200:
                label = 'BAJISTA'
            else:
                label = 'NEUTRAL'

            result = {
                'spy_price': round(spy_price, 2),
                'spy_ma50':  round(ma50, 2),
                'spy_ma200': round(ma200, 2),
                'spy_above_ma50':  above_50,
                'spy_above_ma200': above_200,
                'regime_label': label,
                'bounce_ok': above_50,  # solo operar rebotes si SPY > MA50
            }
        except Exception as e:
            print(f"   ⚠️  No se pudo obtener régimen SPY: {e}")
            result = {
                'spy_price': None, 'spy_ma50': None, 'spy_ma200': None,
                'spy_above_ma50': None, 'spy_above_ma200': None,
                'regime_label': 'DESCONOCIDO', 'bounce_ok': None,
            }

        self._market_regime_cache = result
        return result

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calcula RSI (Relative Strength Index)"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def find_support_resistance(self, prices: pd.Series,
                               window: int = 20) -> Tuple[float, float]:
        """Identifica niveles de soporte y resistencia"""
        # Support = mínimos locales
        rolling_min = prices.rolling(window=window, center=True).min()
        support_level = rolling_min[rolling_min == prices].median()

        # Resistance = máximos locales
        rolling_max = prices.rolling(window=window, center=True).max()
        resistance_level = rolling_max[rolling_max == prices].median()

        return support_level, resistance_level

    def detect_oversold_bounce(self, ticker: str,
                               company_name: str = None) -> Dict:
        """
        Detecta oportunidades de oversold bounce

        Criterios:
        - RSI < 30 (oversold)
        - Caída > 20% desde máximo reciente
        - Volumen incrementando en bounce
        - Fundamentales sólidos
        """
        try:
            from yfinance_client import get_history, YFClientError, RateLimitError
            # Obtener datos históricos
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.lookback_days)
            try:
                hist = get_history(ticker, start=start_date, end=end_date, min_rows=50)
            except RateLimitError:
                return None  # rate-limit no es problema del ticker
            except YFClientError:
                return None  # data missing / other

            # Ticker handle para metadata (calendar, market cap, rangos 52s).
            # OJO: esta variable se perdió en un refactor y los usos de abajo
            # lanzaban NameError dentro de try/except — el de market cap hacía
            # `return None` y rechazaba EL 100% de los candidatos en silencio.
            stock = yf.Ticker(ticker)

            # Calcular indicadores
            current_price = hist['Close'].iloc[-1]
            rsi = self.calculate_rsi(hist['Close'])
            current_rsi = rsi.iloc[-1]

            # Máximo de los últimos 60 días
            max_60d = hist['Close'].tail(60).max()
            drawdown_pct = ((current_price - max_60d) / max_60d) * 100

            # Soporte y resistencia
            support, resistance = self.find_support_resistance(hist['Close'])
            distance_to_support = ((current_price - support) / support) * 100

            # Volumen promedio
            avg_volume_20d = hist['Volume'].tail(20).mean()
            current_volume = hist['Volume'].iloc[-1]
            volume_ratio = current_volume / avg_volume_20d if avg_volume_20d > 0 else 0

            # ── Indicadores adicionales para bounce confidence ─────────────────

            # Días bajistas consecutivos (agotamiento vendedor)
            closes = hist['Close'].tail(10)
            consecutive_down = 0
            for i in range(len(closes) - 1, 0, -1):
                if closes.iloc[i] < closes.iloc[i - 1]:
                    consecutive_down += 1
                else:
                    break

            # Bollinger Bands (20 días, 2 desv)
            sma20 = hist['Close'].tail(20).mean()
            std20 = hist['Close'].tail(20).std()
            bb_lower = sma20 - 2 * std20
            bb_upper = sma20 + 2 * std20
            bb_pct_b = round((current_price - bb_lower) / (bb_upper - bb_lower) * 100, 1) if (bb_upper - bb_lower) > 0 else 50
            below_bb = current_price <= bb_lower

            # Stochastic %K (14 días)
            low14  = hist['Low'].tail(14).min()
            high14 = hist['High'].tail(14).max()
            stoch_k = round((current_price - low14) / (high14 - low14) * 100, 1) if (high14 - low14) > 0 else 50

            # Volumen decreciente en últimos 3 días (señal de agotamiento)
            vols = hist['Volume'].tail(4)
            volume_drying = bool(vols.iloc[-1] < vols.iloc[-2] < vols.iloc[-3]) if len(vols) >= 3 else False

            # ── RSI Semanal (Connors: daily < 30 + weekly < 35 = +15-20% win rate) ──
            weekly = hist['Close'].resample('W').last().dropna()
            rsi_weekly_series = self.calculate_rsi(weekly, period=14)
            rsi_weekly = round(float(rsi_weekly_series.iloc[-1]), 1) if len(rsi_weekly_series) >= 14 else None
            # < 35 = confirmación doble timeframe más robusta (Connors research)
            weekly_oversold = rsi_weekly is not None and rsi_weekly < 35

            # ── RSI(2) Acumulado — Connors, 83% win rate documentado ──────────────
            # Señal: CumRSI(2) de los últimos 2 días < 10
            rsi2_series = self.calculate_rsi(hist['Close'], period=2)
            cum_rsi2 = round(float(rsi2_series.iloc[-1] + rsi2_series.iloc[-2]), 1) if len(rsi2_series) >= 2 else None
            # Connors Research: <10 = 83% win rate; <35 es demasiado amplio (~65%)
            connors_signal = cum_rsi2 is not None and cum_rsi2 < 10
            connors_weak   = cum_rsi2 is not None and 10 <= cum_rsi2 < 35

            # ── ATR(14) — para stop más preciso según volatilidad real ───────────
            high_low = hist['High'] - hist['Low']
            high_close = (hist['High'] - hist['Close'].shift()).abs()
            low_close  = (hist['Low']  - hist['Close'].shift()).abs()
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr14 = round(float(true_range.tail(14).mean()), 4)

            # ── Vela de capitulación (hammer/pin bar) ────────────────────────────
            # Mecha inferior > 60% del rango total + cierre en tercio superior
            last = hist.tail(1).iloc[0]
            candle_range = last['High'] - last['Low']
            lower_wick   = last['Close'] - last['Low'] if last['Close'] > last['Open'] else last['Open'] - last['Low']
            upper_body   = last['High'] - max(last['Open'], last['Close'])
            hammer_candle = (
                candle_range > 0 and
                lower_wick / candle_range >= 0.55 and
                upper_body / candle_range <= 0.25
            )

            # Bullish engulfing: cuerpo actual engloba cuerpo anterior, cierra al alza
            prev = hist.tail(2).iloc[0]
            engulfing_candle = (
                last['Close'] > last['Open'] and              # hoy alcista
                prev['Close'] < prev['Open'] and              # ayer bajista
                last['Open'] <= prev['Close'] and             # abre bajo el cierre de ayer
                last['Close'] >= prev['Open']                 # cierra sobre la apertura de ayer
            )

            # ── Divergencia OBV (institucionales comprando mientras precio baja) ─
            obv = (hist['Volume'] * (2 * (hist['Close'] > hist['Close'].shift()).astype(int) - 1)).cumsum()
            obv5 = obv.tail(5)
            price5 = hist['Close'].tail(5)
            # OBV subiendo mientras precio bajando = divergencia alcista
            obv_divergence = (
                float(obv5.iloc[-1]) > float(obv5.iloc[0]) and   # OBV sube
                float(price5.iloc[-1]) < float(price5.iloc[0])   # precio baja
            )

            # ── Divergencia alcista RSI: precio baja pero RSI sube ───────────────
            # Significa que los vendedores pierden fuerza — 30% más fiable que RSI solo
            rsi5_prev    = float(rsi.iloc[-6])         if len(rsi)  >= 6 else None
            price5_prev  = float(hist['Close'].iloc[-6]) if len(hist) >= 6 else None
            rsi_divergence = (
                rsi5_prev is not None and price5_prev is not None
                and current_price < price5_prev   # precio bajó en los últimos 5 días
                and current_rsi   > rsi5_prev     # RSI subió (presión vendedora decrece)
            )

            # ── Régimen de mercado ───────────────────────────────────────────────
            regime = self.get_market_regime()
            market_ok = regime.get('bounce_ok')  # True si SPY > MA50

            # Earnings próximos (desde fundamental_scores.csv si está disponible)
            days_to_earnings: int | None = None
            earnings_warning = False
            try:
                cal = stock.calendar
                if cal is not None and not cal.empty:
                    earn_date = pd.Timestamp(cal.columns[0]) if hasattr(cal, 'columns') else None
                    if earn_date is None and 'Earnings Date' in cal.index:
                        earn_date = pd.Timestamp(cal.loc['Earnings Date'].iloc[0])
                    if earn_date is not None:
                        days_to_earnings = max(0, (earn_date.date() - datetime.now().date()).days)
                        earnings_warning = days_to_earnings <= 7
            except Exception:
                pass

            # Rechazo duro: si el precio ya rompió el soporte por más del 5%,
            # el soporte pasó a ser resistencia — no hay base técnica para el rebote
            if distance_to_support < -3:
                return None  # soporte ya roto más del 3% — no hay suelo claro

            # Criterios de oversold bounce
            is_oversold = current_rsi < 30
            significant_dip = drawdown_pct < -20
            near_support = -3 <= distance_to_support <= 5  # precio puede estar hasta 3% bajo soporte
            volume_spike = volume_ratio > 1.2  # Volumen 20% mayor

            # Score de oportunidad (0-100)
            score = 0
            if is_oversold:
                score += 30
            if significant_dip:
                score += 25
            if near_support:
                score += 25
            if volume_spike:
                score += 20

            # ── FILTROS DUROS DE RECHAZO ─────────────────────────────────────────
            # Solo retornar si hay potencial real
            if score < 50 or not is_oversold:
                return None
            if current_rsi == 0.0:
                return None  # error de datos yfinance
            if current_price < 5.00:
                return None  # penny/micro-cap: spread y liquidez inasumibles para bounce
            avg_dollar_volume = avg_volume_20d * current_price
            if avg_dollar_volume < 1_000_000:
                return None  # volumen en dólares insuficiente (<$1M/día) — spread y slippage inasumibles
            # Market cap mínimo $300M: micro-caps son manipulables y tienen spreads elevados
            # Si el dato no está disponible (0) también se rechaza — fail closed
            try:
                market_cap = float(stock.fast_info.get('marketCap') or 0)
                if market_cap < 300_000_000:
                    return None
            except Exception:
                return None  # sin datos de market cap → rechazar
            # Mínimo de confirmaciones técnicas: al menos 2 de los 4 pilares deben cumplirse
            # (near_support, significant_dip, stoch<30, below_bb ó connors)
            tech_confirmations = sum([
                near_support,
                significant_dip,
                stoch_k < 30,
                below_bb or connors_signal,
            ])
            if tech_confirmations < 2:
                return None  # setup demasiado débil — solo RSI bajo no es suficiente

            # Rechazo duro: mínimo y máximo 52 semanas
            # Usar fast_info para datos reales de 52 semanas (más fiable que tail(252) con solo 180d de hist)
            try:
                fi_52 = stock.fast_info
                high_52w = float(fi_52.get('yearHigh') or hist['Close'].tail(252).max())
                low_52w  = float(fi_52.get('yearLow')  or hist['Close'].tail(252).min())
            except Exception:
                high_52w = float(hist['Close'].tail(252).max())
                low_52w  = float(hist['Close'].tail(252).min())

            near_52w_low = current_price <= low_52w * 1.03  # dentro del 3% del mínimo anual
            if near_52w_low:
                return None  # no hay soporte histórico, setup de cuchillo cayendo

            # Rechazo duro: caída >45% desde máximo anual = deterioro estructural
            # (corrección técnica válida ≤ -40%; -45%+ = empresa con problemas reales)
            drawdown_from_52w = (current_price - high_52w) / high_52w * 100
            if drawdown_from_52w < -45:
                return None  # declive estructural — no hay compradores naturales para rebote

            # Rechazo duro: earnings en ≤7 días = veto total (no penalty, veto)
            # En 1-3 días no puedes aguantar hasta earnings — la caída puede ser anticipatoria
            if earnings_warning:
                return None

            # VIX: si está disponible, matar setups en pánico extremo (VIX > 35)
            try:
                vix_hist = yf.Ticker('^VIX').history(period='2d')
                vix_now  = float(vix_hist['Close'].iloc[-1]) if not vix_hist.empty else 0
                if vix_now > 35:
                    return None  # pánico extremo: oversold se resetea a más oversold
            except Exception:
                vix_now = 0

            # Rechazo duro: caída de noticias (>8% en un solo día en los últimos 5 días)
            # Earnings miss, guidance cut, fraud — no es sobrevendido técnico, es cuchillo en caída
            recent_daily_rets = [
                (float(hist['Close'].iloc[i]) / float(hist['Close'].iloc[i - 1]) - 1) * 100
                for i in range(-5, 0)
            ]
            if recent_daily_rets and min(recent_daily_rets) < -8.0:
                return None  # evento de noticias reciente — no rebote técnico fiable

            # Bounce confidence score — señales adicionales de alta probabilidad
            # Basado en backtests: RSI(2) acumulado 83% win rate, RSI semanal +15-20%
            bounce_signals: list[str] = []
            # Base: cualquier setup que pase RSI<30 + score≥50 ya tiene valor
            bounce_confidence = 20

            # RSI diario (bonus encima de la base) — rsi_tier se define aquí antes de usarse
            if current_rsi < 20:
                rsi_tier = 'EXTREMO'
                bounce_confidence += 25
                bounce_signals.append('RSI extremo <20')
            elif current_rsi < 25:
                rsi_tier = 'ALTO'
                bounce_confidence += 15
                bounce_signals.append('RSI muy bajo')
            else:
                rsi_tier = 'MEDIO'
                bounce_confidence += 5

            # RSI semanal — confirmación de timeframe superior (+15-20% win rate)
            if weekly_oversold:
                bounce_confidence += 20
                bounce_signals.append(f'RSI semanal {rsi_weekly}')
            elif rsi_tier == 'MEDIO' and rsi_weekly is not None and rsi_weekly >= 45:
                # RSI diario 25-30 (señal débil) sin confirmación semanal = setup frágil
                bounce_confidence -= 10
                bounce_signals.append(f'⚠ RSI sem {rsi_weekly} (sin conf.)')

            # Connors CumRSI(2) — tiered (Connors Research)
            if connors_signal:  # <10 = 83% win rate documentado
                bounce_confidence += 20
                bounce_signals.append(f'CumRSI2={cum_rsi2:.0f}')
            elif connors_weak:  # 10-35 = señal moderada, sin el edge documentado
                bounce_confidence += 8
                bounce_signals.append(f'CumRSI2={cum_rsi2:.0f} (mod)')

            # Bollinger Band inferior
            if below_bb:
                bounce_confidence += 15
                bounce_signals.append('Bajo BB inferior')

            # Stochastic oversold
            if stoch_k < 20:
                bounce_confidence += 10
                bounce_signals.append('Stoch oversold')

            # Vela de capitulación
            if hammer_candle:
                bounce_confidence += 12
                bounce_signals.append('Hammer')
            elif engulfing_candle:
                bounce_confidence += 10
                bounce_signals.append('Engulfing alcista')

            # Divergencia OBV (institucionales comprando)
            if obv_divergence:
                bounce_confidence += 12
                bounce_signals.append('Div. OBV alcista')

            # Divergencia alcista RSI (vendedores perdiendo fuerza)
            if rsi_divergence:
                bounce_confidence += 10
                bounce_signals.append('Div. RSI alcista')

            # Días bajistas consecutivos — cap en 10: más de 10 = tendencia bajista, no agotamiento
            if 3 <= consecutive_down <= 10:
                bounce_confidence += 8
                bounce_signals.append(f'{consecutive_down}d bajistas')
            elif consecutive_down > 10:
                bounce_confidence -= 5  # tendencia, no agotamiento
                bounce_signals.append(f'⚠ {consecutive_down}d bajistas (tendencia)')

            # Volumen secándose
            if volume_drying:
                bounce_confidence += 6
                bounce_signals.append('Vol secándose')

            # Régimen de mercado
            spy_above_ma200 = regime.get('spy_above_ma200', True)
            if market_ok is False:
                if not spy_above_ma200:
                    # SPY bajo MA50 Y MA200 = bear market real — penalización severa
                    bounce_confidence = int(bounce_confidence * 0.5)
                    bounce_signals.append('⚠ Bear market')
                else:
                    # Solo bajo MA50 (corrección) — penalización moderada
                    bounce_confidence = int(bounce_confidence * 0.7)
                    bounce_signals.append('⚠ Mercado bajista')
            elif market_ok is True:
                bounce_signals.append('✓ Mercado favorable')

            # VIX elevado (25-35): penalizar confianza — no es el momento óptimo
            if 25 < vix_now <= 35:
                bounce_confidence = int(bounce_confidence * 0.75)
                bounce_signals.append(f'⚠ VIX {vix_now:.0f}')

            bounce_confidence = min(100, bounce_confidence)

            # Piso de confianza: setup demasiado débil tras penalizaciones → no mostrar
            if bounce_confidence < 40:
                return None

            # Stop basado en ATR: más preciso que % fijo (adapta a la volatilidad real)
            # Estructura: soporte - 1.5x ATR (academia y LuxAlgo)
            # ── La zona de entrada ES la operación ───────────────────────
            # El stop, el objetivo y el R:R se calculaban desde `current_price`
            # mientras la ficha decía «entra entre X e Y». Quien siguiera la
            # instrucción operaba con números que no eran los suyos.
            #
            # HEI salió el 16-sep-2026 cotizando a 296,85 con la zona en
            # 299,38-311,60 y un R:R de 3,21 — cierto solo si entras a 296,85.
            # Entrando arriba de la zona, que es lo que la ficha te manda, el
            # R:R real era 0,28. Y la zona estaba POR ENCIMA del precio porque
            # el soporte ya estaba roto (el precio 2,8% por debajo de él).
            #
            # Dos consecuencias:
            #  · si el soporte está por encima del precio, está roto: no hay
            #    rebote que hacer desde ahí y el setup se descarta;
            #  · todo se calcula desde `entrada_ref`, lo peor que pagarías
            #    siguiendo la instrucción. Si el número sale peor, es que
            #    siempre lo fue.
            if support > current_price:
                return None
            zona_baja = round(support * 0.98, 2)
            zona_alta = round(min(support * 1.02, current_price), 2)
            entrada_ref = zona_alta

            atr_stop = round(support - 1.5 * atr14, 2)
            pct_stop  = round(support * 0.95, 2)
            # Usar el más conservador de los dos (el más cercano al precio)
            stop_loss = max(atr_stop, pct_stop)
            if stop_loss >= entrada_ref:
                return None
            stop_pct = round((stop_loss / entrada_ref - 1) * 100, 1)

            # Techo técnico: hasta dónde llegaría si el rebote se extendiera.
            # Es CONTEXTO, no el objetivo de la operación. Durante meses se
            # publicó como `target` —que es lo que leen la app, el tracker y
            # Telegram— mientras el R:R se calculaba contra el objetivo de
            # rebote. Ninguna ficha cuadraba: 0 de 12 el 16-sep-2026. HEI decía
            # «objetivo +19,5%, R:R 3,21» y ese 3,21 correspondía a +7,0%.
            techo_tecnico = round(resistance, 2)

            # Target corto: rebote realista 1-3 días (+7% o resistencia, lo menor).
            #
            # OJO con el `min`: si la resistencia calculada queda POR DEBAJO del
            # precio actual, el target sale por debajo y la señal se publica
            # igual — una "oportunidad de rebote" que pide comprar a 177 para
            # vender a 156. Pasó el 20-ago-2026 con DVA (-11,6%) y UNH
            # (-10,5%), y llegó a producción.
            #
            # La causa de fondo es que el RSI marcaba sobreventa pero el precio
            # estaba un 22-37% POR ENCIMA del soporte: no hay rebote que hacer
            # desde ahí. Se descarta el setup entero, que es lo honesto — el
            # usuario prefiere 0 señales antes que señales falsas.
            if resistance <= entrada_ref:
                return None
            bounce_target = round(min(entrada_ref * 1.07, resistance), 2)
            bounce_usd = round(bounce_target - entrada_ref, 2)
            bounce_pct = round((bounce_target / entrada_ref - 1) * 100, 1)
            bounce_rr = round(bounce_usd / (entrada_ref - stop_loss), 2) if (entrada_ref - stop_loss) > 0 else 0

            return {
                'ticker': ticker,
                'company_name': company_name or ticker,
                'strategy': 'Oversold Bounce',
                'current_price': round(current_price, 2),
                'rsi': round(current_rsi, 1),
                'rsi_tier': rsi_tier,
                'drawdown_pct': round(drawdown_pct, 1),
                'support_level': round(support, 2),
                'resistance_level': round(resistance, 2),
                'distance_to_support_pct': round(distance_to_support, 1),
                'volume_ratio': round(volume_ratio, 2),
                'reversion_score': round(score, 1),
                'quality': self._get_quality_label(score),
                'entry_zone': f"${zona_baja} - ${zona_alta}",
                'entry_ref': entrada_ref,
                'target': bounce_target,
                'techo_tecnico': techo_tecnico,
                'bounce_target': bounce_target,
                'bounce_usd': bounce_usd,
                'bounce_pct': bounce_pct,
                'stop_loss': stop_loss,
                'stop_pct': stop_pct,
                'risk_reward': bounce_rr,
                # Bounce confidence
                'bounce_confidence': bounce_confidence,
                'bounce_signals': bounce_signals,
                'consecutive_down_days': consecutive_down,
                'bb_pct_b': bb_pct_b,
                'below_bb': below_bb,
                'stoch_k': stoch_k,
                'volume_drying': volume_drying,
                # Nuevas señales avanzadas
                'rsi_weekly': rsi_weekly,
                'weekly_oversold': weekly_oversold,
                'cum_rsi2': cum_rsi2,
                'connors_signal': connors_signal,
                'rsi_divergence': rsi_divergence,
                'atr14': round(atr14, 2),
                'hammer_candle': hammer_candle,
                'engulfing_candle': engulfing_candle,
                'obv_divergence': obv_divergence,
                'market_regime': regime.get('regime_label', 'DESCONOCIDO'),
                'market_ok': market_ok,
                'vix': round(vix_now, 1) if vix_now else None,
                # Earnings
                'days_to_earnings': days_to_earnings,
                'earnings_warning': earnings_warning,
                'detected_date': datetime.now().strftime('%Y-%m-%d')
            }

        except Exception as e:
            print(f"   ⚠️  Error analizando {ticker}: {e}")
            return None

    def detect_bull_flag_pullback(self, ticker: str,
                                  company_name: str = None) -> Dict:
        """
        Detecta bull flag pullbacks

        Criterios:
        - Rally previo > 30%
        - Pullback 10-15%
        - Volumen decreciente en pullback
        - Tendencia mayor alcista (SMA50 > SMA200)
        """
        try:
            stock = yf.Ticker(ticker)

            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.lookback_days)
            hist = stock.history(start=start_date, end=end_date)

            if len(hist) < 100:
                return None

            current_price = hist['Close'].iloc[-1]

            # Filtros básicos de liquidez — igual que oversold bounce
            if current_price < 5.00:
                return None
            avg_dollar_volume_bf = hist['Volume'].tail(20).mean() * current_price
            if avg_dollar_volume_bf < 1_000_000:
                return None

            # Un bull flag se DEFINE por la tendencia mayor alcista (SMA50>SMA200).
            # Sin 200 sesiones no se puede confirmar → no es un setup válido, no
            # inventamos una SMA200 falsa (regla del proyecto: 0 señales > falsas).
            if len(hist) < 200:
                return None

            # Calcular medias móviles
            sma_50 = hist['Close'].rolling(window=50).mean().iloc[-1]
            sma_200 = hist['Close'].rolling(window=200).mean().iloc[-1]

            # RSI diario (informativo en el bull flag; el trigger es el pullback)
            rsi_series = self.calculate_rsi(hist['Close'])
            _last_rsi = rsi_series.iloc[-1] if len(rsi_series) >= 14 else None
            current_rsi_bf = round(float(_last_rsi), 1) if _last_rsi is not None and not pd.isna(_last_rsi) else None
            if current_rsi_bf is None:
                rsi_tier_bf = None
            elif current_rsi_bf < 20:
                rsi_tier_bf = 'EXTREMO'
            elif current_rsi_bf < 30:
                rsi_tier_bf = 'ALTO'
            elif current_rsi_bf < 40:
                rsi_tier_bf = 'MEDIO'
            else:
                rsi_tier_bf = 'NEUTRAL'

            # Buscar rally previo (últimos 60 días)
            low_60d = hist['Close'].tail(60).min()
            high_60d = hist['Close'].tail(60).max()
            rally_pct = ((high_60d - low_60d) / low_60d) * 100

            # Pullback desde high
            pullback_pct = ((current_price - high_60d) / high_60d) * 100

            # Volumen en pullback vs rally
            rally_volume = hist['Volume'].tail(60).head(30).mean()
            pullback_volume = hist['Volume'].tail(30).mean()
            volume_decrease = (pullback_volume / rally_volume) < 0.8 if rally_volume > 0 else False

            # Criterios
            bullish_trend = sma_50 > sma_200
            strong_rally = rally_pct > 30
            healthy_pullback = -15 <= pullback_pct <= -10

            score = 0
            if bullish_trend:
                score += 25
            if strong_rally:
                score += 30
            if healthy_pullback:
                score += 30
            if volume_decrease:
                score += 15

            if score < 60:  # Más estricto para bull flags
                return None

            # El stop cuelga de la SMA50: si el precio ya cayó POR DEBAJO de su
            # media de 50, el stop queda por encima de la entrada — y además
            # deja de ser un bull flag, que por definición retrocede SOBRE la
            # media. UNH salió así el 20-ago: precio 388,61 y stop 402,08.
            # Misma regla que en Oversold Bounce: la zona de entrada es la
            # operación. Aquí la zona es el precio ±2%, así que `entrada_ref`
            # es +2% — lo máximo que pagarías sin salirte de la instrucción.
            zona_baja_bf = round(current_price * 0.98, 2)
            zona_alta_bf = round(current_price * 1.02, 2)
            entrada_ref_bf = zona_alta_bf

            stop_loss_bf = round(sma_50 * 0.97, 2)
            if stop_loss_bf >= entrada_ref_bf:
                return None
            stop_pct_bf = round((stop_loss_bf / entrada_ref_bf - 1) * 100, 1)
            techo_tecnico_bf = round(high_60d, 2)
            # Mismo `min` peligroso que en Oversold Bounce: si el máximo de 60
            # días queda por debajo del precio de hoy —el ticker acaba de hacer
            # nuevo máximo— el target saldría por debajo del precio.
            if high_60d <= entrada_ref_bf:
                return None
            bounce_target_bf = round(min(entrada_ref_bf * 1.07, high_60d), 2)
            bounce_usd_bf = round(bounce_target_bf - entrada_ref_bf, 2)
            bounce_pct_bf = round((bounce_target_bf / entrada_ref_bf - 1) * 100, 1)
            bounce_rr_bf = round(bounce_usd_bf / (entrada_ref_bf - stop_loss_bf), 2) if (entrada_ref_bf - stop_loss_bf) > 0 else 0

            return {
                'ticker': ticker,
                'company_name': company_name or ticker,
                'strategy': 'Bull Flag Pullback',
                'current_price': round(current_price, 2),
                'rsi': current_rsi_bf,
                'rsi_tier': rsi_tier_bf,
                'rally_pct': round(rally_pct, 1),
                'pullback_pct': round(pullback_pct, 1),
                'sma_50': round(sma_50, 2),
                'sma_200': round(sma_200, 2),
                'trend': 'Bullish' if bullish_trend else 'Bearish',
                'volume_decrease': volume_decrease,
                'reversion_score': round(score, 1),
                'quality': self._get_quality_label(score),
                'entry_zone': f"${zona_baja_bf} - ${zona_alta_bf}",
                'entry_ref': entrada_ref_bf,
                'target': bounce_target_bf,
                'techo_tecnico': techo_tecnico_bf,
                'bounce_target': bounce_target_bf,
                'bounce_usd': bounce_usd_bf,
                'bounce_pct': bounce_pct_bf,
                'stop_loss': stop_loss_bf,
                'stop_pct': stop_pct_bf,
                'risk_reward': bounce_rr_bf,
                'detected_date': datetime.now().strftime('%Y-%m-%d')
            }

        except Exception as e:
            print(f"   ⚠️  Error analizando {ticker}: {e}")
            return None

    def _aplicar_veredicto_ia(self, opportunities: list) -> list:
        """El veredicto del gate manda. Hasta hoy no mandaba nada.

        El 16-sep-2026 el CSV publicaba 12 setups. Diez tenían el veredicto en
        contra —ocho "NO" y uno "CAUTION"— y salían igualmente, etiquetados por
        `quality` como "⭐⭐⭐ EXCELENTE" y "⭐⭐ MUY BUENA". Los dos primeros de
        la lista, los dos marcados EXCELENTE, eran los dos rechazados.

        `quality` se calculaba solo desde `reversion_score`, que mide si el
        PATRÓN está bien formado. Eso es una cosa; si el setup es operable hoy,
        otra. Mezclarlas en una sola etiqueta hacía que el sistema se
        contradijera a sí mismo en la misma fila.

        Ahora: "NO" no se publica —el usuario prefiere 0 señales antes que
        señales falsas— y lo que se publica lleva una etiqueta que no puede
        decir más de lo que el gate respalda.
        """
        publicables, rechazados = [], []
        for o in opportunities:
            veredicto = o.get('ai_confirmation')
            if veredicto == 'NO':
                rechazados.append(f"{o['ticker']} ({o.get('ai_reason') or 'sin motivo'})")
                continue
            o['quality'] = self._etiqueta_calidad(o.get('reversion_score', 0), veredicto)
            publicables.append(o)
        if rechazados:
            print(f"   🚫 {len(rechazados)} descartados por el filtro IA: "
                  f"{', '.join(rechazados[:6])}{'…' if len(rechazados) > 6 else ''}")
        return publicables

    def _etiqueta_calidad(self, score: float, veredicto: str | None) -> str:
        """La etiqueta no puede afirmar más de lo que el veredicto respalda."""
        if veredicto is None:
            # El gate no llegó a correr (sin GROQ_API_KEY, o más de 20 setups).
            # Que se note: un hueco silencioso se lee como aprobación.
            return "SIN VERIFICAR"
        if veredicto == 'CAUTION':
            return "⭐ CON DUDAS"
        return self._get_quality_label(score)

    def _get_quality_label(self, score: float) -> str:
        """Retorna etiqueta de calidad según score"""
        if score >= 80:
            return "⭐⭐⭐ EXCELENTE"
        elif score >= 70:
            return "⭐⭐ MUY BUENA"
        elif score >= 60:
            return "⭐ BUENA"
        else:
            return "MODERADA"

    def scan_tickers(self, tickers: List[str],
                    company_names: Dict[str, str] = None) -> List[Dict]:
        """
        Escanea lista de tickers buscando oportunidades de reversión

        Args:
            tickers: Lista de símbolos a analizar
            company_names: Dict opcional {ticker: company_name}

        Returns:
            Lista de oportunidades detectadas
        """
        print(f"🔄 Mean Reversion Detector")
        print(f"   Escaneando {len(tickers)} tickers...")

        # Régimen de mercado — advierte si SPY < MA50 (rebotes en bajista = falling knife)
        regime = self.get_market_regime()
        if regime['regime_label'] != 'DESCONOCIDO':
            icon = '✅' if regime['bounce_ok'] else '⚠️ '
            print(f"   {icon} Régimen mercado: {regime['regime_label']} "
                  f"(SPY ${regime['spy_price']} vs MA50 ${regime['spy_ma50']})")
            if not regime['bounce_ok']:
                print("   ⚠️  SPY < MA50 → mercado bajista. Rebotes de alto riesgo.")
        print()

        opportunities = []

        for i, ticker in enumerate(tickers, 1):
            if i % 50 == 0:
                print(f"   Progreso: {i}/{len(tickers)}")

            company = company_names.get(ticker) if company_names else None

            # Intentar ambas estrategias
            for setup, icono, nombre in (
                (self.detect_oversold_bounce(ticker, company), '🎯', 'Oversold Bounce'),
                (self.detect_bull_flag_pullback(ticker, company), '📊', 'Bull Flag'),
            ):
                if not setup:
                    continue
                ok, motivo = setup_coherente(setup)
                if not ok:
                    print(f"   ⛔ {ticker}: {nombre} descartado — {motivo}")
                    continue
                opportunities.append(setup)
                print(f"   {icono} {ticker}: {nombre} ({setup['reversion_score']:.0f}/100)")

            import time
            time.sleep(0.5)

        # Una señal por ticker mientras la anterior siga viva. Sin esto el
        # detector reemitía el mismo ticker cada día mientras caía: HRI salió
        # SIETE veces entre el 26-ago y el 7-sep (158 → 156 → 157 → 151 → 152
        # → 138 → 139). No son siete oportunidades, es la misma acción cayendo.
        # Y contaminaba las estadísticas: deduplicando, el acierto a 7d de esta
        # estrategia sube del 33% al 45%. Ver `senales_abiertas`.
        import senales_abiertas
        opportunities, omitidos = senales_abiertas.filtrar(opportunities, 'MEAN_REVERSION')
        if omitidos:
            print(f"   🔁 {len(omitidos)} con señal ya abierta, no se reemiten: "
                  f"{', '.join(sorted(set(omitidos))[:8])}"
                  f"{'…' if len(set(omitidos)) > 8 else ''}")

        # Sort by score
        opportunities.sort(key=lambda x: x['reversion_score'], reverse=True)

        print()
        print(f"✅ Scan completado: {len(opportunities)} oportunidades detectadas")

        # Enrich with historical win rate + AI validation
        self._add_win_rates(opportunities)
        self._ai_filter_batch(opportunities)
        opportunities = self._aplicar_veredicto_ia(opportunities)

        # Enrich bounce setups with PCR, short interest, dark pool proxy
        bounce_opps = [o for o in opportunities if o.get('strategy') == 'Oversold Bounce']
        if bounce_opps:
            print(f"🔍 Enriqueciendo {len(bounce_opps)} setups con PCR, short interest y dark pool...")
            self._enrich_bounce_signals(bounce_opps)
            self._tag_conviction_tier(bounce_opps)

        # Lo último, y sobre los pocos que quedan: qué habría pasado con ESTE
        # stop y ESTE objetivo las otras veces que el valor estuvo así.
        self._anadir_esperanza_historica(opportunities)
        opportunities = self._filtrar_por_esperanza(opportunities)

        self.results = opportunities
        return opportunities

    # ── La esperanza real del setup, no la del estado ────────────────────────

    def _anadir_esperanza_historica(self, opportunities: List[Dict]) -> None:
        """Simula el setup —su objetivo y su stop— sobre los episodios análogos.

        La tasa base dice dónde ESTÁ el precio a 45 sesiones. Una operación con
        stop no llega al final: la cierra lo primero que toca. Starbucks el
        17-sep-2026 tenía un 89% de episodios en positivo y una esperanza de
        +0,39%, porque lo típico era caer otro 4% antes de girar y el stop
        estaba a -2,5%. Publicar el 89% al lado de ese setup es enseñar un
        número cierto que responde a otra pregunta.

        Hace falta histórico largo (diez años) y con máximos y mínimos: un stop
        salta intradía. Son pocas descargas porque a estas alturas quedan dos o
        tres candidatos, no el universo entero.
        """
        if not opportunities:
            return
        try:
            from tasa_base import simular_operacion
        except Exception as exc:
            print(f"   ⚠️  esperanza histórica no disponible: {exc}")
            return

        print(f"📐 Simulando {len(opportunities)} setups sobre su propio histórico...")
        for o in opportunities:
            t = o.get('ticker')
            entrada = o.get('entry_ref') or o.get('current_price')
            objetivo, stop = o.get('target'), o.get('stop_loss')
            if not (t and entrada and objetivo and stop):
                continue
            try:
                h = yf.Ticker(t).history(period='10y')
                if h is None or h.empty:
                    continue
                if getattr(h.index, 'tz', None) is not None:
                    h.index = h.index.tz_localize(None)
                r = simular_operacion(h, (objetivo / entrada - 1) * 100,
                                      (stop / entrada - 1) * 100)
            except Exception as exc:
                print(f"   ⚠️  {t}: no se pudo simular ({exc})")
                continue
            # Se publica siempre, también cuando no hay muestra: «no lo sé» es
            # un dato, y callarlo deja al usuario creyendo que no se miró.
            o['esperanza_pct'] = r.get('esperanza_pct')
            o['esperanza_n'] = r.get('n')
            o['esperanza_aciertos'] = r.get('aciertos')
            o['esperanza_stops'] = r.get('stops')
            o['esperanza_dias_mediana'] = r.get('dias_mediana_al_objetivo')
            o['esperanza_muestra_ok'] = r.get('muestra_suficiente')
            o['esperanza_frase'] = r.get('frase')
            if r.get('esperanza_pct') is not None:
                signo = '✅' if r['esperanza_pct'] > 0 else '🚫'
                print(f"   {signo} {t}: esperanza {r['esperanza_pct']:+.2f}% "
                      f"({r['aciertos']}/{r['n']} aciertos"
                      f"{'' if r['muestra_suficiente'] else ', muestra corta'})")

    def _filtrar_por_esperanza(self, opportunities: List[Dict]) -> List[Dict]:
        """Fuera los setups cuya esperanza medida no cubre ni los costes.

        Solo se descarta con MUESTRA SUFICIENTE: sin episodios anteriores no se
        sabe, y «no lo sé» no es motivo para tirar una señal — se publica con
        el aviso puesto. El usuario prefiere 0 señales antes que señales
        falsas, pero eso no es lo mismo que 0 señales antes que señales
        inciertas.
        """
        from tasa_base import ESPERANZA_MINIMA_PCT
        fuera, dentro = [], []
        for o in opportunities:
            e, ok = o.get('esperanza_pct'), o.get('esperanza_muestra_ok')
            if ok and e is not None and e < ESPERANZA_MINIMA_PCT:
                fuera.append((o.get('ticker'), e, o.get('esperanza_n')))
            else:
                dentro.append(o)
        if fuera:
            detalle = ', '.join(f'{t} ({e:+.2f}% en {n} casos)' for t, e, n in fuera)
            print(f"   🚫 {len(fuera)} fuera por esperanza < {ESPERANZA_MINIMA_PCT}%: {detalle}")
        return dentro


    # ── Win rate: del tracker real, o nada ───────────────────────────────────

    # Aquí había una tabla fija que traducía el score a un número:
    #
    #     (90, 100): 100.0      (70, 79): 63.2
    #     (80,  89):  83.9      (60, 69): 71.7
    #
    # y se publicaba en la columna `historical_win_rate`, que el frontend pinta
    # como «100% hist». No venía de ningún histórico: un score de 92 devolvía
    # «100%» porque caía en el primer tramo, y ya. La tabla ni siquiera era
    # monótona — el tramo 60-69 daba MEJOR win rate (71,7%) que el 70-79
    # (63,2%), señal de que salió de un backtest con muestras diminutas por
    # tramo y nadie la revisó.
    #
    # Un número que dice ser medido y no lo es engaña más que no tener número,
    # y va contra la regla de la casa: si el dato falla, no se inventa.
    #
    # Ahora sale del tracker o no sale. Con la muestra de hoy —cero señales con
    # 30 días cumplidos— la columna irá vacía, que es la respuesta honesta
    # hasta que las de agosto cumplan plazo.

    # Mínimo de señales resueltas para publicar un porcentaje. Por debajo, el
    # número diría más del azar que del sistema.
    MUESTRA_MINIMA_WIN_RATE = 30

    def _win_rate_real(self):
        """% de acierto medido en el tracker, al horizonte de esta familia.

        None si no hay muestra suficiente — y entonces no se publica nada.
        """
        try:
            import csv as _csv
            from horizontes import CORTO_PRINCIPAL
            ruta = Path(__file__).parent / 'docs' / 'portfolio_tracker' / 'recommendations.csv'
            if not ruta.exists():
                return None
            col = f'return_{CORTO_PRINCIPAL}'
            vals = []
            with open(ruta) as fh:
                for r in _csv.DictReader(fh):
                    if r.get('strategy') != 'MEAN_REVERSION':
                        continue
                    v = r.get(col)
                    if v in (None, '', 'nan'):
                        continue
                    try:
                        vals.append(float(v))
                    except ValueError:
                        continue
            if len(vals) < self.MUESTRA_MINIMA_WIN_RATE:
                return None
            return 100.0 * sum(1 for x in vals if x > 0) / len(vals)
        except Exception:
            return None

    def _add_win_rates(self, opportunities: list) -> None:
        wr = self._win_rate_real()
        if wr is None:
            print(f"   ℹ️  Sin muestra suficiente (<{self.MUESTRA_MINIMA_WIN_RATE} "
                  f"señales resueltas a {__import__('horizontes').CORTO_PRINCIPAL}): "
                  f"no se publica win rate")
            return
        for opp in opportunities:
            opp['historical_win_rate'] = round(wr, 1)


    # ── Batch AI validation via Groq ─────────────────────────────────────────

    def _ai_filter_batch(self, opportunities: list) -> None:
        """
        Single Groq call to validate up to 20 setups.
        Adds ai_confirmation ('YES'|'CAUTION'|'NO'), ai_confidence (0-100),
        ai_reason (string) to each opportunity. Skips silently if no API key.
        """
        import os
        api_key = os.environ.get('GROQ_API_KEY', '')
        if not api_key or not opportunities:
            for opp in opportunities:
                opp.setdefault('ai_confirmation', None)
                opp.setdefault('ai_confidence', None)
                opp.setdefault('ai_reason', None)
            return

        batch = opportunities[:20]  # cap to avoid token overflow
        regime = self.get_market_regime()
        regime_str = regime.get('regime_label', 'DESCONOCIDO')

        lines = []
        for o in batch:
            campos = [
                f"- {o['ticker']} | {o['strategy']}",
                f"score={o.get('reversion_score', 0):.0f}",
                f"RSI={o.get('rsi', '?')}",
                f"objetivo={o.get('bounce_pct', 0):.1f}%",
                f"stop={o.get('stop_pct', 0):.1f}%",
                f"R:R={o.get('risk_reward', 0):.1f}",
            ]
            if o.get('strategy') == 'Oversold Bounce':
                campos += [
                    f"caída20d={o.get('drawdown_pct', 0):.0f}%",
                    f"al soporte={o.get('distance_to_support_pct', 0):.1f}%",
                    f"vol={o.get('volume_ratio', 0):.2f}x",
                ]
            else:
                campos += [
                    f"rally60d={o.get('rally_pct', 0):.0f}%",
                    f"pullback={o.get('pullback_pct', 0):.1f}%",
                    f"tendencia={o.get('trend', '?')}",
                    f"vol secándose={'sí' if o.get('volume_decrease') else 'no'}",
                ]
            wr = o.get('historical_win_rate')
            campos.append(f"acierto histórico={wr:.0f}%" if wr else "acierto histórico=sin muestra")
            lines.append(' | '.join(campos))
        setups_text = '\n'.join(lines)

        # Cada estrategia, por su criterio.
        #
        # La regla anterior era una sola para las dos: «en mercado bajista o
        # corrección, solo YES si RSI<25 y R:R>2.5». Un Bull Flag Pullback es
        # por definición un retroceso SUAVE dentro de una tendencia alcista
        # (-15% a -10% desde máximos): no tiene ni puede tener RSI<25. Así que
        # en cuanto el mercado entraba en corrección, el gate rechazaba el
        # 100% de los bull flags — no por débiles, sino por no ser algo que no
        # pretenden ser. El 16-sep-2026 los 8 bull flags salieron "NO", todos
        # con el mismo motivo literal: "RSI >25 y R:R bajo".
        #
        # Y ese motivo era falso además de genérico: AJG tenía R:R 11,9 y ROP
        # 4,1. El modelo repetía la plantilla de la regla en vez de mirar el
        # dato. Se le pide ahora que el motivo cite un número concreto.
        #
        # Esto no afloja ningún umbral: el listón del bull flag (tendencia
        # mayor intacta, retroceso dentro de banda, volumen secándose) es el
        # que define el patrón, y en corrección se exige entero.
        prompt = f"""Eres un analista técnico. Valida estos setups de entrada a corto plazo (1-5 días) en el contexto actual del mercado.

Régimen de mercado actual: {regime_str}

Setups a validar:
{setups_text}

Cada estrategia se juzga por SU criterio, no por el de la otra:

· "Oversold Bounce" — agotamiento de una caída. Buscas RSI bajo (<25 es
  extremo), precio cerca del soporte por ENCIMA de él, y volumen de capitulación.
  Un RSI alto lo invalida.

· "Bull Flag Pullback" — respiro dentro de una tendencia alcista. Un RSI de 30-45
  es lo NORMAL y lo correcto aquí: un RSI de 20 significaría que la tendencia se
  ha roto, no que el setup sea mejor. Buscas tendencia mayor intacta (Bullish),
  retroceso contenido (-15% a -10%) y volumen secándose en el retroceso. NO
  penalices un RSI>25 en esta estrategia.

En mercado BAJISTA o CORRECCIÓN sé más exigente con las dos: el Oversold necesita
RSI<25, y el Bull Flag necesita la tendencia mayor intacta Y el volumen secándose.

Responde ÚNICAMENTE con JSON válido:
{{"results": [{{"ticker":"X","confirmation":"YES","confidence":85,"reason":"RSI 18 y soporte a 1,2%"}}, ...]}}

Reglas:
- confirmation: "YES" si el setup es válido, "CAUTION" si hay dudas, "NO" si hay razones para evitarlo
- confidence: 0-100 (cuánta convicción tienes)
- reason: máximo 8 palabras en español y DEBE citar un número concreto de la ficha.
  Nada de motivos genéricos: si dices "R:R bajo", el R:R tiene que ser bajo de verdad"""

        try:
            from groq import Groq
            from groq_utils import groq_chat as _groq_chat
            client = Groq(api_key=api_key)
            resp = _groq_chat(
                client,
                messages=[{'role': 'user', 'content': prompt}],
                max_tokens=600,
                temperature=0.15,
                response_format={"type": "json_object"},
            )
            raw = resp.choices[0].message.content.strip()
            parsed = json.loads(raw)
            ai_results = parsed.get('results', [])
            ai_map = {r['ticker']: r for r in ai_results if isinstance(r, dict)}
            for opp in opportunities:
                ai = ai_map.get(opp['ticker'], {})
                opp['ai_confirmation'] = ai.get('confirmation', None)
                opp['ai_confidence']   = ai.get('confidence', None)
                opp['ai_reason']       = ai.get('reason', None)
            print(f"  🤖 AI validó {len(ai_map)} setups ({sum(1 for o in batch if o.get('ai_confirmation')=='YES')} YES / "
                  f"{sum(1 for o in batch if o.get('ai_confirmation')=='CAUTION')} CAUTION / "
                  f"{sum(1 for o in batch if o.get('ai_confirmation')=='NO')} NO)")
            return
        except Exception as e:
            print(f"  ⚠️  AI filter skipped: {e}")

        # Fallback: set None
        for opp in opportunities:
            opp.setdefault('ai_confirmation', None)
            opp.setdefault('ai_confidence', None)
            opp.setdefault('ai_reason', None)

    def _enrich_bounce_signals(self, opportunities: list) -> None:
        """
        Enriquece oportunidades de rebote con señales externas gratuitas:
        - PCR (Put/Call Ratio) desde CBOE CDN — JSON, sin auth, 15min delay
        - Short interest desde Nasdaq API — JSON, sin auth, bi-semanal
        - Dark pool proxy (off-exchange %) desde FINRA CDN — pipe-delimited, diario

        Fuentes verificadas sin API key ni pago.
        """
        HEADERS = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
        }

        # ── Cargar FINRA dark pool (un solo fichero para todo el batch) ─────────
        finra_dark: Dict[str, float] = {}  # ticker → short_pct_of_volume hoy
        try:
            today_str = date.today().strftime("%Y%m%d")
            # Probar hoy y los 3 días previos (puede no estar publicado aún hoy)
            for delta in range(4):
                dt = date.today() - timedelta(days=delta)
                if dt.weekday() >= 5:
                    continue
                fname = dt.strftime("%Y%m%d")
                url = f"https://cdn.finra.org/equity/regsho/daily/CNMSshvol{fname}.txt"
                r = requests.get(url, headers=HEADERS, timeout=10)
                if r.status_code == 200:
                    from io import StringIO
                    df_finra = pd.read_csv(StringIO(r.text), sep="|", skipfooter=1, engine="python")
                    df_finra.columns = df_finra.columns.str.strip()
                    for _, row in df_finra.iterrows():
                        sym = str(row.get("Symbol", "")).strip()
                        short_vol = row.get("ShortVolume", 0) or 0
                        total_vol = row.get("TotalVolume", 1) or 1
                        if sym:
                            finra_dark[sym] = round(float(short_vol) / float(total_vol) * 100, 1)
                    print(f"   📊 FINRA dark pool: {fname} ({len(finra_dark)} tickers)")
                    break
        except Exception as e:
            print(f"   ⚠️  FINRA dark pool fallido: {e}")

        # ── Por ticker: PCR (CBOE) + short interest (Nasdaq) ────────────────────
        for opp in opportunities:
            ticker = opp.get("ticker", "")

            # ── PCR desde CBOE CDN ───────────────────────────────────────────
            try:
                url = f"https://cdn.cboe.com/api/global/delayed_quotes/options/{ticker}.json"
                r = requests.get(url, headers=HEADERS, timeout=8)
                if r.status_code == 200:
                    opts = r.json().get("data", {}).get("options", [])
                    # Option symbol format: TICKER+YYMMDD+[C/P]+PRICE8 — type at 9th char from right
                    def _opt_type(o):
                        sym = o.get("option", "")
                        return sym[-9] if len(sym) >= 9 else ""
                    put_vol  = sum(o.get("volume", 0) or 0 for o in opts if _opt_type(o) == "P")
                    call_vol = sum(o.get("volume", 0) or 0 for o in opts if _opt_type(o) == "C")
                    pcr = round(put_vol / call_vol, 2) if call_vol > 0 else None
                    opp["pcr"] = pcr
                    # PCR > 1.5 = puts muy elevadas = contrarian bullish (hedging exagerado)
                    opp["pcr_signal"] = "CONTRARIAN_BULLISH" if pcr and pcr > 1.5 else \
                                        "NEUTRAL" if pcr else None
                    if pcr and pcr > 1.5:
                        opp["bounce_signals"] = opp.get("bounce_signals", []) + [f"PCR {pcr:.1f}↑"]
                        opp["bounce_confidence"] = min(100, opp.get("bounce_confidence", 0) + 10)
            except Exception:
                opp["pcr"] = None
                opp["pcr_signal"] = None

            # ── Short interest desde Nasdaq API ──────────────────────────────
            try:
                url = (
                    f"https://api.nasdaq.com/api/quote/{ticker.lower()}/short-interest"
                    "?type=SHORT_INTEREST&assetClass=stocks"
                )
                headers_nasdaq = {**HEADERS, "Referer": f"https://www.nasdaq.com/market-activity/stocks/{ticker.lower()}/short-interest"}
                r = requests.get(url, headers=headers_nasdaq, timeout=8)
                if r.status_code == 200:
                    rows = r.json().get("data", {}).get("shortInterestTable", {}).get("rows", [])
                    if rows:
                        latest = rows[0]
                        # Nasdaq field names: "interest" (shares), "daysToCover", "avgDailyShareVolume"
                        short_int = str(latest.get("interest", "") or "").replace(",", "")
                        dtc_raw = latest.get("daysToCover")
                        avg_vol_raw = str(latest.get("avgDailyShareVolume", "") or "").replace(",", "")
                        dtc = float(dtc_raw) if dtc_raw else None
                        si_shares = int(float(short_int)) if short_int and short_int.replace('.','').isdigit() else None
                        avg_vol = int(float(avg_vol_raw)) if avg_vol_raw and avg_vol_raw.replace('.','').isdigit() else None
                        # Approximate % float: not available directly — use DTC as squeeze proxy
                        opp["short_interest_shares"] = si_shares
                        opp["short_days_to_cover"] = dtc
                        opp["short_pct_float"] = None  # Nasdaq doesn't provide this field
                        # Short squeeze potential: DTC > 5 days
                        squeeze = bool(dtc and dtc > 5)
                        opp["squeeze_potential"] = bool(squeeze)
                        if squeeze:
                            opp["bounce_signals"] = opp.get("bounce_signals", []) + [f"DTC {dtc:.1f}d" if dtc else "Short squeeze"]
                            opp["bounce_confidence"] = min(100, opp.get("bounce_confidence", 0) + 8)
            except Exception:
                opp["short_interest_shares"] = None
                opp["short_days_to_cover"] = None
                opp["short_pct_float"] = None
                opp["squeeze_potential"] = False

            # ── Dark pool proxy desde FINRA ──────────────────────────────────
            finra_pct = finra_dark.get(ticker)
            opp["finra_short_vol_pct"] = finra_pct
            # > 60% = volumen bajista dominante en dark pool; < 40% = compradores dominan
            if finra_pct is not None:
                if finra_pct < 40:
                    opp["dark_pool_signal"] = "ACCUMULATION"
                    opp["bounce_signals"] = opp.get("bounce_signals", []) + [f"DP acumulación ({finra_pct:.0f}%)"]
                    opp["bounce_confidence"] = min(100, opp.get("bounce_confidence", 0) + 8)
                elif finra_pct > 60:
                    opp["dark_pool_signal"] = "DISTRIBUTION"
                else:
                    opp["dark_pool_signal"] = "NEUTRAL"
            else:
                opp["dark_pool_signal"] = None

            print(f"   ✅ {ticker}: PCR={opp.get('pcr')} | Short%={opp.get('short_pct_float')} | DP={opp.get('finra_short_vol_pct')} | conf={opp.get('bounce_confidence')}")

    def _tag_conviction_tier(self, bounce_opps: list) -> None:
        """
        Tier 2 = rebote técnico + empresa fundamentalmente sólida (también en VALUE ≥60).
        Tier 1 = rebote puramente técnico (puede ser empresa débil, pero el setup es válido).
        Cross-referencia con value_opportunities.csv sin llamadas externas.
        """
        value_scores: Dict[str, Dict] = {}
        for csv_path in ["docs/value_opportunities.csv", "docs/european_value_opportunities.csv"]:
            try:
                df = pd.read_csv(csv_path)
                for _, row in df.iterrows():
                    ticker = str(row.get("ticker", "")).strip()
                    score = row.get("value_score") or row.get("score")
                    grade = row.get("grade", "")
                    if ticker and score:
                        value_scores[ticker] = {"value_score": float(score), "value_grade": str(grade)}
            except Exception:
                pass

        for opp in bounce_opps:
            ticker = opp.get("ticker", "")
            v = value_scores.get(ticker)
            if v and v["value_score"] >= 60:
                opp["conviction_tier"] = 2
                opp["value_score"] = v["value_score"]
                opp["value_grade"] = v["value_grade"]
                # Boost confianza: empresa buena + caída técnica = alta convicción
                opp["bounce_confidence"] = min(100, opp.get("bounce_confidence", 0) + 15)
                print(f"   ⭐ {ticker}: Tier 2 — VALUE score {v['value_score']:.0f} ({v['value_grade']})")
            else:
                opp["conviction_tier"] = 1
                opp["value_score"] = None
                opp["value_grade"] = None

    def save_results(self, output_path: str = "docs/mean_reversion_opportunities.csv"):
        """Guarda resultados en CSV.

        Cero oportunidades es un resultado, no un fallo: hay que publicarlo.
        Antes se hacía `return` sin tocar los ficheros, así que el CSV del día
        anterior seguía en producción y la app mostraba una señal caducada como
        si fuera de hoy — indefinidamente, hasta que hubiera otra. Justo lo que
        pasó con AJG: al aplicarle el suelo de R:R el scan salió a cero y AJG
        se habría quedado publicado para siempre.
        """
        # Ordenar columnas
        cols_order = [
            'ticker', 'company_name', 'strategy', 'quality', 'reversion_score',
            'current_price', 'entry_zone', 'target', 'stop_loss', 'risk_reward',
            # La esperanza va junto al R:R y antes que el veredicto de la IA:
            # es el número que decide si la operación merece el dinero.
            'esperanza_pct', 'esperanza_n', 'esperanza_aciertos', 'esperanza_stops',
            'esperanza_dias_mediana', 'esperanza_muestra_ok',
            'ai_confirmation', 'ai_confidence', 'ai_reason', 'historical_win_rate',
            'detected_date'
        ]

        if not self.results:
            print("ℹ️  0 oportunidades — se publica vacío para no dejar zombis")
            df = pd.DataFrame(columns=cols_order)
        else:
            df = pd.DataFrame(self.results)

            # Añadir columnas restantes
            remaining_cols = [c for c in df.columns if c not in cols_order]
            final_cols = cols_order + remaining_cols
            final_cols = [c for c in final_cols if c in df.columns]  # Solo las que existen

            df = df[final_cols]

        # Guardar
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)

        print(f"💾 Resultados guardados: {output_path}")

        # También guardar JSON para dashboard
        json_path = output_path.with_suffix('.json')

        # Convertir a tipos nativos de Python para JSON
        json_safe_results = []
        for r in self.results:
            json_safe = {}
            for k, v in r.items():
                if isinstance(v, (np.integer, np.floating)):
                    fv = float(v)
                    json_safe[k] = None if math.isnan(fv) or math.isinf(fv) else fv
                elif isinstance(v, float):
                    json_safe[k] = None if math.isnan(v) or math.isinf(v) else v
                elif isinstance(v, np.bool_):
                    json_safe[k] = bool(v)
                else:
                    json_safe[k] = v
            json_safe_results.append(json_safe)

        # ── AI narrative ──────────────────────────────────────────────────
        ai_narrative = None
        try:
            import os
            from groq import Groq as _Groq
            _key = os.environ.get('GROQ_API_KEY', '')
            if _key and self.results:
                _client = _Groq(api_key=_key)
                _top = self.results[:5]
                _top_text = '\n'.join([
                    f"- {r['ticker']} ({r['strategy']}) score={r.get('reversion_score', 0):.0f}"
                    f" RSI={r.get('rsi', '?')} drawdown={r.get('drawdown_pct', 0):.0f}%"
                    f" R:R={r.get('risk_reward', 0):.1f}"
                    for r in _top
                ])
                _prompt = f"""Eres un analista de mean reversion y value. Analiza este batch de {len(self.results)} setups de reversión a la media y genera un insight en español (3-4 frases, máx 110 palabras).

Distribución: {len([r for r in self.results if r['strategy']=='Oversold Bounce'])} oversold bounce, {len([r for r in self.results if r['strategy']=='Bull Flag Pullback'])} bull flag pullback
Top 5 setups:
{_top_text}

Analiza: 1) Calidad general del batch actual, 2) Si hay concentración sectorial, 3) Cómo filtrar los mejores en este entorno.
Tono: técnico, directo. Sin emojis."""
                from groq_utils import groq_chat as _groq_chat_mr
                _resp = _groq_chat_mr(
                    _client,
                    messages=[{'role': 'user', 'content': _prompt}],
                    max_tokens=180,
                    temperature=0.25,
                )
                ai_narrative = _resp.choices[0].message.content.strip()
                print(f"  MR AI: {ai_narrative[:80]}...")
        except Exception as _e:
            print(f"  MR Groq skipped: {_e}")

        # `generated_at` es la clave que mira el watchdog de frescura
        # (daily-analysis.yml, MODULES['mean_reversion']). Este JSON solo
        # escribía `scan_date`, así que el watchdog no encontraba fecha y caía
        # al mtime del fichero — que en un runner de CI es SIEMPRE el del
        # checkout, o sea hoy. Resultado: si el detector crasheaba, el JSON
        # viejo del repo se marcaba 'ok' igualmente y nadie se enteraba. Es el
        # mismo fallo que ya está documentado para VCP ("el mtime miente en
        # CI"). `scan_date` se mantiene por si algo lo lee.
        ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        results_dict = {
            'generated_at': ahora,
            'scan_date': ahora,
            'total_opportunities': len(self.results),
            'strategies': {
                'oversold_bounce': len([r for r in self.results if r['strategy'] == 'Oversold Bounce']),
                'bull_flag_pullback': len([r for r in self.results if r['strategy'] == 'Bull Flag Pullback'])
            },
            'ai_narrative': ai_narrative,
            'opportunities': json_safe_results
        }

        with open(json_path, 'w') as f:
            json.dump(results_dict, f, indent=2)

        print(f"📊 JSON guardado: {json_path}")


def load_5d_opportunities() -> Tuple[List[str], Dict[str, str]]:
    """Carga tickers del universo curado (Tier 1+2+3, ~105 empresas de calidad)."""
    from curated_tickers import get_universe
    tickers = get_universe(include_hf_watch=True)

    # Intentar cargar company_names desde fundamental_scores si existe
    company_names = {}
    fs_path = Path("docs/fundamental_scores.csv")
    if fs_path.exists():
        try:
            df = pd.read_csv(fs_path)
            if 'company_name' in df.columns:
                company_names = dict(zip(df['ticker'], df['company_name']))
        except Exception:
            pass

    print(f"📊 Cargados {len(tickers)} tickers desde universo curado")
    return tickers, company_names


def main():
    """Main execution"""
    print("=" * 80)
    print("🔄 MEAN REVERSION DETECTOR")
    print("   Identifica oportunidades de compra en dips de calidad")
    print("=" * 80)
    print()

    # Cargar tickers
    tickers, company_names = load_5d_opportunities()

    # Ejecutar detector
    detector = MeanReversionDetector()
    opportunities = detector.scan_tickers(tickers, company_names)

    # Guardar resultados
    detector.save_results()

    # Mostrar top 10
    if opportunities:
        print()
        print("=" * 80)
        print("🏆 TOP 10 OPORTUNIDADES DE REVERSIÓN")
        print("=" * 80)
        print()

        for i, opp in enumerate(opportunities[:10], 1):
            print(f"{i}. {opp['ticker']} - {opp['company_name']}")
            print(f"   Estrategia: {opp['strategy']}")
            print(f"   Score: {opp['reversion_score']:.0f}/100 ({opp['quality']})")
            print(f"   Precio: ${opp['current_price']:.2f}")
            print(f"   Entry: {opp['entry_zone']}")
            print(f"   Target: ${opp['target']:.2f} | Stop: ${opp['stop_loss']:.2f}")
            print(f"   R/R: {opp['risk_reward']:.1f}:1")
            print()
    else:
        print("ℹ️  No se detectaron oportunidades de reversión en este momento")

    print("=" * 80)
    print("✅ Mean Reversion Detector completado")
    print("=" * 80)


if __name__ == "__main__":
    main()
