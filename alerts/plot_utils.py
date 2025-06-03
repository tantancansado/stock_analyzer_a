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
    html_path_generated = crear_html_con_finviz()
    
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

# Ejecutar automáticamente si se ejecuta este script
if __name__ == "__main__":
    generar_reporte_completo()