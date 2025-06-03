#!/usr/bin/env python3
"""
Sistema para subir automáticamente reportes HTML a GitHub Pages
"""

import os
import subprocess
import shutil
from datetime import datetime
import json

class GitHubPagesUploader:
    def __init__(self, repo_name="insider-reports"):
        self.repo_name = repo_name
        self.local_repo_path = f"github_pages_{repo_name}"
        self.base_url = None
        
    def setup_github_repo(self):
        """
        Configura el repositorio de GitHub Pages (solo primera vez)
        """
        print("🛠️ Configurando repositorio de GitHub Pages...")
        
        try:
            # Verificar si ya existe el directorio local
            if os.path.exists(self.local_repo_path):
                print(f"✅ Repositorio local ya existe: {self.local_repo_path}")
                return True
            
            # Crear directorio local
            os.makedirs(self.local_repo_path, exist_ok=True)
            os.chdir(self.local_repo_path)
            
            # Inicializar git
            subprocess.run(["git", "init"], check=True)
            subprocess.run(["git", "checkout", "-b", "main"], check=True)
            
            # Crear archivo index.html básico
            self.create_index_page()
            
            # Configurar git
            subprocess.run(["git", "add", "."], check=True)
            subprocess.run(["git", "commit", "-m", "Initial commit for insider reports"], check=True)
            
            print(f"✅ Repositorio local configurado en: {self.local_repo_path}")
            print(f"📋 Próximos pasos:")
            print(f"1. Ve a https://github.com/new")
            print(f"2. Crea un repositorio público llamado: {self.repo_name}")
            print(f"3. NO inicialices con README")
            print(f"4. Copia la URL del repositorio")
            print(f"5. Ejecuta: git remote add origin https://github.com/TU_USUARIO/{self.repo_name}.git")
            print(f"6. Ejecuta: git push -u origin main")
            print(f"7. Ve a Settings > Pages > Source: Deploy from a branch > main")
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Error configurando repositorio: {e}")
            return False
        finally:
            # Volver al directorio original
            os.chdir("..")
    
    def create_index_page(self):
        """
        Crea una página index.html con lista de reportes
        """
        index_html = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📊 Reportes de Insider Trading</title>
    <style>
        body {
            font-family: 'Segoe UI', sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.2);
        }
        h1 {
            color: #2c3e50;
            text-align: center;
            margin-bottom: 30px;
        }
        .report-list {
            list-style: none;
            padding: 0;
        }
        .report-item {
            background: #f8f9fa;
            margin: 10px 0;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        .report-item a {
            text-decoration: none;
            color: #2c3e50;
            font-weight: bold;
        }
        .report-item a:hover {
            color: #667eea;
        }
        .date {
            color: #666;
            font-size: 0.9em;
        }
        .new-badge {
            background: #28a745;
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            margin-left: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Reportes de Insider Trading</h1>
        <div id="report-list">
            <p>🔄 Cargando reportes...</p>
        </div>
    </div>
    
    <script>
        // Esta lista se actualizará automáticamente
        const reports = [];
        
        function loadReports() {
            const container = document.getElementById('report-list');
            if (reports.length === 0) {
                container.innerHTML = '<p>📄 No hay reportes disponibles aún.</p>';
                return;
            }
            
            let html = '<ul class="report-list">';
            reports.forEach(report => {
                const isNew = (Date.now() - new Date(report.date).getTime()) < 86400000; // 24 horas
                html += `
                    <li class="report-item">
                        <a href="${report.file}" target="_blank">
                            ${report.title}
                            ${isNew ? '<span class="new-badge">NUEVO</span>' : ''}
                        </a>
                        <div class="date">${report.date}</div>
                    </li>
                `;
            });
            html += '</ul>';
            container.innerHTML = html;
        }
        
        loadReports();
    </script>
</body>
</html>"""
        
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(index_html)
    
    def upload_report(self, html_file_path, title=None):
        """
        Sube un reporte HTML a GitHub Pages
        """
        if not os.path.exists(html_file_path):
            print(f"❌ Archivo no encontrado: {html_file_path}")
            return None
            
        print(f"📤 Subiendo reporte a GitHub Pages...")
        
        try:
            # Cambiar al directorio del repositorio
            original_dir = os.getcwd()
            os.chdir(self.local_repo_path)
            
            # Generar nombre único para el archivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"reporte_{timestamp}.html"
            
            # Copiar archivo
            shutil.copy2(html_file_path, filename)
            
            # Actualizar index con el nuevo reporte
            self.update_index_with_new_report(filename, title)
            
            # Git add, commit, push
            subprocess.run(["git", "add", "."], check=True)
            commit_msg = f"Nuevo reporte: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            subprocess.run(["git", "commit", "-m", commit_msg], check=True)
            subprocess.run(["git", "push"], check=True)
            
            # Construir URL pública
            repo_url = self.get_github_pages_url()
            if repo_url:
                file_url = f"{repo_url}/{filename}"
                print(f"✅ Reporte subido exitosamente")
                print(f"🌐 URL pública: {file_url}")
                return file_url
            else:
                print("⚠️ No se pudo determinar la URL de GitHub Pages")
                return None
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Error subiendo reporte: {e}")
            return None
        finally:
            os.chdir(original_dir)
    
    def update_index_with_new_report(self, filename, title):
        """
        Actualiza el index.html con el nuevo reporte
        """
        if not title:
            title = f"Reporte {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
        # Leer index actual
        with open("index.html", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Buscar la línea de reports = [] y reemplazarla
        new_report = {
            "file": filename,
            "title": title,
            "date": datetime.now().isoformat()
        }
        
        # Simular agregado del reporte (en producción usarías JavaScript o JSON)
        reports_line = "const reports = [];"
        if reports_line in content:
            new_reports_line = f"const reports = [{json.dumps(new_report)}];"
            content = content.replace(reports_line, new_reports_line)
            
            with open("index.html", "w", encoding="utf-8") as f:
                f.write(content)
    
    def get_github_pages_url(self):
        """
        Intenta determinar la URL de GitHub Pages
        """
        try:
            # Obtener remote URL
            result = subprocess.run(["git", "remote", "get-url", "origin"], 
                                 capture_output=True, text=True, check=True)
            remote_url = result.stdout.strip()
            
            # Extraer usuario y repo
            if "github.com" in remote_url:
                # https://github.com/usuario/repo.git -> usuario/repo
                parts = remote_url.replace(".git", "").split("/")
                if len(parts) >= 2:
                    user = parts[-2]
                    repo = parts[-1]
                    return f"https://{user}.github.io/{repo}"
            
        except:
            pass
        
        return None

def integrate_with_telegram():
    """
    Integra la subida a GitHub Pages con el envío de Telegram
    """
    return """
# Agrega esta función a tu insider_tracker.py

def enviar_reporte_telegram_con_github(csv_path, html_path):
    '''
    Versión mejorada que sube HTML a GitHub Pages y envía link
    '''
    try:
        # ... código anterior de Telegram ...
        
        # NUEVO: Subir HTML a GitHub Pages
        if html_path and os.path.exists(html_path):
            from github_pages_uploader import GitHubPagesUploader
            
            uploader = GitHubPagesUploader("insider-reports")
            public_url = uploader.upload_report(html_path, 
                f"Reporte Insider Trading - {datetime.now().strftime('%Y-%m-%d')}")
            
            if public_url:
                # Agregar URL pública al mensaje
                mensaje += f"\\n\\n🌐 **Ver en navegador:** {public_url}"
                print(f"✅ HTML subido a: {public_url}")
            else:
                print("⚠️ No se pudo subir HTML a GitHub Pages")
        
        # ... resto del código de Telegram ...
        
    except Exception as e:
        print(f"❌ Error en envío con GitHub: {e}")
        # Fallback al método anterior
        return enviar_reporte_telegram_original(csv_path, html_path)
"""

def setup_instructions():
    """
    Muestra instrucciones de configuración
    """
    print("""
🛠️ INSTRUCCIONES DE CONFIGURACIÓN:

1. 📁 Ejecutar configuración inicial:
   python3 github_pages_setup.py

2. 🌐 Crear repositorio en GitHub:
   - Ve a https://github.com/new
   - Nombre: insider-reports (público)
   - NO inicializar con README

3. 🔗 Conectar repositorio local:
   cd github_pages_insider-reports
   git remote add origin https://github.com/TU_USUARIO/insider-reports.git
   git push -u origin main

4. ⚙️ Activar GitHub Pages:
   - Ve a Settings > Pages
   - Source: Deploy from a branch
   - Branch: main
   - Folder: / (root)
   - Save

5. 🔗 Tu URL será:
   https://TU_USUARIO.github.io/insider-reports

6. 📱 Integrar con Telegram:
   - Reemplazar función enviar_reporte_telegram
   - Ahora enviará link público + archivo
""")

if __name__ == "__main__":
    uploader = GitHubPagesUploader()
    
    if uploader.setup_github_repo():
        setup_instructions()
    else:
        print("❌ Error en configuración")