#!/usr/bin/env python3
"""
TipRanks Buyback Scraper - Versión Directa API
Accede directamente al endpoint JSON que encontraste
"""

import requests
import json
import csv
from datetime import datetime
import time
import random

class TipRanksDirectScraper:
    """Scraper directo usando el endpoint JSON de TipRanks"""
    
    def __init__(self):
        self.base_url = "https://tr-cdn.tipranks.com/calendars/prod/calendars/stock-buybacks/payload.json"
        self.session = requests.Session()
        
        # Headers que viste en el navegador
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Referer': 'https://www.tipranks.com/',
            'Sec-Ch-Ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"'
        }
    
    def get_buybacks(self):
        """Obtiene los buybacks directamente de la API"""
        try:
            print("🎯 Accediendo a TipRanks API...")
            
            # Generar timestamp similar al que viste
            timestamp = int(time.time() * 1000)
            
            params = {
                'ver': timestamp
            }
            
            response = self.session.get(
                self.base_url,
                params=params,
                headers=self.headers,
                timeout=30
            )
            
            print(f"📡 Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                return self.parse_buybacks(data)
            else:
                print(f"❌ Error: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Error obteniendo datos: {e}")
            return []
    
    def parse_buybacks(self, data):
        """Parsea los datos JSON de buybacks"""
        buybacks = []
        
        try:
            # Navegar por la estructura JSON
            calendar_data = data.get('StockBuybacksCalendar', {})
            buybacks_data = calendar_data.get('data', {}).get('buybacks', {})
            buybacks_list = buybacks_data.get('list', [])
            
            print(f"📊 Encontrados {len(buybacks_list)} buybacks")
            
            for item in buybacks_list:
                # Extraer datos de cada buyback
                ticker = item.get('ticker', '')
                company_name = item.get('name', '')
                
                # Obtener monto del buyback
                buyback_info = item.get('buybacks', {})
                amount = buyback_info.get('amount', 0)
                
                # Otros datos útiles
                market_cap = item.get('marketCap', 0)
                
                # Obtener fecha de earnings (como proxy de fecha de anuncio)
                earning_info = item.get('earning', {})
                reported_date = earning_info.get('reported', '')
                
                if reported_date:
                    try:
                        # Convertir fecha ISO a formato simple
                        date_obj = datetime.fromisoformat(reported_date.replace('Z', '+00:00'))
                        announcement_date = date_obj.strftime('%Y-%m-%d')
                    except:
                        announcement_date = datetime.now().strftime('%Y-%m-%d')
                else:
                    announcement_date = datetime.now().strftime('%Y-%m-%d')
                
                # Clasificar por tamaño
                if amount >= 1_000_000_000:
                    size_category = 'Large'
                    impact_level = 'HIGH'
                elif amount >= 100_000_000:
                    size_category = 'Medium'
                    impact_level = 'MEDIUM'
                else:
                    size_category = 'Small'
                    impact_level = 'LOW'
                
                buyback = {
                    'ticker': ticker,
                    'company_name': company_name,
                    'amount_authorized': amount,
                    'amount_formatted': self.format_amount(amount),
                    'market_cap': market_cap,
                    'market_cap_formatted': self.format_amount(market_cap),
                    'announcement_date': announcement_date,
                    'size_category': size_category,
                    'impact_level': impact_level,
                    'source': 'TipRanks_API',
                    'scraped_at': datetime.now().isoformat(),
                    'url': 'https://www.tipranks.com/calendars/stock-buybacks'
                }
                
                if ticker:  # Solo añadir si tiene ticker válido
                    buybacks.append(buyback)
            
            # Ordenar por monto (mayor a menor)
            buybacks.sort(key=lambda x: x['amount_authorized'], reverse=True)
            
            return buybacks
            
        except Exception as e:
            print(f"❌ Error parseando datos: {e}")
            return []
    
    def format_amount(self, amount):
        """Formatea cantidades en billones/millones"""
        if amount >= 1_000_000_000:
            return f"${amount/1_000_000_000:.2f}B"
        elif amount >= 1_000_000:
            return f"${amount/1_000_000:.1f}M"
        else:
            return f"${amount:,.0f}"
    
    def save_to_csv(self, buybacks, filename='tipranks_buybacks.csv'):
        """Guarda los buybacks en CSV"""
        if not buybacks:
            print("⚠️  No hay datos para guardar")
            return
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                fieldnames = buybacks[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(buybacks)
            
            print(f"💾 Guardado en: {filename}")
            
        except Exception as e:
            print(f"❌ Error guardando: {e}")
    
    def show_summary(self, buybacks):
        """Muestra resumen de los buybacks"""
        if not buybacks:
            print("❌ No hay buybacks para mostrar")
            return
        
        print(f"\n📊 RESUMEN DE BUYBACKS")
        print("=" * 60)
        print(f"📈 Total encontrados: {len(buybacks)}")
        
        # Calcular estadísticas
        amounts = [b['amount_authorized'] for b in buybacks if b['amount_authorized'] > 0]
        if amounts:
            total_amount = sum(amounts)
            avg_amount = total_amount / len(amounts)
            
            print(f"💰 Valor total: ${total_amount/1_000_000_000:.1f}B")
            print(f"📊 Valor promedio: ${avg_amount/1_000_000_000:.2f}B")
        
        # Top 10
        print(f"\n🏆 TOP 10 BUYBACKS:")
        print("-" * 60)
        
        for i, buyback in enumerate(buybacks[:10], 1):
            ticker = buyback['ticker']
            company = buyback['company_name'][:30]
            amount_fmt = buyback['amount_formatted']
            impact = buyback['impact_level']
            
            print(f"{i:2d}. {ticker:<6} | {company:<30} | {amount_fmt:<10} | {impact}")
        
        print("=" * 60)

def main():
    """Función principal"""
    scraper = TipRanksDirectScraper()
    
    print("🚀 TipRanks Direct Buyback Scraper")
    print("=" * 50)
    
    # Obtener datos
    buybacks = scraper.get_buybacks()
    
    if buybacks:
        # Mostrar resumen
        scraper.show_summary(buybacks)
        
        # Guardar en CSV
        scraper.save_to_csv(buybacks)
        
        print(f"\n✅ Proceso completado exitosamente!")
        print(f"📁 Datos disponibles en: tipranks_buybacks.csv")
    else:
        print("❌ No se pudieron obtener datos")

if __name__ == "__main__":
    main()