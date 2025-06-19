#!/usr/bin/env python3
"""
VCP Scanner Enhanced - Escanea TODAS las acciones de Wall Street
No solo las que tienen actividad insider
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


class VCPScannerEnhanced:
    """Scanner VCP mejorado para escanear todo el mercado"""
    
    def __init__(self):
        self.min_price = 10
        self.min_volume = 500000  # Volumen mínimo más alto
        self.min_market_cap = 1_000_000_000  # $1B mínimo
        self.lookback_days = 90
        self.max_workers = 10  # Threads paralelos para acelerar
        
    def get_all_tickers(self):
        """Obtiene todos los tickers de NYSE y NASDAQ reales (≈ 5.000-6.000)"""
        try:
            print("📥 Descargando tickers de NASDAQ Trader...")
            nasdaq_url = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
            nasdaq = pd.read_csv(nasdaq_url, sep='|')
            nasdaq = nasdaq[~nasdaq['Symbol'].str.contains('File Creation')]
            nasdaq_tickers = set(nasdaq['Symbol'].tolist())

            other_url = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
            other = pd.read_csv(other_url, sep='|')
            other = other[~other['ACT Symbol'].str.contains('File Creation')]
            nyse_tickers = set(other['ACT Symbol'].tolist())

            all_tickers = nasdaq_tickers.union(nyse_tickers)
            # Filtrar símbolos raros, solo letras, no fondos/ETFs
            tickers = [t for t in all_tickers if t.isalpha() and 1 < len(t) < 6]
            print(f"✅ Total tickers USA: {len(tickers)}")
            return sorted(set(tickers))
        except Exception as e:
            print(f"❌ Error obteniendo tickers: {e}")
            # fallback
            return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA']
    
    def get_stock_data_batch(self, tickers, period="3mo"):
        """Obtiene datos de múltiples tickers en paralelo"""
        data = {}
        
        def fetch_ticker(ticker):
            try:
                stock = yf.Ticker(ticker)
                df = stock.history(period=period)
                if len(df) >= 50:
                    info = stock.info
                    market_cap = info.get('marketCap', 0)
                    if market_cap >= self.min_market_cap:
                        return ticker, df, market_cap
            except:
                pass
            return ticker, None, 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(fetch_ticker, ticker): ticker 
                      for ticker in tickers}
            
            for future in as_completed(futures):
                ticker, df, market_cap = future.result()
                if df is not None:
                    data[ticker] = {'df': df, 'market_cap': market_cap}
        
        return data
    
    def scan_market_for_vcp(self, include_insider_tickers=None):
        """Escanea todo el mercado para patrones VCP"""
        print("\n🚀 ESCÁNER VCP DE MERCADO COMPLETO")
        print("=" * 50)
        
        # Obtener todos los tickers
        all_tickers = self.get_all_tickers()
        
        # Añadir tickers con actividad insider si se proporcionan
        if include_insider_tickers:
            print(f"📊 Añadiendo {len(include_insider_tickers)} tickers con actividad insider")
            all_tickers.extend(include_insider_tickers)
            all_tickers = list(set(all_tickers))  # Eliminar duplicados
        
        print(f"🔍 Escaneando {len(all_tickers)} tickers en total...")
        
        # Procesar en lotes para mejor rendimiento
        batch_size = 50
        vcp_candidates = []
        
        for i in range(0, len(all_tickers), batch_size):
            batch = all_tickers[i:i+batch_size]
            print(f"\n📈 Procesando lote {i//batch_size + 1}/{(len(all_tickers)//batch_size) + 1}")
            
            # Obtener datos del lote
            batch_data = self.get_stock_data_batch(batch)
            
            # Analizar cada ticker del lote
            for ticker, data in batch_data.items():
                df = data['df']
                market_cap = data['market_cap']
                
                # Verificar precio y volumen
                current_price = df['Close'].iloc[-1]
                avg_volume = df['Volume'].iloc[-20:].mean()
                
                if current_price < self.min_price or avg_volume < self.min_volume:
                    continue
                
                # Detectar VCP
                result = self.detect_vcp_pattern(ticker, df)
                if result:
                    result['market_cap'] = market_cap
                    result['has_insider_activity'] = ticker in (include_insider_tickers or [])
                    vcp_candidates.append(result)
                    
                    # Mostrar candidatos prometedores en tiempo real
                    if result['pattern_strength'] > 80:
                        print(f"  🎯 {ticker}: Fuerza {result['pattern_strength']:.0f}%")
            
            # Pequeña pausa para no sobrecargar
            time.sleep(0.5)
        
        # Ordenar por fuerza del patrón y actividad insider
        vcp_candidates.sort(key=lambda x: (
            x['has_insider_activity'],  # Priorizar los que tienen insider
            x['pattern_strength']
        ), reverse=True)
        
        print(f"\n✅ Escaneo completado: {len(vcp_candidates)} patrones VCP encontrados")
        
        return vcp_candidates
    
    def detect_vcp_pattern(self, ticker, df):
        """Detecta patrón VCP mejorado"""
        try:
            # Calcular contracciones
            highs = df['High'].rolling(window=5, center=True).max() == df['High']
            lows = df['Low'].rolling(window=5, center=True).min() == df['Low']
            
            pivot_highs = df[highs]['High'].values
            pivot_lows = df[lows]['Low'].values
            
            if len(pivot_highs) < 3 or len(pivot_lows) < 3:
                return None
            
            # Calcular contracciones
            contractions = []
            for i in range(1, min(len(pivot_highs), len(pivot_lows))):
                if i < len(pivot_highs) and i < len(pivot_lows):
                    contraction = ((pivot_highs[i-1] - pivot_lows[i]) / pivot_highs[i-1]) * 100
                    contractions.append(contraction)
            
            if len(contractions) < 2:
                return None
            
            # Verificar patrón VCP válido
            is_valid_vcp = all(contractions[i] < contractions[i-1] 
                              for i in range(1, len(contractions)))
            
            if not is_valid_vcp:
                return None
            
            # Verificar volumen
            vol_50 = df['Volume'].iloc[-50:].mean()
            vol_10 = df['Volume'].iloc[-10:].mean()
            volume_contracting = vol_10 < vol_50 * 0.7
            
            # Proximidad a resistencia
            current_price = df['Close'].iloc[-1]
            recent_high = df['High'].iloc[-20:].max()
            near_resistance = current_price >= recent_high * 0.98
            
            # Calcular fuerza
            last_contraction = contractions[-1]
            pattern_strength = 100 - last_contraction
            
            # Verificar tendencia general (MA50 < MA200)
            if len(df) >= 200:
                ma50 = df['Close'].iloc[-50:].mean()
                ma200 = df['Close'].iloc[-200:].mean()
                uptrend = ma50 > ma200
            else:
                uptrend = True
            
            return {
                'ticker': ticker,
                'current_price': current_price,
                'contractions': contractions,
                'num_contractions': len(contractions),
                'last_contraction': last_contraction,
                'volume_contracting': volume_contracting,
                'near_resistance': near_resistance,
                'pattern_strength': pattern_strength,
                'uptrend': uptrend,
                'ready_to_buy': near_resistance and volume_contracting and pattern_strength > 70 and uptrend
            }
            
        except:
            return None
    
    def generate_enhanced_vcp_report(self, vcp_candidates, output_file='vcp_report.html'):
        """Genera reporte HTML mejorado con todos los candidatos VCP"""
        
        # Separar por categorías
        insider_ready = [v for v in vcp_candidates if v['has_insider_activity'] and v['ready_to_buy']]
        insider_watch = [v for v in vcp_candidates if v['has_insider_activity'] and not v['ready_to_buy']]
        market_ready = [v for v in vcp_candidates if not v['has_insider_activity'] and v['ready_to_buy']]
        market_watch = [v for v in vcp_candidates if not v['has_insider_activity'] and not v['ready_to_buy']]
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>🎯 VCP Scanner - Análisis Completo del Mercado</title>
    <style>
        body {{ font-family: Arial, sans-serif; background: #0a0e1a; color: #fff; margin: 20px; }}
        h1, h2 {{ color: #4a90e2; }}
        .summary {{ background: #1a202c; padding: 20px; border-radius: 10px; margin: 20px 0; }}
        .category {{ margin: 30px 0; }}
        .ticker-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }}
        .ticker-card {{ background: #2d3748; padding: 20px; border-radius: 8px; border: 1px solid #4a5568; }}
        .ticker-card.ready {{ border-color: #48bb78; box-shadow: 0 0 10px rgba(72, 187, 120, 0.3); }}
        .ticker-card.insider {{ background: #1a202c; border-color: #ffd700; }}
        .ticker {{ font-size: 1.5em; font-weight: bold; color: #4a90e2; }}
        .price {{ color: #48bb78; }}
        .stat {{ margin: 5px 0; font-size: 0.9em; }}
        .ready-badge {{ background: #48bb78; color: white; padding: 5px 10px; border-radius: 15px; font-size: 0.8em; }}
        .watch-badge {{ background: #ed8936; color: white; padding: 5px 10px; border-radius: 15px; font-size: 0.8em; }}
    </style>
</head>
<body>
    <h1>🎯 VCP Scanner - Análisis Completo del Mercado</h1>
    
    <div class="summary">
        <h2>📊 Resumen del Escaneo</h2>
        <p>Total de patrones VCP detectados: <strong>{len(vcp_candidates)}</strong></p>
        <p>Con actividad insider: <strong>{len(insider_ready + insider_watch)}</strong></p>
        <p>Listos para comprar: <strong>{len(insider_ready + market_ready)}</strong></p>
        <p>En observación: <strong>{len(insider_watch + market_watch)}</strong></p>
    </div>
"""
        
        # Sección 1: Insider + VCP + Listo
        if insider_ready:
            html += self._generate_category_section(
                "🏆 MÁXIMA PRIORIDAD: Insider + VCP + Listo",
                insider_ready, 
                "Estas acciones tienen la combinación perfecta: actividad insider + patrón VCP completo",
                is_ready=True, 
                has_insider=True
            )
        
        # Sección 2: Insider + VCP en formación
        if insider_watch:
            html += self._generate_category_section(
                "🔍 VIGILAR: Insider + VCP en Formación",
                insider_watch[:20],  # Top 20
                "Acciones con actividad insider desarrollando patrón VCP",
                is_ready=False, 
                has_insider=True
            )
        
        # Sección 3: Solo VCP Listo
        if market_ready:
            html += self._generate_category_section(
                "✅ OPORTUNIDADES: VCP Completo sin Insider",
                market_ready[:20],  # Top 20
                "Patrones VCP listos para ruptura (sin actividad insider reciente)",
                is_ready=True, 
                has_insider=False
            )
        
        html += """
</body>
</html>
"""
        
        with open(output_file, 'w') as f:
            f.write(html)
        
        return output_file
    
    def _generate_category_section(self, title, candidates, description, is_ready, has_insider):
        """Genera una sección de categoría para el HTML"""
        if not candidates:
            return ""
        
        html = f"""
    <div class="category">
        <h2>{title}</h2>
        <p>{description}</p>
        <div class="ticker-grid">
"""
        
        for vcp in candidates:
            card_class = "ticker-card"
            if is_ready:
                card_class += " ready"
            if has_insider:
                card_class += " insider"
            
            badge = '<span class="ready-badge">COMPRAR</span>' if is_ready else '<span class="watch-badge">VIGILAR</span>'
            
            html += f"""
            <div class="{card_class}">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span class="ticker">{vcp['ticker']}</span>
                    {badge}
                </div>
                <div class="stat">Precio: <span class="price">${vcp['current_price']:.2f}</span></div>
                <div class="stat">Contracciones: {vcp['num_contractions']}</div>
                <div class="stat">Última: {vcp['last_contraction']:.1f}%</div>
                <div class="stat">Fuerza: {vcp['pattern_strength']:.0f}%</div>
                <div class="stat">Cap. Mercado: ${vcp.get('market_cap', 0)/1e9:.1f}B</div>
            </div>
"""
        
        html += """
        </div>
    </div>
"""
        return html


# Función principal para ejecutar el scanner
def run_enhanced_vcp_scanner(insider_tickers=None):
    """Ejecuta el scanner VCP mejorado"""
    scanner = VCPScannerEnhanced()
    
    # Escanear todo el mercado
    candidates = scanner.scan_market_for_vcp(insider_tickers)
    
    # Generar reporte
    if candidates:
        report_file = scanner.generate_enhanced_vcp_report(candidates)
        print(f"\n📄 Reporte generado: {report_file}")
        print(f"🎯 Top 5 oportunidades:")
        for i, vcp in enumerate(candidates[:5]):
            status = "COMPRAR" if vcp['ready_to_buy'] else "VIGILAR"
            insider = "✓ Insider" if vcp['has_insider_activity'] else ""
            print(f"{i+1}. {vcp['ticker']} - {status} - Fuerza: {vcp['pattern_strength']:.0f}% {insider}")
    else:
        print("❌ No se encontraron patrones VCP")


if __name__ == "__main__":
    # Ejecutar scanner
    run_enhanced_vcp_scanner()