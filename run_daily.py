import requests
import os
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime, timedelta
import time

# Intenta importar yfinance, si no está disponible usará datos simulados
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
    print("✅ yfinance disponible")
except ImportError:
    YFINANCE_AVAILABLE = False
    print("⚠️ yfinance no disponible, usando datos simulados")

# Configuración Alpha Vantage (tu API key ya configurada)
ALPHA_VANTAGE_API_KEY = "GPA37GJVIDCNNTRL"

def descargar_grafico_finviz_con_cache(ticker: str, timeframe: str = "d", output_dir: str = "reports/graphs") -> str:
    """
    Descarga/genera el gráfico del ticker usando múltiples fuentes como alternativa a FinViz.
    
    Args:
        ticker (str): símbolo de la acción.
        timeframe (str): 'd' para diario, 'w' para semanal.
        output_dir (str): carpeta donde guardar el gráfico.

    Returns:
        str: ruta local del archivo de imagen, o None si falla.
    """
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{ticker}_{timeframe}.png")

    # Si ya existe y es una imagen válida, no generar de nuevo
    if os.path.exists(output_path):
        try:
            with open(output_path, "rb") as f:
                header = f.read(8)
                if header.startswith(b"\x89PNG") and os.path.getsize(output_path) > 5000:
                    print(f"⏭️ Ya existe {output_path}, se omite generación.")
                    return output_path
        except Exception as e:
            print(f"⚠️ Error comprobando imagen local {output_path}: {e}")

    try:
        # Método 1: Alpha Vantage PRIMERO (ya que tienes API key)
        success = generar_grafico_alphavantage(ticker, timeframe, output_path)
        if success:
            return output_path
        
        # Método 2: Fallback a yfinance si Alpha Vantage falla
        if YFINANCE_AVAILABLE:
            success = generar_grafico_yfinance(ticker, timeframe, output_path)
            if success:
                return output_path
        
        # Método 3: Fallback final - gráfico con datos simulados pero realistas
        success = generar_grafico_realista(ticker, timeframe, output_path)
        
        if success:
            print(f"✅ Gráfico generado para {ticker} ({timeframe}) en {output_path}")
            return output_path
        else:
            print(f"❌ No se pudo generar gráfico para {ticker} ({timeframe})")
            return None
            
    except Exception as e:
        print(f"❌ Excepción al generar gráfico de {ticker}: {e}")
        return None

def generar_grafico_alphavantage(ticker: str, timeframe: str, output_path: str) -> bool:
    """
    Genera gráfico usando Alpha Vantage API (MEJORADO)
    """
    try:
        # Determinar función de API
        if timeframe == "d":
            function = "TIME_SERIES_DAILY"
            time_key = "Time Series (Daily)"
        else:
            function = "TIME_SERIES_WEEKLY"
            time_key = "Time Series (Weekly)"
        
        # Hacer petición a Alpha Vantage
        url = f"https://www.alphavantage.co/query"
        params = {
            "function": function,
            "symbol": ticker,
            "apikey": ALPHA_VANTAGE_API_KEY,
            "outputsize": "compact"
        }
        
        print(f"📡 Consultando Alpha Vantage para {ticker}...")
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code != 200:
            print(f"❌ Error HTTP {response.status_code} en Alpha Vantage")
            return False
            
        data = response.json()
        
        # Verificar errores en la respuesta
        if "Error Message" in data:
            print(f"❌ Error de Alpha Vantage: {data['Error Message']}")
            return False
        
        if "Note" in data:
            print(f"⚠️ Límite de API alcanzado: {data['Note']}")
            return False
        
        # Verificar que tenemos datos
        if time_key not in data:
            print(f"⚠️ No hay datos para {ticker} en Alpha Vantage")
            print(f"🔍 Claves disponibles: {list(data.keys())}")
            return False
        
        # Procesar datos
        time_series = data[time_key]
        
        if not time_series:
            print(f"⚠️ Series temporales vacías para {ticker}")
            return False
        
        dates = []
        opens = []
        highs = []
        lows = []
        closes = []
        volumes = []
        
        # Obtener últimos 100 puntos y ordenar por fecha
        sorted_dates = sorted(time_series.keys())[-100:]
        
        for date_str in sorted_dates:
            values = time_series[date_str]
            dates.append(pd.to_datetime(date_str))
            opens.append(float(values["1. open"]))
            highs.append(float(values["2. high"]))
            lows.append(float(values["3. low"]))
            closes.append(float(values["4. close"]))
            volumes.append(int(values["5. volume"]))
        
        if not dates:
            print(f"⚠️ No se pudieron procesar datos para {ticker}")
            return False
        
        # Crear gráfico profesional
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1]})
        
        # Gráfico de precio con candlestick simplificado
        ax1.plot(dates, closes, linewidth=2, color='#1565C0', label='Precio de Cierre')
        ax1.fill_between(dates, lows, highs, alpha=0.2, color='#42A5F5', label='Rango Diario')
        
        # Títulos y etiquetas
        title_suffix = "Diario" if timeframe == "d" else "Semanal"
        ax1.set_title(f'{ticker.upper()} - {title_suffix} (Alpha Vantage)', 
                     fontsize=16, fontweight='bold', color='#1565C0', pad=20)
        ax1.set_ylabel('Precio ($)', fontweight='bold', fontsize=12)
        ax1.grid(True, alpha=0.3, linestyle='--')
        ax1.legend(frameon=True, shadow=True)
        
        # Estadísticas
        current_price = closes[-1]
        price_change = closes[-1] - closes[0]
        price_change_pct = (price_change / closes[0]) * 100 if closes[0] != 0 else 0
        
        stats_text = f'Último: ${current_price:.2f} | Cambio: {price_change_pct:+.1f}%'
        ax1.text(0.02, 0.98, stats_text, transform=ax1.transAxes, fontsize=10,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))
        
        # Gráfico de volumen con colores
        volume_colors = ['red' if closes[i] < opens[i] else 'green' for i in range(len(closes))]
        ax2.bar(dates, volumes, alpha=0.7, color=volume_colors, width=1)
        ax2.set_ylabel('Volumen', fontweight='bold', fontsize=12)
        ax2.set_xlabel('Fecha', fontweight='bold', fontsize=12)
        ax2.grid(True, alpha=0.3, linestyle='--')
        
        # Formato de fechas
        fig.autofmt_xdate()
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        plt.close()
        
        print(f"✅ Gráfico Alpha Vantage generado para {ticker}")
        return True
        
    except Exception as e:
        print(f"⚠️ Error en Alpha Vantage para {ticker}: {e}")
        return False

def generar_grafico_yfinance(ticker: str, timeframe: str, output_path: str) -> bool:
    """
    Genera gráfico usando yfinance (Yahoo Finance) - MEJORADO
    """
    try:
        # Determinar período de datos
        if timeframe == "d":
            period = "3mo"  # 3 meses de datos diarios
            interval = "1d"
        else:  # timeframe == "w"
            period = "1y"   # 1 año de datos semanales
            interval = "1wk"
        
        print(f"📡 Consultando Yahoo Finance para {ticker}...")
        
        # Descargar datos
        stock = yf.Ticker(ticker)
        data = stock.history(period=period, interval=interval)
        
        if data.empty:
            print(f"⚠️ No hay datos para {ticker} en yfinance")
            return False
        
        # Verificar que tenemos datos suficientes
        if len(data) < 5:
            print(f"⚠️ Datos insuficientes para {ticker} (solo {len(data)} puntos)")
            return False
        
        # Crear gráfico mejorado
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1]})
        
        # Línea de precio de cierre
        ax1.plot(data.index, data['Close'], linewidth=2, color='#1565C0', label='Precio de Cierre', alpha=0.9)
        
        # Área entre máximos y mínimos
        ax1.fill_between(data.index, data['Low'], data['High'], alpha=0.2, color='#42A5F5', label='Rango')
        
        # Títulos y etiquetas
        title_suffix = "Diario" if timeframe == "d" else "Semanal"
        ax1.set_title(f'{ticker.upper()} - {title_suffix} (Yahoo Finance)', 
                     fontsize=16, fontweight='bold', color='#1565C0', pad=20)
        ax1.set_ylabel('Precio ($)', fontweight='bold', fontsize=12)
        ax1.grid(True, alpha=0.3, linestyle='--')
        ax1.legend(frameon=True, shadow=True)
        
        # Añadir estadísticas
        current_price = data['Close'].iloc[-1]
        price_change = data['Close'].iloc[-1] - data['Close'].iloc[0]
        price_change_pct = (price_change / data['Close'].iloc[0]) * 100
        
        stats_text = f'Último: ${current_price:.2f} | Cambio: {price_change_pct:+.1f}%'
        ax1.text(0.02, 0.98, stats_text, transform=ax1.transAxes, fontsize=10,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
        
        # Gráfico de volumen con colores
        volume_colors = ['red' if data['Close'].iloc[i] < data['Open'].iloc[i] else 'green' 
                        for i in range(len(data))]
        ax2.bar(data.index, data['Volume'], alpha=0.7, color=volume_colors, width=1)
        ax2.set_ylabel('Volumen', fontweight='bold', fontsize=12)
        ax2.set_xlabel('Fecha', fontweight='bold', fontsize=12)
        ax2.grid(True, alpha=0.3, linestyle='--')
        
        # Formato de fechas
        fig.autofmt_xdate()
        
        # Ajustar layout y guardar
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        plt.close()
        
        print(f"✅ Gráfico Yahoo Finance generado para {ticker}")
        return True
        
    except Exception as e:
        print(f"⚠️ Error en yfinance para {ticker}: {e}")
        return False

def generar_grafico_realista(ticker: str, timeframe: str, output_path: str) -> bool:
    """
    Genera un gráfico realista usando datos simulados - MEJORADO
    """
    try:
        import numpy as np
        
        # Configurar parámetros según timeframe
        if timeframe == "d":
            periods = 90  # 3 meses
            freq = 'D'
            title_suffix = "Diario (Simulado)"
        else:
            periods = 52  # 1 año
            freq = 'W'
            title_suffix = "Semanal (Simulado)"
        
        # Generar fechas
        dates = pd.date_range(end=datetime.now(), periods=periods, freq=freq)
        
        # Simular precios realistas
        np.random.seed(hash(ticker) % 2**32)  # Seed basado en ticker para consistencia
        
        # Precio base más realista
        base_price = 10 + (hash(ticker) % 100)  # Entre $10 y $110
        
        # Generar walk aleatorio con tendencia más realista
        returns = np.random.normal(0.0005, 0.025, periods)  # Rendimientos más volátiles
        prices = [base_price]
        
        for ret in returns[1:]:
            new_price = prices[-1] * (1 + ret)
            prices.append(max(new_price, 0.1))  # Precio mínimo de $0.1
        
        # Simular volúmenes más realistas
        base_volume = 50000 + (hash(ticker + "volume") % 500000)
        volume_multipliers = np.random.lognormal(0, 0.8, periods)
        volumes = [int(base_volume * mult) for mult in volume_multipliers]
        
        # Simular máximos y mínimos
        highs = [price * (1 + np.random.uniform(0.005, 0.04)) for price in prices]
        lows = [price * (1 - np.random.uniform(0.005, 0.04)) for price in prices]
        
        # Crear DataFrame
        data = pd.DataFrame({
            'Close': prices,
            'High': highs,
            'Low': lows,
            'Volume': volumes
        }, index=dates)
        
        # Crear gráfico
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1]})
        
        # Gráfico de precio
        ax1.plot(data.index, data['Close'], linewidth=2, color='#1565C0', label='Precio Simulado')
        ax1.fill_between(data.index, data['Low'], data['High'], alpha=0.2, color='#42A5F5', label='Rango')
        
        ax1.set_title(f'{ticker.upper()} - {title_suffix}', 
                     fontsize=16, fontweight='bold', color='#1565C0')
        ax1.set_ylabel('Precio ($)', fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        # Añadir marca de agua MÁS SUTIL
        ax1.text(0.5, 0.3, 'DATOS SIMULADOS', transform=ax1.transAxes, 
                fontsize=16, color='red', alpha=0.2, ha='center', va='center',
                rotation=30, fontweight='bold')
        
        # Estadísticas
        current_price = data['Close'].iloc[-1]
        price_change = data['Close'].iloc[-1] - data['Close'].iloc[0]
        price_change_pct = (price_change / data['Close'].iloc[0]) * 100
        
        stats_text = f'Simulado: ${current_price:.2f} | Cambio: {price_change_pct:+.1f}%'
        ax1.text(0.02, 0.98, stats_text, transform=ax1.transAxes, fontsize=10,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.8))
        
        # Gráfico de volumen
        ax2.bar(data.index, data['Volume'], alpha=0.7, color='#FF9800', width=1)
        ax2.set_ylabel('Volumen', fontweight='bold')
        ax2.set_xlabel('Fecha', fontweight='bold')
        ax2.grid(True, alpha=0.3)
        
        # Formato de fechas
        fig.autofmt_xdate()
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        plt.close()
        
        print(f"✅ Gráfico simulado generado para {ticker}")
        return True
        
    except Exception as e:
        print(f"⚠️ Error generando gráfico simulado: {e}")
        return False

def procesar_insiders_csv_y_generar_graficos(csv_path="reports/insiders_daily.csv"):
    """
    Lee el CSV de insiders y genera gráficos para todos los tickers únicos
    """
    try:
        # Leer CSV
        df = pd.read_csv(csv_path)
        print(f"📊 CSV cargado: {len(df)} filas")
        print(f"🔍 Columnas detectadas: {list(df.columns)}")
        
        # El ticker está en la columna 'Insider' según tu estructura
        if 'Insider' in df.columns:
            tickers = df['Insider'].dropna().unique()
        else:
            print("❌ No se encontró la columna 'Insider'")
            return []
        
        # Filtrar tickers válidos
        tickers_validos = []
        for ticker in tickers:
            if pd.notna(ticker) and isinstance(ticker, str) and ticker.strip():
                ticker_clean = str(ticker).strip().upper()
                if len(ticker_clean) <= 5 and ticker_clean.isalpha():  # Filtro básico
                    tickers_validos.append(ticker_clean)
        
        print(f"🎯 Tickers válidos encontrados: {len(tickers_validos)}")
        print(f"📋 Tickers: {tickers_validos[:10]}{'...' if len(tickers_validos) > 10 else ''}")
        
        graficos_generados = []
        
        for i, ticker in enumerate(tickers_validos):
            print(f"\n--- [{i+1}/{len(tickers_validos)}] Procesando {ticker} ---")
            
            # Generar gráfico diario
            daily_path = descargar_grafico_finviz_con_cache(ticker, "d")
            if daily_path:
                graficos_generados.append(daily_path)
            
            # Pausa corta para Alpha Vantage
            time.sleep(0.5)
            
            # Generar gráfico semanal
            weekly_path = descargar_grafico_finviz_con_cache(ticker, "w")
            if weekly_path:
                graficos_generados.append(weekly_path)
            
            # Pausa entre tickers para respetar límites de API
            time.sleep(1)
        
        print(f"\n🎉 Proceso completado. {len(graficos_generados)} gráficos generados.")
        return graficos_generados
        
    except Exception as e:
        print(f"❌ Error procesando CSV: {e}")
        return []

# Función principal para usar desde otros scripts
def run_daily(ticker=None):
    """
    Función principal compatible con tu código existente
    """
    if ticker:
        # Modo individual (como en tu openinsider_scraper.py)
        print(f"🎯 Generando gráficos para {ticker}")
        d_path = descargar_grafico_finviz_con_cache(ticker, "d")
        time.sleep(3)
        w_path = descargar_grafico_finviz_con_cache(ticker, "w")
        return d_path, w_path
    else:
        # Modo batch - procesar todo el CSV
        print("🎯 Generando gráficos para todos los tickers del CSV")
        return procesar_insiders_csv_y_generar_graficos()

# Ejemplo de uso y testing
if __name__ == "__main__":
    print("🚀 Iniciando generación de gráficos...")
    
    # Procesar todos los tickers del CSV
    graficos = procesar_insiders_csv_y_generar_graficos()
    
    print(f"\n📊 RESUMEN:")
    print(f"✅ Gráficos generados: {len(graficos)}")
    
    if graficos:
        print(f"📁 Ubicación: reports/graphs/")
        print(f"🔍 Primeros archivos: {[os.path.basename(g) for g in graficos[:5]]}")