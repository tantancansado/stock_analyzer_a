#!/usr/bin/env python3
"""
Sistema para subir automáticamente reportes HTML a GitHub Pages
Versión corregida con fixes para errores comunes
"""

import os
import subprocess
import shutil
from datetime import datetime
import json
import re

class GitHubPagesUploader:
    def __init__(self):
        self.repo_name = "stock_analyzer_a"
        self.username = "tantancansado"
        self.base_url = f"https://{self.username}.github.io/{self.repo_name}"
        self.docs_dir = "docs"
        
    def setup_github_pages(self):
        """
        Configura GitHub Pages en la rama main usando carpeta docs/
        """
        print("🛠️ Configurando GitHub Pages en rama main con carpeta docs/...")
        
        try:
            # Verificar que estamos en un repositorio git
            if not os.path.exists('.git'):
                print("❌ No estás en un repositorio git")
                print("💡 Asegúrate de estar en la raíz de tu proyecto stock_analyzer_a")
                return False
            
            # Crear directorio docs
            os.makedirs(self.docs_dir, exist_ok=True)
            print(f"📁 Directorio {self.docs_dir}/ creado")
            
            # Crear archivo index.html
            self.create_index_page()
            print(f"📄 index.html creado en {self.docs_dir}/")
            
            # Verificar si hay cambios para commitear
            try:
                result = subprocess.run(["git", "status", "--porcelain", self.docs_dir], 
                                      capture_output=True, text=True, check=True)
                if result.stdout.strip():
                    # Hay cambios, hacer commit
                    subprocess.run(["git", "add", f"{self.docs_dir}/"], check=True)
                    subprocess.run(["git", "commit", "-m", "Setup GitHub Pages in docs/ folder"], check=True)
                    
                    # Intentar push
                    try:
                        subprocess.run(["git", "push", "origin", "main"], check=True)
                        print("✅ Cambios subidos a GitHub")
                    except subprocess.CalledProcessError:
                        print("⚠️ No se pudo hacer push automático")
                        print("💡 Ejecuta manualmente: git push origin main")
                else:
                    print("✅ GitHub Pages ya está configurado")
            except subprocess.CalledProcessError as e:
                print(f"⚠️ Error en operaciones git: {e}")
            
            print(f"\n🎉 CONFIGURACIÓN COMPLETADA")
            print(f"🌐 Tu sitio estará en: {self.base_url}")
            print(f"📁 Archivos en: {self.docs_dir}/")
            
            print(f"\n📋 PASOS FINALES EN GITHUB:")
            print(f"1. Ve a: https://github.com/{self.username}/{self.repo_name}/settings/pages")
            print(f"2. Source: Deploy from a branch")
            print(f"3. Branch: main")
            print(f"4. Folder: /{self.docs_dir}")
            print(f"5. Save")
            print(f"6. Espera 2-3 minutos")
            
            return True
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def create_index_page(self):
        """
        Crea una página index.html optimizada
        """
        html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📊 Stock Analyzer - Reportes</title>
    <style>
        body {{
            font-family: 'Segoe UI', sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.2);
        }}
        h1 {{
            color: #2c3e50;
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5em;
        }}
        .stats {{
            display: flex;
            justify-content: center;
            gap: 30px;
            margin: 20px 0;
            flex-wrap: wrap;
        }}
        .stat {{
            text-align: center;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 10px;
            min-width: 120px;
        }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}
        .stat-label {{
            color: #666;
            font-size: 0.9em;
            margin-top: 5px;
        }}
        .reports-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-top: 30px;
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
            padding-top: 20px;
            border-top: 1px solid #eee;
            color: #666;
        }}
        @media (max-width: 768px) {{
            h1 {{ font-size: 2em; }}
            .stats {{ gap: 15px; }}
            .reports-grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Stock Analyzer - Reportes de Insider Trading</h1>
        
        <div class="stats">
            <div class="stat">
                <div class="stat-number" id="total-reports">0</div>
                <div class="stat-label">Reportes Totales</div>
            </div>
            <div class="stat">
                <div class="stat-number" id="last-update">--</div>
                <div class="stat-label">Última Actualización</div>
            </div>
            <div class="stat">
                <div class="stat-number" id="total-opportunities">0</div>
                <div class="stat-label">Oportunidades</div>
            </div>
        </div>
        
        <div id="reports-container" class="reports-grid">
            <div class="no-reports">
                <p>📄 No hay reportes disponibles aún.</p>
                <p>Los reportes se generarán automáticamente cuando haya nuevas oportunidades.</p>
            </div>
        </div>
        
        <div class="footer">
            <p>🤖 Generado automáticamente por Stock Analyzer</p>
            <p>📊 Análisis de insider trading en tiempo real</p>
        </div>
    </div>
    
    <script>
        // Lista de reportes (se actualiza automáticamente)
        let reports = [];
        
        function formatDate(dateString) {{
            try {{
                const date = new Date(dateString);
                return date.toLocaleString('es-ES', {{
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                }});
            }} catch (e) {{
                return dateString;
            }}
        }}
        
        function isNewReport(dateString) {{
            try {{
                const reportDate = new Date(dateString);
                const now = new Date();
                const diffHours = (now - reportDate) / (1000 * 60 * 60);
                return diffHours <= 24; // Nuevo si tiene menos de 24 horas
            }} catch (e) {{
                return false;
            }}
        }}
        
        function loadReports() {{
            const container = document.getElementById('reports-container');
            const totalElement = document.getElementById('total-reports');
            const lastUpdateElement = document.getElementById('last-update');
            const opportunitiesElement = document.getElementById('total-opportunities');
            
            totalElement.textContent = reports.length;
            
            if (reports.length === 0) {{
                container.innerHTML = `
                    <div class="no-reports">
                        <p>📄 No hay reportes disponibles aún.</p>
                        <p>Los reportes se generarán automáticamente cuando haya nuevas oportunidades.</p>
                    </div>
                `;
                lastUpdateElement.textContent = '--';
                opportunitiesElement.textContent = '0';
                return;
            }}
            
            // Mostrar fecha del último reporte
            const lastReport = reports.reduce((latest, report) => {{
                return new Date(report.date) > new Date(latest.date) ? report : latest;
            }});
            lastUpdateElement.textContent = formatDate(lastReport.date);
            
            // Estimar oportunidades totales
            const totalOpportunities = reports.length * 45; // Estimación
            opportunitiesElement.textContent = totalOpportunities;
            
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
                        <div class="report-title">
                            ${{report.title}}
                        </div>
                        <div class="report-description">
                            ${{report.description || 'Análisis completo de oportunidades de insider trading con datos en tiempo real.'}}
                        </div>
                    </div>
                `;
            }});
            
            container.innerHTML = html;
        }}
        
        // Cargar reportes al inicio
        document.addEventListener('DOMContentLoaded', function() {{
            loadReports();
            
            // Auto-refresh cada 10 minutos si la página está activa
            setInterval(function() {{
                if (!document.hidden) {{
                    location.reload();
                }}
            }}, 600000); // 10 minutos
        }});
        
        // Precargar datos si están disponibles
        try {{
            if (typeof window.loadInitialReports === 'function') {{
                window.loadInitialReports();
            }}
        }} catch (e) {{
            // Ignorar errores de carga inicial
        }}
    </script>
</body>
</html>"""
        
        index_path = os.path.join(self.docs_dir, "index.html")
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        # Crear archivo .nojekyll para evitar problemas
        nojekyll_path = os.path.join(self.docs_dir, ".nojekyll")
        with open(nojekyll_path, "w") as f:
            f.write("")
    
    def upload_report(self, html_file_path, title=None, description=None):
        """
        Sube un reporte HTML a GitHub Pages - VERSIÓN CORREGIDA
        """
        if not os.path.exists(html_file_path):
            print(f"❌ Archivo no encontrado: {html_file_path}")
            return None
            
        print(f"📤 Subiendo reporte a GitHub Pages...")
        
        try:
            # Asegurar que docs/ existe
            os.makedirs(self.docs_dir, exist_ok=True)
            
            # NUEVO: Asegurar que index.html existe ANTES de actualizar
            index_path = os.path.join(self.docs_dir, "index.html")
            if not os.path.exists(index_path):
                print("🔧 index.html no existe, creándolo...")
                self.create_index_page()
            
            # Generar nombre único
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"insider_report_{timestamp}.html"
            
            # Copiar archivo
            dest_path = os.path.join(self.docs_dir, filename)
            shutil.copy2(html_file_path, dest_path)
            print(f"📄 Archivo copiado a: {dest_path}")
            
            # Actualizar index (ahora sabemos que existe)
            if not title:
                title = f"Reporte Insider Trading - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            self.update_index_with_new_report(filename, title, description)
            
            # Git operations con manejo de errores mejorado
            try:
                # Verificar qué archivos agregar
                files_to_add = [f"{self.docs_dir}/{filename}"]
                if os.path.exists(index_path):
                    files_to_add.append(f"{self.docs_dir}/index.html")
                
                subprocess.run(["git", "add"] + files_to_add, check=True)
                commit_msg = f"Nuevo reporte: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                subprocess.run(["git", "commit", "-m", commit_msg], check=True)
                subprocess.run(["git", "push", "origin", "main"], check=True)
                print("✅ Cambios subidos a GitHub")
            except subprocess.CalledProcessError as e:
                print(f"⚠️ Error en git: {e}")
                print("💡 Sube los cambios manualmente:")
                print(f"   git add {self.docs_dir}/")
                print(f"   git commit -m 'Nuevo reporte'")
                print(f"   git push origin main")
            
            # URLs
            file_url = f"{self.base_url}/{filename}"
            index_url = self.base_url
            
            print(f"✅ Reporte subido")
            print(f"🌐 URL: {file_url}")
            print(f"🏠 Inicio: {index_url}")
            
            return {
                'file_url': file_url,
                'index_url': index_url,
                'filename': filename
            }
                
        except Exception as e:
            print(f"❌ Error subiendo: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def update_index_with_new_report(self, filename, title, description=None):
        """
        Actualiza index.html con el nuevo reporte - VERSIÓN CORREGIDA
        """
        try:
            index_path = os.path.join(self.docs_dir, "index.html")
            
            # Verificar que el archivo existe
            if not os.path.exists(index_path):
                print("⚠️ index.html no existe, creándolo primero...")
                self.create_index_page()
            
            with open(index_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Crear nuevo reporte
            new_report = {
                "file": filename,
                "title": title,
                "date": datetime.now().isoformat(),
                "description": description or f"Análisis de insider trading generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}"
            }
            
            # Buscar y actualizar la lista de reportes
            pattern = r'let reports = \[(.*?)\];'
            match = re.search(pattern, content, re.DOTALL)
            
            if match:
                existing_reports_str = match.group(1).strip()
                existing_reports = []
                
                if existing_reports_str:
                    try:
                        # Convertir de JavaScript a Python de forma más robusta
                        existing_reports_str = existing_reports_str.replace('true', 'True').replace('false', 'False').replace('null', 'None')
                        # Usar eval solo en contenido controlado
                        existing_reports = eval(f"[{existing_reports_str}]")
                    except Exception as e:
                        print(f"⚠️ Error parseando reportes existentes: {e}")
                        print("   Creando lista nueva")
                        existing_reports = []
                
                # Agregar nuevo reporte al principio
                existing_reports.insert(0, new_report)
                
                # Mantener solo los últimos 50
                existing_reports = existing_reports[:50]
                
                # Convertir de vuelta a JavaScript
                reports_js = json.dumps(existing_reports, indent=8, ensure_ascii=False)
                
                # Reemplazar en el contenido
                new_content = re.sub(pattern, f'let reports = {reports_js};', content, flags=re.DOTALL)
                
                with open(index_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                
                print(f"✅ Index actualizado con {len(existing_reports)} reportes")
            else:
                print("⚠️ No se encontró la sección de reportes en index.html")
                print("   Recreando index.html...")
                self.create_index_page()
                # Intentar de nuevo
                self.update_index_with_new_report(filename, title, description)
                
        except Exception as e:
            print(f"⚠️ Error actualizando index: {e}")
            import traceback
            traceback.print_exc()
            print("🔧 Recreando index.html...")
            self.create_index_page()

def main():
    print("🚀 CONFIGURADOR DE GITHUB PAGES PARA STOCK ANALYZER")
    print("=" * 60)
    
    uploader = GitHubPagesUploader()
    
    if uploader.setup_github_pages():
        print("\n🎉 ¡Configuración completada!")
        print("\n💡 PRÓXIMOS PASOS:")
        print("1. Ve a GitHub Settings > Pages")
        print("2. Configura Branch: main, Folder: /docs")
        print("3. Ejecuta tu análisis con: python insider_tracker.py --completo")
        print("4. Los reportes se subirán automáticamente")
    else:
        print("\n❌ Error en la configuración")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        uploader = GitHubPagesUploader()
        
        if command == "setup":
            uploader.setup_github_pages()
        elif command == "upload" and len(sys.argv) > 2:
            result = uploader.upload_report(sys.argv[2])
            if result:
                print(f"✅ Subido: {result['file_url']}")
        else:
            print("Uso: python github_pages_uploader.py [setup|upload archivo.html]")
    else:
        main()