#!/usr/bin/env python3
"""
Script para extraer datos del Fear and Greed Index de CNN
"""

import requests
import json
from datetime import datetime
from typing import Dict, Optional
import argparse


class FearAndGreedScraper:
    """Scraper para el índice Fear and Greed de CNN"""
    
    BASE_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Origin': 'https://edition.cnn.com',
            'Referer': 'https://edition.cnn.com/'
        })
    
    def get_current_data(self) -> Optional[Dict]:
        """
        Obtiene los datos actuales del índice Fear and Greed
        
        Returns:
            Dict con los datos del índice o None si hay error
        """
        date_str = datetime.now().strftime('%Y-%m-%d')
        url = f"{self.BASE_URL}/{date_str}"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error al obtener datos: {e}")
            return None
    
    def get_data_by_date(self, date: str) -> Optional[Dict]:
        """
        Obtiene los datos del índice para una fecha específica
        
        Args:
            date: Fecha en formato YYYY-MM-DD
            
        Returns:
            Dict con los datos del índice o None si hay error
        """
        url = f"{self.BASE_URL}/{date}"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error al obtener datos para {date}: {e}")
            return None
    
    def parse_fear_and_greed(self, data: Dict) -> Dict:
        """
        Extrae y formatea los datos principales del Fear and Greed Index
        
        Args:
            data: Datos JSON completos de la API
            
        Returns:
            Dict con los datos formateados
        """
        if not data or 'fear_and_greed' not in data:
            return {}
        
        fg_data = data['fear_and_greed']
        
        return {
            'score': fg_data.get('score'),
            'rating': fg_data.get('rating'),
            'timestamp': fg_data.get('timestamp'),
            'previous_close': fg_data.get('previous_close'),
            'previous_1_week': fg_data.get('previous_1_week'),
            'previous_1_month': fg_data.get('previous_1_month'),
            'previous_1_year': fg_data.get('previous_1_year')
        }
    
    def get_all_indicators(self, data: Dict) -> Dict:
        """
        Extrae todos los indicadores disponibles
        
        Args:
            data: Datos JSON completos de la API
            
        Returns:
            Dict con todos los indicadores
        """
        if not data:
            return {}
        
        indicators = {}
        
        # Lista de indicadores disponibles
        indicator_keys = [
            'fear_and_greed',
            'market_momentum_sp500',
            'market_momentum_sp125',
            'stock_price_strength',
            'stock_price_breadth',
            'put_call_options',
            'market_volatility_vix',
            'market_volatility_vix_50',
            'junk_bond_demand',
            'safe_haven_demand'
        ]
        
        for key in indicator_keys:
            if key in data:
                indicators[key] = {
                    'score': data[key].get('score'),
                    'rating': data[key].get('rating')
                }
        
        return indicators
    
    def save_to_json(self, data: Dict, filename: str = 'fear_and_greed_data.json'):
        """
        Guarda los datos en un archivo JSON
        
        Args:
            data: Datos a guardar
            filename: Nombre del archivo
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"Datos guardados en {filename}")
        except Exception as e:
            print(f"Error al guardar archivo: {e}")
    
    def print_summary(self, data: Dict):
        """
        Imprime un resumen de los datos en consola
        
        Args:
            data: Datos a mostrar
        """
        if not data:
            print("No hay datos para mostrar")
            return
        
        fg = self.parse_fear_and_greed(data)
        
        if fg:
            print("\n" + "="*50)
            print("FEAR AND GREED INDEX - CNN")
            print("="*50)
            print(f"Score:          {fg['score']:.2f}")
            print(f"Rating:         {fg['rating'].upper()}")
            print(f"Timestamp:      {fg['timestamp']}")
            print(f"\nComparación:")
            print(f"  Cierre prev:  {fg['previous_close']:.2f}")
            print(f"  Hace 1 sem:   {fg['previous_1_week']:.2f}")
            print(f"  Hace 1 mes:   {fg['previous_1_month']:.2f}")
            print(f"  Hace 1 año:   {fg['previous_1_year']:.2f}")
            print("="*50 + "\n")


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description='Extrae datos del Fear and Greed Index de CNN'
    )
    parser.add_argument(
        '-d', '--date',
        help='Fecha específica en formato YYYY-MM-DD',
        type=str
    )
    parser.add_argument(
        '-s', '--save',
        help='Guardar datos en archivo JSON',
        action='store_true'
    )
    parser.add_argument(
        '-f', '--filename',
        help='Nombre del archivo de salida (default: fear_and_greed_data.json)',
        type=str,
        default='fear_and_greed_data.json'
    )
    parser.add_argument(
        '-a', '--all-indicators',
        help='Mostrar todos los indicadores',
        action='store_true'
    )
    
    args = parser.parse_args()
    
    # Crear scraper
    scraper = FearAndGreedScraper()
    
    # Obtener datos
    if args.date:
        data = scraper.get_data_by_date(args.date)
    else:
        data = scraper.get_current_data()
    
    if not data:
        print("No se pudieron obtener los datos")
        return
    
    # Mostrar resumen
    scraper.print_summary(data)
    
    # Mostrar todos los indicadores si se solicita
    if args.all_indicators:
        indicators = scraper.get_all_indicators(data)
        print("\nTodos los indicadores:")
        print(json.dumps(indicators, indent=2))
    
    # Guardar en archivo si se solicita
    if args.save:
        scraper.save_to_json(data, args.filename)


if __name__ == "__main__":
    main()