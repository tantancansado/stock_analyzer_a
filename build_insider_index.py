#!/usr/bin/env python3
"""
Genera índice JSON de todos los insiders para búsqueda web
"""
import pandas as pd
import glob
import json
from collections import defaultdict

def build_insider_index():
    """Construye índice completo de insiders desde todos los CSVs"""
    print("🔨 CONSTRUYENDO ÍNDICE DE INSIDERS")
    print("=" * 70)

    # Buscar todos los CSVs
    csv_files = glob.glob("docs/reports/daily/report_*/data.csv")
    print(f"📂 Procesando {len(csv_files)} archivos...")

    # Diccionario: ticker -> [transacciones]
    index = defaultdict(list)

    for csv_file in sorted(csv_files, reverse=True):
        try:
            # Extraer fecha
            parts = csv_file.split('/')
            date = None
            for part in parts:
                if part.startswith('report_'):
                    date = part.replace('report_', '')
                    break

            if not date:
                continue

            # Leer CSV
            df = pd.read_csv(csv_file)

            # Procesar cada fila
            for _, row in df.iterrows():
                ticker = str(row['Insider']).strip().upper()  # Columna corrida

                if len(ticker) > 10 or not ticker:
                    continue

                # Crear transacción
                transaction = {
                    'date': date,
                    'company': str(row['Title']),
                    'insider': str(row['Date']),
                    'type': str(row['Type']),
                    'price': float(row['Price']) if pd.notna(row['Price']) else 0,
                    'qty': int(row['Qty']) if pd.notna(row['Qty']) else 0,
                }

                index[ticker].append(transaction)

        except Exception as e:
            pass

    # Convertir a formato JSON-friendly
    output = {}
    for ticker, transactions in index.items():
        # Calcular stats
        purchases = [t for t in transactions if 'P -' in t['type']]
        sales = [t for t in transactions if 'S -' in t['type']]

        output[ticker] = {
            'total': len(transactions),
            'purchases': len(purchases),
            'sales': len(sales),
            'transactions': sorted(transactions, key=lambda x: x['date'], reverse=True)[:50]  # Top 50 más recientes
        }

    print(f"✅ Índice construido: {len(output)} tickers únicos")

    # Guardar JSON
    output_path = 'docs/insider_index.json'
    with open(output_path, 'w') as f:
        json.dump(output, f, separators=(',', ':'))  # Compacto

    print(f"💾 Guardado en: {output_path}")

    # Stats
    total_transactions = sum(data['total'] for data in output.values())
    print(f"\n📊 Estadísticas:")
    print(f"   Tickers: {len(output):,}")
    print(f"   Transacciones: {total_transactions:,}")

    return output_path

if __name__ == "__main__":
    build_insider_index()
