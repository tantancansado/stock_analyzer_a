#!/usr/bin/env python3
"""
Construye mapeo de ticker -> nombre de empresa
"""
import json
import yfinance as yf
from pathlib import Path
import time

def build_ticker_names():
    """Construye diccionario de tickers a nombres de empresas"""
    print("🏢 CONSTRUYENDO MAPEO DE NOMBRES DE EMPRESAS")
    print("=" * 70)

    # Cargar índice de insiders
    index_path = Path('docs/insider_index.json')
    with open(index_path, 'r') as f:
        insider_data = json.load(f)

    tickers = list(insider_data.keys())
    print(f"📊 Total tickers a procesar: {len(tickers)}")

    # Cargar nombres existentes si existen
    names_path = Path('docs/ticker_names.json')
    if names_path.exists():
        with open(names_path, 'r') as f:
            ticker_names = json.load(f)
        print(f"📂 Cargados {len(ticker_names)} nombres existentes")
    else:
        ticker_names = {}

    # Procesar tickers
    processed = 0
    errors = 0

    for i, ticker in enumerate(tickers, 1):
        # Skip si ya existe
        if ticker in ticker_names:
            continue

        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            name = info.get('longName') or info.get('shortName', ticker)
            ticker_names[ticker] = name

            processed += 1
            if processed % 10 == 0:
                print(f"✅ Procesados: {processed}/{len(tickers)} | Errores: {errors}")
                # Guardar progreso cada 10
                with open(names_path, 'w') as f:
                    json.dump(ticker_names, f, indent=2)

            # Rate limiting
            time.sleep(0.1)

        except Exception as e:
            errors += 1
            # Si no encontramos, usar el ticker como nombre
            ticker_names[ticker] = ticker

    # Guardar resultado final
    with open(names_path, 'w') as f:
        json.dump(ticker_names, f, indent=2)

    print(f"\n✅ Completado!")
    print(f"   Nombres obtenidos: {len(ticker_names)}")
    print(f"   Errores: {errors}")
    print(f"   Guardado en: {names_path}")

    return ticker_names

if __name__ == "__main__":
    build_ticker_names()
