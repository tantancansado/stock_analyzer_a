#!/usr/bin/env python3
"""
INSIDER TICKER FILTER
Herramienta para buscar transacciones de insiders por ticker en todos los CSVs históricos
"""
import pandas as pd
import glob
from datetime import datetime
from pathlib import Path
import sys

def search_ticker_in_all_csvs(ticker, days_back=365):
    """Busca un ticker en todos los CSVs de insider trading"""
    ticker = ticker.upper()

    print(f"\n🔍 BUSCANDO {ticker} EN HISTORIAL DE INSIDERS")
    print("=" * 80)

    # Buscar todos los CSVs
    csv_pattern = "docs/reports/daily/report_*/data.csv"
    csv_files = glob.glob(csv_pattern)

    print(f"📂 Archivos a escanear: {len(csv_files)}")

    # Filtrar por fecha si es necesario
    cutoff_date = None
    if days_back:
        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=days_back)

    all_transactions = []

    for csv_file in sorted(csv_files, reverse=True):
        try:
            # Extraer fecha del path
            parts = csv_file.split('/')
            for part in parts:
                if part.startswith('report_'):
                    date_str = part.replace('report_', '')
                    try:
                        file_date = datetime.strptime(date_str, '%Y-%m-%d')
                        if cutoff_date and file_date < cutoff_date:
                            continue
                    except:
                        pass

            # Leer CSV
            df = pd.read_csv(csv_file)

            # Buscar ticker (columna Insider = ticker real por el bug de columnas corridas)
            ticker_rows = df[
                (df['Insider'].str.upper() == ticker) |
                (df['Insider'].str.upper() == f"{ticker}")
            ]

            if not ticker_rows.empty:
                for _, row in ticker_rows.iterrows():
                    all_transactions.append({
                        'date': date_str,
                        'company': row['Title'],
                        'insider': row['Date'],
                        'type': row['Type'],
                        'price': row['Price'],
                        'qty': row['Qty'],
                        'owned': row.get('Owned', 'N/A'),
                        'value': row.get('Value', 'N/A')
                    })
        except Exception as e:
            pass

    return all_transactions

def display_transactions(ticker, transactions):
    """Muestra las transacciones de forma bonita"""
    if not transactions:
        print(f"\n❌ No se encontraron transacciones de {ticker}")
        print(f"   Últimos {len(glob.glob('docs/reports/daily/report_*/data.csv'))} días escaneados")
        return

    # Agrupar por tipo
    purchases = [t for t in transactions if 'P -' in t['type']]
    sales = [t for t in transactions if 'S -' in t['type']]

    print(f"\n✅ ENCONTRADAS {len(transactions)} TRANSACCIONES DE {ticker}")
    print("=" * 80)

    if purchases:
        print(f"\n🟢 COMPRAS ({len(purchases)}):")
        print("-" * 80)
        total_shares = 0
        total_value = 0

        for t in sorted(purchases, key=lambda x: x['date'], reverse=True):
            print(f"\n📅 {t['date']}")
            print(f"   Insider: {t['insider']}")
            print(f"   Compra: {t['qty']:,} acciones @ ${t['price']}")
            value = float(t['qty']) * float(t['price'])
            print(f"   Valor: ${value:,.0f}")
            total_shares += float(t['qty'])
            total_value += value

        print(f"\n📊 TOTAL COMPRAS:")
        print(f"   Acciones: {total_shares:,.0f}")
        print(f"   Inversión: ${total_value:,.0f}")

    if sales:
        print(f"\n🔴 VENTAS ({len(sales)}):")
        print("-" * 80)
        total_shares = 0

        for t in sorted(sales, key=lambda x: x['date'], reverse=True):
            print(f"\n📅 {t['date']}")
            print(f"   Insider: {t['insider']}")
            print(f"   Venta: {t['qty']:,} acciones @ ${t['price']}")
            total_shares += float(t['qty'])

        print(f"\n📊 TOTAL VENTAS:")
        print(f"   Acciones: {total_shares:,.0f}")

    # Análisis
    print(f"\n💡 ANÁLISIS:")
    if purchases and not sales:
        print(f"   🟢 SOLO COMPRAS - Señal muy positiva")
        print(f"   🟢 {len(purchases)} transacciones de compra")
        print(f"   🟢 Sin ventas recientes")
    elif purchases and sales:
        if len(purchases) > len(sales):
            print(f"   🟡 MÁS COMPRAS QUE VENTAS - Señal positiva")
            print(f"   🟢 {len(purchases)} compras vs {len(sales)} ventas")
        else:
            print(f"   🔴 MÁS VENTAS QUE COMPRAS - Señal negativa")
            print(f"   🔴 {len(sales)} ventas vs {len(purchases)} compras")
    elif sales and not purchases:
        print(f"   🔴 SOLO VENTAS - Señal negativa")
        print(f"   🔴 {len(sales)} transacciones de venta")
        print(f"   🔴 Sin compras recientes")

def generate_html_report(ticker, transactions):
    """Genera reporte HTML para el ticker"""
    if not transactions:
        return None

    purchases = [t for t in transactions if 'P -' in t['type']]
    sales = [t for t in transactions if 'S -' in t['type']]

    # Generar tabla HTML
    rows_html = ""
    for t in sorted(transactions, key=lambda x: x['date'], reverse=True):
        type_color = "#48bb78" if 'P -' in t['type'] else "#fc8181"
        type_icon = "🟢" if 'P -' in t['type'] else "🔴"
        value = float(t['qty']) * float(t['price'])

        rows_html += f"""
        <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.05);">
            <td style="padding: 1rem;">{t['date']}</td>
            <td style="padding: 1rem;">{t['insider']}</td>
            <td style="padding: 1rem; color: {type_color}; font-weight: 600;">{type_icon} {t['type']}</td>
            <td style="padding: 1rem; text-align: right;">{float(t['qty']):,.0f}</td>
            <td style="padding: 1rem; text-align: right;">${float(t['price']):.2f}</td>
            <td style="padding: 1rem; text-align: right; font-weight: 600;">${value:,.0f}</td>
        </tr>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔍 {ticker} Insider Trading History</title>
    <style>
        :root {{
            --glass-primary: rgba(99, 102, 241, 0.8);
            --glass-accent: rgba(59, 130, 246, 0.9);
            --glass-bg: rgba(255, 255, 255, 0.03);
            --glass-border: rgba(255, 255, 255, 0.1);
            --text-primary: rgba(255, 255, 255, 0.95);
            --text-secondary: rgba(255, 255, 255, 0.7);
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', Roboto, sans-serif;
            background: #020617;
            color: var(--text-primary);
            line-height: 1.6;
            padding: 2rem;
        }}
        .container {{ max-width: 1600px; margin: 0 auto; }}
        .glass-card {{
            background: var(--glass-bg);
            backdrop-filter: blur(20px) saturate(180%);
            border: 1px solid var(--glass-border);
            border-radius: 24px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }}
        h1 {{
            font-size: 2.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, var(--glass-primary), var(--glass-accent));
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 1rem;
            text-align: center;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            margin: 2rem 0;
        }}
        .stat-box {{
            background: var(--glass-bg);
            border: 1px solid var(--glass-border);
            border-radius: 16px;
            padding: 1.5rem;
            text-align: center;
        }}
        .stat-number {{
            font-size: 2.5rem;
            font-weight: 900;
            background: linear-gradient(135deg, var(--glass-accent), var(--glass-primary));
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }}
        .stat-label {{
            color: var(--text-secondary);
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{
            padding: 1rem;
            text-align: left;
            border-bottom: 2px solid var(--glass-border);
            color: var(--text-primary);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.85rem;
        }}
        .back-link {{
            display: inline-block;
            padding: 0.75rem 1.5rem;
            background: linear-gradient(135deg, var(--glass-primary), var(--glass-accent));
            color: white;
            text-decoration: none;
            border-radius: 12px;
            font-weight: 600;
            margin-bottom: 2rem;
            transition: all 0.3s ease;
        }}
    </style>
</head>
<body>
    <div class="container">
        <a href="https://tantancansado.github.io/stock_analyzer_a" class="back-link">🏠 Volver al Dashboard</a>

        <div class="glass-card">
            <h1>🔍 {ticker} - Insider Trading History</h1>
            <p style="text-align: center; color: var(--text-secondary);">
                Historial completo de transacciones de insiders
            </p>
        </div>

        <div class="stats-grid">
            <div class="stat-box">
                <div class="stat-number">{len(transactions)}</div>
                <div class="stat-label">Transacciones</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{len(purchases)}</div>
                <div class="stat-label">🟢 Compras</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{len(sales)}</div>
                <div class="stat-label">🔴 Ventas</div>
            </div>
        </div>

        <div class="glass-card">
            <h2 style="color: var(--text-primary); margin-bottom: 1.5rem;">📊 Historial de Transacciones</h2>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Fecha</th>
                            <th>Insider</th>
                            <th>Tipo</th>
                            <th style="text-align: right;">Cantidad</th>
                            <th style="text-align: right;">Precio</th>
                            <th style="text-align: right;">Valor</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</body>
</html>"""

    output_path = Path(f"docs/insider_history_{ticker}.html")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return str(output_path)

if __name__ == "__main__":
    # Obtener ticker del argumento o preguntar
    if len(sys.argv) > 1:
        ticker = sys.argv[1]
    else:
        ticker = input("🔍 Ingresa el ticker a buscar (ej: AAPL, TSLA): ").strip()

    if not ticker:
        print("❌ Debes ingresar un ticker")
        sys.exit(1)

    # Buscar transacciones
    transactions = search_ticker_in_all_csvs(ticker, days_back=365)

    # Mostrar resultados
    display_transactions(ticker, transactions)

    # Generar HTML si hay datos
    if transactions:
        html_path = generate_html_report(ticker, transactions)
        print(f"\n📄 Reporte HTML generado: {html_path}")
        print(f"   URL: https://tantancansado.github.io/stock_analyzer_a/insider_history_{ticker}.html")
