#!/usr/bin/env python3
"""
MASTER AUTOMATION SCRIPT
Ejecuta todos los scanners del sistema periódicamente
"""
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import json

class MasterScanner:
    """Orquestador de todos los scanners"""

    def __init__(self):
        self.results = {}
        self.errors = []
        self.start_time = datetime.now()

    def log(self, message):
        """Log con timestamp"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] {message}")

    def run_command(self, name, command, timeout=600):
        """Ejecuta un comando y captura resultado"""
        self.log(f"🚀 Iniciando: {name}")

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            success = result.returncode == 0

            self.results[name] = {
                'success': success,
                'returncode': result.returncode,
                'output_lines': len(result.stdout.split('\n')),
                'duration': '0s'  # Placeholder
            }

            if success:
                self.log(f"   ✅ {name} completado")
            else:
                self.log(f"   ⚠️  {name} terminó con errores")
                self.errors.append(name)

            return success

        except subprocess.TimeoutExpired:
            self.log(f"   ❌ {name} timeout")
            self.errors.append(name)
            return False
        except Exception as e:
            self.log(f"   ❌ {name} error: {e}")
            self.errors.append(name)
            return False

    def run_all_scanners(self):
        """Ejecuta todos los scanners en orden"""
        self.log("="*80)
        self.log("🎯 MASTER SCANNER - Iniciando escaneo completo")
        self.log("="*80)

        # 1. VCP Scanner
        self.log("\n📊 FASE 1: VCP SCANNER")
        self.run_command(
            "VCP Scanner",
            "python3 vcp_scanner_usa.py --sp500 --parallel",
            timeout=1800  # ~15-20 min parallel scan of S&P 500
        )

        # 2. Insider Analysis (ya se ejecuta diario con sistema_principal.py)
        self.log("\n🏛️ FASE 2: INSIDER ANALYSIS")
        # Los insiders ya se actualizan automáticamente
        self.log("   ℹ️  Insiders se actualizan automáticamente")

        # 3. Recurring Insiders
        self.log("\n🔁 FASE 3: RECURRING INSIDERS")
        self.run_command(
            "Recurring Insiders",
            "python3 analyze_recurring_insiders.py",
            timeout=300
        )

        # 4. Sectorial Analysis (DJ)
        self.log("\n📊 FASE 4: SECTORIAL ANALYSIS")
        self.log("   ℹ️  DJ Sectorial se actualiza automáticamente")

        # 5. Institutional Tracker
        self.log("\n🏛️ FASE 5: INSTITUTIONAL TRACKER")
        # Solo escanear whales una vez por semana (13F es trimestral)
        # Aquí solo reconstruimos el índice
        self.run_command(
            "Build Institutional Index",
            "python3 build_institutional_index.py",
            timeout=300
        )

        # 6. Super Analyzer 4D
        self.log("\n🎯 FASE 6: SUPER ANALYZER 4D")
        self.run_command(
            "Super Analyzer 4D",
            "python3 run_super_analyzer_4d.py",
            timeout=900  # Increased: downloads data for ~500 stocks
        )

        # 7. Super Opportunities (3D - legacy)
        self.log("\n⭐ FASE 7: SUPER OPPORTUNITIES")
        self.run_command(
            "Super Analyzer",
            "python3 super_analyzer.py",
            timeout=300
        )

        # 8. Earnings Calendar Enrichment
        self.log("\n📅 FASE 8: EARNINGS CALENDAR")
        self.run_command(
            "Earnings Calendar",
            "python3 -c \"from earnings_calendar import EarningsCalendar; EarningsCalendar().enrich_opportunities_csv('docs/super_opportunities_5d_complete.csv')\"",
            timeout=600
        )

        # 9. Data Quality Validation
        self.log("\n✅ FASE 9: DATA QUALITY VALIDATION")
        self.run_data_quality_checks()

        # 10. Backtest Snapshot Creation
        self.log("\n📸 FASE 10: BACKTEST SNAPSHOT")
        self.create_backtest_snapshot()

        # 11. Telegram Alerts (si están configuradas)
        self.log("\n📱 FASE 11: TELEGRAM ALERTS")
        self.send_telegram_alerts()

    def create_backtest_snapshot(self):
        """Crea snapshot diario de oportunidades para backtesting"""
        try:
            from backtest_system import BacktestSystem
            from pathlib import Path

            csv_path = Path('docs/super_opportunities_5d_complete_with_earnings.csv')
            if not csv_path.exists():
                csv_path = Path('docs/super_opportunities_5d_complete.csv')

            if not csv_path.exists():
                self.log("   ℹ️  No hay datos 5D - saltando snapshot")
                return

            backtest = BacktestSystem()
            snapshot = backtest.create_snapshot(str(csv_path))

            if snapshot is not None:
                self.log(f"   ✅ Snapshot creado con {len(snapshot)} oportunidades")
            else:
                self.log("   ⚠️  Error creando snapshot")

        except ImportError:
            self.log("   ⚠️  backtest_system.py no encontrado")
        except Exception as e:
            self.log(f"   ⚠️  Error en snapshot: {e}")

    def send_telegram_alerts(self):
        """Envía alertas de Telegram si hay LEGENDARY opportunities"""
        try:
            from telegram_legendary_alerts import TelegramLegendaryAlerts

            # Verificar si existe configuración
            config_path = Path('config/telegram_config.json')
            if not config_path.exists():
                self.log("   ℹ️  Telegram no configurado - saltando alertas")
                self.log("   💡 Ver TELEGRAM_SETUP.md para configurar")
                return

            # Intentar enviar alertas
            alerts = TelegramLegendaryAlerts()

            # Verificar si hay LEGENDARY opportunities
            csv_path = Path('docs/super_opportunities_5d_complete.csv')
            if not csv_path.exists():
                self.log("   ℹ️  No hay datos 4D para alertas")
                return

            import pandas as pd
            df = pd.read_csv(csv_path)
            legendary = df[df['super_score_4d'] >= 85]

            if legendary.empty:
                self.log("   ℹ️  No hay LEGENDARY opportunities - sin alertas")
                return

            self.log(f"   🌟 {len(legendary)} LEGENDARY opportunities detectadas!")
            self.log("   📤 Enviando alertas...")

            # Enviar alertas
            sent = 0
            for _, row in legendary.iterrows():
                opportunity = {
                    'ticker': row['ticker'],
                    'super_score_4d': row['super_score_4d'],
                    'tier': row.get('tier', '⭐⭐⭐⭐ LEGENDARY'),
                    'dimensions': {
                        'vcp': row.get('vcp_score', 0),
                        'insiders': row.get('insiders_score', 0),
                        'sector': row.get('sector_score', 0),
                        'institutional': row.get('institutional_score', 0)
                    },
                    'description': 'Confirmación cuádruple - Probabilidad histórica',
                    'institutional_details': {
                        'num_whales': row.get('num_whales', 0),
                        'top_whales': row.get('top_whales', '').split(', ') if row.get('top_whales') else []
                    }
                }

                message = alerts.format_legendary_alert(opportunity)
                if alerts.send_message(message):
                    sent += 1

            self.log(f"   ✅ {sent}/{len(legendary)} alertas enviadas")

        except ImportError:
            self.log("   ⚠️  telegram_legendary_alerts.py no encontrado")
        except ValueError as e:
            self.log(f"   ℹ️  Telegram no configurado: {e}")
        except Exception as e:
            self.log(f"   ⚠️  Error enviando alertas: {e}")

    def run_data_quality_checks(self):
        """Ejecuta validación de calidad de datos en el CSV 5D"""
        try:
            from validators.data_quality import DataQualityValidator
            from pathlib import Path

            # Buscar CSV 5D (con o sin earnings)
            csv_path = Path('docs/super_opportunities_5d_complete_with_earnings.csv')
            if not csv_path.exists():
                csv_path = Path('docs/super_opportunities_5d_complete.csv')

            if not csv_path.exists():
                self.log("   ⚠️  CSV 5D no encontrado - saltando validación")
                return

            self.log(f"   📊 Validando: {csv_path}")

            # Ejecutar validación
            validator = DataQualityValidator(verbose=False)
            report = validator.validate_5d_pipeline(str(csv_path))

            # Guardar reporte
            validator.save_report(report, "data_quality_report.json")
            self.log(f"   💾 Reporte guardado: data_quality_report.json")

            # Mostrar resultados
            total_rows = report.get('total_rows', 0)
            completeness = report.get('completeness', {})
            comp_score = completeness.get('score', 0) if isinstance(completeness, dict) else 0

            if report['passed']:
                self.log(f"   ✅ VALIDACIÓN PASSED - Datos OK")
                self.log(f"      Tickers: {total_rows}")
                self.log(f"      Completeness: {comp_score:.1f}%")
            else:
                num_issues = len(report.get('issues', []))
                self.log(f"   ⚠️  VALIDACIÓN FAILED - {num_issues} problemas")
                self.log(f"      Tickers: {total_rows}")
                self.log(f"      Completeness: {comp_score:.1f}%")

                # Mostrar primeros 5 problemas
                issues = report.get('issues', [])
                if issues:
                    self.log(f"\n   Top 5 problemas:")
                    for i, issue in enumerate(issues[:5], 1):
                        self.log(f"      {i}. {issue}")

                    if len(issues) > 5:
                        self.log(f"      ... y {len(issues) - 5} más (ver reporte)")

                # NO falla el workflow, solo advierte
                self.log(f"\n   ℹ️  Continuando a pesar de los warnings...")

        except ImportError:
            self.log("   ⚠️  validators/data_quality.py no encontrado")
        except Exception as e:
            self.log(f"   ⚠️  Error en validación: {e}")

    def print_summary(self):
        """Imprime resumen de ejecución"""
        duration = (datetime.now() - self.start_time).total_seconds()

        self.log("\n" + "="*80)
        self.log("📊 RESUMEN DE EJECUCIÓN")
        self.log("="*80)

        successful = len([r for r in self.results.values() if r['success']])
        total = len(self.results)

        self.log(f"\n✅ Exitosos: {successful}/{total}")
        self.log(f"⏱️  Duración total: {duration:.0f}s ({duration/60:.1f} min)")

        if self.errors:
            self.log(f"\n⚠️  Errores en:")
            for error in self.errors:
                self.log(f"   • {error}")

        self.log("\n🎉 Escaneo maestro completado")
        self.log("="*80)

        # Guardar log
        log_data = {
            'timestamp': self.start_time.isoformat(),
            'duration_seconds': duration,
            'results': self.results,
            'errors': self.errors
        }

        log_path = Path('logs') / f"scan_{self.start_time.strftime('%Y%m%d_%H%M%S')}.json"
        log_path.parent.mkdir(exist_ok=True)

        with open(log_path, 'w') as f:
            json.dump(log_data, f, indent=2)

        self.log(f"💾 Log guardado: {log_path}")


def main():
    """Main execution"""
    scanner = MasterScanner()

    try:
        scanner.run_all_scanners()
        scanner.print_summary()

        # Git commit y push si hay cambios
        scanner.log("\n📤 Verificando cambios para commit...")

        result = subprocess.run(
            "git status --porcelain",
            shell=True,
            capture_output=True,
            text=True
        )

        if result.stdout.strip():
            scanner.log("   📝 Hay cambios - haciendo commit...")

            # Commit
            commit_msg = f"Auto-update: Scanners ejecutados {datetime.now().strftime('%Y-%m-%d %H:%M')}"

            subprocess.run(f'git add -A', shell=True)
            subprocess.run(f'git commit -m "{commit_msg}\n\nCo-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"', shell=True)

            # Push
            push_result = subprocess.run('git push', shell=True, capture_output=True, text=True)

            if push_result.returncode == 0:
                scanner.log("   ✅ Cambios subidos a GitHub")
            else:
                scanner.log("   ⚠️  Error al hacer push")

        else:
            scanner.log("   ℹ️  No hay cambios para commit")

        return 0

    except KeyboardInterrupt:
        scanner.log("\n⚠️  Escaneo interrumpido por usuario")
        return 1
    except Exception as e:
        scanner.log(f"\n❌ Error crítico: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
