#!/usr/bin/env python3
"""
Technical Signal Analyzer
Detects bullish/bearish technical signals for portfolio + value opportunities.
Output: docs/technical_signals.csv + docs/technical_signals_summary.csv
"""

import pandas as pd
import numpy as np
import yfinance as yf
import os
import json
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

DOCS_DIR = "docs"
OUTPUT_SIGNALS = os.path.join(DOCS_DIR, "technical_signals.csv")
OUTPUT_SUMMARY = os.path.join(DOCS_DIR, "technical_signals_summary.csv")


# ─── Indicator Calculations ────────────────────────────────────────────────

def sma(series, period):
    return series.rolling(window=period, min_periods=period).mean()

def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def macd(series, fast=12, slow=26, signal=9):
    macd_line = ema(series, fast) - ema(series, slow)
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def bollinger_bands(series, period=20, std_dev=2):
    middle = sma(series, period)
    std = series.rolling(window=period).std()
    upper = middle + std_dev * std
    lower = middle - std_dev * std
    bandwidth = (upper - lower) / middle
    return upper, middle, lower, bandwidth


# ─── Signal Detectors ─────────────────────────────────────────────────────

def detect_signals(ticker, df_daily, df_weekly, company_name="", source=""):
    signals = []

    def add(name, direction, timeframe, triggered_date, description, strength):
        signals.append({
            "ticker": ticker,
            "company_name": company_name,
            "source": source,
            "signal_name": name,
            "direction": direction,  # BULLISH / BEARISH / NEUTRAL
            "timeframe": timeframe,  # DAILY / WEEKLY
            "triggered_date": triggered_date,
            "days_ago": (datetime.now().date() - pd.to_datetime(triggered_date).date()).days,
            "description": description,
            "strength": strength,  # 1=weak, 2=moderate, 3=strong
        })

    for label, df in [("DAILY", df_daily), ("WEEKLY", df_weekly)]:
        if df is None or len(df) < 50:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]
        open_ = df["Open"]
        dates = df.index

        # ── Moving Averages ──
        ma20 = sma(close, 20)
        ma50 = sma(close, 50)
        ma200 = sma(close, 200) if len(df) >= 200 else pd.Series([np.nan]*len(df), index=df.index)

        last_date = str(dates[-1].date())

        # Golden Cross (50 crossed above 200 in last 10 bars)
        if len(df) >= 200:
            for i in range(max(1, len(df)-10), len(df)):
                if (pd.notna(ma50.iloc[i]) and pd.notna(ma200.iloc[i]) and
                    pd.notna(ma50.iloc[i-1]) and pd.notna(ma200.iloc[i-1])):
                    if ma50.iloc[i-1] <= ma200.iloc[i-1] and ma50.iloc[i] > ma200.iloc[i]:
                        cross_date = str(dates[i].date())
                        add("Golden Cross", "BULLISH", label, cross_date,
                            f"MA50 cruzó por encima de MA200 — inicio de tendencia alcista de largo plazo",
                            3)
                    elif ma50.iloc[i-1] >= ma200.iloc[i-1] and ma50.iloc[i] < ma200.iloc[i]:
                        cross_date = str(dates[i].date())
                        add("Death Cross", "BEARISH", label, cross_date,
                            f"MA50 cruzó por debajo de MA200 — señal bajista de largo plazo",
                            3)

        # Price vs MAs (current state)
        curr_close = close.iloc[-1]
        curr_ma50 = ma50.iloc[-1]
        curr_ma200 = ma200.iloc[-1] if len(df) >= 200 else np.nan

        if pd.notna(curr_ma50):
            pct_vs_ma50 = (curr_close - curr_ma50) / curr_ma50 * 100
            if pct_vs_ma50 > 0:
                add("Precio sobre MA50", "BULLISH", label, last_date,
                    f"Precio {pct_vs_ma50:+.1f}% sobre MA50 — soporte dinámico activo",
                    1 if abs(pct_vs_ma50) < 5 else 2)
            elif pct_vs_ma50 < -8:
                add("Precio bajo MA50", "BEARISH", label, last_date,
                    f"Precio {pct_vs_ma50:+.1f}% bajo MA50 — tendencia deteriorada",
                    2)

        if pd.notna(curr_ma200):
            pct_vs_ma200 = (curr_close - curr_ma200) / curr_ma200 * 100
            if pct_vs_ma200 < -15:
                add("Precio bajo MA200", "BEARISH", label, last_date,
                    f"Precio {pct_vs_ma200:+.1f}% bajo MA200 — tendencia bajista estructural",
                    3)
            elif pct_vs_ma200 > 20:
                add("Extendido sobre MA200", "BEARISH", label, last_date,
                    f"Precio {pct_vs_ma200:+.1f}% sobre MA200 — sobreextensión, riesgo de corrección",
                    2)

        # MA50 bounce (price pulled back to MA50 and bounced, last 5 bars)
        if pd.notna(curr_ma50) and len(df) >= 60:
            for i in range(max(2, len(df)-5), len(df)):
                lo = low.iloc[i]
                ma = ma50.iloc[i]
                cl = close.iloc[i]
                if pd.notna(ma) and lo <= ma * 1.01 and cl > ma * 1.01:
                    # candle touched MA50 but closed above
                    body = abs(cl - open_.iloc[i])
                    lower_wick = min(open_.iloc[i], cl) - lo
                    if lower_wick > body * 0.5:
                        add("Rebote MA50", "BULLISH", label, str(dates[i].date()),
                            f"Precio testó MA50 y rebotó con mecha inferior — soporte validado",
                            2)
                        break

        # ── RSI ──
        rsi_vals = rsi(close)
        curr_rsi = rsi_vals.iloc[-1]

        if pd.notna(curr_rsi):
            if curr_rsi < 30:
                add("RSI Sobrevendido", "BULLISH", label, last_date,
                    f"RSI {curr_rsi:.1f} — zona de sobreventa extrema, posible rebote",
                    3 if curr_rsi < 25 else 2)
            elif curr_rsi < 40:
                add("RSI Zona Baja", "BULLISH", label, last_date,
                    f"RSI {curr_rsi:.1f} — presión vendedora cediendo",
                    1)
            elif curr_rsi > 75:
                add("RSI Sobrecomprado", "BEARISH", label, last_date,
                    f"RSI {curr_rsi:.1f} — zona de sobrecompra, riesgo de reversión",
                    2 if curr_rsi < 80 else 3)

        # RSI Bullish Divergence (price makes lower low, RSI makes higher low — last 20 bars)
        if len(rsi_vals.dropna()) >= 20:
            window = 20
            price_window = close.iloc[-window:]
            rsi_window = rsi_vals.iloc[-window:].dropna()
            if len(rsi_window) >= 10:
                price_lows_idx = price_window.nsmallest(3).index
                if len(price_lows_idx) >= 2:
                    sorted_lows = sorted(price_lows_idx, key=lambda x: dates.get_loc(x) if x in dates else 0)
                    if len(sorted_lows) >= 2:
                        i1, i2 = sorted_lows[0], sorted_lows[-1]
                        if i1 != i2 and i1 in rsi_window.index and i2 in rsi_window.index:
                            p_lower = price_window[i2] < price_window[i1]
                            rsi_higher = rsi_window[i2] > rsi_window[i1] + 3
                            if p_lower and rsi_higher:
                                add("Divergencia RSI Alcista", "BULLISH", label, last_date,
                                    f"Precio hace mínimos más bajos pero RSI hace mínimos más altos — presión bajista agotándose",
                                    3)

        # ── MACD ──
        macd_line, signal_line, histogram = macd(close)
        if len(macd_line.dropna()) >= 5:
            for i in range(max(1, len(df)-5), len(df)):
                m = macd_line.iloc[i]
                s = signal_line.iloc[i]
                mp = macd_line.iloc[i-1]
                sp = signal_line.iloc[i-1]
                if pd.notna(m) and pd.notna(s) and pd.notna(mp) and pd.notna(sp):
                    if mp <= sp and m > s:
                        add("MACD Cruce Alcista", "BULLISH", label, str(dates[i].date()),
                            f"Línea MACD cruzó por encima de la señal — momentum alcista activado",
                            2 if m < 0 else 1)
                        break
                    elif mp >= sp and m < s:
                        add("MACD Cruce Bajista", "BEARISH", label, str(dates[i].date()),
                            f"Línea MACD cruzó por debajo de la señal — momentum bajista",
                            2 if m > 0 else 1)
                        break

            # MACD histogram momentum
            hist_last = histogram.iloc[-1]
            hist_prev = histogram.iloc[-2] if len(histogram) > 1 else np.nan
            if pd.notna(hist_last) and pd.notna(hist_prev):
                if hist_last > 0 and hist_last > hist_prev * 1.2:
                    add("MACD Histograma Creciente", "BULLISH", label, last_date,
                        f"Histograma MACD positivo y en expansión — momentum alcista acelerando",
                        1)
                elif hist_last < 0 and hist_last < hist_prev * 1.2:
                    add("MACD Histograma Cayendo", "BEARISH", label, last_date,
                        f"Histograma MACD negativo y expandiéndose — presión bajista acelerando",
                        1)

        # ── Bollinger Bands ──
        bb_upper, bb_mid, bb_lower, bb_bw = bollinger_bands(close)
        if len(bb_upper.dropna()) >= 5:
            curr_upper = bb_upper.iloc[-1]
            curr_lower = bb_lower.iloc[-1]
            curr_bw = bb_bw.iloc[-1]

            if pd.notna(curr_lower) and curr_close <= curr_lower * 1.01:
                add("Toque Banda Inferior BB", "BULLISH", label, last_date,
                    f"Precio tocando banda inferior de Bollinger — zona de sobreventa estadística",
                    2)
            elif pd.notna(curr_upper) and curr_close >= curr_upper * 0.99:
                add("Toque Banda Superior BB", "BEARISH", label, last_date,
                    f"Precio en banda superior de Bollinger — posible sobreextensión",
                    1)

            # BB Squeeze (bandwidth in bottom 15% of last 6 months = 120 bars)
            if pd.notna(curr_bw) and len(bb_bw.dropna()) >= 60:
                bw_history = bb_bw.dropna().iloc[-120:]
                threshold = bw_history.quantile(0.15)
                if curr_bw <= threshold:
                    add("Squeeze Bollinger", "BULLISH", label, last_date,
                        f"Bandas de Bollinger comprimidas (percentil {(curr_bw/bw_history.max()*100):.0f}%) — compresión previa a movimiento explosivo",
                        2)

        # ── Volume Signals ──
        if len(volume.dropna()) >= 20:
            avg_vol_20 = volume.iloc[-21:-1].mean()
            curr_vol = volume.iloc[-1]
            curr_change = (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100 if len(close) > 1 else 0

            if pd.notna(avg_vol_20) and avg_vol_20 > 0 and pd.notna(curr_vol):
                vol_ratio = curr_vol / avg_vol_20
                if vol_ratio >= 2.0:
                    if curr_change > 0:
                        add("Volumen Extraordinario Alcista", "BULLISH", label, last_date,
                            f"Volumen {vol_ratio:.1f}x la media en día alcista — compra institucional",
                            3 if vol_ratio >= 3 else 2)
                    else:
                        add("Volumen Extraordinario Bajista", "BEARISH", label, last_date,
                            f"Volumen {vol_ratio:.1f}x la media en día bajista — distribución institucional",
                            3 if vol_ratio >= 3 else 2)

            # Dry volume on pullback (low volume on down days = healthy consolidation)
            if len(df) >= 5:
                last5_down_days = [(close.iloc[i] < close.iloc[i-1]) for i in range(-5, 0)]
                last5_vol = [volume.iloc[i] / avg_vol_20 for i in range(-5, 0) if pd.notna(avg_vol_20) and avg_vol_20 > 0]
                if any(last5_down_days) and last5_vol:
                    down_vol_ratios = [last5_vol[i] for i in range(len(last5_down_days)) if last5_down_days[i]]
                    if down_vol_ratios and max(down_vol_ratios) < 0.7:
                        add("Pullback Volumen Seco", "BULLISH", label, last_date,
                            f"Retroceso reciente con volumen <70% de la media — presión vendedora débil, consolidación saludable",
                            2)

        # ── Candlestick Patterns (last 5 daily bars only) ──
        if label == "DAILY" and len(df) >= 5:
            for i in range(max(1, len(df)-5), len(df)):
                o = open_.iloc[i]
                h = high.iloc[i]
                lo = low.iloc[i]
                c = close.iloc[i]
                body = abs(c - o)
                full_range = h - lo
                if full_range < 0.001:
                    continue
                upper_wick = h - max(o, c)
                lower_wick = min(o, c) - lo

                candle_date = str(dates[i].date())
                days_old = (datetime.now().date() - pd.to_datetime(candle_date).date()).days
                if days_old > 10:
                    continue

                # Hammer (lower wick >= 2x body, small upper wick, bullish)
                if body > 0 and lower_wick >= 2 * body and upper_wick <= body * 0.5 and full_range > 0:
                    add("Hammer", "BULLISH", label, candle_date,
                        f"Vela Hammer: mecha inferior larga, cuerpo pequeño — rechazo bajista, posible suelo",
                        2)

                # Shooting Star (upper wick >= 2x body, small lower wick, bearish)
                elif body > 0 and upper_wick >= 2 * body and lower_wick <= body * 0.5 and full_range > 0:
                    add("Shooting Star", "BEARISH", label, candle_date,
                        f"Vela Shooting Star: mecha superior larga — rechazo alcista, posible techo",
                        2)

                # Doji (body < 10% of range)
                elif full_range > 0 and body / full_range < 0.1:
                    prev_trend = close.iloc[i-1] - close.iloc[max(0,i-5)]
                    if prev_trend < 0:
                        add("Doji en Caída", "BULLISH", label, candle_date,
                            f"Doji después de tendencia bajista — indecisión, posible agotamiento vendedor",
                            1)
                    else:
                        add("Doji en Subida", "BEARISH", label, candle_date,
                            f"Doji después de subida — indecisión, posible agotamiento comprador",
                            1)

            # Bullish/Bearish Engulfing (last 2 bars)
            if len(df) >= 3:
                for i in range(max(1, len(df)-4), len(df)):
                    o_prev = open_.iloc[i-1]
                    c_prev = close.iloc[i-1]
                    o_curr = open_.iloc[i]
                    c_curr = close.iloc[i]
                    candle_date = str(dates[i].date())
                    days_old = (datetime.now().date() - pd.to_datetime(candle_date).date()).days
                    if days_old > 10:
                        continue

                    prev_body = abs(c_prev - o_prev)
                    curr_body = abs(c_curr - o_curr)
                    if prev_body < 0.001 or curr_body < 0.001:
                        continue

                    # Bullish engulfing: prev bearish, curr bullish and engulfs prev body
                    if (c_prev < o_prev and c_curr > o_curr and
                        o_curr < c_prev and c_curr > o_prev):
                        add("Bullish Engulfing", "BULLISH", label, candle_date,
                            f"Vela alcista que envuelve la bajista anterior — fuerte reversión compradora",
                            3)

                    # Bearish engulfing: prev bullish, curr bearish and engulfs prev body
                    elif (c_prev > o_prev and c_curr < o_curr and
                          o_curr > c_prev and c_curr < o_prev):
                        add("Bearish Engulfing", "BEARISH", label, candle_date,
                            f"Vela bajista que envuelve la alcista anterior — fuerte reversión vendedora",
                            3)

            # Morning Star (3-candle: bearish + small body + bullish closing above midpoint of first)
            if len(df) >= 5:
                for i in range(max(2, len(df)-5), len(df)):
                    o1, c1 = open_.iloc[i-2], close.iloc[i-2]
                    o2, c2 = open_.iloc[i-1], close.iloc[i-1]
                    o3, c3 = open_.iloc[i], close.iloc[i]
                    candle_date = str(dates[i].date())
                    days_old = (datetime.now().date() - pd.to_datetime(candle_date).date()).days
                    if days_old > 10:
                        continue
                    body1 = abs(c1 - o1)
                    body2 = abs(c2 - o2)
                    body3 = abs(c3 - o3)
                    midpoint1 = (o1 + c1) / 2
                    if (body1 > 0 and body2 < body1 * 0.4 and body3 > body1 * 0.5 and
                        c1 < o1 and c3 > o3 and c3 > midpoint1):
                        add("Morning Star", "BULLISH", label, candle_date,
                            f"Patrón Morning Star (3 velas) — reversión alcista de alta fiabilidad",
                            3)

                    # Evening Star (reverse)
                    if (body1 > 0 and body2 < body1 * 0.4 and body3 > body1 * 0.5 and
                        c1 > o1 and c3 < o3 and c3 < midpoint1):
                        add("Evening Star", "BEARISH", label, candle_date,
                            f"Patrón Evening Star (3 velas) — reversión bajista de alta fiabilidad",
                            3)

        # ── Trend Structure ──
        if len(df) >= 20:
            window20 = close.iloc[-20:]
            window20_high = high.iloc[-20:]
            window20_low = low.iloc[-20:]

            # Simple HH/HL detection (split window in halves)
            first_half_high = window20_high.iloc[:10].max()
            second_half_high = window20_high.iloc[10:].max()
            first_half_low = window20_low.iloc[:10].min()
            second_half_low = window20_low.iloc[10:].min()

            if second_half_high > first_half_high * 1.02 and second_half_low > first_half_low * 1.02:
                add("Tendencia Alcista HH/HL", "BULLISH", label, last_date,
                    f"Máximos y mínimos crecientes en las últimas 20 velas — uptrend confirmado",
                    2)
            elif second_half_high < first_half_high * 0.98 and second_half_low < first_half_low * 0.98:
                add("Tendencia Bajista LH/LL", "BEARISH", label, last_date,
                    f"Máximos y mínimos decrecientes en las últimas 20 velas — downtrend confirmado",
                    2)

        # ── 52-week proximity ──
        if len(close) >= 50:
            high_52w = close.iloc[-252:].max() if len(close) >= 252 else close.max()
            low_52w = close.iloc[-252:].min() if len(close) >= 252 else close.min()
            pct_from_high = (curr_close - high_52w) / high_52w * 100
            pct_from_low = (curr_close - low_52w) / low_52w * 100

            if pct_from_high >= -5:
                add("Cerca de Máximo 52s", "BULLISH", label, last_date,
                    f"Precio a {abs(pct_from_high):.1f}% del máximo de 52 semanas — fuerza relativa excepcional",
                    2)
            elif pct_from_low <= 10:
                add("Cerca de Mínimo 52s", "BEARISH", label, last_date,
                    f"Precio a {pct_from_low:.1f}% del mínimo de 52 semanas — cuchillo cayendo",
                    2)

    return signals


# ─── Data Loading ─────────────────────────────────────────────────────────

def load_tickers():
    """Load tickers from all sources with source label."""
    ticker_info = {}  # ticker → {company_name, source, sector}

    # 1. Active portfolio
    try:
        df = pd.read_csv(os.path.join(DOCS_DIR, "portfolio_tracker", "recommendations.csv"))
        active = df[df.get("status", pd.Series(["ACTIVE"]*len(df))) == "ACTIVE"] if "status" in df.columns else df
        for _, row in active.iterrows():
            t = str(row.get("ticker", "")).strip().upper()
            if t:
                ticker_info[t] = {
                    "company_name": str(row.get("company_name", "")),
                    "source": "portfolio",
                    "sector": str(row.get("sector", ""))
                }
        print(f"  Portfolio: {len(active)} tickers")
    except Exception as e:
        print(f"  Portfolio load error: {e}")

    # 2. Value US
    try:
        df = pd.read_csv(os.path.join(DOCS_DIR, "value_opportunities.csv"))
        for _, row in df.iterrows():
            t = str(row.get("ticker", "")).strip().upper()
            if t and t not in ticker_info:
                ticker_info[t] = {
                    "company_name": str(row.get("company_name", "")),
                    "source": "value_us",
                    "sector": str(row.get("sector", ""))
                }
        print(f"  Value US: {len(df)} tickers")
    except Exception as e:
        print(f"  Value US load error: {e}")

    # 3. Value EU
    try:
        df = pd.read_csv(os.path.join(DOCS_DIR, "european_value_opportunities.csv"))
        for _, row in df.iterrows():
            t = str(row.get("ticker", "")).strip().upper()
            if t and t not in ticker_info:
                ticker_info[t] = {
                    "company_name": str(row.get("company_name", "")),
                    "source": "value_eu",
                    "sector": str(row.get("sector", ""))
                }
        print(f"  Value EU: {len(df)} tickers")
    except Exception as e:
        print(f"  Value EU load error: {e}")

    # 4. Global Value
    try:
        df = pd.read_csv(os.path.join(DOCS_DIR, "global_value_opportunities.csv"))
        for _, row in df.iterrows():
            t = str(row.get("ticker", "")).strip().upper()
            if t and t not in ticker_info:
                ticker_info[t] = {
                    "company_name": str(row.get("company_name", "")),
                    "source": "value_global",
                    "sector": str(row.get("sector", ""))
                }
        print(f"  Value Global: {len(df)} tickers")
    except Exception as e:
        print(f"  Value Global load error: {e}")

    return ticker_info


def download_price_data(ticker):
    """Download daily + weekly OHLCV. Returns (df_daily, df_weekly)."""
    try:
        stock = yf.Ticker(ticker)
        # 2 years daily + 5 years weekly
        df_d = stock.history(period="2y", interval="1d", auto_adjust=True)
        df_w = stock.history(period="5y", interval="1wk", auto_adjust=True)

        if df_d is not None and len(df_d) < 30:
            df_d = None
        if df_w is not None and len(df_w) < 20:
            df_w = None

        return df_d, df_w
    except Exception as e:
        print(f"    Data error {ticker}: {e}")
        return None, None


# ─── Main ──────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Technical Signal Analyzer")
    print(f"Run date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    ticker_info = load_tickers()
    print(f"\nTotal tickers to analyze: {len(ticker_info)}")

    all_signals = []
    processed = 0
    errors = 0

    for ticker, info in ticker_info.items():
        print(f"  [{processed+1}/{len(ticker_info)}] {ticker} ({info['source']})...", end=" ")
        try:
            df_daily, df_weekly = download_price_data(ticker)
            if df_daily is None and df_weekly is None:
                print("no data")
                errors += 1
                continue

            signals = detect_signals(
                ticker=ticker,
                df_daily=df_daily,
                df_weekly=df_weekly,
                company_name=info.get("company_name", ""),
                source=info.get("source", "")
            )
            all_signals.extend(signals)
            print(f"{len(signals)} signals")
        except Exception as e:
            print(f"ERROR: {e}")
            errors += 1

        processed += 1

    print(f"\nTotal signals detected: {len(all_signals)}")
    print(f"Errors: {errors}")

    if not all_signals:
        print("No signals detected, exiting.")
        return

    # ── Save signals CSV ──
    df_signals = pd.DataFrame(all_signals)
    df_signals["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    df_signals.sort_values(["ticker", "timeframe", "strength"], ascending=[True, True, False], inplace=True)
    df_signals.to_csv(OUTPUT_SIGNALS, index=False)
    print(f"\nSignals saved: {OUTPUT_SIGNALS}")

    # ── Build summary CSV (one row per ticker) ──
    summary_rows = []
    for ticker, info in ticker_info.items():
        t_signals = [s for s in all_signals if s["ticker"] == ticker]
        if not t_signals:
            continue

        bullish = [s for s in t_signals if s["direction"] == "BULLISH"]
        bearish = [s for s in t_signals if s["direction"] == "BEARISH"]
        b_count = len(bullish)
        be_count = len(bearish)
        net = b_count - be_count

        # Net score weighted by strength
        b_score = sum(s["strength"] for s in bullish)
        be_score = sum(s["strength"] for s in bearish)
        net_score = b_score - be_score

        if net_score > 3:
            bias = "BULLISH"
        elif net_score < -3:
            bias = "BEARISH"
        else:
            bias = "NEUTRAL"

        top_bullish = max(bullish, key=lambda s: s["strength"], default={}).get("signal_name", "") if bullish else ""
        top_bearish = max(bearish, key=lambda s: s["strength"], default={}).get("signal_name", "") if bearish else ""

        # Most recent triggered signal
        all_sorted = sorted(t_signals, key=lambda s: s["days_ago"])
        most_recent = all_sorted[0]["signal_name"] if all_sorted else ""

        summary_rows.append({
            "ticker": ticker,
            "company_name": info.get("company_name", ""),
            "source": info.get("source", ""),
            "sector": info.get("sector", ""),
            "bullish_count": b_count,
            "bearish_count": be_count,
            "net_signals": net,
            "net_score": net_score,
            "bias": bias,
            "top_bullish_signal": top_bullish,
            "top_bearish_signal": top_bearish,
            "most_recent_signal": most_recent,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M")
        })

    df_summary = pd.DataFrame(summary_rows)
    df_summary.sort_values("net_score", ascending=False, inplace=True)
    df_summary.to_csv(OUTPUT_SUMMARY, index=False)
    print(f"Summary saved: {OUTPUT_SUMMARY}")

    # ── Print top picks ──
    print("\n── TOP BULLISH ──")
    top_bull = df_summary[df_summary["bias"] == "BULLISH"].head(10)
    for _, row in top_bull.iterrows():
        print(f"  {row['ticker']:10} | {row['bias']:8} | +{row['bullish_count']}B -{row['bearish_count']}Be | {row['top_bullish_signal']}")

    print("\n── TOP BEARISH (avoid/caution) ──")
    top_bear = df_summary[df_summary["bias"] == "BEARISH"].head(10)
    for _, row in top_bear.iterrows():
        print(f"  {row['ticker']:10} | {row['bias']:8} | +{row['bullish_count']}B -{row['bearish_count']}Be | {row['top_bearish_signal']}")

    print("\nDone.")


if __name__ == "__main__":
    main()
