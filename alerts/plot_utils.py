import pandas as pd
import os
import zipfile
from datetime import datetime

# Rutas de archivos
csv_path = "reports/insiders_daily.csv"
html_path = "reports/insiders_report.html"

# Leer CSV con la estructura correcta
df = pd.read_csv(csv_path)
print(f"📊 CSV cargado: {len(df)} filas")
print(f"🔍 Columnas: {df.columns.tolist()}")

def crear_html_moderno_finviz():
    """
    HTML optimizado para móvil con diseño Liquid Glass
    MANTIENE: Layout exacto, estructura móvil, gráficos
    MEJORA: Colores, transparencias, efectos glass
    """
    try:
        # Verificar que existe el CSV
        csv_path = "reports/insiders_daily.csv"
        if not os.path.exists(csv_path):
            print(f"❌ CSV no encontrado: {csv_path}")
            return None
            
        df = pd.read_csv(csv_path)
        print(f"📊 CSV cargado: {len(df)} filas")
        
        def safe_convert_to_float(value):
            try:
                if pd.isna(value):
                    return 0.0
                if isinstance(value, (int, float)):
                    return float(value)
                str_value = str(value).strip().replace(',', '').replace('$', '')
                return float(str_value)
            except:
                return 0.0

        def safe_convert_to_int(value):
            try:
                if pd.isna(value):
                    return 0
                if isinstance(value, (int, float)):
                    return int(value)
                str_value = str(value).strip().replace(',', '')
                return int(float(str_value))
            except:
                return 0
        
        def format_large_number(num):
            """Formatea números grandes de forma compacta"""
            if num >= 1_000_000:
                return f"${num/1_000_000:.1f}M"
            elif num >= 1_000:
                return f"${num/1_000:.0f}K"
            else:
                return f"${num:.0f}"
        
        def calculate_holdings_change(qty, owned, value_pct):
            """Calcula el cambio en las holdings del insider"""
            try:
                if owned > 0 and qty > 0:
                    prev_owned = owned - qty
                    if prev_owned > 0:
                        change_pct = (qty / prev_owned) * 100
                        return {
                            'before': prev_owned,
                            'after': owned,
                            'change_pct': change_pct
                        }
                return None
            except:
                return None
        
        # Calcular estadísticas
        total_transactions = len(df)
        unique_tickers = df['Insider'].nunique()
        
        try:
            prices = df['Price'].apply(safe_convert_to_float)
            quantities = df['Qty'].apply(safe_convert_to_int)
            total_value = (prices * quantities).sum()
        except:
            total_value = 0
        
        last_update = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
        
        # Agrupar por ticker
        ticker_stats = {}
        for ticker in df['Insider'].unique():
            if pd.notna(ticker):
                ticker_data = df[df['Insider'] == ticker]
                
                # Calcular totales
                total_qty = ticker_data['Qty'].apply(safe_convert_to_int).sum()
                total_value_ticker = (ticker_data['Price'].apply(safe_convert_to_float) * 
                                    ticker_data['Qty'].apply(safe_convert_to_int)).sum()
                
                # Obtener el último owned (más reciente)
                last_owned = safe_convert_to_int(ticker_data['Owned'].iloc[-1])
                
                ticker_stats[ticker] = {
                    'count': len(ticker_data),
                    'total_value': total_value_ticker,
                    'total_qty': total_qty,
                    'company_name': ticker_data['Title'].iloc[0] if len(ticker_data) > 0 else ticker,
                    'insider_title': ticker_data['Date'].iloc[0] if len(ticker_data) > 0 else 'N/A',
                    'transaction_type': ticker_data['Type'].iloc[0] if len(ticker_data) > 0 else 'N/A',
                    'avg_price': ticker_data['Price'].apply(safe_convert_to_float).mean(),
                    'value_pct': str(ticker_data['Value'].iloc[0]).strip() if 'Value' in ticker_data.columns and len(ticker_data) > 0 and pd.notna(ticker_data['Value'].iloc[0]) else 'N/A',
                    'owned': last_owned,
                    'raw_data': ticker_data
                }

        # HTML con diseño Liquid Glass optimizado para móvil
        html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📊 Insider Trading Dashboard</title>
    <style>
        /* === LIQUID GLASS DESIGN SYSTEM PARA INSIDER TRADING === */
        
        :root {{
            /* Colores principales - Más claros y modernos */
            --glass-primary: rgba(99, 102, 241, 0.9);
            --glass-secondary: rgba(139, 92, 246, 0.8);
            --glass-accent: rgba(59, 130, 246, 1);
            
            /* Glassmorphism backgrounds */
            --glass-bg: rgba(255, 255, 255, 0.05);
            --glass-bg-hover: rgba(255, 255, 255, 0.12);
            --glass-border: rgba(255, 255, 255, 0.15);
            --glass-shadow: 0 8px 32px rgba(0, 0, 0, 0.37);
            --glass-shadow-hover: 0 16px 64px rgba(99, 102, 241, 0.3);
            
            /* Colores de texto más suaves */
            --text-primary: rgba(255, 255, 255, 0.95);
            --text-secondary: rgba(255, 255, 255, 0.75);
            --text-muted: rgba(255, 255, 255, 0.6);
            
            /* Fondo con gradiente */
            --bg-gradient: radial-gradient(ellipse at top, rgba(16, 23, 42, 0.9) 0%, rgba(2, 6, 23, 0.95) 50%, rgba(0, 0, 0, 0.98) 100%);
            
            /* Colores de estado más vibrantes */
            --success: rgba(72, 187, 120, 0.9);
            --warning: rgba(251, 191, 36, 0.9);
            --info: rgba(96, 165, 250, 0.9);
            
            /* Transiciones suaves */
            --transition-smooth: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            --transition-bounce: all 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }}
        
        * {{
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', Roboto, sans-serif;
            background: #020617;
            background-image: var(--bg-gradient);
            background-attachment: fixed;
            color: var(--text-primary);
            margin: 0;
            padding: 0;
            line-height: 1.6;
            overflow-x: hidden;
        }}
        
        /* Floating particles background */
        body::before {{
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: 
                radial-gradient(circle at 20% 80%, rgba(99, 102, 241, 0.08) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(139, 92, 246, 0.08) 0%, transparent 50%);
            pointer-events: none;
            z-index: -1;
            animation: float 20s ease-in-out infinite;
        }}
        
        @keyframes float {{
            0%, 100% {{ transform: translateY(0px) rotate(0deg); }}
            33% {{ transform: translateY(-15px) rotate(0.5deg); }}
            66% {{ transform: translateY(-8px) rotate(-0.5deg); }}
        }}
        
        /* Header con glassmorphism */
        .header {{
            background: var(--glass-bg);
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
            border: 1px solid var(--glass-border);
            border-radius: 0 0 24px 24px;
            padding: 20px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }}
        
        .header::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
            animation: shimmer 3s ease-in-out infinite;
        }}
        
        @keyframes shimmer {{
            0%, 100% {{ opacity: 0; }}
            50% {{ opacity: 1; }}
        }}
        
        .header h1 {{
            font-size: 2rem;
            font-weight: 800;
            background: linear-gradient(135deg, var(--glass-primary), var(--glass-secondary));
            background-size: 200% 200%;
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 0 0 8px 0;
            animation: gradient-shift 4s ease-in-out infinite;
        }}
        
        @keyframes gradient-shift {{
            0%, 100% {{ background-position: 0% 50%; }}
            50% {{ background-position: 100% 50%; }}
        }}
        
        .header .subtitle {{
            color: var(--text-secondary);
            font-size: 1rem;
            font-weight: 300;
        }}
        
        /* Stats bar con glassmorphism */
        .stats-bar {{
            background: var(--glass-bg);
            backdrop-filter: blur(16px);
            border: 1px solid var(--glass-border);
            border-radius: 16px;
            margin: 15px;
            padding: 20px 15px;
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            box-shadow: var(--glass-shadow);
        }}
        
        .stat-item {{
            text-align: center;
            transition: var(--transition-smooth);
        }}
        
        .stat-item:hover {{
            transform: translateY(-2px);
        }}
        
        .stat-number {{
            font-size: 1.4em;
            font-weight: 900;
            background: linear-gradient(135deg, var(--glass-accent), var(--glass-primary));
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            display: block;
        }}
        
        .stat-label {{
            color: var(--text-secondary);
            font-size: 0.8em;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 500;
        }}
        
        /* Main container */
        .main-container {{
            padding: 15px;
            max-width: 100%;
        }}
        
        /* Ticker cards con efectos glass */
        .ticker-card {{
            background: var(--glass-bg);
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            margin-bottom: 20px;
            overflow: hidden;
            box-shadow: var(--glass-shadow);
            transition: var(--transition-bounce);
            position: relative;
        }}
        
        .ticker-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
            animation: shimmer 4s ease-in-out infinite;
        }}
        
        .ticker-card:hover {{
            transform: translateY(-8px) scale(1.02);
            box-shadow: var(--glass-shadow-hover);
            border-color: rgba(255, 255, 255, 0.25);
        }}
        
        /* Ticker header */
        .ticker-header {{
            padding: 20px;
            background: rgba(255, 255, 255, 0.03);
            border-bottom: 1px solid var(--glass-border);
            position: relative;
        }}
        
        .ticker-header-top {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }}
        
        .ticker-symbol {{
            font-size: 1.8em;
            font-weight: 900;
            background: linear-gradient(135deg, var(--glass-accent), var(--glass-primary));
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .transaction-count {{
            background: linear-gradient(135deg, var(--glass-primary), var(--glass-secondary));
            color: white;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: 700;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
        }}
        
        .company-name {{
            color: var(--text-secondary);
            font-size: 1rem;
            margin-bottom: 6px;
            font-weight: 500;
        }}
        
        .insider-name {{
            color: var(--text-muted);
            font-size: 0.9em;
            font-weight: 400;
        }}
        
        /* Data grid - MANTIENE layout 2 columnas */
        .data-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            padding: 20px;
            background: rgba(255, 255, 255, 0.02);
        }}
        
        .data-item {{
            background: var(--glass-bg);
            backdrop-filter: blur(8px);
            padding: 15px;
            border-radius: 12px;
            border: 1px solid var(--glass-border);
            border-left: 3px solid var(--glass-primary);
            transition: var(--transition-smooth);
        }}
        
        .data-item:hover {{
            background: var(--glass-bg-hover);
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(99, 102, 241, 0.2);
        }}
        
        .data-item.full-width {{
            grid-column: 1 / -1;
        }}
        
        .data-label {{
            color: var(--text-secondary);
            font-size: 0.75em;
            text-transform: uppercase;
            margin-bottom: 4px;
            letter-spacing: 0.5px;
            font-weight: 600;
        }}
        
        .data-value {{
            color: var(--text-primary);
            font-weight: 700;
            font-size: 1.1em;
        }}
        
        .data-value.highlight {{
            background: linear-gradient(135deg, var(--warning), #f59e0b);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .data-value.success {{
            background: linear-gradient(135deg, var(--success), #10b981);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        /* Holdings change con mejor styling */
        .holdings-change {{
            background: rgba(72, 187, 120, 0.1);
            border-left-color: var(--success);
            border: 1px solid rgba(72, 187, 120, 0.3);
        }}
        
        .change-indicator {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.95em;
        }}
        
        .arrow-up {{
            color: var(--success);
            font-weight: bold;
            font-size: 1.2em;
        }}
        
        /* Charts container - MANTIENE layout vertical */
        .charts-container {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 20px;
            padding: 20px;
        }}
        
        .chart-section {{
            text-align: center;
        }}
        
        .chart-title {{
            color: var(--glass-primary);
            font-size: 0.9em;
            margin-bottom: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .finviz-image {{
            width: 100%;
            height: auto;
            max-height: 200px;
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.95);
            padding: 4px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            cursor: pointer;
            transition: var(--transition-bounce);
            object-fit: contain;
            border: 1px solid var(--glass-border);
        }}
        
        .finviz-image:hover {{
            transform: scale(1.05) translateY(-4px);
            box-shadow: 0 16px 48px rgba(99, 102, 241, 0.4);
        }}
        
        /* Links section */
        .links-section {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            padding: 20px;
        }}
        
        .external-link {{
            padding: 12px;
            border-radius: 12px;
            text-decoration: none;
            text-align: center;
            font-weight: 700;
            font-size: 0.9em;
            transition: var(--transition-bounce);
            backdrop-filter: blur(10px);
            border: 1px solid transparent;
        }}
        
        .external-link:active {{
            transform: scale(0.95);
        }}
        
        .finviz-link {{
            background: linear-gradient(135deg, rgba(255, 107, 107, 0.8), rgba(238, 90, 36, 0.8));
            color: white;
            border-color: rgba(255, 107, 107, 0.3);
            box-shadow: 0 8px 25px rgba(255, 107, 107, 0.3);
        }}
        
        .finviz-link:hover {{
            background: linear-gradient(135deg, rgba(255, 107, 107, 1), rgba(238, 90, 36, 1));
            transform: translateY(-4px) scale(1.05);
            box-shadow: 0 12px 35px rgba(255, 107, 107, 0.5);
        }}
        
        .yahoo-link {{
            background: linear-gradient(135deg, rgba(165, 94, 234, 0.8), rgba(139, 92, 246, 0.8));
            color: white;
            border-color: rgba(165, 94, 234, 0.3);
            box-shadow: 0 8px 25px rgba(165, 94, 234, 0.3);
        }}
        
        .yahoo-link:hover {{
            background: linear-gradient(135deg, rgba(165, 94, 234, 1), rgba(139, 92, 246, 1));
            transform: translateY(-4px) scale(1.05);
            box-shadow: 0 12px 35px rgba(165, 94, 234, 0.5);
        }}
        
        /* Modal para gráficos */
        .modal {{
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.95);
            backdrop-filter: blur(10px);
        }}
        
        .modal-content {{
            position: relative;
            margin: 2% auto;
            width: 95%;
            max-width: 1000px;
            text-align: center;
        }}
        
        .modal img {{
            max-width: 100%;
            max-height: 90vh;
            border-radius: 15px;
            box-shadow: 0 25px 80px rgba(0, 0, 0, 0.5);
        }}
        
        .close {{
            position: absolute;
            top: -60px;
            right: 10px;
            color: white;
            font-size: 35px;
            font-weight: bold;
            cursor: pointer;
            background: rgba(0,0,0,0.6);
            backdrop-filter: blur(10px);
            width: 50px;
            height: 50px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            line-height: 1;
            transition: var(--transition-smooth);
            border: 1px solid var(--glass-border);
        }}
        
        .close:hover {{
            background: rgba(255, 107, 107, 0.8);
            transform: scale(1.1);
        }}
        
        /* Transactions summary */
        .transactions-summary {{
            padding: 20px;
            background: rgba(255, 255, 255, 0.02);
            border-top: 1px solid var(--glass-border);
        }}
        
        .summary-title {{
            color: var(--glass-primary);
            font-size: 0.95em;
            font-weight: 700;
            margin-bottom: 15px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .transaction-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid rgba(99, 102, 241, 0.15);
            font-size: 0.9em;
            transition: var(--transition-smooth);
        }}
        
        .transaction-item:hover {{
            background: rgba(255, 255, 255, 0.03);
            border-radius: 8px;
            padding-left: 8px;
            padding-right: 8px;
        }}
        
        .transaction-item:last-child {{
            border-bottom: none;
        }}
        
        .transaction-date {{
            color: var(--text-secondary);
            font-weight: 500;
        }}
        
        .transaction-value {{
            color: var(--success);
            font-weight: 700;
        }}
        
        /* Responsive optimizations */
        @media (max-width: 375px) {{
            .header h1 {{
                font-size: 1.6em;
            }}
            
            .data-grid {{
                gap: 10px;
                padding: 15px;
            }}
            
            .data-item {{
                padding: 12px;
            }}
            
            .ticker-symbol {{
                font-size: 1.5em;
            }}
            
            .charts-container {{
                grid-template-columns: 1fr;
            }}
        }}
        
        /* Loading states */
        .loading {{
            text-align: center;
            padding: 30px;
            color: var(--text-secondary);
            background: var(--glass-bg);
            border-radius: 12px;
            backdrop-filter: blur(10px);
        }}
        
        /* Smooth entry animations */
        @keyframes fadeInUp {{
            from {{ 
                opacity: 0; 
                transform: translateY(30px); 
            }}
            to {{ 
                opacity: 1; 
                transform: translateY(0); 
            }}
        }}
        
        .ticker-card {{
            animation: fadeInUp 0.6s ease-out;
        }}
        
        /* Accessibility improvements */
        @media (prefers-reduced-motion: reduce) {{
            *, *::before, *::after {{
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Insider Trading</h1>
        <p class="subtitle">Análisis de transacciones con FinViz</p>
    </div>
    
    <div class="stats-bar">
        <div class="stat-item">
            <span class="stat-number">{total_transactions}</span>
            <span class="stat-label">Transacciones</span>
        </div>
        <div class="stat-item">
            <span class="stat-number">{unique_tickers}</span>
            <span class="stat-label">Empresas</span>
        </div>
        <div class="stat-item">
            <span class="stat-number">{format_large_number(total_value)}</span>
            <span class="stat-label">Valor Total</span>
        </div>
        <div class="stat-item">
            <span class="stat-number">{last_update.split()[1]}</span>
            <span class="stat-label">Actualización</span>
        </div>
    </div>
    
    <div class="main-container">
"""
        
        # Generar cards optimizadas para móvil - MANTIENE estructura exacta
        for ticker, stats in ticker_stats.items():
            if pd.isna(ticker) or ticker == 'nan':
                continue
                
            company_name = stats['company_name']
            total_value = stats['total_value']
            total_qty = stats['total_qty']
            transaction_count = stats['count']
            value_pct = stats['value_pct']
            avg_price = stats['avg_price']
            owned = stats['owned']
            insider_title = stats['insider_title']
            raw_data = stats['raw_data']
            
            # Calcular cambio en holdings
            holdings_info = calculate_holdings_change(total_qty, owned, value_pct)
            
            html_content += f"""
        <div class="ticker-card">
            <div class="ticker-header">
                <div class="ticker-header-top">
                    <span class="ticker-symbol">{ticker}</span>
                    <span class="transaction-count">{transaction_count} transacción{"es" if transaction_count > 1 else ""}</span>
                </div>
                <div class="company-name">{company_name[:50]}...</div>
                <div class="insider-name">👤 {insider_title}</div>
            </div>
            
            <div class="data-grid">
                <div class="data-item">
                    <div class="data-label">Precio Promedio</div>
                    <div class="data-value">${avg_price:.2f}</div>
                </div>
                <div class="data-item">
                    <div class="data-label">Cantidad Total</div>
                    <div class="data-value">{total_qty:,}</div>
                </div>
                <div class="data-item">
                    <div class="data-label">Valor Total</div>
                    <div class="data-value highlight">{format_large_number(total_value)}</div>
                </div>
                <div class="data-item">
                    <div class="data-label">% del Total</div>
                    <div class="data-value highlight">{value_pct if value_pct not in ['N/A', 'nan', ''] else 'N/A'}</div>
                </div>
"""
            
            # Añadir información de cambio en holdings si está disponible
            if holdings_info and holdings_info['change_pct'] > 0:
                change_pct = holdings_info['change_pct']
                html_content += f"""
                <div class="data-item full-width holdings-change">
                    <div class="data-label">Cambio en Holdings</div>
                    <div class="data-value success">
                        <div class="change-indicator">
                            <span class="arrow-up">↗</span>
                            <span>+{change_pct:.1f}% ({holdings_info['before']:,} → {owned:,})</span>
                        </div>
                    </div>
                </div>
"""
            else:
                html_content += f"""
                <div class="data-item full-width">
                    <div class="data-label">Acciones Totales</div>
                    <div class="data-value">{owned:,}</div>
                </div>
"""
            
            html_content += """
            </div>
            
            <!-- Resumen de transacciones -->
            <div class="transactions-summary">
                <div class="summary-title">📋 Últimas Transacciones</div>
"""
            
            # Mostrar últimas 3 transacciones
            for i, (_, row) in enumerate(raw_data.head(3).iterrows()):
                price = safe_convert_to_float(row['Price'])
                qty = safe_convert_to_int(row['Qty'])
                transaction_value = price * qty
                date = row.get('Ticker', 'N/A')
                
                html_content += f"""
                <div class="transaction-item">
                    <span class="transaction-date">{date}</span>
                    <span class="transaction-value">{format_large_number(transaction_value)} ({qty:,} @ ${price:.2f})</span>
                </div>
"""
            
            html_content += f"""
            </div>
            
            <!-- Gráficos FinViz - MANTIENE estructura vertical -->
            <div class="charts-container">
                <div class="chart-section">
                    <div class="chart-title">📊 Gráfico Diario</div>
                    <img 
                        src="https://finviz.com/chart.ashx?t={ticker}&ty=c&ta=1&p=d&s=l" 
                        alt="{ticker} Daily"
                        class="finviz-image"
                        onclick="openModal(this.src, '{ticker} - Diario')"
                        onerror="this.style.display='none'; this.parentElement.innerHTML='<div class=\\'loading\\'>📊 No disponible</div>'"
                        loading="lazy">
                </div>
                
                <div class="chart-section">
                    <div class="chart-title">📈 Gráfico Semanal</div>
                    <img 
                        src="https://finviz.com/chart.ashx?t={ticker}&ty=c&ta=1&p=w&s=l" 
                        alt="{ticker} Weekly"
                        class="finviz-image"
                        onclick="openModal(this.src, '{ticker} - Semanal')"
                        onerror="this.style.display='none'; this.parentElement.innerHTML='<div class=\\'loading\\'>📈 No disponible</div>'"
                        loading="lazy">
                </div>
            </div>
            
            <!-- Enlaces externos -->
            <div class="links-section">
                <a href="https://finviz.com/quote.ashx?t={ticker}" target="_blank" class="external-link finviz-link">
                    📊 FinViz
                </a>
                <a href="https://finance.yahoo.com/chart/{ticker}" target="_blank" class="external-link yahoo-link">
                    📈 Yahoo
                </a>
            </div>
        </div>
"""
        
        html_content += """
    </div>
    
    <!-- Modal para gráficos -->
    <div id="imageModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeModal()">&times;</span>
            <img id="modalImage" src="" alt="Chart">
        </div>
    </div>
    
    <script>
        function openModal(src, title) {
            document.getElementById('imageModal').style.display = 'block';
            document.getElementById('modalImage').src = src;
        }
        
        function closeModal() {
            document.getElementById('imageModal').style.display = 'none';
        }
        
        // Cerrar con click fuera o ESC
        window.onclick = function(event) {
            const modal = document.getElementById('imageModal');
            if (event.target === modal) closeModal();
        }
        
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') closeModal();
        });
        
        // Mejorar performance en móvil
        if ('loading' in HTMLImageElement.prototype) {
            const images = document.querySelectorAll('img[loading="lazy"]');
            images.forEach(img => {
                img.src = img.src;
            });
        }
        
        // Log con nueva información
        console.log('🎨 Dashboard Insider Trading - Liquid Glass Design');
        console.log('✨ Efectos glassmorphism activados');
        console.log('📱 Layout móvil vertical preservado');
        console.log('🌊 Transparencias y animaciones suaves');
    </script>
</body>
</html>
"""
        
        # Guardar HTML
        html_path = "reports/insiders_report_completo.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print(f"✅ HTML Liquid Glass generado: {html_path}")
        print("🎨 Mejoras Liquid Glass implementadas:")
        print("   ✨ Glassmorphism con blur y transparencias")
        print("   🌊 Colores más claros y modernos")
        print("   💫 Animaciones suaves y naturales")
        print("   📱 Layout móvil vertical preservado")
        print("   🎯 Efectos hover interactivos")
        print("   ⚡ Gradientes dinámicos en texto")
        
        return html_path
        
    except Exception as e:
        print(f"❌ Error generando HTML Liquid Glass: {e}")
        import traceback
        traceback.print_exc()
        return None

# Mantener todas las demás funciones igual - solo cambié crear_html_moderno_finviz()
def safe_convert_to_float(value):
    """Convierte un valor a float manejando comas y otros formatos"""
    if pd.isna(value):
        return 0.0
    
    try:
        if isinstance(value, (int, float)):
            return float(value)
        
        str_value = str(value).strip()
        str_value = str_value.replace(',', '')
        str_value = str_value.replace('$', '').replace('€', '')
        
        return float(str_value)
    except (ValueError, TypeError):
        return 0.0

def safe_convert_to_int(value):
    """Convierte un valor a int manejando diferentes formatos"""
    if pd.isna(value):
        return 0
    
    try:
        if isinstance(value, (int, float)):
            return int(value)
        
        str_value = str(value).strip()
        str_value = str_value.replace(',', '')
        
        return int(float(str_value))
    except (ValueError, TypeError):
        return 0

# [Resto de funciones igual...]
def generate_finviz_chart_iframe(ticker, timeframe="d", width=320, height=200):
    """Genera un iframe con el gráfico de FinViz embebido"""
    finviz_url = f"https://finviz.com/chart.ashx?t={ticker}&ta=1&ty=c&p={timeframe}&s=l"
    
    return f'''
    <div class="chart-container" onclick="openChart('{finviz_url}', '{ticker}', '{timeframe}')" 
         style="cursor: pointer; position: relative;">
        <iframe 
            src="{finviz_url}" 
            width="{width}" 
            height="{height}" 
            frameborder="0" 
            style="border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);"
            title="{ticker} - FinViz Chart ({timeframe})">
        </iframe>
        <div class="chart-overlay">
            <span class="zoom-icon">🔍</span>
        </div>
    </div>
    '''

def calcular_porcentaje_insider(ticker_data):
    """Calcula el porcentaje de incremento de los insiders para un ticker"""
    try:
        if len(ticker_data) == 0:
            return 0.0
        
        total_compras = len(ticker_data)
        
        valores = []
        for _, row in ticker_data.iterrows():
            price = safe_convert_to_float(row['Price'])
            qty = safe_convert_to_int(row['Qty'])
            valores.append(price * qty)
        
        valor_total = sum(valores)
        
        if 'Value' in ticker_data.columns:
            percentages = []
            for value in ticker_data['Value']:
                if pd.notna(value) and isinstance(value, str) and '%' in str(value):
                    try:
                        pct = float(str(value).replace('%', '').strip())
                        percentages.append(pct)
                    except:
                        pass
            
            if percentages:
                return sum(percentages) / len(percentages)
        
        if total_compras >= 5:
            return 15.0
        elif total_compras >= 3:
            return 10.0
        elif total_compras >= 2:
            return 7.5
        else:
            return 5.0
            
    except Exception as e:
        print(f"⚠️ Error calculando porcentaje para ticker: {e}")
        return 0.0

def crear_bundle_completo():
    """Crea un ZIP con el HTML y CSV"""
    zip_path = "reports/insiders_report_bundle.zip"
    with zipfile.ZipFile(zip_path, "w") as zipf:
        if os.path.exists(html_path):
            zipf.write(html_path, arcname=os.path.basename(html_path))
        
        if os.path.exists(csv_path):
            zipf.write(csv_path, arcname=os.path.basename(csv_path))
    
    print(f"✅ ZIP bundle generado en {zip_path}")
    return zip_path

def enviar_por_telegram(html_path, bundle_path):
    """Envía SOLO el archivo HTML por Telegram"""
    try:
        try:
            from config import TELEGRAM_CHAT_ID, TELEGRAM_BOT_TOKEN
            chat_id = TELEGRAM_CHAT_ID
            token = TELEGRAM_BOT_TOKEN
        except ImportError as e:
            print(f"❌ Error importando configuración: {e}")
            return False
        
        if not chat_id or not token:
            print("⚠️ TELEGRAM_CHAT_ID o TELEGRAM_BOT_TOKEN están vacíos")
            return False
        
        from alerts.telegram_utils import send_message, send_file
        
        total_transactions = len(df)
        unique_tickers = df['Insider'].nunique()
        mensaje_inicio = f"""🚀 REPORTE INSIDER TRADING ACTUALIZADO

📊 {total_transactions} transacciones analizadas
🏢 {unique_tickers} empresas únicas
✨ Nuevo diseño Liquid Glass
📈 Gráficos FinViz interactivos
🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}

📄 Archivo HTML adjunto con análisis completo"""
        
        send_message(token, chat_id, mensaje_inicio)
        
        if os.path.exists(html_path):
            send_file(token, chat_id, html_path, "📊 Reporte Insider Trading - Liquid Glass")
        
        mensaje_final = """✅ Reporte enviado exitosamente

🎨 Nuevo diseño Liquid Glass con:
• ✨ Efectos glassmorphism
• 🌊 Transparencias modernas  
• 💫 Animaciones suaves
• 📱 Optimizado para móvil
• 🔍 Gráficos interactivos"""
        
        send_message(token, chat_id, mensaje_final)
        
        print("🎉 Envío por Telegram completado exitosamente")
        return True
        
    except Exception as e:
        print(f"❌ Error enviando por Telegram: {e}")
        import traceback
        traceback.print_exc()
        return False

# Ejecutar automáticamente si se ejecuta este script
if __name__ == "__main__":
    crear_html_moderno_finviz()