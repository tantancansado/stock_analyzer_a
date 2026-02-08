#!/usr/bin/env python3
"""
SCAN ALL WHALES - Mass 13F Scraper
Escanea todos los whale investors y extrae sus holdings
"""
import time
from datetime import datetime
from pathlib import Path
from sec_13f_scraper import SEC13FScraper
from parse_13f_holdings import Holdings13FParser
from institutional_tracker import WHALE_INVESTORS

class MassWhaleScraper:
    """Scanner masivo de todos los whales"""

    def __init__(self):
        self.scraper = SEC13FScraper()
        self.parser = Holdings13FParser()
        self.results = []
        self.errors = []

    def scan_single_whale(self, cik, whale_info):
        """Escanea un whale individual"""
        print(f"\n{'='*80}")
        print(f"🐋 {whale_info['name']} (CIK: {cik})")
        print(f"   Tier: {whale_info['tier'].upper()}")
        print(f"{'='*80}")

        try:
            # Obtener filings
            filings_data = self.scraper.get_recent_filings(cik, count=1)

            if not filings_data or not filings_data['filings']:
                print(f"   ⚠️  No se encontraron filings")
                self.errors.append({
                    'cik': cik,
                    'whale_name': whale_info['name'],
                    'error': 'No filings found'
                })
                return None

            latest_filing = filings_data['filings'][0]
            print(f"   📅 Filing: {latest_filing['filing_date']}")

            # Parsear holdings
            holdings = self.parser.parse_filing(latest_filing['url'])

            if not holdings:
                print(f"   ⚠️  No se pudieron parsear holdings")
                self.errors.append({
                    'cik': cik,
                    'whale_name': whale_info['name'],
                    'error': 'Parsing failed'
                })
                return None

            # Guardar
            output_path = self.parser.save_holdings(
                cik=cik,
                whale_name=whale_info['name'],
                holdings=holdings,
                filing_date=latest_filing['filing_date']
            )

            result = {
                'cik': cik,
                'whale_name': whale_info['name'],
                'tier': whale_info['tier'],
                'filing_date': latest_filing['filing_date'],
                'holdings_count': len(holdings),
                'tickers_with_symbols': len([h for h in holdings if h.get('ticker') and h['ticker'] != 'N/A']),
                'output_path': str(output_path),
                'status': 'success'
            }

            self.results.append(result)

            print(f"   ✅ SUCCESS")
            print(f"   📊 Holdings: {len(holdings)}")
            print(f"   🎯 Con tickers: {result['tickers_with_symbols']}")

            return result

        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            self.errors.append({
                'cik': cik,
                'whale_name': whale_info['name'],
                'error': str(e)
            })
            return None

    def scan_all_whales(self, limit=None):
        """
        Escanea todos los whales

        Args:
            limit: Limitar número de whales (para testing)
        """
        print("🐋🐋🐋 MASS WHALE SCAN INICIADO 🐋🐋🐋")
        print("=" * 80)
        print(f"⏰ Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 Whales a escanear: {limit if limit else len(WHALE_INVESTORS)}")
        print(f"⚠️  Tiempo estimado: {(limit if limit else len(WHALE_INVESTORS)) * 45} segundos")
        print("=" * 80)

        whales_list = list(WHALE_INVESTORS.items())

        if limit:
            whales_list = whales_list[:limit]

        total = len(whales_list)

        for i, (cik, info) in enumerate(whales_list, 1):
            print(f"\n\n🔄 PROGRESO: {i}/{total} ({i/total*100:.0f}%)")

            self.scan_single_whale(cik, info)

            # Rate limiting (SEC requiere max 10 req/segundo)
            # Con parseo incluido, ~30-45 segundos por whale
            if i < total:
                print(f"\n⏳ Esperando antes del siguiente whale...")
                time.sleep(2)  # Espera adicional entre whales

        # Resumen final
        self.print_summary()

    def print_summary(self):
        """Imprime resumen del scan"""
        print("\n\n" + "=" * 80)
        print("📊 RESUMEN DEL SCAN")
        print("=" * 80)

        print(f"\n✅ Exitosos: {len(self.results)}")
        print(f"❌ Errores: {len(self.errors)}")

        if self.results:
            print(f"\n🏆 TOP WHALES POR HOLDINGS:")
            print("-" * 80)

            sorted_results = sorted(self.results, key=lambda x: x['holdings_count'], reverse=True)

            for i, result in enumerate(sorted_results[:10], 1):
                print(f"{i:2}. {result['whale_name']:45} {result['holdings_count']:4} holdings "
                      f"({result['tickers_with_symbols']:3} con ticker)")

        if self.errors:
            print(f"\n⚠️  ERRORES:")
            for error in self.errors:
                print(f"   • {error['whale_name']}: {error['error']}")

        # Stats por tier
        if self.results:
            tier_stats = {}
            for result in self.results:
                tier = result['tier']
                if tier not in tier_stats:
                    tier_stats[tier] = {'count': 0, 'total_holdings': 0}
                tier_stats[tier]['count'] += 1
                tier_stats[tier]['total_holdings'] += result['holdings_count']

            print(f"\n📈 ESTADÍSTICAS POR TIER:")
            print("-" * 80)
            for tier, stats in sorted(tier_stats.items()):
                avg = stats['total_holdings'] / stats['count']
                print(f"{tier.upper():10} - {stats['count']:2} whales | "
                      f"{stats['total_holdings']:5} holdings | "
                      f"Avg: {avg:.0f}")

        print(f"\n⏰ Completado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        # Siguiente paso
        print(f"\n🎯 SIGUIENTE PASO:")
        print(f"   python3 build_institutional_index.py")
        print(f"\n   Esto construirá el índice completo y calculará scores institucionales")


def main():
    """Main execution"""
    print("🐋 WHALE SCANNER - Mass 13F Extraction")
    print("=" * 80)

    scanner = MassWhaleScraper()

    print("\nOpciones:")
    print("1. Scan completo (20 whales) - ~15-20 minutos")
    print("2. Test rápido (5 whales) - ~3-4 minutos")
    print("3. Test mini (2 whales) - ~1 minuto")

    choice = input("\nSelecciona (1-3): ").strip()

    if choice == '1':
        scanner.scan_all_whales()
    elif choice == '2':
        scanner.scan_all_whales(limit=5)
    else:
        scanner.scan_all_whales(limit=2)

    print("\n🎉 SCAN COMPLETADO!")

    # Auto-run index builder si hay datos
    if scanner.results:
        print("\n" + "=" * 80)
        print("🤔 ¿Quieres construir el índice ahora? (recomendado)")
        build_now = input("Construir índice (y/n): ").strip().lower()

        if build_now == 'y':
            print("\n🏗️  Construyendo índice...")
            from build_institutional_index import InstitutionalIndexBuilder
            builder = InstitutionalIndexBuilder()
            builder.build_and_save_index()


if __name__ == "__main__":
    main()
