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
                # Nombres de columna desfasados una posición en origen (ver
                # comentario en insiders/openinsider_scraper.py): 'Title' es la
                # empresa y 'Date' el cargo del insider.
                transaction = {
                    # `date` era la fecha de SCRAPEO, no la de la operación: el
                    # scraper pide los últimos 7 días y este bucle concatena
                    # todos los CSV diarios, así que la misma compra entraba
                    # hasta 7 veces con fechas distintas (59,7% del índice eran
                    # duplicados: 16.868 compras registradas, 6.794 reales).
                    # Se usa TradeDate cuando está; los CSV anteriores al
                    # 8-ago-2026 no la traen y ahí se cae a la de scrapeo.
                    'date': (str(row['TradeDate'])
                             if 'TradeDate' in row and pd.notna(row['TradeDate'])
                             and str(row['TradeDate']).strip() not in ('', 'nan', 'N/A')
                             else date),
                    'scraped_date': date,
                    'company': str(row['Title']),
                    'insider': str(row['Date']),
                    # Nombre real de la persona. Los CSV anteriores al
                    # 8-ago-2026 no lo traen; ahí queda None y quien cuente
                    # insiders únicos debe caer al cargo.
                    'insider_name': (str(row['InsiderName'])
                                     if 'InsiderName' in row and pd.notna(row['InsiderName'])
                                     else None),
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
        # Deduplicar: la misma operación aparece en cada CSV diario mientras
        # sigue dentro de la ventana de 7 días del scraper. Identidad de una
        # operación real = persona + fecha de operación + precio + cantidad.
        # Sin esto el índice inflaba las compras un 59,7% y disparaba el
        # criterio de "compras recurrentes" (>=2) con UNA sola operación
        # rescrapeada — 562 tickers marcados sin merecerlo.
        # La fecha NO entra en la clave a propósito: los CSV anteriores al
        # 8-ago-2026 no traen TradeDate, así que su `date` es la de scrapeo y
        # difiere entre copias de la misma operación — incluirla no
        # deduplicaría nada del histórico. Persona + precio + cantidad basta:
        # que alguien compre la misma cantidad exacta al mismo precio AL
        # CÉNTIMO en dos días distintos es re-scrapeo, no dos compras (el
        # precio se mueve). Se conserva la copia más reciente, que con
        # TradeDate ya trae la fecha real de la operación.
        vistas = set()
        unicas = []
        for t in transactions:
            clave = (t.get('insider_name') or t.get('insider'),
                     t.get('price'), t.get('qty'), t.get('type'))
            if clave in vistas:
                continue
            vistas.add(clave)
            unicas.append(t)
        transactions = unicas

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
