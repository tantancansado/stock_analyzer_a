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
    HTML completo con TODOS los datos del CSV + gráficos FinViz
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
        
        # Agrupar por ticker para mantener la estructura actual
        ticker_stats = {}
        for ticker in df['Insider'].unique():
            if pd.notna(ticker):
                ticker_data = df[df['Insider'] == ticker]
                ticker_stats[ticker] = {
                    'count': len(ticker_data),
                    'total_value': (ticker_data['Price'].apply(safe_convert_to_float) * 
                                  ticker_data['Qty'].apply(safe_convert_to_int)).sum(),
                    'company_name': ticker_data['Title'].iloc[0] if len(ticker_data) > 0 else ticker,
                    'insider_title': ticker_data['Date'].iloc[0] if len(ticker_data) > 0 else 'N/A',
                    'transaction_type': ticker_data['Type'].iloc[0] if len(ticker_data) > 0 else 'N/A',
                    'avg_price': ticker_data['Price'].apply(safe_convert_to_float).mean(),
                    'source': ticker_data['Source'].iloc[0] if 'Source' in ticker_data.columns and len(ticker_data) > 0 else 'N/A',
                    'value_pct': str(ticker_data['Value'].iloc[0]).strip() if 'Value' in ticker_data.columns and len(ticker_data) > 0 and pd.notna(ticker_data['Value'].iloc[0]) else 'N/A',
                    'owned': ticker_data['Owned'].iloc[0] if 'Owned' in ticker_data.columns and len(ticker_data) > 0 else 0,
                    'scraped_at': ticker_data['ScrapedAt'].iloc[0] if 'ScrapedAt' in ticker_data.columns and len(ticker_data) > 0 else 'N/A',
                    'raw_data': ticker_data  # Añadir datos completos del CSV
                }

        # HTML con sección completa de datos CSV
        html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📊 Insider Trading Dashboard - Datos Completos</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #0a0e1a;
            color: #ffffff;
            margin: 0;
            padding: 0;
        }}
        
        .header {{
            background: linear-gradient(135deg, #1a1f35 0%, #2d3748 100%);
            padding: 20px;
            text-align: center;
            border-bottom: 2px solid #4a90e2;
        }}
        
        .header h1 {{
            color: #4a90e2;
            font-size: 2.2em;
            margin: 0 0 10px 0;
        }}
        
        .header .subtitle {{
            color: #a0aec0;
            font-size: 1.1em;
        }}
        
        .stats-bar {{
            background: #1a202c;
            padding: 15px;
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
            border-bottom: 1px solid #2d3748;
        }}
        
        .stat-item {{
            text-align: center;
            margin: 5px 15px;
        }}
        
        .stat-number {{
            font-size: 1.5em;
            font-weight: bold;
            color: #4a90e2;
            display: block;
        }}
        
        .stat-label {{
            color: #a0aec0;
            font-size: 0.85em;
            text-transform: uppercase;
        }}
        
        .main-container {{
            padding: 20px;
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        .ticker-card {{
            background: #1a202c;
            border: 1px solid #2d3748;
            border-radius: 8px;
            margin-bottom: 20px;
            overflow: hidden;
        }}
        
        .ticker-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px 20px;
            background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);
            border-bottom: 1px solid #2d3748;
        }}
        
        .ticker-symbol {{
            font-size: 1.5em;
            font-weight: bold;
            color: #4a90e2;
        }}
        
        .company-name {{
            color: #a0aec0;
            margin-left: 15px;
            flex: 1;
        }}
        
        .transaction-badge {{
            background: #4a90e2;
            color: white;
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 0.9em;
            font-weight: bold;
        }}
        
        /* SECCIÓN DE DATOS COMPLETOS DEL CSV */
        .csv-data-section {{
            padding: 20px;
            background: #2d3748;
            margin: 0 20px 20px 20px;
            border-radius: 8px;
        }}
        
        .csv-data-title {{
            color: #4a90e2;
            font-size: 1.2em;
            font-weight: bold;
            margin-bottom: 15px;
            border-bottom: 2px solid #4a90e2;
            padding-bottom: 8px;
        }}
        
        .data-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        
        .data-item {{
            background: #4a5568;
            padding: 12px;
            border-radius: 6px;
            border-left: 4px solid #4a90e2;
        }}
        
        .data-label {{
            color: #a0aec0;
            font-size: 0.85em;
            text-transform: uppercase;
            margin-bottom: 5px;
        }}
        
        .data-value {{
            color: #ffffff;
            font-weight: bold;
            font-size: 1.1em;
        }}
        
        .data-highlight {{
            color: #ffd700;
        }}
        
        /* TABLA DE TRANSACCIONES DETALLADA */
        .transactions-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            background: #1a202c;
            border-radius: 8px;
            overflow: hidden;
        }}
        
        .transactions-table th {{
            background: #4a90e2;
            color: white;
            padding: 12px 8px;
            text-align: center;
            font-size: 0.85em;
            font-weight: bold;
        }}
        
        .transactions-table td {{
            padding: 10px 8px;
            text-align: center;
            border-bottom: 1px solid #2d3748;
            font-size: 0.9em;
        }}
        
        .transactions-table tr:nth-child(even) {{
            background: #2d3748;
        }}
        
        .transactions-table tr:hover {{
            background: #4a5568;
        }}
        
        /* GRÁFICOS (mantener estilo actual) */
        .charts-container {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin: 20px;
        }}
        
        .chart-section {{
            text-align: center;
        }}
        
        .chart-title {{
            color: #4a90e2;
            font-size: 1em;
            margin-bottom: 10px;
            font-weight: bold;
        }}
        
        .finviz-image {{
            width: 100%;
            height: auto;
            max-height: 300px;
            border-radius: 8px;
            background: white;
            padding: 5px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            cursor: pointer;
            transition: transform 0.3s ease;
            object-fit: contain;
        }}
        
        .finviz-image:hover {{
            transform: scale(1.05);
        }}
        
        .links-section {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin: 15px 20px;
        }}
        
        .external-link {{
            padding: 12px;
            border-radius: 8px;
            text-decoration: none;
            text-align: center;
            font-weight: bold;
            font-size: 0.9em;
            transition: all 0.3s ease;
        }}
        
        .external-link:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.3);
        }}
        
        .finviz-link {{
            background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
            color: white;
        }}
        
        .yahoo-link {{
            background: linear-gradient(135deg, #a55eea 0%, #8b5cf6 100%);
            color: white;
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
            background-color: rgba(0,0,0,0.9);
        }}
        
        .modal-content {{
            position: relative;
            margin: 5% auto;
            width: 90%;
            max-width: 1000px;
            text-align: center;
        }}
        
        .modal img {{
            max-width: 100%;
            max-height: 80vh;
            border-radius: 10px;
        }}
        
        .close {{
            position: absolute;
            top: -40px;
            right: 0;
            color: white;
            font-size: 35px;
            font-weight: bold;
            cursor: pointer;
        }}
        
        @media (max-width: 768px) {{
            .data-grid {{
                grid-template-columns: 1fr;
            }}
            
            .charts-container {{
                grid-template-columns: 1fr;
            }}
            
            .transactions-table {{
                font-size: 0.8em;
            }}
            
            .transactions-table th,
            .transactions-table td {{
                padding: 6px 4px;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Dashboard Insider Trading</h1>
        <p class="subtitle">Datos Completos del CSV + Gráficos FinViz</p>
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
            <span class="stat-number">${total_value:,.0f}</span>
            <span class="stat-label">Valor Total</span>
        </div>
        <div class="stat-item">
            <span class="stat-number">{last_update}</span>
            <span class="stat-label">Última Actualización</span>
        </div>
    </div>
    
    <div class="main-container">
"""
        
        # Generar cards de tickers con TODOS los datos del CSV
        for ticker, stats in ticker_stats.items():
            if pd.isna(ticker) or ticker == 'nan':
                continue
                
            company_name = stats['company_name']
            total_value = stats['total_value']
            transaction_count = stats['count']
            value_pct = stats['value_pct']
            avg_price = stats['avg_price']
            owned = safe_convert_to_int(stats['owned'])
            source = stats['source']
            insider_title = stats['insider_title']
            scraped_at = stats['scraped_at']
            raw_data = stats['raw_data']
            
            html_content += f"""
        <div class="ticker-card">
            <div class="ticker-header">
                <span class="ticker-symbol">{ticker}</span>
                <span class="company-name">{company_name}</span>
                <span class="transaction-badge">{transaction_count} trans</span>
            </div>
            
            <!-- SECCIÓN DE DATOS COMPLETOS DEL CSV -->
            <div class="csv-data-section">
                <div class="csv-data-title">📋 Información Completa del CSV</div>
                
                <div class="data-grid">
                    <div class="data-item">
                        <div class="data-label">Ticker</div>
                        <div class="data-value">{ticker}</div>
                    </div>
                    <div class="data-item">
                        <div class="data-label">Empresa</div>
                        <div class="data-value">{company_name}</div>
                    </div>
                    <div class="data-item">
                        <div class="data-label">Precio Promedio</div>
                        <div class="data-value">${avg_price:.2f}</div>
                    </div>
                    <div class="data-item">
                        <div class="data-label">Valor Total</div>
                        <div class="data-value data-highlight">${total_value:,.0f}</div>
                    </div>
                    <div class="data-item">
                        <div class="data-label">Tipo</div>
                        <div class="data-value">P - Purchase</div>
                    </div>
                    <div class="data-item">
                        <div class="data-label">Insider</div>
                        <div class="data-value">{insider_title}</div>
                    </div>
                    <div class="data-item">
                        <div class="data-label">% Value</div>
                        <div class="data-value data-highlight">{value_pct if value_pct not in ['N/A', 'nan', ''] else 'N/A'}</div>
                    </div>
                    <div class="data-item">
                        <div class="data-label">Acciones Owned</div>
                        <div class="data-value">{owned:,}</div>
                    </div>
                    <div class="data-item">
                        <div class="data-label">Fuente</div>
                        <div class="data-value">{source}</div>
                    </div>
                    <div class="data-item">
                        <div class="data-label">Scraped At</div>
                        <div class="data-value">{scraped_at}</div>
                    </div>
                </div>
                
                <!-- TABLA DETALLADA DE TODAS LAS TRANSACCIONES -->
                <div class="csv-data-title">📊 Detalle de Transacciones</div>
                <table class="transactions-table">
                    <thead>
                        <tr>
                            <th>Fecha</th>
                            <th>Insider</th>
                            <th>Precio</th>
                            <th>Cantidad</th>
                            <th>Valor Trans.</th>
                            <th>% Value</th>
                            <th>Owned</th>
                        </tr>
                    </thead>
                    <tbody>
"""
            
            # Añadir todas las transacciones del ticker
            for _, row in raw_data.iterrows():
                price = safe_convert_to_float(row['Price'])
                qty = safe_convert_to_int(row['Qty'])
                transaction_value = price * qty
                
                html_content += f"""
                        <tr>
                            <td>{row.get('Ticker', 'N/A')}</td>
                            <td>{row.get('Date', 'N/A')}</td>
                            <td>${price:.2f}</td>
                            <td>{qty:,}</td>
                            <td>${transaction_value:,.0f}</td>
                            <td>{row.get('Value', 'N/A')}</td>
                            <td>{safe_convert_to_int(row.get('Owned', 0)):,}</td>
                        </tr>
"""
            
            html_content += f"""
                    </tbody>
                </table>
            </div>
            
            <!-- GRÁFICOS FINVIZ (mantener como están) -->
            <div class="charts-container">
                <div class="chart-section">
                    <div class="chart-title">📊 Gráfico Diario</div>
                    <img 
                        src="https://finviz.com/chart.ashx?t={ticker}&ty=c&ta=1&p=d&s=l" 
                        alt="{ticker} Daily Chart"
                        class="finviz-image"
                        onclick="openModal(this.src, '{ticker} - Diario')"
                        onerror="this.style.display='none'; this.parentElement.innerHTML='<div style=\\'color:#666;padding:40px;\\'>📊 Gráfico no disponible</div>'"
                        loading="lazy">
                </div>
                
                <div class="chart-section">
                    <div class="chart-title">📈 Gráfico Semanal</div>
                    <img 
                        src="https://finviz.com/chart.ashx?t={ticker}&ty=c&ta=1&p=w&s=l" 
                        alt="{ticker} Weekly Chart"
                        class="finviz-image"
                        onclick="openModal(this.src, '{ticker} - Semanal')"
                        onerror="this.style.display='none'; this.parentElement.innerHTML='<div style=\\'color:#666;padding:40px;\\'>📈 Gráfico no disponible</div>'"
                        loading="lazy">
                </div>
            </div>
            
            <!-- ENLACES EXTERNOS -->
            <div class="links-section">
                <a href="https://finviz.com/quote.ashx?t={ticker}" target="_blank" class="external-link finviz-link">
                    📊 Ver en FinViz
                </a>
                <a href="https://finance.yahoo.com/chart/{ticker}" target="_blank" class="external-link yahoo-link">
                    📈 Yahoo Finance
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
            <div id="modalTitle" style="color: white; margin-top: 10px; font-size: 18px;"></div>
        </div>
    </div>
    
    <script>
        function openModal(src, title) {
            document.getElementById('imageModal').style.display = 'block';
            document.getElementById('modalImage').src = src;
            document.getElementById('modalTitle').textContent = title;
        }
        
        function closeModal() {
            document.getElementById('imageModal').style.display = 'none';
        }
        
        // Cerrar con escape o click fuera
        window.onclick = function(event) {
            const modal = document.getElementById('imageModal');
            if (event.target === modal) closeModal();
        }
        
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') closeModal();
        });
        
        // Log
        console.log('📊 Dashboard con datos completos del CSV cargado');
        console.log('✅ Mostrando TODOS los datos del CSV + gráficos FinViz');
    </script>
</body>
</html>
"""
        
        # Guardar HTML
        html_path = "reports/insiders_report_completo.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print(f"✅ HTML completo generado: {html_path}")
        print("🔧 Características:")
        print("   ✅ TODOS los datos del CSV mostrados")
        print("   ✅ Tabla detallada de transacciones")
        print("   ✅ Gráficos FinViz mantenidos")
        print("   ✅ Diseño responsive")
        
        return html_path
        
    except Exception as e:
        print(f"❌ Error generando HTML completo: {e}")
        import traceback
        traceback.print_exc()
        return None
def safe_convert_to_float(value):
    """
    Convierte un valor a float manejando comas y otros formatos
    """
    if pd.isna(value):
        return 0.0
    
    try:
        # Si ya es un número, devolverlo
        if isinstance(value, (int, float)):
            return float(value)
        
        # Si es string, limpiar y convertir
        str_value = str(value).strip()
        # Remover comas de separadores de miles
        str_value = str_value.replace(',', '')
        # Remover símbolos de moneda si existen
        str_value = str_value.replace('$', '').replace('€', '')
        
        return float(str_value)
    except (ValueError, TypeError):
        return 0.0

def safe_convert_to_int(value):
    """
    Convierte un valor a int manejando diferentes formatos
    """
    if pd.isna(value):
        return 0
    
    try:
        # Si ya es un número, devolverlo
        if isinstance(value, (int, float)):
            return int(value)
        
        # Si es string, limpiar y convertir
        str_value = str(value).strip()
        # Remover comas de separadores de miles
        str_value = str_value.replace(',', '')
        
        return int(float(str_value))  # Convertir a float primero por si tiene decimales
    except (ValueError, TypeError):
        return 0

def generate_finviz_chart_iframe(ticker, timeframe="d", width=320, height=200):
    """
    Genera un iframe con el gráfico de FinViz embebido que se puede abrir en grande
    
    Args:
        ticker (str): símbolo de la acción
        timeframe (str): 'd' para diario, 'w' para semanal, 'm' para mensual
        width (int): ancho del iframe
        height (int): altura del iframe
    
    Returns:
        str: HTML del iframe de FinViz con funcionalidad de clic
    """
    # URL de FinViz con parámetros
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
    """
    Calcula el porcentaje de incremento de los insiders para un ticker
    """
    try:
        if len(ticker_data) == 0:
            return 0.0
        
        # Sumar todas las compras para este ticker
        total_compras = len(ticker_data)
        
        # Calcular el valor total invertido
        valores = []
        for _, row in ticker_data.iterrows():
            price = safe_convert_to_float(row['Price'])
            qty = safe_convert_to_int(row['Qty'])
            valores.append(price * qty)
        
        valor_total = sum(valores)
        
        # Si hay columna 'Value' que ya tenga porcentajes, usarla
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
                return sum(percentages) / len(percentages)  # Promedio
        
        # Fallback: calcular basado en número de transacciones
        # Más transacciones = más confianza
        if total_compras >= 5:
            return 15.0  # Alta confianza
        elif total_compras >= 3:
            return 10.0  # Media confianza
        elif total_compras >= 2:
            return 7.5   # Baja confianza
        else:
            return 5.0   # Muy baja confianza
            
    except Exception as e:
        print(f"⚠️ Error calculando porcentaje para ticker: {e}")
        return 0.0

def crear_html_con_finviz():
    """
    Crea el HTML con gráficos de FinViz embebidos y porcentajes de insider
    """
    # Calcular estadísticas de forma segura
    total_transactions = len(df)
    unique_tickers = df['Insider'].nunique()
    
    # Calcular valor total de forma segura
    try:
        prices = df['Price'].apply(safe_convert_to_float)
        quantities = df['Qty'].apply(safe_convert_to_int)
        total_value = (prices * quantities).sum()
    except Exception as e:
        print(f"⚠️ Error calculando valor total: {e}")
        total_value = 0
    
    last_update = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
    
    # Agrupar por ticker para calcular estadísticas
    ticker_stats = {}
    for ticker in df['Insider'].unique():
        if pd.notna(ticker):
            ticker_data = df[df['Insider'] == ticker]
            ticker_stats[ticker] = {
                'count': len(ticker_data),
                'percentage': calcular_porcentaje_insider(ticker_data),
                'total_value': (ticker_data['Price'].apply(safe_convert_to_float) * 
                              ticker_data['Qty'].apply(safe_convert_to_int)).sum()
            }
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Informe de Compras de Insiders</title>
        <style>
            body {{ 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                padding: 0; 
                margin: 0;
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            }}
            
            .container {{
                max-width: 1800px;
                margin: 0 auto;
                background: white;
                min-height: 100vh;
            }}
            
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }}
            
            h1 {{ 
                margin: 0;
                font-size: 2.5em;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }}
            
            .subtitle {{
                margin-top: 10px;
                font-size: 1.1em;
                opacity: 0.9;
            }}
            
            .stats-bar {{
                background: #f8f9fa;
                padding: 20px;
                text-align: center;
                border-bottom: 2px solid #e9ecef;
                display: flex;
                justify-content: space-around;
                flex-wrap: wrap;
            }}
            
            .stat-item {{
                margin: 10px;
                text-align: center;
            }}
            
            .stat-number {{
                font-size: 1.5em;
                font-weight: bold;
                color: #1976D2;
            }}
            
            .stat-label {{
                color: #666;
                font-size: 0.9em;
            }}
            
            table {{ 
                width: 100%; 
                border-collapse: collapse; 
                margin: 0;
                font-size: 0.9em;
            }}
            
            th, td {{ 
                border: 1px solid #dee2e6; 
                padding: 10px; 
                text-align: center; 
                vertical-align: middle; 
            }}
            
            th {{ 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                font-weight: 600;
                position: sticky;
                top: 0;
                z-index: 10;
                font-size: 0.85em;
            }}
            
            tr:nth-child(even) {{
                background-color: #f8f9fa;
            }}
            
            tr:hover {{
                background-color: #e3f2fd;
                transition: background-color 0.3s ease;
            }}
            
            .ticker-cell {{
                font-weight: bold;
                font-size: 1.1em;
                color: #1976d2;
                background-color: #e3f2fd !important;
            }}
            
            .price-cell {{
                font-weight: bold;
                color: #2e7d32;
            }}
            
            .chart-cell {{
                padding: 5px;
                background-color: #fafafa;
            }}
            
            .company-name {{
                font-size: 0.85em;
                color: #666;
                max-width: 150px;
                overflow: hidden;
                text-overflow: ellipsis;
            }}
            
            .transaction-type {{
                background: #4caf50;
                color: white;
                padding: 3px 6px;
                border-radius: 12px;
                font-size: 0.75em;
            }}
            
            .percentage-cell {{
                font-weight: bold;
                color: #ff5722;
            }}
            
            .percentage-positive {{
                color: #4caf50 !important;
            }}
            
            .percentage-high {{
                background-color: #c8e6c9 !important;
            }}
            
            .chart-container {{
                position: relative;
                display: inline-block;
                transition: transform 0.2s ease;
            }}
            
            .chart-container:hover {{
                transform: scale(1.02);
            }}
            
            .chart-overlay {{
                position: absolute;
                top: 5px;
                right: 5px;
                background: rgba(0,0,0,0.7);
                color: white;
                padding: 5px 8px;
                border-radius: 15px;
                font-size: 12px;
                opacity: 0;
                transition: opacity 0.3s ease;
            }}
            
            .chart-container:hover .chart-overlay {{
                opacity: 1;
            }}
            
            .zoom-icon {{
                font-size: 14px;
            }}
            
            /* Modal para gráfico en grande */
            .modal {{
                display: none;
                position: fixed;
                z-index: 1000;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0,0,0,0.9);
            }}
            
            .modal-content {{
                position: relative;
                margin: 1% auto;
                width: 95%;
                max-width: 1400px;
                height: 95%;
            }}
            
            .modal iframe {{
                width: 100%;
                height: 100%;
                border: none;
                border-radius: 10px;
            }}
            
            .close {{
                position: absolute;
                top: -50px;
                right: 0;
                color: white;
                font-size: 40px;
                font-weight: bold;
                cursor: pointer;
                z-index: 1001;
                background: rgba(0,0,0,0.5);
                padding: 5px 15px;
                border-radius: 50%;
            }}
            
            .close:hover {{
                color: #ff4444;
                background: rgba(0,0,0,0.8);
            }}
            
            .modal-title {{
                position: absolute;
                top: -50px;
                left: 0;
                color: white;
                font-size: 22px;
                font-weight: bold;
                background: rgba(0,0,0,0.7);
                padding: 10px 20px;
                border-radius: 25px;
            }}
            
            iframe {{
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
            
            @media (max-width: 768px) {{
                .stats-bar {{
                    flex-direction: column;
                }}
                
                th, td {{
                    padding: 4px;
                    font-size: 0.7em;
                }}
                
                iframe {{
                    width: 280px !important;
                    height: 180px !important;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 Informe de Compras de Insiders</h1>
                <p class="subtitle">Análisis en tiempo real con gráficos de FinViz</p>
            </div>
            
            <div class="stats-bar">
                <div class="stat-item">
                    <div class="stat-number">{total_transactions}</div>
                    <div class="stat-label">Total Transacciones</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">{unique_tickers}</div>
                    <div class="stat-label">Empresas Únicas</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">${total_value:,.0f}</div>
                    <div class="stat-label">Valor Total</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">{last_update}</div>
                    <div class="stat-label">Última Actualización</div>
                </div>
            </div>
            
            <table>
                <tr>
                    <th>Ticker</th>
                    <th>Empresa</th>
                    <th>Insider</th>
                    <th>Tipo</th>
                    <th>Precio</th>
                    <th>Cantidad</th>
                    <th>Poseídas</th>
                    <th>Valor Trans.</th>
                    <th>% Insider</th>
                    <th>Fuente</th>
                    <th>Fecha Scraping</th>
                    <th>Gráfico Diario (FinViz)</th>
                    <th>Gráfico Semanal (FinViz)</th>
                </tr>
    """
    
    # Procesar cada fila del DataFrame - TODAS LAS COLUMNAS
    for _, row in df.iterrows():
        # Extraer todos los datos del CSV
        ticker = str(row['Insider']).strip().upper()
        company_name = str(row['Title'])
        insider_title = str(row['Date'])
        transaction_type = str(row['Type'])
        
        # Convertir valores numéricos de forma segura
        price = safe_convert_to_float(row['Price'])
        quantity = safe_convert_to_int(row['Qty'])
        owned = safe_convert_to_int(row['Owned'])
        value_column = str(row.get('Value', ''))
        source = str(row.get('Source', ''))
        scraped_at = str(row.get('ScrapedAt', ''))
        
        # Calcular valor de transacción
        transaction_value = price * quantity
        
        # Obtener porcentaje de insider
        insider_percentage = ticker_stats.get(ticker, {}).get('percentage', 0.0)
        
        # Clases CSS para porcentaje
        percentage_class = "percentage-cell"
        if insider_percentage > 0:
            percentage_class += " percentage-positive"
        if insider_percentage >= 10:
            percentage_class += " percentage-high"
        
        # Generar iframes de FinViz
        daily_chart = generate_finviz_chart_iframe(ticker, "d", 320, 200)
        weekly_chart = generate_finviz_chart_iframe(ticker, "w", 320, 200)
        
        html_content += f"""
            <tr>
                <td class="ticker-cell">{ticker}</td>
                <td class="company-name">{company_name}</td>
                <td>{insider_title}</td>
                <td><span class="transaction-type">{transaction_type}</span></td>
                <td class="price-cell">${price:.2f}</td>
                <td>{quantity:,}</td>
                <td>{owned:,}</td>
                <td class="price-cell">${transaction_value:,.0f}</td>
                <td class="{percentage_class}">{insider_percentage:.1f}%</td>
                <td>{source}</td>
                <td style="font-size: 0.8em;">{scraped_at}</td>
                <td class="chart-cell">{daily_chart}</td>
                <td class="chart-cell">{weekly_chart}</td>
            </tr>
        """
    
    html_content += """
            </table>
        </div>
        
        <!-- Modal para gráfico en grande -->
        <div id="chartModal" class="modal">
            <div class="modal-content">
                <div class="modal-title" id="modalTitle"></div>
                <span class="close" onclick="closeChart()">&times;</span>
                <iframe id="modalChart" src="" frameborder="0"></iframe>
            </div>
        </div>
        
        <script>
            // Función para abrir gráfico en grande
            function openChart(url, ticker, timeframe) {
                const modal = document.getElementById('chartModal');
                const modalChart = document.getElementById('modalChart');
                const modalTitle = document.getElementById('modalTitle');
                
                modalChart.src = url;
                modalTitle.textContent = `${ticker} - Gráfico ${timeframe === 'd' ? 'Diario' : 'Semanal'}`;
                modal.style.display = 'block';
            }
            
            // Función para cerrar gráfico
            function closeChart() {
                const modal = document.getElementById('chartModal');
                const modalChart = document.getElementById('modalChart');
                
                modal.style.display = 'none';
                modalChart.src = ''; // Limpiar src para parar la carga
            }
            
            // Cerrar modal al hacer clic fuera
            window.onclick = function(event) {
                const modal = document.getElementById('chartModal');
                if (event.target === modal) {
                    closeChart();
                }
            }
            
            // Cerrar modal con tecla ESC
            document.addEventListener('keydown', function(event) {
                if (event.key === 'Escape') {
                    closeChart();
                }
            });
            
            // Verificar si los iframes de FinViz se cargan correctamente
            document.addEventListener('DOMContentLoaded', function() {
                const iframes = document.querySelectorAll('iframe');
                console.log(`📊 ${iframes.length} gráficos de FinViz cargados`);
                
                // Añadir evento de error para iframes
                iframes.forEach((iframe, index) => {
                    iframe.addEventListener('error', function() {
                        console.warn(`⚠️ Error cargando gráfico ${index + 1}`);
                    });
                    
                    iframe.addEventListener('load', function() {
                        console.log(`✅ Gráfico ${index + 1} cargado`);
                    });
                });
            });
        </script>
    </body>
    </html>
    """
    
    # Escribir el archivo HTML
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"✅ HTML con FinViz generado en {html_path}")
    return html_path

def crear_bundle_completo():
    """
    Crea un ZIP con el HTML y CSV (ya no necesitamos gráficos PNG)
    """
    zip_path = "reports/insiders_report_bundle.zip"
    with zipfile.ZipFile(zip_path, "w") as zipf:
        # Añadir HTML
        if os.path.exists(html_path):
            zipf.write(html_path, arcname=os.path.basename(html_path))
        
        # Añadir CSV original
        if os.path.exists(csv_path):
            zipf.write(csv_path, arcname=os.path.basename(csv_path))
    
    print(f"✅ ZIP bundle generado en {zip_path}")
    return zip_path

def enviar_por_telegram(html_path, bundle_path):
    """
    Envía SOLO el archivo HTML por Telegram (más simple y eficiente)
    """
    try:
        # Importar configuración de Telegram
        try:
            from config import TELEGRAM_CHAT_ID, TELEGRAM_BOT_TOKEN
            chat_id = TELEGRAM_CHAT_ID
            token = TELEGRAM_BOT_TOKEN
        except ImportError as e:
            print(f"❌ Error importando configuración: {e}")
            print("   Asegúrate de que config.py tenga TELEGRAM_CHAT_ID y TELEGRAM_BOT_TOKEN")
            return False
        
        if not chat_id or not token:
            print("⚠️ TELEGRAM_CHAT_ID o TELEGRAM_BOT_TOKEN están vacíos")
            return False
        
        print(f"📱 Chat ID: {chat_id}")
        print(f"🤖 Token: {token[:10]}...")
        
        # Importar funciones de Telegram
        from alerts.telegram_utils import send_message, send_file
        
        # Mensaje de inicio con estadísticas
        total_transactions = len(df)
        unique_tickers = df['Insider'].nunique()
        mensaje_inicio = f"""🚀 REPORTE INSIDER TRADING ACTUALIZADO

📊 {total_transactions} transacciones analizadas
🏢 {unique_tickers} empresas únicas
📈 Gráficos FinViz interactivos
🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}

📄 Archivo HTML adjunto con análisis completo"""
        
        print("📤 Enviando mensaje de inicio...")
        send_message(token, chat_id, mensaje_inicio)
        print("✅ Mensaje de inicio enviado")
        
        # Enviar SOLO el archivo HTML (contiene todo lo necesario)
        if os.path.exists(html_path):
            print("📄 Enviando archivo HTML...")
            send_file(token, chat_id, html_path)
            print(f"✅ HTML enviado: {html_path}")
        else:
            print(f"⚠️ HTML no encontrado: {html_path}")
            return False
        
        # Mensaje final con instrucciones
        mensaje_final = """✅ Reporte enviado exitosamente

🔍 Abre el archivo HTML en tu navegador
📱 Los gráficos son interactivos (haz clic para agrandar)
🔄 Datos actualizados en tiempo real desde FinViz"""
        
        print("📤 Enviando mensaje final...")
        send_message(token, chat_id, mensaje_final)
        print("✅ Mensaje final enviado")
        
        print("🎉 Envío por Telegram completado exitosamente")
        return True
        
    except ImportError as e:
        print(f"❌ Error de importación: {e}")
        return False
    except Exception as e:
        print(f"❌ Error enviando por Telegram: {e}")
        import traceback
        traceback.print_exc()
        return False
def enviar_reporte_completo_con_github_pages(html_path, csv_path, bundle_path):
    """
    Versión mejorada que sube HTML a GitHub Pages y envía por Telegram
    Integra con el sistema existente de análisis de insider trading
    """
    try:
        from github_pages_uploader import GitHubPagesUploader
        from datetime import datetime
        import os
        
        print("🌐 Subiendo reporte a GitHub Pages...")
        
        # Inicializar uploader
        uploader = GitHubPagesUploader()
        
        # Generar título y descripción
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        title = f"📊 Análisis Insider Trading - {timestamp}"
        
        # Contar estadísticas del reporte
        total_transactions = len(df) if 'df' in globals() else 0
        unique_tickers = df['Insider'].nunique() if 'df' in globals() else 0
        
        description = f"""Reporte completo de insider trading con {total_transactions} transacciones 
        de {unique_tickers} empresas. Incluye gráficos interactivos de FinViz y análisis detallado."""
        
        # Subir a GitHub Pages
        github_result = uploader.upload_report(html_path, title, description)
        
        if github_result:
            print(f"✅ Subido a GitHub Pages: {github_result['file_url']}")
            
            # Enviar por Telegram con URL de GitHub Pages
            enviar_telegram_con_github_pages(github_result, csv_path, bundle_path)
            
            return github_result
        else:
            print("⚠️ Error subiendo a GitHub Pages, enviando por método tradicional")
            # Fallback al método original
            enviar_por_telegram(html_path, bundle_path)
            return None
            
    except ImportError:
        print("⚠️ github_pages_uploader no disponible, usando método tradicional")
        enviar_por_telegram(html_path, bundle_path)
        return None
    except Exception as e:
        print(f"❌ Error con GitHub Pages: {e}")
        # Fallback al método original
        enviar_por_telegram(html_path, bundle_path)
        return None


def enviar_telegram_con_github_pages(github_result, csv_path, bundle_path):
    """
    Envía notificación por Telegram con enlaces de GitHub Pages
    """
    try:
        from config import TELEGRAM_CHAT_ID, TELEGRAM_BOT_TOKEN
        from alerts.telegram_utils import send_message, send_file
        
        if not TELEGRAM_CHAT_ID or not TELEGRAM_BOT_TOKEN:
            print("⚠️ Configuración de Telegram no disponible")
            return False
        
        # Estadísticas del reporte
        total_transactions = len(df) if 'df' in globals() else 0
        unique_tickers = df['Insider'].nunique() if 'df' in globals() else 0
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        # Mensaje principal con enlaces
        mensaje = f"""🚀 NUEVO REPORTE INSIDER TRADING

📊 **Estadísticas:**
• {total_transactions} transacciones analizadas
• {unique_tickers} empresas únicas
• Actualizado: {timestamp}

🌐 **Enlaces directos:**
• 📈 [Ver reporte completo]({github_result['file_url']})
• 🏠 [Todos los reportes]({github_result['index_url']})

✨ **Características:**
📱 Optimizado para móvil
🔍 Gráficos interactivos FinViz
💾 Historial completo disponible
🔄 Datos en tiempo real

📄 CSV adjunto para análisis detallado"""
        
        # Enviar mensaje principal
        print("📤 Enviando mensaje con enlaces...")
        send_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, mensaje)
        
        # Enviar CSV como archivo adjunto
        if csv_path and os.path.exists(csv_path):
            print("📎 Enviando CSV...")
            send_file(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, csv_path)
        
        print("✅ Notificación de GitHub Pages enviada por Telegram")
        return True
        
    except Exception as e:
        print(f"❌ Error enviando por Telegram: {e}")
        return False
    
def generar_reporte_completo():
    """
    Ejecuta todo el proceso: HTML con FinViz, bundle y envío con GitHub Pages
    """
    print("🚀 Iniciando generación de reporte con FinViz y GitHub Pages...")
    
    # 1. Crear HTML con FinViz embebido
    print("\n📄 PASO 1: Generando HTML con FinViz...")
    html_path_generated = crear_html_moderno_finviz()
    
    # 2. Crear bundle ZIP
    print("\n📦 PASO 2: Creando bundle...")
    bundle_path = crear_bundle_completo()
    
    # 3. NUEVO: Subir a GitHub Pages y enviar por Telegram
    print("\n🌐 PASO 3: Subiendo a GitHub Pages y enviando por Telegram...")
    github_result = enviar_reporte_completo_con_github_pages(
        html_path_generated, 
        csv_path, 
        bundle_path
    )
    
    print(f"\n🎉 ¡Proceso completado!")
    print(f"📄 HTML local: {html_path_generated}")
    print(f"📦 Bundle: {bundle_path}")
    if github_result:
        print(f"🌐 URL pública: {github_result['file_url']}")
        print(f"🏠 Sitio principal: {github_result['index_url']}")
    print(f"📊 Gráficos: FinViz embebidos (interactivos)")
    print(f"📱 Telegram: ✅ Enviado con enlaces públicos")
    
    return {
        'html_path': html_path_generated,
        'bundle_path': bundle_path,
        'github_result': github_result
    }
def enviar_reporte_completo_con_github_pages_historial(html_path, csv_path, bundle_path):
    """
    Versión mejorada que mantiene historial completo en GitHub Pages
    """
    try:
        from github_pages_historial import GitHubPagesHistoricalUploader
        from datetime import datetime
        import os
        
        print("🌐 Subiendo reporte con historial completo...")
        
        # Inicializar uploader histórico
        uploader = GitHubPagesHistoricalUploader()
        
        # Generar título y descripción basados en datos
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        # Leer estadísticas del CSV
        try:
            import pandas as pd
            df = pd.read_csv(csv_path)
            
            if len(df) > 0 and 'Mensaje' not in df.columns:
                title = f"📊 Análisis Completo Insider Trading - {len(df)} oportunidades - {timestamp}"
                description = f"Reporte completo con gráficos FinViz y análisis de {len(df)} oportunidades detectadas el {timestamp}"
            else:
                title = f"📊 Monitoreo Insider Trading - {timestamp}"
                description = f"Análisis completado el {timestamp}. Sistema funcionando correctamente."
        except:
            title = f"📊 Análisis Insider Trading - {timestamp}"
            description = f"Reporte de análisis completo generado el {timestamp}"
        
        # Subir con historial mantenido
        github_result = uploader.upload_historical_report(html_path, csv_path, title, description)
        
        if github_result:
            print(f"✅ Subido con historial: {github_result['file_url']}")
            
            # Generar análisis cruzado
            print("🔍 Generando análisis cruzado...")
            cross_analysis_file = uploader.generate_cross_analysis_report(30)
            
            # Enviar por Telegram con enlaces históricos
            enviar_telegram_con_historial_completo(csv_path, html_path, github_result, cross_analysis_file)
            
            return github_result
        else:
            print("⚠️ Error subiendo con historial, usando método tradicional")
            # Fallback al método original
            enviar_por_telegram(html_path, bundle_path)
            return None
            
    except ImportError:
        print("⚠️ Sistema de historial no disponible, usando método tradicional")
        enviar_por_telegram(html_path, bundle_path)
        return None
    except Exception as e:
        print(f"❌ Error con sistema de historial: {e}")
        enviar_por_telegram(html_path, bundle_path)
        return None


def enviar_telegram_con_historial_completo(csv_path, html_path, github_result, cross_analysis_file):
    """
    Envía notificación por Telegram con enlaces históricos completos
    """
    try:
        from config import TELEGRAM_CHAT_ID, TELEGRAM_BOT_TOKEN
        from alerts.telegram_utils import send_message, send_file
        import pandas as pd
        from datetime import datetime
        
        if not TELEGRAM_CHAT_ID or not TELEGRAM_BOT_TOKEN:
            print("⚠️ Configuración de Telegram no disponible")
            return False
        
        # Leer estadísticas del CSV
        df = pd.read_csv(csv_path)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        if len(df) == 0 or 'Mensaje' in df.columns:
            # Sin oportunidades pero con historial
            mensaje = f"""🎯 MONITOREO INSIDER TRADING

📊 Resultado: Sin oportunidades detectadas
📅 Fecha: {timestamp}
✅ Sistema funcionando correctamente

🌐 **HISTORIAL COMPLETO:**
• 📈 Ver todos los reportes: {github_result['index_url']}
• 🔍 Análisis cruzado: cross_analysis.html
• 📊 Tendencias temporales: trends.html
• 📅 Resúmenes semanales: reports/weekly/
• 📊 Resúmenes mensuales: reports/monthly/

🎯 **Análisis Cruzado Disponible:**
El sistema ahora mantiene historial completo para identificar:
• Tickers con actividad recurrente de insiders
• Patrones de compra sostenida en el tiempo
• Señales que se repiten múltiples veces
• Tendencias a largo plazo por empresa

💡 **Próxima vez que aparezcan oportunidades:**
Podrás ver si ya habían aparecido antes y evaluar la consistencia de las señales."""

        else:
            # Con oportunidades + historial
            score_column = "FinalScore" if "FinalScore" in df.columns else "InsiderConfidence"
            
            # Calcular estadísticas
            try:
                score_values = pd.to_numeric(df[score_column], errors='coerce').dropna()
                avg_score = score_values.mean() if len(score_values) > 0 else 0
                top_ticker = df.iloc[0]['Ticker'] if len(df) > 0 else "N/A"
                top_score_raw = df.iloc[0][score_column] if len(df) > 0 and score_column in df.columns else 0
                top_score = float(top_score_raw) if pd.notna(top_score_raw) else 0
            except:
                avg_score = 0
                top_ticker = "N/A"
                top_score = 0
            
            mensaje = f"""🎯 REPORTE INSIDER TRADING CON HISTORIAL

📊 **Oportunidades actuales:** {len(df)}
📈 **Score promedio:** {avg_score:.1f}
🏆 **Top oportunidad:** {top_ticker} (Score: {top_score:.1f})
📅 **Fecha:** {timestamp}

🔝 **Top 5 oportunidades:**"""
            
            # Agregar top 5
            for i, row in df.head(5).iterrows():
                try:
                    ticker = row.get('Ticker', 'N/A')
                    score_raw = row.get(score_column, 0)
                    confidence = row.get('ConfidenceLevel', 'N/A')
                    transactions = row.get('NumTransactions', 0)
                    
                    try:
                        score_val = float(score_raw) if pd.notna(score_raw) else 0
                    except:
                        score_val = 0
                    
                    mensaje += f"\n{i+1}. {ticker} - Score: {score_val:.1f} ({confidence}) - {transactions} trans"
                    
                except:
                    continue
            
            mensaje += f"""

🌐 **ENLACES COMPLETOS:**
• 📊 Reporte actual: {github_result['file_url']}
• 📈 Historial completo: {github_result['index_url']}
• 🔍 Análisis cruzado: cross_analysis.html
• 📊 Tendencias: trends.html

✨ **NUEVAS CARACTERÍSTICAS:**
🏛️ **Historial permanente:** Todos los reportes se mantienen
🔍 **Análisis cruzado:** Identifica actividad recurrente de tickers
📈 **Detección de patrones:** Ve si un ticker aparece múltiples veces
🎯 **Evaluación de consistencia:** Analiza si las señales se repiten
📅 **Resúmenes temporales:** Análisis semanal y mensual
🔄 **Tendencias a largo plazo:** Patrones de comportamiento sostenido

💡 **Cómo usar el historial:**
1. Revisa si las oportunidades actuales ya aparecieron antes
2. Evalúa la frecuencia de aparición de cada ticker
3. Confirma patrones con el análisis cruzado
4. Usa tendencias para timing de inversión"""
        
        # Enviar mensaje principal
        print("📤 Enviando mensaje con historial...")
        send_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, mensaje)
        
        # Enviar archivo CSV para análisis detallado
        if csv_path and os.path.exists(csv_path):
            print("📎 Enviando CSV...")
            send_file(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, csv_path)
        
        print("✅ Notificación con historial enviada por Telegram")
        return True
        
    except Exception as e:
        print(f"❌ Error enviando por Telegram: {e}")
        return False


# Modificar la función generar_reporte_completo existente
def generar_reporte_completo_con_historial():
    """
    Versión mejorada de generar_reporte_completo que mantiene historial
    """
    print("🚀 Iniciando generación de reporte con historial...")
    
    # 1. Crear HTML con FinViz embebido (mantener función existente)
    print("\n📄 PASO 1: Generando HTML con FinViz...")
    html_path_generated = crear_html_moderno_finviz()
    
    # 2. Crear bundle ZIP (mantener función existente)
    print("\n📦 PASO 2: Creando bundle...")
    bundle_path = crear_bundle_completo()
    
    # 3. NUEVO: Subir con historial completo y enviar por Telegram
    print("\n🌐 PASO 3: Subiendo con historial y enviando por Telegram...")
    github_result = enviar_reporte_completo_con_github_pages_historial(
        html_path_generated, 
        csv_path,  # Variable global del CSV
        bundle_path
    )
    
    print(f"\n🎉 ¡Proceso completado!")
    print(f"📄 HTML local: {html_path_generated}")
    print(f"📦 Bundle: {bundle_path}")
    if github_result:
        print(f"🌐 URL pública: {github_result['file_url']}")
        print(f"🏠 Historial completo: {github_result['index_url']}")
        print(f"🔍 Análisis cruzado: cross_analysis.html")
    print(f"📊 Gráficos: FinViz embebidos (interactivos)")
    print(f"📱 Telegram: ✅ Enviado con enlaces históricos")
    
    return {
        'html_path': html_path_generated,
        'bundle_path': bundle_path,
        'github_result': github_result,
        'csv_path': csv_path
    }

# Ejecutar automáticamente si se ejecuta este script
if __name__ == "__main__":
    crear_html_moderno_finviz()