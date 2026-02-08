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
            "python3 vcp_scanner_usa.py --scan",
            timeout=600
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
            timeout=300
        )

        # 7. Super Opportunities (3D - legacy)
        self.log("\n⭐ FASE 7: SUPER OPPORTUNITIES")
        self.run_command(
            "Super Analyzer",
            "python3 super_analyzer.py",
            timeout=300
        )

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
