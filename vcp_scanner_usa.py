#!/usr/bin/env python3
"""
VCP Scanner FINAL - Sin errores, completamente funcional
Versión corregida que elimina todos los bugs
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

warnings.filterwarnings('ignore')

class VCPScannerFinal:
    def __init__(self):
        self.min_price = 10.0
        self.min_volume = 100_000
        self.min_market_cap = 500_000_000
        self.max_workers = 8
        
        # Contadores
        self.data_success = 0
        self.vcp_found = 0
        self.filtered_count = 0

    def get_stock_data_robust(self, ticker):
        """Obtener datos de forma robusta"""
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period='4mo', timeout=15)
            
            if len(df) < 50:
                return None, {}
            
            try:
                info = stock.info
                market_cap = info.get('marketCap', 0)
                sector = info.get('sector', 'Unknown')
                industry = info.get('industry', 'Unknown')
            except:
                market_cap = 0
                sector = 'Unknown'
                industry = 'Unknown'
            
            metadata = {
                'market_cap': market_cap,
                'sector': sector,
                'industry': industry,
                'source': 'yfinance'
            }
            
            self.data_success += 1
            return df, metadata
            
        except Exception as e:
            return None, {}

    def detect_vcp_strict(self, ticker, df):
        """Detección VCP con criterios estrictos"""
        try:
            if len(df) < 60:
                return None
            
            recent_df = df.iloc[-80:].copy()
            
            # Encontrar pivots
            window = 7
            recent_df['pivot_high'] = recent_df['High'].rolling(window=window, center=True).max() == recent_df['High']
            recent_df['pivot_low'] = recent_df['Low'].rolling(window=window, center=True).min() == recent_df['Low']
            
            pivot_highs = recent_df[recent_df['pivot_high']]['High'].values
            pivot_lows = recent_df[recent_df['pivot_low']]['Low'].values
            
            if len(pivot_highs) < 3:
                return None
            
            # Calcular contracciones
            contractions = []
            for i in range(1, len(pivot_highs)):
                high_1 = pivot_highs[i-1]
                high_2 = pivot_highs[i]
                
                mask = (recent_df.index >= recent_df[recent_df['High'] == high_1].index[0]) & \
                       (recent_df.index <= recent_df[recent_df['High'] == high_2].index[0])
                low_between = recent_df[mask]['Low'].min()
                
                if pd.notna(low_between):
                    contraction = ((high_1 - low_between) / high_1) * 100
                    if 8 <= contraction <= 40:
                        contractions.append(contraction)
            
            if len(contractions) < 2:
                return None
            
            # Verificar patrón decreciente
            decreasing_contractions = 0
            strictly_decreasing = True
            
            for i in range(1, len(contractions)):
                if contractions[i] <= contractions[i-1] * 0.95:
                    decreasing_contractions += 1
                else:
                    strictly_decreasing = False
            
            decreasing_ratio = decreasing_contractions / (len(contractions) - 1) if len(contractions) > 1 else 0
            if decreasing_ratio < 0.7:
                return None
            
            # Análisis de volumen
            vol_periods = [
                df['Volume'].iloc[-10:].mean(),
                df['Volume'].iloc[-20:-10].mean(),
                df['Volume'].iloc[-40:-20].mean(),
                df['Volume'].iloc[-60:-40].mean()
            ]
            
            volume_trend_valid = (
                vol_periods[0] < vol_periods[1] * 1.05 and
                vol_periods[1] < vol_periods[2] * 1.05 and
                vol_periods[2] < vol_periods[3] * 1.10
            )
            
            if not volume_trend_valid:
                return None
            
            # Análisis de precio
            current_price = df['Close'].iloc[-1]
            recent_high = df['High'].iloc[-40:].max()
            overall_high = df['High'].max()
            
            distance_from_recent_high = ((recent_high - current_price) / recent_high) * 100
            distance_from_overall_high = ((overall_high - current_price) / overall_high) * 100
            
            near_resistance = distance_from_recent_high <= 8
            if not near_resistance:
                return None
            
            # Tendencia alcista
            ma_5 = df['Close'].iloc[-5:].mean()
            ma_10 = df['Close'].iloc[-10:].mean()
            ma_20 = df['Close'].iloc[-20:].mean()
            ma_50 = df['Close'].iloc[-50:].mean()
            
            strict_uptrend = (ma_5 > ma_10 * 1.01 and 
                            ma_10 > ma_20 * 1.01 and 
                            ma_20 > ma_50 * 1.01)
            
            if not strict_uptrend:
                return None
            
            # Calcular score
            base_score = 100 - contractions[-1]
            score_bonuses = 0
            
            if strictly_decreasing:
                score_bonuses += 20
            elif decreasing_ratio >= 0.8:
                score_bonuses += 10
            
            if len(contractions) >= 4:
                score_bonuses += 15
            elif len(contractions) >= 3:
                score_bonuses += 10
            
            if contractions[-1] <= 12:
                score_bonuses += 10
            
            if distance_from_recent_high <= 3:
                score_bonuses += 10
            
            score_penalties = 0
            
            if contractions[-1] > 25:
                score_penalties += 15
            
            if distance_from_overall_high > 15:
                score_penalties += 10
            
            final_score = max(0, min(100, base_score + score_bonuses - score_penalties))
            
            ready_to_buy = (
                final_score >= 75 and
                distance_from_recent_high <= 5 and
                strictly_decreasing and
                len(contractions) >= 3 and
                contractions[-1] <= 15 and
                current_price >= 10.0
            )
            
            if final_score < 60:
                return None
            
            return {
                'ticker': ticker,
                'current_price': current_price,
                'recent_high': recent_high,
                'overall_high': overall_high,
                'contractions': contractions,
                'num_contractions': len(contractions),
                'last_contraction': contractions[-1],
                'decreasing_ratio': decreasing_ratio,
                'strictly_decreasing': strictly_decreasing,
                'distance_from_recent_high': distance_from_recent_high,
                'distance_from_overall_high': distance_from_overall_high,
                'volume_trend_valid': volume_trend_valid,
                'near_resistance': near_resistance,
                'strict_uptrend': strict_uptrend,
                'pattern_strength': final_score,
                'ready_to_buy': ready_to_buy
            }
            
        except Exception as e:
            return None

    def process_ticker(self, ticker):
        """Procesar un ticker individual"""
        df, metadata = self.get_stock_data_robust(ticker)
        
        if df is None:
            return None
        
        current_price = df['Close'].iloc[-1]
        avg_volume = df['Volume'].iloc[-30:].mean()
        market_cap = metadata.get('market_cap', 0)
        
        if (current_price < self.min_price or 
            avg_volume < self.min_volume or 
            (market_cap > 0 and market_cap < self.min_market_cap)):
            self.filtered_count += 1
            return None
        
        result = self.detect_vcp_strict(ticker, df)
        
        if result:
            result.update(metadata)
            result['avg_volume'] = int(avg_volume)
            self.vcp_found += 1
            return result
        
        return None

    def scan_tickers_parallel(self, tickers):
        """Escanear tickers en paralelo"""
        print(f"\n🚀 ESCANEANDO {len(tickers)} TICKERS (CRITERIOS ESTRICTOS)")
        print("=" * 70)
        
        candidates = []
        processed = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_ticker = {executor.submit(self.process_ticker, ticker): ticker for ticker in tickers}
            
            for future in as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                processed += 1
                
                try:
                    result = future.result()
                    if result:
                        candidates.append(result)
                        status = "🟢 COMPRAR" if result['ready_to_buy'] else "🟡 VIGILAR"
                        print(f"[{processed:3d}/{len(tickers)}] ✅ {ticker}: Score {result['pattern_strength']:.1f}% | {status}")
                    else:
                        print(f"[{processed:3d}/{len(tickers)}] ⚪ {ticker}: No cumple criterios VCP estrictos")
                        
                except Exception as e:
                    print(f"[{processed:3d}/{len(tickers)}] ❌ {ticker}: Error")
                
                if processed % 25 == 0:
                    print(f"    📊 Progreso: {processed}/{len(tickers)} | VCP encontrados: {len(candidates)}")
        
        return candidates

    def print_results(self, candidates, total_tickers):
        """Mostrar resultados"""
        print(f"\n" + "="*80)
        print("📊 RESULTADOS VCP - CRITERIOS ESTRICTOS")
        print(f"Total tickers procesados: {total_tickers}")
        print(f"Datos obtenidos: {self.data_success}")
        print(f"Filtrados por precio/volumen/cap: {self.filtered_count}")
        print(f"🎯 CANDIDATOS VCP (ALTA CALIDAD): {len(candidates)}")
        
        if self.data_success > 0:
            vcp_rate = (len(candidates) / self.data_success) * 100
            print(f"📈 Tasa de VCP de calidad: {vcp_rate:.1f}% (objetivo: 5-15%)")
            
            if vcp_rate > 20:
                print("⚠️ Tasa muy alta - considerando hacer criterios aún más estrictos")
            elif vcp_rate < 3:
                print("⚠️ Tasa muy baja - considerando relajar ligeramente los criterios")
            else:
                print("✅ Tasa de detección VCP en rango óptimo")
        
        if not candidates:
            print("\n✅ RESULTADO NORMAL: Pocos/ningún VCP en mercado actual")
            print("💡 Los patrones VCP verdaderos son raros y valiosos")
            return
        
        candidates.sort(key=lambda x: x['pattern_strength'], reverse=True)
        
        buy_candidates = [c for c in candidates if c['ready_to_buy']]
        watch_candidates = [c for c in candidates if not c['ready_to_buy']]
        
        print(f"\n🟢 ALTA PROBABILIDAD DE COMPRA: {len(buy_candidates)}")
        print(f"🟡 VIGILAR DE CERCA: {len(watch_candidates)}")
        
        print(f"\n🏆 CANDIDATOS VCP DE ALTA CALIDAD:")
        print("-" * 130)
        print(f"{'#':<3} {'Ticker':<6} {'Precio':<8} {'Score':<6} {'Contracciones':<12} {'Última':<7} {'Del Max':<8} {'Patrón':<8} {'Sector':<12} {'Estado':<8}")
        print("-" * 130)
        
        for i, candidate in enumerate(candidates, 1):
            status = "COMPRAR" if candidate['ready_to_buy'] else "VIGILAR"
            sector = candidate.get('sector', 'Unknown')[:11]
            pattern_quality = "PERFECTO" if candidate['strictly_decreasing'] else "BUENO"
            
            print(f"{i:<3} {candidate['ticker']:<6} "
                  f"${candidate['current_price']:<7.2f} "
                  f"{candidate['pattern_strength']:<5.1f}% "
                  f"{candidate['num_contractions']:<11d} "
                  f"{candidate['last_contraction']:<6.1f}% "
                  f"{candidate['distance_from_recent_high']:<7.1f}% "
                  f"{pattern_quality:<8} "
                  f"{sector:<12} "
                  f"{status:<8}")
        
        if candidates:
            df_results = pd.DataFrame(candidates)
            filename = f"vcp_final_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
            df_results.to_csv(filename, index=False)
            print(f"\n📁 Resultados guardados en: {filename}")
            
            best = candidates[0]
            print(f"\n🎯 MEJOR CANDIDATO VCP: {best['ticker']}")
            print(f"   💰 Precio: ${best['current_price']:.2f}")
            print(f"   📊 Score: {best['pattern_strength']:.1f}%")
            print(f"   📈 Contracciones: {best['num_contractions']} ({best['last_contraction']:.1f}% la última)")
            print(f"   🎯 Distancia del máximo: {best['distance_from_recent_high']:.1f}%")
            print(f"   ✅ Patrón decreciente: {'Sí' if best['strictly_decreasing'] else 'No'}")
            print(f"   🏭 Sector: {best.get('sector', 'Unknown')}")

def get_sectors():
    """Lista de sectores y tickers"""
    tickers = {
        'Technology': [
            'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX', 'ADBE',
            'CRM', 'ORCL', 'INTC', 'AMD', 'AVGO', 'NOW', 'INTU', 'QCOM', 'TXN', 'MU',
            'AMAT', 'LRCX', 'KLAC', 'MRVL', 'ADI', 'SNPS', 'CDNS', 'FTNT', 'PANW', 'CRWD',
            'ZS', 'OKTA', 'DDOG', 'NET', 'SNOW', 'PLTR'
        ],
        'Industrial': [
            'CAT', 'BA', 'GE', 'MMM', 'HON', 'UPS', 'FDX', 'LMT', 'RTX', 'NOC',
            'DE', 'EMR', 'ETN', 'PH', 'ROK', 'ITW', 'CSX', 'NSC', 'UNP',
            'GD', 'LHX', 'TXT', 'IR', 'CARR', 'OTIS', 'PWR', 'HUBB', 'FAST', 'PCAR'
        ],
        'Energy': [
            'XOM', 'CVX', 'COP', 'EOG', 'SLB', 'HAL', 'MPC', 'VLO', 'PSX', 'PXD',
            'OXY', 'KMI', 'WMB', 'OKE', 'EPD', 'ET', 'MPLX', 'BKR', 'DVN', 'FANG'
        ],
        'Financial': [
            'JPM', 'BAC', 'GS', 'MS', 'WFC', 'C', 'USB', 'PNC', 'BLK', 'SCHW',
            'V', 'MA', 'AXP', 'COF', 'DFS', 'SYF', 'ALLY', 'BX', 'KKR', 'APO',
            'SPGI', 'MCO', 'ICE', 'CME', 'MSCI', 'TRV', 'AIG', 'PRU', 'MET', 'AFL'
        ],
        'Healthcare': [
            'JNJ', 'PFE', 'UNH', 'ABBV', 'BMY', 'MRK', 'GILD', 'AMGN', 'BIIB', 'REGN',
            'TMO', 'DHR', 'ABT', 'SYK', 'MDT', 'ISRG', 'VRTX', 'INCY', 'BMRN', 'SGEN'
        ],
        'Consumer': [
            'HD', 'NKE', 'SBUX', 'MCD', 'DIS', 'CMG', 'LULU', 'TGT', 'LOW',
            'TJX', 'ROST', 'ULTA', 'BBY', 'BKNG', 'MAR', 'HLT', 'MGM', 'WYNN', 'LVS'
        ],
        'Fintech': [
            'PYPL', 'SQ', 'SHOP', 'ROKU', 'SPOT', 'UBER', 'LYFT', 'ABNB', 'DASH', 'COIN',
            'HOOD', 'SOFI', 'UPST', 'AFRM', 'ETSY', 'EBAY', 'W', 'CHWY', 'PINS', 'SNAP'
        ]
    }
    
    all_tickers = []
    for sector_tickers in tickers.values():
        all_tickers.extend(sector_tickers)
    
    return sorted(list(set(all_tickers))), tickers

def run_scanner():
    """Función principal del scanner"""
    print("🎯 VCP SCANNER FINAL - SIN ERRORES")
    print("=" * 50)
    
    scanner = VCPScannerFinal()
    all_tickers, sector_tickers = get_sectors()
    
    print("⚙️ CONFIGURACIÓN:")
    print(f"   💰 Precio mínimo: ${scanner.min_price}")
    print(f"   📊 Volumen mínimo: {scanner.min_volume:,}")
    print(f"   🏭 Market cap mínimo: ${scanner.min_market_cap:,}")
    
    while True:
        print("\n" + "="*60)
        print("OPCIONES DE ESCANEO:")
        print("1. Test rápido (17 empresas)")
        print("2. Technology (36 empresas)")
        print("3. Industrial (30 empresas)")
        print("4. Energy (20 empresas)")
        print("5. Financial (30 empresas)")
        print("6. Healthcare (20 empresas)")
        print("7. Consumer (19 empresas)")
        print("8. Fintech (20 empresas)")
        print("9. Escaneo completo (200+ empresas)")
        print("10. Tickers personalizados")
        print("0. Volver al menú principal")
        print("-"*60)
        
        try:
            opcion = input("Selecciona opción: ").strip()
            
            if opcion == "1":
                top_tickers = [
                    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX',
                    'JPM', 'BAC', 'UNH', 'JNJ', 'HD', 'CAT', 'XOM', 'NEE', 'AMT'
                ]
                candidates = scanner.scan_tickers_parallel(top_tickers)
                scanner.print_results(candidates, len(top_tickers))
                
            elif opcion == "2":
                tickers = sector_tickers['Technology']
                candidates = scanner.scan_tickers_parallel(tickers)
                scanner.print_results(candidates, len(tickers))
                
            elif opcion == "3":
                tickers = sector_tickers['Industrial']
                candidates = scanner.scan_tickers_parallel(tickers)
                scanner.print_results(candidates, len(tickers))
                
            elif opcion == "4":
                tickers = sector_tickers['Energy']
                candidates = scanner.scan_tickers_parallel(tickers)
                scanner.print_results(candidates, len(tickers))
                
            elif opcion == "5":
                tickers = sector_tickers['Financial']
                candidates = scanner.scan_tickers_parallel(tickers)
                scanner.print_results(candidates, len(tickers))
                
            elif opcion == "6":
                tickers = sector_tickers['Healthcare']
                candidates = scanner.scan_tickers_parallel(tickers)
                scanner.print_results(candidates, len(tickers))
                
            elif opcion == "7":
                tickers = sector_tickers['Consumer']
                candidates = scanner.scan_tickers_parallel(tickers)
                scanner.print_results(candidates, len(tickers))
                
            elif opcion == "8":
                tickers = sector_tickers['Fintech']
                candidates = scanner.scan_tickers_parallel(tickers)
                scanner.print_results(candidates, len(tickers))
                
            elif opcion == "9":
                print(f"⚠️ Escaneo completo de {len(all_tickers)} empresas")
                confirmar = input("¿Continuar? (s/n): ").strip().lower()
                if confirmar == 's':
                    candidates = scanner.scan_tickers_parallel(all_tickers)
                    scanner.print_results(candidates, len(all_tickers))
                
            elif opcion == "10":
                custom_input = input("Introduce tickers separados por comas: ").strip()
                if custom_input:
                    custom_tickers = [t.strip().upper() for t in custom_input.split(',')]
                    candidates = scanner.scan_tickers_parallel(custom_tickers)
                    scanner.print_results(candidates, len(custom_tickers))
                
            elif opcion == "0":
                break
            else:
                print("❌ Opción no válida")
                continue
            
            # Preguntar si continuar (sin errores)
            if opcion in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']:
                seguir = input("\n¿Hacer otro escaneo? (s/n): ").strip().lower()
                if seguir != 's':
                    break
                    
        except KeyboardInterrupt:
            print("\n\n👋 Saliendo del scanner...")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Continuando...")

def show_education():
    """Mostrar educación sobre VCP"""
    print("\n📚 GUÍA VCP")
    print("=" * 40)
    print("VCP = Volatility Contraction Pattern")
    print()
    print("🎯 CARACTERÍSTICAS:")
    print("• Tendencia alcista de fondo")
    print("• 2-4 contracciones decrecientes")
    print("• Volumen seco en cada pullback")
    print("• Precio cerca del máximo")
    print("• Preparado para breakout")
    print()
    print("🚀 CÓMO OPERAR:")
    print("• Comprar en breakout del máximo")
    print("• Con aumento de volumen")
    print("• Stop debajo última contracción")
    print("• Objetivo: 20-50% ganancia")

def main_menu():
    """Menú principal sin errores"""
    while True:
        print("\n" + "="*50)
        print("🎯 VCP SCANNER FINAL v3.0")
        print("="*50)
        print("1. 🚀 Ejecutar Scanner VCP")
        print("2. 📚 Guía VCP")
        print("0. 🚪 Salir")
        print("-"*50)
        
        try:
            choice = input("Opción: ").strip()
            
            if choice == "1":
                run_scanner()
            elif choice == "2":
                show_education()
                input("\nPresiona Enter para continuar...")
            elif choice == "0":
                print("👋 ¡Gracias por usar VCP Scanner!")
                break
            else:
                print("❌ Opción no válida")
                
        except KeyboardInterrupt:
            print("\n\n👋 Saliendo...")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    try:
        main_menu()
    except Exception as e:
        print(f"\n❌ Error crítico: {e}")
    finally:
        print("\n🙏 Gracias por usar VCP Scanner Final")