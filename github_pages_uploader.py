#!/usr/bin/env python3
"""
Sistema para subir automáticamente reportes HTML a GitHub Pages
Adaptado para el repositorio stock_analyzer_a existente
"""

import os
import subprocess
import shutil
from datetime import datetime
import json
import re

class GitHubPagesUploader:
    def __init__(self, repo_url="https://github.com/tantancansado/stock_analyzer_a.git", use_main_branch=True):
        self.repo_url = repo_url
        self.use_main_branch = use_main_branch
        self.gh_pages_branch = "main" if use_main_branch else "gh-pages"
        self.repo_name = "stock_analyzer_a"
        self.username = "tantancansado"
        self.base_url = f"https://{self.username}.github.io/{self.repo_name}"
        
        # Si usamos main, trabajamos directamente en el repo actual
        if use_main_branch:
            self.local_repo_path = "."  # Directorio actual
        else:
            self.local_repo_path = "stock_analyzer_gh_pages"
        
    def setup_github_pages_branch(self):
        """
        Configura la rama gh-pages para GitHub Pages
        """
        print("🛠️ Configurando rama gh-pages para GitHub Pages...")
        
        try:
            # Si ya existe el directorio local, actualizarlo
            if os.path.exists(self.local_repo_path):
                print(f"📂 Directorio local existe, actualizando...")
                os.chdir(self.local_repo_path)
                
                # Verificar si estamos en la rama gh-pages
                result = subprocess.run(["git", "branch", "--show-current"], 
                                      capture_output=True, text=True, check=True)
                current_branch = result.stdout.strip()
                
                if current_branch != self.gh_pages_branch:
                    # Intentar cambiar a gh-pages
                    try:
                        subprocess.run(["git", "checkout", self.gh_pages_branch], check=True)
                    except subprocess.CalledProcessError:
                        # Si no existe, crearla
                        subprocess.run(["git", "checkout", "-b", self.gh_pages_branch], check=True)
                
                # Actualizar desde remoto
                try:
                    subprocess.run(["git", "pull", "origin", self.gh_pages_branch], check=True)
                except subprocess.CalledProcessError:
                    print("⚠️ No se pudo hacer pull, continuando...")
                
                os.chdir("..")
                return True
            
            # Clonar el repositorio
            print(f"📥 Clonando repositorio desde {self.repo_url}...")
            subprocess.run(["git", "clone", self.repo_url, self.local_repo_path], check=True)
            os.chdir(self.local_repo_path)
            
            # Verificar si existe la rama gh-pages en remoto
            result = subprocess.run(["git", "ls-remote", "--heads", "origin", self.gh_pages_branch], 
                                  capture_output=True, text=True)
            
            if result.stdout.strip():
                # La rama existe en remoto, hacer checkout
                print(f"✅ Rama {self.gh_pages_branch} existe en remoto")
                subprocess.run(["git", "checkout", self.gh_pages_branch], check=True)
            else:
                # Crear nueva rama gh-pages
                print(f"🆕 Creando nueva rama {self.gh_pages_branch}")
                subprocess.run(["git", "checkout", "--orphan", self.gh_pages_branch], check=True)
                
                # Limpiar todos los archivos del repositorio principal
                subprocess.run(["git", "rm", "-rf", "."], check=True)
                
                # Crear archivo index.html inicial
                self.create_index_page()
                
                # Commit inicial
                subprocess.run(["git", "add", "."], check=True)
                subprocess.run(["git", "commit", "-m", "Initial GitHub Pages setup"], check=True)
                subprocess.run(["git", "push", "-u", "origin", self.gh_pages_branch], check=True)
            
            os.chdir("..")
            print(f"✅ Rama gh-pages configurada exitosamente")
            print(f"🌐 Tu sitio estará disponible en: {self.base_url}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Error configurando GitHub Pages: {e}")
            return False
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
            return False
        finally:
            # Volver al directorio original
            if os.getcwd().endswith(self.local_repo_path):
                os.chdir("..")
    
    def create_index_page(self):
        """
        Crea una página index.html optimizada para reportes de insider trading
        """
        index_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📊 Stock Analyzer - Reportes de Insider Trading</title>
    <meta name="description" content="Análisis automatizado de insider trading con gráficos en tiempo real">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', 'Arial', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            text-align: center;
            background: rgba(255, 255, 255, 0.95);
            padding: 40px 20px;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.2);
            margin-bottom: 30px;
        }}
        
        .header h1 {{
            color: #2c3e50;
            margin-bottom: 10px;
            font-size: 2.5em;
            font-weight: 300;
        }}
        
        .header p {{
            color: #666;
            font-size: 1.2em;
            margin-bottom: 20px;
        }}
        
        .stats {{
            display: flex;
            justify-content: center;
            gap: 30px;
            flex-wrap: wrap;
            margin-top: 20px;
        }}
        
        .stat {{
            text-align: center;
        }}
        
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
            display: block;
        }}
        
        .stat-label {{
            font-size: 0.9em;
            color: #666;
            margin-top: 5px;
        }}
        
        .reports-section {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.2);
        }}
        
        .reports-section h2 {{
            color: #2c3e50;
            margin-bottom: 20px;
            text-align: center;
            font-size: 1.8em;
        }}
        
        .report-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        
        .report-card {{
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            border-left: 5px solid #667eea;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            cursor: pointer;
        }}
        
        .report-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.15);
        }}
        
        .report-title {{
            font-size: 1.2em;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 10px;
            text-decoration: none;
            display: block;
        }}
        
        .report-title:hover {{
            color: #667eea;
        }}
        
        .report-meta {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        
        .report-date {{
            color: #666;
            font-size: 0.9em;
        }}
        
        .report-badge {{
            background: #28a745;
            color: white;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.8em;
        }}
        
        .report-description {{
            color: #666;
            font-size: 0.9em;
            line-height: 1.4;
        }}
        
        .no-reports {{
            text-align: center;
            padding: 40px;
            color: #666;
        }}
        
        .footer {{
            text-align: center;
            margin-top: 40px;
            color: rgba(255, 255, 255, 0.8);
        }}
        
        .footer a {{
            color: rgba(255, 255, 255, 0.9);
            text-decoration: none;
        }}
        
        .footer a:hover {{
            text-decoration: underline;
        }}
        
        @media (max-width: 768px) {{
            .header h1 {{
                font-size: 2em;
            }}
            
            .stats {{
                gap: 20px;
            }}
            
            .stat-number {{
                font-size: 1.5em;
            }}
            
            .report-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Stock Analyzer</h1>
            <p>Análisis automatizado de insider trading con datos en tiempo real</p>
            
            <div class="stats">
                <div class="stat">
                    <span class="stat-number" id="total-reports">0</span>
                    <div class="stat-label">Reportes Totales</div>
                </div>
                <div class="stat">
                    <span class="stat-number" id="last-update">--</span>
                    <div class="stat-label">Última Actualización</div>
                </div>
                <div class="stat">
                    <span class="stat-number" id="total-companies">0</span>
                    <div class="stat-label">Empresas Analizadas</div>
                </div>
            </div>
        </div>
        
        <div class="reports-section">
            <h2>📈 Reportes Disponibles</h2>
            <div id="reports-container" class="report-grid">
                <div class="no-reports">
                    <p>🔄 Cargando reportes...</p>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>🤖 Generado automáticamente por Stock Analyzer | 
               <a href="{self.repo_url}" target="_blank">Ver código en GitHub</a>
            </p>
        </div>
    </div>
    
    <script>
        // Lista de reportes (se actualiza automáticamente)
        let reports = [];
        
        function formatDate(dateString) {{
            const date = new Date(dateString);
            return date.toLocaleString('es-ES', {{
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            }});
        }}
        
        function isNewReport(dateString) {{
            const reportDate = new Date(dateString);
            const now = new Date();
            const diffHours = (now - reportDate) / (1000 * 60 * 60);
            return diffHours <= 24; // Nuevo si tiene menos de 24 horas
        }}
        
        function updateStats() {{
            document.getElementById('total-reports').textContent = reports.length;
            
            if (reports.length > 0) {{
                const lastReport = reports.reduce((latest, report) => {{
                    return new Date(report.date) > new Date(latest.date) ? report : latest;
                }});
                document.getElementById('last-update').textContent = formatDate(lastReport.date);
                
                // Estimar empresas únicas (simplificado)
                const estimatedCompanies = Math.floor(reports.length * 1.5);
                document.getElementById('total-companies').textContent = estimatedCompanies;
            }}
        }}
        
        function loadReports() {{
            const container = document.getElementById('reports-container');
            
            if (reports.length === 0) {{
                container.innerHTML = `
                    <div class="no-reports">
                        <p>📄 No hay reportes disponibles aún.</p>
                        <p style="margin-top: 10px; font-size: 0.9em;">Los reportes se generan automáticamente cuando hay nuevas oportunidades de insider trading.</p>
                    </div>
                `;
                return;
            }}
            
            // Ordenar reportes por fecha (más reciente primero)
            const sortedReports = [...reports].sort((a, b) => new Date(b.date) - new Date(a.date));
            
            let html = '';
            sortedReports.forEach(report => {{
                const isNew = isNewReport(report.date);
                html += `
                    <div class="report-card" onclick="window.open('${{report.file}}', '_blank')">
                        <div class="report-meta">
                            <span class="report-date">${{formatDate(report.date)}}</span>
                            ${{isNew ? '<span class="report-badge">NUEVO</span>' : ''}}
                        </div>
                        <a href="${{report.file}}" target="_blank" class="report-title">
                            ${{report.title}}
                        </a>
                        <div class="report-description">
                            ${{report.description || 'Análisis completo de oportunidades de insider trading con gráficos interactivos de FinViz.'}}
                        </div>
                    </div>
                `;
            }});
            
            container.innerHTML = html;
            updateStats();
        }}
        
        // Cargar reportes al cargar la página
        document.addEventListener('DOMContentLoaded', function() {{
            loadReports();
            
            // Auto-refresh cada 5 minutos si la página está activa
            setInterval(function() {{
                if (!document.hidden) {{
                    location.reload();
                }}
            }}, 300000); // 5 minutos
        }});
    </script>
</body>
</html>"""
        
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(index_html)
        
        # Crear archivo .nojekyll para evitar problemas con GitHub Pages
        with open(".nojekyll", "w") as f:
            f.write("")
    
    def upload_report(self, html_file_path, title=None, description=None):
        """
        Sube un reporte HTML a GitHub Pages (funciona con main o gh-pages)
        """
        if not os.path.exists(html_file_path):
            print(f"❌ Archivo no encontrado: {html_file_path}")
            return None
            
        print(f"📤 Subiendo reporte a GitHub Pages...")
        
        try:
            original_dir = os.getcwd()
            
            if self.use_main_branch:
                # Trabajar en el directorio actual (main branch)
                docs_dir = "docs"
                os.makedirs(docs_dir, exist_ok=True)
                
                # Generar nombre único para el archivo
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"insider_report_{timestamp}.html"
                
                # Copiar archivo a docs/
                shutil.copy2(html_file_path, os.path.join(docs_dir, filename))
                print(f"📄 Archivo copiado a: docs/{filename}")
                
                # Actualizar index
                os.chdir(docs_dir)
                if not title:
                    title = f"Reporte Insider Trading - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                
                self.update_index_with_new_report(filename, title, description)
                os.chdir("..")
                
                # Git add, commit, push desde la raíz del proyecto
                subprocess.run(["git", "add", f"docs/{filename}", "docs/index.html"], check=True)
                commit_msg = f"Nuevo reporte insider: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                subprocess.run(["git", "commit", "-m", commit_msg], check=True)
                subprocess.run(["git", "push", "origin", "main"], check=True)
                
                # Construir URL pública
                file_url = f"{self.base_url}/{filename}"
                index_url = self.base_url
                
            else:
                # Trabajar con rama gh-pages separada
                os.chdir(self.local_repo_path)
                
                # Verificar que estamos en la rama correcta
                result = subprocess.run(["git", "branch", "--show-current"], 
                                      capture_output=True, text=True, check=True)
                current_branch = result.stdout.strip()
                
                if current_branch != self.gh_pages_branch:
                    subprocess.run(["git", "checkout", self.gh_pages_branch], check=True)
                
                # Generar nombre único para el archivo
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"insider_report_{timestamp}.html"
                
                # Copiar archivo
                shutil.copy2(html_file_path, filename)
                print(f"📄 Archivo copiado como: {filename}")
                
                # Actualizar index con el nuevo reporte
                if not title:
                    title = f"Reporte Insider Trading - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                
                self.update_index_with_new_report(filename, title, description)
                
                # Git add, commit, push
                subprocess.run(["git", "add", "."], check=True)
                commit_msg = f"Nuevo reporte insider: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                subprocess.run(["git", "commit", "-m", commit_msg], check=True)
                subprocess.run(["git", "push", "origin", self.gh_pages_branch], check=True)
                
                # Construir URL pública
                file_url = f"{self.base_url}/{filename}"
                index_url = self.base_url
            
            print(f"✅ Reporte subido exitosamente")
            print(f"🌐 URL del reporte: {file_url}")
            print(f"🏠 Página principal: {index_url}")
            
            return {
                'file_url': file_url,
                'index_url': index_url,
                'filename': filename
            }
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Error subiendo reporte: {e}")
            return None
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
            return None
        finally:
            os.chdir(original_dir)
    
    def update_index_with_new_report(self, filename, title, description=None):
        """
        Actualiza el index.html con el nuevo reporte
        """
        try:
            # Leer index actual
            with open("index.html", "r", encoding="utf-8") as f:
                content = f.read()
            
            # Crear nuevo reporte
            new_report = {
                "file": filename,
                "title": title,
                "date": datetime.now().isoformat(),
                "description": description or f"Análisis de insider trading generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}"
            }
            
            # Buscar la línea donde se define reports = []
            pattern = r'let reports = \[(.*?)\];'
            match = re.search(pattern, content, re.DOTALL)
            
            if match:
                # Extraer reportes existentes
                existing_reports_str = match.group(1).strip()
                existing_reports = []
                
                if existing_reports_str:
                    try:
                        # Evaluar JavaScript array como Python (simplificado)
                        existing_reports_str = existing_reports_str.replace('true', 'True').replace('false', 'False').replace('null', 'None')
                        existing_reports = eval(f"[{existing_reports_str}]")
                    except:
                        print("⚠️ No se pudieron parsear reportes existentes, creando lista nueva")
                
                # Agregar nuevo reporte al principio
                existing_reports.insert(0, new_report)
                
                # Mantener solo los últimos 50 reportes
                existing_reports = existing_reports[:50]
                
                # Convertir de vuelta a JavaScript
                reports_js = json.dumps(existing_reports, indent=8, ensure_ascii=False)
                
                # Reemplazar en el contenido
                new_content = re.sub(pattern, f'let reports = {reports_js};', content, flags=re.DOTALL)
                
                with open("index.html", "w", encoding="utf-8") as f:
                    f.write(new_content)
                
                print(f"✅ Index actualizado con {len(existing_reports)} reportes")
            else:
                print("⚠️ No se encontró la sección de reportes en index.html")
                
        except Exception as e:
            print(f"⚠️ Error actualizando index: {e}")
    
    def get_public_url(self, filename=None):
        """
        Obtiene la URL pública del sitio o de un archivo específico
        """
        if filename:
            return f"{self.base_url}/{filename}"
        return self.base_url


def integrar_con_sistema_existente():
    """
    Función para integrar GitHub Pages con el sistema existente
    """
    integration_code = '''
# Agrega esta función a tu alerts/plot_utils.py o donde manejes la generación de reportes

def enviar_reporte_con_github_pages(html_path, csv_path=None):
    """
    Versión mejorada que sube HTML a GitHub Pages y envía links por Telegram
    """
    try:
        from github_pages_uploader import GitHubPagesUploader
        from alerts.telegram_utils import send_message
        from config import TELEGRAM_CHAT_ID, TELEGRAM_BOT_TOKEN
        
        # Subir a GitHub Pages
        uploader = GitHubPagesUploader()
        
        # Generar título descriptivo
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        title = f"📊 Análisis Insider Trading - {timestamp}"
        description = f"Reporte completo con gráficos interactivos de FinViz generado el {timestamp}"
        
        # Subir reporte
        result = uploader.upload_report(html_path, title, description)
        
        if result:
            # Preparar mensaje para Telegram
            mensaje = f"""🚀 NUEVO REPORTE INSIDER TRADING

📊 Análisis actualizado: {timestamp}
🌐 Ver reporte completo: {result['file_url']}
🏠 Todos los reportes: {result['index_url']}

✨ Características:
📈 Gráficos interactivos de FinViz
🔍 Datos en tiempo real
📱 Optimizado para móvil
💾 Historial completo disponible"""
            
            # Enviar por Telegram
            if TELEGRAM_CHAT_ID and TELEGRAM_BOT_TOKEN:
                send_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, mensaje)
                print(f"✅ Notificación enviada por Telegram")
            
            # También enviar archivo CSV si existe
            if csv_path and os.path.exists(csv_path):
                from alerts.telegram_utils import send_file
                send_file(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, csv_path)
                print(f"✅ CSV enviado por Telegram")
            
            return result
        else:
            print("❌ No se pudo subir a GitHub Pages")
            return None
            
    except Exception as e:
        print(f"❌ Error en integración con GitHub Pages: {e}")
        import traceback
        traceback.print_exc()
        return None


# Para reemplazar en tu insider_tracker.py:
def generar_reporte_completo_integrado():
    """
    Versión mejorada que incluye GitHub Pages
    """
    try:
        # ... tu código existente para generar CSV y HTML ...
        
        # Después de generar el HTML:
        if html_path and os.path.exists(html_path):
            # Subir a GitHub Pages y enviar por Telegram
            github_result = enviar_reporte_con_github_pages(html_path, csv_path)
            
            return {
                'csv_opportunities': csv_path,
                'html_opportunities': html_path,
                'html_charts': html_charts_path,  # si lo tienes
                'bundle': bundle_path,  # si lo tienes
                'github_pages': github_result
            }
        
    except Exception as e:
        print(f"❌ Error en reporte integrado: {e}")
        return None
'''
    
    return integration_code


def setup_complete_system():
    """
    Configura todo el sistema de GitHub Pages con opción de usar main branch
    """
    print("🛠️ CONFIGURACIÓN COMPLETA DE GITHUB PAGES")
    print("=" * 50)
    
    # Preguntar qué método prefiere el usuario
    print("🤔 ¿Cómo quieres configurar GitHub Pages?")
    print("1. 📁 Usar rama main con carpeta docs/ (MÁS SIMPLE)")
    print("2. 🌿 Usar rama gh-pages separada (MÁS LIMPIO)")
    
    while True:
        choice = input("Selecciona opción (1 o 2): ").strip()
        if choice in ["1", "2"]:
            break
        print("❌ Por favor selecciona 1 o 2")
    
    use_main = choice == "1"
    uploader = GitHubPagesUploader(use_main_branch=use_main)
    
    # Configurar según la opción elegida
    if uploader.setup_github_repo():
        print(f"\n✅ Sistema configurado exitosamente!")
        print(f"🌐 Tu sitio web: {uploader.base_url}")
        
        if use_main:
            print(f"📁 Archivos en: docs/")
            print(f"🔧 Método: Rama main con carpeta docs/")
            
            print(f"\n📋 PASOS FINALES:")
            print(f"1. Ve a: https://github.com/{uploader.username}/{uploader.repo_name}/settings/pages")
            print(f"2. En 'Source', selecciona: 'Deploy from a branch'")
            print(f"3. En 'Branch', selecciona: 'main'")
            print(f"4. En 'Folder', selecciona: '/docs'")
            print(f"5. Guarda los cambios")
            print(f"6. Espera 2-3 minutos para que se active")
            
        else:
            print(f"📁 Directorio local: {uploader.local_repo_path}")
            print(f"🔧 Método: Rama gh-pages separada")
            
            print(f"\n📋 PASOS FINALES:")
            print(f"1. Ve a: https://github.com/{uploader.username}/{uploader.repo_name}/settings/pages")
            print(f"2. En 'Source', selecciona: 'Deploy from a branch'")
            print(f"3. En 'Branch', selecciona: 'gh-pages'")
            print(f"4. En 'Folder', selecciona: '/ (root)'")
            print(f"5. Guarda los cambios")
            print(f"6. Espera 2-3 minutos para que se active")
        
        print(f"\n7. Tu sitio estará disponible en: {uploader.base_url}")
        
        # Mostrar código de integración
        print(f"\n🔧 INTEGRACIÓN CON TU SISTEMA:")
        if use_main:
            print("Tu sistema usará la rama main. No necesitas clonar nada adicional.")
        else:
            print("Tu sistema usará una rama separada para mayor limpieza.")
        
        return True
    else:
        print("❌ Error en la configuración")
        return False


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "setup":
            setup_complete_system()
        elif sys.argv[1] == "setup-main":
            # Forzar uso de main branch
            uploader = GitHubPagesUploader(use_main_branch=True)
            if uploader.setup_github_repo():
                print(f"✅ Configurado con rama main")
                print(f"🌐 Sitio: {uploader.base_url}")
        elif sys.argv[1] == "setup-gh-pages":
            # Forzar uso de gh-pages branch
            uploader = GitHubPagesUploader(use_main_branch=False)
            if uploader.setup_github_repo():
                print(f"✅ Configurado con rama gh-pages")
                print(f"🌐 Sitio: {uploader.base_url}")
        elif sys.argv[1] == "upload" and len(sys.argv) > 2:
            # Por defecto usar main branch para uploads
            uploader = GitHubPagesUploader(use_main_branch=True)
            result = uploader.upload_report(sys.argv[2])
            if result:
                print(f"✅ Archivo subido: {result['file_url']}")
        else:
            print("Uso: python github_pages_uploader.py [setup|setup-main|setup-gh-pages|upload archivo.html]")
    else:
        setup_complete_system()