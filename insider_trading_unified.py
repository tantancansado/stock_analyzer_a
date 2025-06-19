#!/usr/bin/env python3
"""
Sistema Unificado de Insider Trading
Integra scraping, generación HTML y envío por Telegram
Con soporte opcional para GitHub Pages
"""

# Importar el VCP Scanner Enhanced si existe, si no, stub
try:
    from vcp_scanner_usa import VCPScannerEnhanced
except ImportError:
    class VCPScannerEnhanced:
        def __init__(self):
            print("Función no implementada: VCPScannerEnhanced (stub)")
        def scan_market(self):
            print("Función no implementada: scan_market")
            # Devuelve lista vacía simulando sin candidatos
            return []
        def generate_html(self, results, html_path):
            print("Función no implementada: generate_html")
            # Crea un HTML de stub
            with open(html_path, "w", encoding="utf-8") as f:
                f.write("<html><body><h1>Función no implementada</h1></body></html>")
            return html_path
        def save_csv(self, results, csv_path):
            print("Función no implementada: save_csv")
            import pandas as pd
            pd.DataFrame(results).to_csv(csv_path, index=False)
            return csv_path

def run_vcp_scanner_usa_interactive():
    """
    Flujo interactivo para escanear TODO el mercado USA con el VCP Scanner avanzado.
    """
    import os
    from datetime import datetime

    print("\n🎯 ESCANEO AVANZADO DE TODO EL MERCADO USA (VCP Scanner)")
    print("=" * 60)
    scanner = VCPScannerEnhanced()
    print("🔍 Ejecutando escaneo de mercado USA...")
    try:
        results = scanner.scan_market()
    except Exception as e:
        print(f"❌ Error ejecutando el escaneo: {e}")
        return
    num_candidates = len(results) if results is not None else 0
    print(f"✅ Escaneo completado. Candidatos detectados: {num_candidates}")
    if num_candidates == 0:
        print("⚠️  No se detectaron candidatos.")
    # Preguntar si quiere generar HTML
    gen_html = input("¿Quieres generar HTML con los resultados? (s/n): ").strip().lower()
    if gen_html != "s":
        print("🛑 Proceso finalizado (no se generó HTML).")
        return
    # Generar HTML
    html_path = "reports/vcp_market_scan.html"
    csv_path = "reports/vcp_market_scan.csv"
    try:
        # Guardar CSV si hay resultados (aunque sean 0)
        if results is not None:
            scanner.save_csv(results, csv_path)
        scanner.generate_html(results, html_path)
        print(f"✅ HTML generado: {html_path}")
    except Exception as e:
        print(f"❌ Error generando HTML: {e}")
        return
    # Preguntar si quiere subir a GitHub Pages
    subir = input("¿Quieres subir el HTML a GitHub Pages? (s/n): ").strip().lower()
    if subir != "s":
        print("🛑 Proceso finalizado (HTML no subido a GitHub Pages).")
        return
    # Intentar subir a GitHub Pages usando uploader de historial, con título/desc diferentes
    if not os.path.exists("github_pages_historial.py"):
        print("⚠️ github_pages_historial.py no encontrado. No se puede subir.")
        return
    try:
        from github_pages_historial import GitHubPagesHistoricalUploader
        uploader = GitHubPagesHistoricalUploader()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        title = f"🎯 VCP Market Scanner - {num_candidates} candidatos - {timestamp}"
        description = f"Reporte avanzado de escaneo de TODO el mercado USA. Candidatos detectados: {num_candidates}."
        result = uploader.upload_historical_report(
            html_path,
            csv_path,
            title,
            description
        )
        if result:
            print("✅ Subido a GitHub Pages:")
            for key, value in result.items():
                print(f"   {key}: {value}")
        else:
            print("❌ Error subiendo a GitHub Pages")
    except Exception as e:
        print(f"❌ Error subiendo a GitHub Pages: {e}")
        return
    print("🎉 Proceso de escaneo avanzado finalizado.")

import os
import sys
import subprocess
import pandas as pd
import zipfile
from datetime import datetime
from pathlib import Path
import traceback

class InsiderTradingSystem:
    """Sistema principal que gestiona todo el flujo"""
    
    def __init__(self):
        self.csv_path = "reports/insiders_daily.csv"
        self.html_path = "reports/insiders_report_completo.html"
        self.bundle_path = "reports/insiders_bundle.zip"
        self.setup_directories()
    
    def setup_directories(self):
        """Crea los directorios necesarios"""
        os.makedirs("reports", exist_ok=True)
        os.makedirs("alerts", exist_ok=True)
        print("✅ Directorios verificados")
    
    def run_scraper(self):
        """Ejecuta el scraper de OpenInsider"""
        print("\n🕷️ EJECUTANDO SCRAPER")
        print("=" * 50)
        
        try:
            # Buscar el scraper
            scraper_paths = [
                "insiders/openinsider_scraper.py",
                "openinsider_scraper.py",
                "paste-3.txt"  # Por si está como texto
            ]
            
            scraper_found = None
            for path in scraper_paths:
                if os.path.exists(path):
                    scraper_found = path
                    break
            
            if not scraper_found:
                print("❌ Scraper no encontrado")
                return False
            
            print(f"✅ Ejecutando: {scraper_found}")
            
            # Si es paste-3.txt, ejecutarlo como Python
            if scraper_found.endswith('.txt'):
                with open(scraper_found, 'r') as f:
                    exec(f.read())
            else:
                result = subprocess.run(
                    [sys.executable, scraper_found],
                    capture_output=True,
                    text=True,
                    timeout=180
                )
                
                if result.returncode != 0:
                    print(f"❌ Error ejecutando scraper: {result.stderr}")
                    return False
            
            # Verificar que se generó el CSV
            if os.path.exists(self.csv_path):
                df = pd.read_csv(self.csv_path)
                print(f"✅ CSV generado: {len(df)} registros")
                return True
            else:
                print("❌ CSV no generado")
                return False
                
        except Exception as e:
            print(f"❌ Error en scraper: {e}")
            traceback.print_exc()
            return False
    
    def generate_html(self):
        """Genera el HTML con los datos del CSV"""
        print("\n📄 GENERANDO HTML")
        print("=" * 50)
        
        try:
            # Verificar CSV
            if not os.path.exists(self.csv_path):
                print("❌ CSV no encontrado")
                return False
            
            # Importar función de generación
            try:
                from alerts.plot_utils import crear_html_moderno_finviz
                self.html_path = crear_html_moderno_finviz()
                return self.html_path is not None
            except ImportError:
                print("⚠️ plot_utils no disponible, generando HTML básico")
                return self.generate_basic_html()
                
        except Exception as e:
            print(f"❌ Error generando HTML: {e}")
            return False
    
    def generate_basic_html(self):
        """Genera un HTML básico si plot_utils no está disponible"""
        try:
            df = pd.read_csv(self.csv_path)
            
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Insider Trading Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>📊 Insider Trading Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}</h1>
    <p>Total transacciones: {len(df)}</p>
    <p>Empresas únicas: {df['Insider'].nunique() if 'Insider' in df.columns else 0}</p>
    
    <table>
        <tr>
            <th>Ticker</th>
            <th>Company</th>
            <th>Price</th>
            <th>Qty</th>
            <th>Value</th>
            <th>Type</th>
        </tr>
"""
            
            for _, row in df.head(50).iterrows():
                html_content += f"""
        <tr>
            <td>{row.get('Insider', 'N/A')}</td>
            <td>{row.get('Title', 'N/A')}</td>
            <td>{row.get('Price', 'N/A')}</td>
            <td>{row.get('Qty', 'N/A')}</td>
            <td>{row.get('Value', 'N/A')}</td>
            <td>{row.get('Type', 'N/A')}</td>
        </tr>
"""
            
            html_content += """
    </table>
</body>
</html>
"""
            
            with open(self.html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"✅ HTML básico generado: {self.html_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error generando HTML básico: {e}")
            return False
    
    def create_bundle(self):
        """Crea un ZIP con todos los archivos"""
        print("\n📦 CREANDO BUNDLE")
        print("=" * 50)
        
        try:
            with zipfile.ZipFile(self.bundle_path, 'w') as zipf:
                if os.path.exists(self.html_path):
                    zipf.write(self.html_path, arcname=os.path.basename(self.html_path))
                if os.path.exists(self.csv_path):
                    zipf.write(self.csv_path, arcname=os.path.basename(self.csv_path))
            
            print(f"✅ Bundle creado: {self.bundle_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error creando bundle: {e}")
            return False
    
    def send_telegram(self):
        """Envía reporte por Telegram"""
        print("\n📱 ENVIANDO POR TELEGRAM")
        print("=" * 50)
        
        try:
            # Intentar importar configuración
            try:
                from config import TELEGRAM_CHAT_ID, TELEGRAM_BOT_TOKEN
            except ImportError:
                print("❌ config.py no encontrado")
                return False
            
            if not TELEGRAM_CHAT_ID or not TELEGRAM_BOT_TOKEN:
                print("❌ Configuración Telegram incompleta")
                return False
            
            # Importar utilidades de Telegram
            try:
                from alerts.telegram_utils import send_message, send_file
            except ImportError:
                print("❌ telegram_utils no encontrado")
                return False
            
            # Leer estadísticas
            df = pd.read_csv(self.csv_path)
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
            
            # Crear mensaje
            mensaje = f"""📊 REPORTE INSIDER TRADING

📅 Fecha: {timestamp}
📊 Transacciones: {len(df)}
🏢 Empresas: {df['Insider'].nunique() if 'Insider' in df.columns else 0}

📄 Archivos adjuntos:"""
            
            # Enviar mensaje
            send_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, mensaje)
            
            # Enviar archivos
            if os.path.exists(self.html_path):
                send_file(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, self.html_path)
            
            if os.path.exists(self.csv_path):
                send_file(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, self.csv_path)
            
            print("✅ Enviado por Telegram")
            return True
            
        except Exception as e:
            print(f"❌ Error enviando por Telegram: {e}")
            traceback.print_exc()
            return False
    
    def upload_github_pages(self):
        """Intenta subir a GitHub Pages si está disponible"""
        print("\n🌐 SUBIENDO A GITHUB PAGES")
        print("=" * 50)
        
        try:
            # Verificar si existe el módulo
            if not os.path.exists("github_pages_historial.py"):
                print("⚠️ github_pages_historial.py no encontrado")
                print("   GitHub Pages no disponible")
                return None
            
            # Intentar importar
            try:
                from github_pages_historial import GitHubPagesHistoricalUploader
            except ImportError as e:
                print(f"❌ Error importando: {e}")
                return None
            
            # Crear uploader
            uploader = GitHubPagesHistoricalUploader()
            
            # Preparar datos
            df = pd.read_csv(self.csv_path)
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
            
            if len(df) > 0:
                title = f"📊 Insider Trading - {len(df)} oportunidades - {timestamp}"
                description = f"Reporte con {len(df)} transacciones detectadas"
            else:
                title = f"📊 Monitoreo Insider Trading - {timestamp}"
                description = "Monitoreo completado sin oportunidades"
            
            # Subir
            result = uploader.upload_historical_report(
                self.html_path,
                self.csv_path,
                title,
                description
            )
            
            if result:
                print(f"✅ Subido a GitHub Pages:")
                for key, value in result.items():
                    print(f"   {key}: {value}")
                return result
            else:
                print("❌ Error subiendo a GitHub Pages")
                return None
                
        except Exception as e:
            print(f"❌ Error con GitHub Pages: {e}")
            traceback.print_exc()
            return None
    
    def run_complete_process(self):
        """Ejecuta el proceso completo"""
        print("\n🚀 PROCESO COMPLETO INSIDER TRADING")
        print("=" * 60)
        print(f"📅 Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        results = {
            'scraper': False,
            'html': False,
            'bundle': False,
            'telegram': False,
            'github': None
        }
        
        try:
            # 1. Ejecutar scraper
            results['scraper'] = self.run_scraper()
            if not results['scraper']:
                print("❌ Fallo en scraper, abortando")
                return results
            
            # 2. Generar HTML
            results['html'] = self.generate_html()
            if not results['html']:
                print("⚠️ Fallo en HTML, continuando...")
            
            # 3. Crear bundle
            results['bundle'] = self.create_bundle()
            
            # 4. GitHub Pages (opcional)
            results['github'] = self.upload_github_pages()
            
            # 5. Telegram
            results['telegram'] = self.send_telegram()
            
            # Resumen
            print("\n" + "=" * 60)
            print("📊 RESUMEN DE EJECUCIÓN")
            print("=" * 60)
            print(f"✅ Scraper: {'✓' if results['scraper'] else '✗'}")
            print(f"✅ HTML: {'✓' if results['html'] else '✗'}")
            print(f"✅ Bundle: {'✓' if results['bundle'] else '✗'}")
            print(f"✅ Telegram: {'✓' if results['telegram'] else '✗'}")
            print(f"✅ GitHub Pages: {'✓' if results['github'] else '✗ (opcional)'}")
            
            if results['github']:
                print(f"\n🌐 Ver en GitHub Pages:")
                print(f"   {results['github'].get('index_url', 'N/A')}")
            
            return results
            
        except Exception as e:
            print(f"\n❌ Error crítico: {e}")
            traceback.print_exc()
            return results

def test_components():
    """Prueba cada componente individualmente"""
    print("\n🔧 MODO TEST - VERIFICANDO COMPONENTES")
    print("=" * 60)
    
    # 1. Verificar archivos necesarios
    print("\n📁 Verificando archivos:")
    files_to_check = [
        ("Scraper", ["insiders/openinsider_scraper.py", "openinsider_scraper.py", "paste-3.txt"]),
        ("Plot Utils", ["alerts/plot_utils.py", "paste-2.txt"]),
        ("Config", ["config.py"]),
        ("Telegram Utils", ["alerts/telegram_utils.py"]),
        ("GitHub Pages", ["github_pages_historial.py"])
    ]
    
    for name, paths in files_to_check:
        found = False
        for path in paths:
            if os.path.exists(path):
                print(f"✅ {name}: {path}")
                found = True
                break
        if not found:
            print(f"❌ {name}: NO ENCONTRADO")
    
    # 2. Verificar CSV existente
    print("\n📊 Verificando datos:")
    if os.path.exists("reports/insiders_daily.csv"):
        try:
            df = pd.read_csv("reports/insiders_daily.csv")
            print(f"✅ CSV existente: {len(df)} registros")
        except Exception as e:
            print(f"❌ CSV corrupto: {e}")
    else:
        print("❌ CSV no existe")
    
    # 3. Verificar configuración Telegram
    print("\n📱 Verificando Telegram:")
    try:
        from config import TELEGRAM_CHAT_ID, TELEGRAM_BOT_TOKEN
        if TELEGRAM_CHAT_ID and TELEGRAM_BOT_TOKEN:
            print(f"✅ Chat ID: {TELEGRAM_CHAT_ID}")
            print(f"✅ Token: {TELEGRAM_BOT_TOKEN[:10]}...")
        else:
            print("❌ Configuración incompleta")
    except ImportError:
        print("❌ config.py no importable")

def main():
    """Función principal con menú"""
    if len(sys.argv) > 1:
        # Modo automático
        if sys.argv[1] == "--auto":
            system = InsiderTradingSystem()
            system.run_complete_process()
        elif sys.argv[1] == "--test":
            test_components()
        elif sys.argv[1] == "--scraper":
            system = InsiderTradingSystem()
            system.run_scraper()
        elif sys.argv[1] == "--html":
            system = InsiderTradingSystem()
            system.generate_html()
        elif sys.argv[1] == "--telegram":
            system = InsiderTradingSystem()
            system.send_telegram()
    else:
        # Modo interactivo
        while True:
            print("\n" + "=" * 60)
            print("📊 SISTEMA INSIDER TRADING - MENÚ PRINCIPAL")
            print("=" * 60)
            print("1. 🚀 Ejecutar proceso completo")
            print("2. 🕷️  Solo ejecutar scraper")
            print("3. 📄 Solo generar HTML")
            print("4. 📱 Solo enviar Telegram")
            print("5. 🔧 Verificar componentes")
            print("6. 🌐 Probar GitHub Pages")
            print("7. 🎯 Escanear TODO el mercado USA (VCP Scanner avanzado)")
            print("0. ❌ Salir")
            print("=" * 60)

            opcion = input("Selecciona opción: ").strip()

            system = InsiderTradingSystem()

            if opcion == "1":
                system.run_complete_process()
            elif opcion == "2":
                system.run_scraper()
            elif opcion == "3":
                system.generate_html()
            elif opcion == "4":
                system.send_telegram()
            elif opcion == "5":
                test_components()
            elif opcion == "6":
                result = system.upload_github_pages()
                if result:
                    print("✅ GitHub Pages funcionando")
                else:
                    print("❌ GitHub Pages no disponible")
            elif opcion == "7":
                run_vcp_scanner_usa_interactive()
            elif opcion == "0":
                print("👋 ¡Hasta luego!")
                break
            else:
                print("❌ Opción inválida")

            input("\nPresiona Enter para continuar...")

if __name__ == "__main__":
    main()