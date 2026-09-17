#!/usr/bin/env python3
"""
ADD ENTRY/EXIT TO OPPORTUNITIES
Añade precios de entrada/salida a las oportunidades del super score

Lee: docs/super_scores_ultimate.csv
Añade: entry_price, stop_loss, exit_price, risk_reward
Guarda: docs/super_opportunities_with_prices.csv

Data source: yfinance (no Seeking Alpha cookies needed)
"""

import pandas as pd
import numpy as np
import time
import sys
from pathlib import Path
from entry_exit_calculator import EntryExitCalculator

# Rate limiting config
YF_DELAY_BETWEEN_TICKERS = 2.0  # seconds between tickers
YF_DELAY_ON_ERROR = 10.0        # seconds after a rate limit error
YF_MAX_RETRIES = 3


def fetch_ticker_yfinance(ticker: str, attempt: int = 1) -> dict:
    """
    Fetch ticker data from yfinance with retry logic.
    Returns dict with current_price, hist (DataFrame), 52w high/low.
    """
    import yfinance as yf

    try:
        stock = yf.Ticker(ticker)

        # Get historical data (200+ days for SMA calculations)
        hist = stock.history(period='1y')

        if hist.empty:
            print(f"   ⚠️  No historical data from yfinance")
            return None

        # Get current price from latest close
        current_price = float(hist['Close'].iloc[-1])

        # 52-week high/low from historical
        week_52_high = float(hist['High'].max())
        week_52_low = float(hist['Low'].min())

        return {
            'current_price': current_price,
            'hist': hist,
            '52_week_high': week_52_high,
            '52_week_low': week_52_low,
        }

    except Exception as e:
        error_msg = str(e).lower()

        # Rate limit detection
        if '429' in str(e) or 'too many requests' in error_msg or 'rate' in error_msg:
            if attempt < YF_MAX_RETRIES:
                wait = YF_DELAY_ON_ERROR * attempt
                print(f"   ⏳ Rate limited, waiting {wait:.0f}s (attempt {attempt}/{YF_MAX_RETRIES})...")
                time.sleep(wait)
                return fetch_ticker_yfinance(ticker, attempt + 1)

        print(f"   ⚠️  yfinance error: {str(e)[:80]}")
        return None


# Máxima antigüedad del dato de origen. El pipeline corre a diario; siete días
# deja margen para fines de semana y festivos, y caza un fósil de meses.
MAX_ANTIGUEDAD_DIAS = 7


def _antiguedad_del_dato(df) -> int | None:
    """Días desde la fecha del DATO (no del fichero). None si no la declara."""
    for col in ('data_as_of_date', 'score_timestamp', 'scan_date'):
        if col not in df.columns:
            continue
        try:
            fechas = pd.to_datetime(df[col], errors='coerce').dropna()
            if fechas.empty:
                continue
            return (pd.Timestamp.now().normalize() - fechas.max().normalize()).days
        except Exception:
            continue
    return None


def add_entry_exit_prices(input_file: str = None, output_file: str = None):
    """
    Añade entry/exit prices a todas las oportunidades usando yfinance
    """
    if not input_file:
        # `super_scores_ultimate.csv` es un FÓSIL: nadie lo escribe desde
        # feb-2026 y sus 82 filas llevan `data_as_of_date 2026-02-19`. Este
        # script lo leía por defecto, le pedía precios FRESCOS a yfinance y
        # escribía `super_opportunities_with_prices.csv` — que `ticker_api`
        # sirve como entrada, stop y objetivo.
        #
        # El resultado: un fichero que se commitea cada día con precios de hoy
        # y fundamentales de hace siete meses. Parecía vivo justo porque el
        # precio SÍ se actualizaba. Para AVGO servía «BUY NOW, entrada 344,72,
        # objetivo 479,44, R:R 14,59» calculado sobre febrero.
        #
        # La fuente viva del lado momentum es `momentum_opportunities.csv`.
        input_file = 'docs/momentum_opportunities.csv'
    if not output_file:
        output_file = 'docs/super_opportunities_with_prices.csv'

    print(f"\n{'='*80}")
    print("📊 ADDING ENTRY/EXIT PRICES TO OPPORTUNITIES")
    print(f"{'='*80}")
    print(f"📡 Data source: yfinance (with rate limiting)\n")

    # Load opportunities
    if not Path(input_file).exists():
        print(f"❌ File not found: {input_file}")
        return

    df = pd.read_csv(input_file)

    # Un origen caducado no se procesa. Sin esto, el script hace su trabajo con
    # esmero —precios frescos, entradas, stops, objetivos— sobre un universo
    # muerto, y el resultado es indistinguible de uno bueno: es el tipo de
    # fallo que sobrevive meses porque nada falla.
    dias = _antiguedad_del_dato(df)
    if dias is not None and dias > MAX_ANTIGUEDAD_DIAS:
        print(f"🛑 {input_file}: el DATO es de hace {dias} días "
              f"(máximo {MAX_ANTIGUEDAD_DIAS}). No se calculan precios sobre un origen caducado.")
        print("   Un objetivo calculado sobre fundamentales viejos parece "
              "actual porque el precio sí lo es. Mejor sin dato que con uno que engaña.")
        return

    total = min(len(df), 50)
    print(f"✅ Loaded {len(df)} opportunities from {input_file}"
          + (f" (dato de hace {dias}d)" if dias is not None else ""))
    print(f"📋 Processing top {total}...\n")

    # Initialize calculator
    calc = EntryExitCalculator()

    results = []
    failed = []

    for idx, row in df.head(total).iterrows():
        ticker = row['ticker']
        print(f"[{idx+1}/{total}] Processing {ticker}...")

        # Rate limiting between tickers
        if idx > 0:
            time.sleep(YF_DELAY_BETWEEN_TICKERS)

        try:
            # Fetch from yfinance
            data = fetch_ticker_yfinance(ticker)
            if not data:
                failed.append(ticker)
                continue

            hist = data['hist']
            current_price = data['current_price']

            # Normalize columns to lowercase
            hist.columns = [col.lower() for col in hist.columns]

            # Prepare VCP analysis from row data
            vcp_analysis = {
                'score': row.get('vcp_score', 0),
                'pattern_detected': row.get('vcp_ready_to_buy', False)
            }

            # Prepare fundamental data
            fundamental_data = {
                'pe_ratio': row.get('pe_ratio'),
                'peg_ratio': row.get('peg_ratio'),
            }

            # Price vs ATH
            year_high = data.get('52_week_high')
            if year_high and year_high > 0:
                price_vs_ath = ((current_price - year_high) / year_high) * 100
            else:
                price_vs_ath = None

            validation = {
                'price_vs_ath': price_vs_ath
            }

            # Calculate entry/exit
            entry_exit = calc.calculate_entry_exit(
                ticker=ticker,
                current_price=current_price,
                hist=hist,
                vcp_analysis=vcp_analysis,
                fundamental_data=fundamental_data,
                validation=validation
            )

            # Add to row
            result = row.to_dict()
            result.update({
                'current_price': entry_exit['current_price'],
                'entry_price': entry_exit['entry_price'],
                'entry_range': f"${entry_exit['entry_range_low']}-${entry_exit['entry_range_high']}",
                'stop_loss': entry_exit['stop_loss'],
                'exit_price': entry_exit['exit_price'],
                'exit_range': (f"${entry_exit['exit_range_low']}-${entry_exit['exit_range_high']}"
                               if entry_exit['exit_range_low'] is not None else None),
                'risk_reward': entry_exit['risk_reward_ratio'],
                'risk_pct': entry_exit['risk_pct'],
                'reward_pct': entry_exit['reward_pct'],
                'entry_timing': entry_exit['entry_timing'],
                'meets_risk_reward': entry_exit['meets_criteria']
            })

            results.append(result)
            # El objetivo puede no existir: desde el 16-sep-2026 sale del
            # consenso de analistas y vale None cuando los modelos propios lo
            # desmienten. Formatearlo a ciegas tumbó el pipeline entero el 17
            # ("unsupported format string passed to NoneType.__format__"), y
            # como este paso es [CRITICAL] se llevó por delante todo lo que va
            # detrás: technical_filter, portfolio_tracker, entry_verdicts,
            # cerebro. Nueve pasos sin correr por un `:.2f`.
            _salida = entry_exit['exit_price']
            _rr = entry_exit['risk_reward_ratio']
            _destino = (f"Target ${_salida:.2f} (R/R: {_rr:.1f}:1)"
                        if _salida is not None and _rr is not None
                        else "sin objetivo por valoración")
            print(f"   ✅ ${entry_exit['current_price']:.2f} → Entry: ${entry_exit['entry_price']:.2f}"
                  f" | Stop: ${entry_exit['stop_loss']:.2f} | {_destino}")

        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            failed.append(ticker)
            continue

    # Create DataFrame and save
    if results:
        result_df = pd.DataFrame(results)

        # Reorder columns to show prices first
        price_cols = ['ticker', 'current_price', 'entry_price', 'entry_range', 'stop_loss',
                      'exit_price', 'exit_range', 'risk_reward', 'risk_pct', 'reward_pct',
                      'entry_timing', 'meets_risk_reward']

        other_cols = [col for col in result_df.columns if col not in price_cols]
        result_df = result_df[price_cols + other_cols]

        # Save
        result_df.to_csv(output_file, index=False)

        print(f"\n{'='*80}")
        print(f"✅ SAVED {len(result_df)} opportunities with entry/exit prices")
        print(f"📁 Output: {output_file}")
        if failed:
            print(f"⚠️  Failed ({len(failed)}): {', '.join(failed)}")
        print(f"{'='*80}\n")

        # Con objetivos que pueden faltar, la columna llega como `object` y
        # `nlargest` levanta un TypeError — fue la segunda mitad de la caída del
        # 17-sep. Se convierte a número y las filas sin objetivo se cuentan
        # aparte en vez de colarse en las medias.
        result_df['risk_reward'] = pd.to_numeric(result_df['risk_reward'], errors='coerce')
        for c in ('risk_pct', 'reward_pct'):
            result_df[c] = pd.to_numeric(result_df[c], errors='coerce')
        con_objetivo = result_df[result_df['risk_reward'].notna()]

        print("📊 SUMMARY:")
        print(f"   Processed: {len(result_df)}/{total}")
        print(f"   Con objetivo por valoración: {len(con_objetivo)}/{len(result_df)}")
        if len(con_objetivo):
            print(f"   Average R/R Ratio: {con_objetivo['risk_reward'].mean():.2f}:1")
            print(f"   Meets Criteria (3:1): {int(result_df['meets_risk_reward'].sum())}/{len(result_df)}")
            print(f"   Average Risk: {result_df['risk_pct'].mean():.1f}%")
            print(f"   Average Reward: {con_objetivo['reward_pct'].mean():.1f}%")

            print(f"\n🏆 TOP 10 BY RISK/REWARD:")
            top_10 = con_objetivo.nlargest(min(10, len(con_objetivo)), 'risk_reward')[
                ['ticker', 'current_price', 'entry_price', 'exit_price', 'risk_reward', 'entry_timing']]
            print(top_10.to_string(index=False))
        else:
            print("   Ninguna con objetivo: los modelos propios desmienten al consenso en todas.")

    else:
        print(f"\n❌ No opportunities processed successfully")
        if failed:
            print(f"   Failed tickers: {', '.join(failed)}")


def _enrich_csv_with_entry_exit(input_file: str):
    """
    Enrich a CSV in-place with entry/exit columns.
    Reads the file, adds entry/exit data, writes back to same file.
    Only updates rows where entry/exit was successfully calculated.
    Preserves ALL original rows (doesn't drop any).
    """
    p = Path(input_file)
    if not p.exists():
        return
    df = pd.read_csv(input_file)
    if df.empty:
        print(f"  {input_file} is empty, skipping")
        return

    print(f"\n📊 Enriching {input_file} with entry/exit ({len(df)} tickers)")
    calc = EntryExitCalculator()

    for idx, row in df.head(50).iterrows():
        ticker = row['ticker']
        if idx > 0:
            time.sleep(YF_DELAY_BETWEEN_TICKERS)
        try:
            data = fetch_ticker_yfinance(ticker)
            if not data:
                continue
            hist = data['hist']
            hist.columns = [col.lower() for col in hist.columns]
            current_price = data['current_price']

            vcp_analysis = {'score': row.get('vcp_score', 0), 'pattern_detected': False}
            fundamental_data = {'pe_ratio': row.get('pe_ratio'), 'peg_ratio': row.get('peg_ratio')}
            year_high = data.get('52_week_high')
            price_vs_ath = ((current_price - year_high) / year_high * 100) if year_high and year_high > 0 else None

            entry_exit = calc.calculate_entry_exit(
                ticker=ticker, current_price=current_price, hist=hist,
                vcp_analysis=vcp_analysis, fundamental_data=fundamental_data,
                # Los objetivos REALES que el pipeline ya ha calculado. Sin
                # esto, `_calculate_exit_price` se los inventaba: un 20% de
                # «precio × 1,30» que el propio código llamaba "Placeholder",
                # un 40% de «suponer PER 25 para todos», y un suelo de +20%.
                # El resultado quedaba por encima del consenso de analistas en
                # 33 de 34 filas.
                validation={'price_vs_ath': price_vs_ath,
                            'target_price_analyst': row.get('target_price_analyst'),
                            'target_price_dcf': row.get('target_price_dcf'),
                            'target_price_pe': row.get('target_price_pe')}
            )

            df.at[idx, 'entry_price'] = entry_exit['entry_price']
            df.at[idx, 'stop_loss'] = entry_exit['stop_loss']
            df.at[idx, 'exit_price'] = entry_exit['exit_price']
            df.at[idx, 'risk_pct'] = entry_exit['risk_pct']
            df.at[idx, 'reward_pct'] = entry_exit['reward_pct']
            df.at[idx, 'entry_timing'] = entry_exit['entry_timing']

            # El R:R DE ESTA FICHA, calculado con la entrada, el stop y la
            # salida que se acaban de escribir tres líneas más arriba.
            #
            # Hacía falta porque `risk_reward_ratio` NO es eso: el integrator
            # (y el escáner europeo por su cuenta) lo calculan como
            # `analyst_upside_pct / 8`, el upside reescalado contra un stop
            # estándar del 8% que estas fichas no usan. El 16-sep-2026 no
            # cuadraba NINGUNA fila: las 34 del VALUE filtrado y las 3 suizas.
            #     PGHN.SW  publicaba R:R 3,34  ·  su propia ficha da 13,41
            #     GIVN.SW             0,85                        6,51
            # Los dos números eran correctos por separado y el par mentía, que
            # es la forma exacta de todos los fallos de datos de este repo.
            #
            # Se publica en una columna NUEVA en vez de redefinir la vieja: hay
            # consumidores calibrados sobre `risk_reward_ratio` (la predicción
            # ML lo usa de variable, cerebro reparte estadísticas por tramos) y
            # cambiarle el significado en silencio sería el mismo error otra vez.
            entrada = entry_exit['entry_price']
            riesgo = entrada - entry_exit['stop_loss']
            salida = entry_exit['exit_price']
            if riesgo > 0 and salida is not None:
                df.at[idx, 'rr_operativo'] = round((salida - entrada) / riesgo, 2)
            destino = f"Target ${salida:.2f}" if salida is not None else "sin objetivo por valoración"
            print(f"  [{idx+1}] {ticker}: Entry ${entrada:.2f} → {destino}")

        except Exception as e:
            print(f"  [{idx+1}] {ticker}: Error {str(e)[:60]}")
            continue

    # Save back — ALL rows preserved, entry/exit columns added where available
    df.to_csv(input_file, index=False)
    print(f"  Saved {input_file}")


def add_entry_exit_all():
    """Run entry/exit for all opportunity types: momentum, US VALUE, EU VALUE"""
    # 1. Momentum (original behavior — separate output file)
    add_entry_exit_prices()

    # 2. US VALUE — enrich in-place (preserves all rows)
    for vf in ['docs/value_opportunities_filtered.csv', 'docs/value_opportunities.csv']:
        if Path(vf).exists() and pd.read_csv(vf).shape[0] > 0:
            _enrich_csv_with_entry_exit(vf)
            break

    # 3. EU VALUE — enrich in-place (preserves all rows)
    for ef in ['docs/european_value_opportunities_filtered.csv', 'docs/european_value_opportunities.csv']:
        if Path(ef).exists() and pd.read_csv(ef).shape[0] > 0:
            _enrich_csv_with_entry_exit(ef)
            break


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Add entry/exit prices to opportunities')
    parser.add_argument('--input', type=str, help='Input CSV file')
    parser.add_argument('--output', type=str, help='Output CSV file')
    parser.add_argument('--all', action='store_true', help='Process all opportunity types (momentum + VALUE + EU)')
    args = parser.parse_args()

    if args.all:
        add_entry_exit_all()
    else:
        add_entry_exit_prices(args.input, args.output)
