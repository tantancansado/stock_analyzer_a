#!/usr/bin/env python3
"""
Sistema de Historial en GitHub Pages - Mantiene reportes históricos organizados online
"""

import os
import shutil
import json
import subprocess
from datetime import datetime, timedelta
import re

class GitHubPagesHistorico:
    def __init__(self):
        self.docs_dir = "docs"
        self.historical_dir = "docs/historical"
        self.daily_dir = "docs/historical/daily"
        self.repo_name = "stock_analyzer_a"
        self.username = "tantancansado"
        self.base_url = f"https://{self.username}.github.io/{self.repo_name}"
        
        # Crear directorios si no existen
        os.makedirs(self.daily_dir, exist_ok=True)
    
    def organizar_reporte_diario_github(self):
        """
        Organiza el reporte del día en GitHub Pages con estructura histórica
        """
        fecha_hoy = datetime.now().strftime('%Y-%m-%d')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        
        print(f"📁 Organizando reporte del {fecha_hoy} en GitHub Pages...")
        
        # Buscar el reporte más reciente en docs/
        reportes_recientes = []
        if os.path.exists(self.docs_dir):
            for archivo in os.listdir(self.docs_dir):
                if archivo.startswith('insider_report_') and archivo.endswith('.html'):
                    archivo_path = os.path.join(self.docs_dir, archivo)
                    mtime = os.path.getmtime(archivo_path)
                    reportes_recientes.append((archivo, mtime, archivo_path))
        
        if not reportes_recientes:
            print("❌ No se encontraron reportes recientes en docs/")
            return None
        
        # Ordenar por fecha de modificación (más reciente primero)
        reportes_recientes.sort(key=lambda x: x[1], reverse=True)
        reporte_mas_reciente = reportes_recientes[0]
        
        print(f"📄 Reporte más reciente: {reporte_mas_reciente[0]}")
        
        # Crear directorio para el día
        day_dir = os.path.join(self.daily_dir, fecha_hoy)
        os.makedirs(day_dir, exist_ok=True)
        
        # Nuevo nombre para el archivo histórico
        nombre_historico = f"insider_report_{fecha_hoy}_{timestamp}.html"
        destino_historico = os.path.join(day_dir, nombre_historico)
        
        # Copiar el reporte al histórico
        try:
            shutil.copy2(reporte_mas_reciente[2], destino_historico)
            print(f"✅ Copiado a histórico: {destino_historico}")
            
            # Crear metadata del día
            metadata = {
                'fecha': fecha_hoy,
                'timestamp': timestamp,
                'archivo_original': reporte_mas_reciente[0],
                'archivo_historico': nombre_historico,
                'url_historico': f"{self.base_url}/historical/daily/{fecha_hoy}/{nombre_historico}",
                'size': os.path.getsize(destino_historico),
                'creado': datetime.now().isoformat()
            }
            
            # Guardar metadata
            metadata_path = os.path.join(day_dir, f"metadata_{fecha_hoy}.json")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            return metadata
            
        except Exception as e:
            print(f"❌ Error copiando reporte: {e}")
            return None
    
    def actualizar_index_historico(self):
        """
        Actualiza el index.html principal con enlaces al histórico
        """
        print("🔄 Actualizando index.html con histórico...")
        
        index_path = os.path.join(self.docs_dir, "index.html")
        
        if not os.path.exists(index_path):
            print("❌ index.html no existe")
            return False
        
        try:
            # Leer index actual
            with open(index_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Recopilar reportes históricos
            reportes_historicos = self.obtener_reportes_historicos()
            
            # Buscar la sección de reportes en el JavaScript
            pattern = r'let reports = \[(.*?)\];'
            match = re.search(pattern, content, re.DOTALL)
            
            if match:
                # Agregar reportes históricos a la lista existente
                reportes_js = []
                
                # Procesar reportes históricos
                for reporte in reportes_historicos:
                    reporte_js = {
                        "file": reporte['url_relativa'],
                        "title": f"📊 {reporte['titulo']} - {reporte['fecha']}",
                        "date": reporte['fecha_iso'],
                        "description": reporte['descripcion'],
                        "historical": True,
                        "daily_archive": True
                    }
                    reportes_js.append(reporte_js)
                
                # Convertir a JavaScript
                if reportes_js:
                    reportes_json = json.dumps(reportes_js, indent=8, ensure_ascii=False)
                    
                    # Reemplazar en el contenido
                    new_content = re.sub(pattern, f'let reports = {reportes_json};', content, flags=re.DOTALL)
                    
                    # Escribir archivo actualizado
                    with open(index_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    
                    print(f"✅ Index actualizado con {len(reportes_js)} reportes históricos")
                    return True
                else:
                    print("⚠️ No hay reportes históricos para agregar")
                    return True
            else:
                print("⚠️ No se encontró la sección de reportes en index.html")
                return False
                
        except Exception as e:
            print(f"❌ Error actualizando index: {e}")
            return False
    
    def obtener_reportes_historicos(self):
        """
        Obtiene la lista de reportes históricos disponibles
        """
        reportes = []
        
        if not os.path.exists(self.daily_dir):
            return reportes
        
        # Buscar por cada día
        for dia_dir in sorted(os.listdir(self.daily_dir), reverse=True):
            dia_path = os.path.join(self.daily_dir, dia_dir)
            
            if os.path.isdir(dia_path):
                # Buscar archivos HTML en el día
                for archivo in os.listdir(dia_path):
                    if archivo.endswith('.html') and archivo.startswith('insider_report_'):
                        archivo_path = os.path.join(dia_path, archivo)
                        
                        try:
                            # Parsear fecha del nombre del directorio
                            fecha_dt = datetime.strptime(dia_dir, '%Y-%m-%d')
                            
                            reporte = {
                                'fecha': dia_dir,
                                'fecha_iso': fecha_dt.isoformat(),
                                'archivo': archivo,
                                'url_relativa': f"historical/daily/{dia_dir}/{archivo}",
                                'url_completa': f"{self.base_url}/historical/daily/{dia_dir}/{archivo}",
                                'titulo': f"Reporte Diario",
                                'descripcion': f"Análisis de insider trading del {fecha_dt.strftime('%d/%m/%Y')}",
                                'size': os.path.getsize(archivo_path)
                            }
                            
                            reportes.append(reporte)
                            
                        except ValueError:
                            continue
        
        return reportes[:30]  # Últimos 30 días
    
    def crear_index_historico_dedicado(self):
        """
        Crea una página dedicada para navegar el histórico
        """
        print("🌐 Creando página de histórico dedicada...")
        
        reportes_historicos = self.obtener_reportes_historicos()
        
        if not reportes_historicos:
            print("⚠️ No hay reportes históricos para mostrar")
            return None
        
        # Agrupar por mes
        reportes_por_mes = {}
        for reporte in reportes_historicos:
            fecha_dt = datetime.fromisoformat(reporte['fecha_iso'])
            mes_clave = fecha_dt.strftime('%Y-%m')
            mes_nombre = fecha_dt.strftime('%B %Y')
            
            if mes_clave not in reportes_por_mes:
                reportes_por_mes[mes_clave] = {
                    'nombre': mes_nombre,
                    'reportes': []
                }
            
            reportes_por_mes[mes_clave]['reportes'].append(reporte)
        
        # Crear HTML
        html_content = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>📚 Histórico de Reportes - Insider Trading</title>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    color: #333;
                    padding: 20px;
                }}
                
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 15px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                    overflow: hidden;
                }}
                
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 40px;
                    text-align: center;
                }}
                
                .header h1 {{
                    font-size: 2.5em;
                    margin-bottom: 10px;
                }}
                
                .header p {{
                    font-size: 1.2em;
                    opacity: 0.9;
                }}
                
                .stats {{
                    display: flex;
                    justify-content: center;
                    gap: 40px;
                    margin: 20px 0;
                    flex-wrap: wrap;
                }}
                
                .stat {{
                    text-align: center;
                }}
                
                .stat-number {{
                    font-size: 2em;
                    font-weight: bold;
                    color: white;
                }}
                
                .stat-label {{
                    color: rgba(255,255,255,0.8);
                    font-size: 0.9em;
                }}
                
                .content {{
                    padding: 40px;
                }}
                
                .month-section {{
                    margin-bottom: 40px;
                }}
                
                .month-header {{
                    background: #ecf0f1;
                    padding: 15px 20px;
                    border-radius: 10px;
                    margin-bottom: 20px;
                    border-left: 5px solid #3498db;
                }}
                
                .month-title {{
                    font-size: 1.3em;
                    font-weight: bold;
                    color: #2c3e50;
                }}
                
                .reports-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                    gap: 20px;
                }}
                
                .report-card {{
                    background: #f8f9fa;
                    border-radius: 10px;
                    padding: 20px;
                    border-left: 4px solid #3498db;
                    transition: transform 0.3s ease, box-shadow 0.3s ease;
                    cursor: pointer;
                }}
                
                .report-card:hover {{
                    transform: translateY(-5px);
                    box-shadow: 0 10px 25px rgba(0,0,0,0.15);
                }}
                
                .report-date {{
                    font-weight: bold;
                    color: #2c3e50;
                    font-size: 1.1em;
                    margin-bottom: 8px;
                }}
                
                .report-description {{
                    color: #7f8c8d;
                    margin-bottom: 15px;
                    line-height: 1.4;
                }}
                
                .report-meta {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    font-size: 0.9em;
                    color: #95a5a6;
                }}
                
                .report-size {{
                    background: #e8f5e8;
                    padding: 3px 8px;
                    border-radius: 12px;
                    color: #27ae60;
                }}
                
                .navigation {{
                    text-align: center;
                    margin: 30px 0;
                }}
                
                .nav-button {{
                    display: inline-block;
                    background: #3498db;
                    color: white;
                    padding: 12px 25px;
                    border-radius: 25px;
                    text-decoration: none;
                    margin: 0 10px;
                    transition: background 0.3s ease;
                }}
                
                .nav-button:hover {{
                    background: #2980b9;
                }}
                
                @media (max-width: 768px) {{
                    .header h1 {{ font-size: 2em; }}
                    .stats {{ gap: 20px; }}
                    .reports-grid {{ grid-template-columns: 1fr; }}
                    .content {{ padding: 20px; }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📚 Histórico de Reportes</h1>
                    <p>Archivo completo de análisis de insider trading</p>
                    
                    <div class="stats">
                        <div class="stat">
                            <div class="stat-number">{len(reportes_historicos)}</div>
                            <div class="stat-label">Reportes Totales</div>
                        </div>
                        <div class="stat">
                            <div class="stat-number">{len(reportes_por_mes)}</div>
                            <div class="stat-label">Meses Cubiertos</div>
                        </div>
                        <div class="stat">
                            <div class="stat-number">{datetime.now().strftime('%Y')}</div>
                            <div class="stat-label">Año Actual</div>
                        </div>
                    </div>
                </div>
                
                <div class="content">
                    <div class="navigation">
                        <a href="index.html" class="nav-button">🏠 Inicio</a>
                        <a href="#" onclick="window.history.back()" class="nav-button">⬅️ Volver</a>
                    </div>
        """
        
        # Agregar secciones por mes
        for mes_clave in sorted(reportes_por_mes.keys(), reverse=True):
            mes_data = reportes_por_mes[mes_clave]
            
            html_content += f"""
                    <div class="month-section">
                        <div class="month-header">
                            <div class="month-title">📅 {mes_data['nombre']} ({len(mes_data['reportes'])} reportes)</div>
                        </div>
                        
                        <div class="reports-grid">
            """
            
            for reporte in mes_data['reportes']:
                fecha_formatted = datetime.fromisoformat(reporte['fecha_iso']).strftime('%d/%m/%Y')
                size_kb = reporte['size'] // 1024
                
                html_content += f"""
                            <div class="report-card" onclick="window.open('{reporte['url_relativa']}', '_blank')">
                                <div class="report-date">📊 {fecha_formatted}</div>
                                <div class="report-description">{reporte['descripcion']}</div>
                                <div class="report-meta">
                                    <span>📄 Reporte Completo</span>
                                    <span class="report-size">{size_kb} KB</span>
                                </div>
                            </div>
                """
            
            html_content += """
                        </div>
                    </div>
            """
        
        html_content += f"""
                </div>
            </div>
            
            <script>
                document.addEventListener('DOMContentLoaded', function() {{
                    console.log('📚 Histórico cargado: {len(reportes_historicos)} reportes');
                }});
            </script>
        </body>
        </html>
        """
        
        # Guardar archivo
        historico_path = os.path.join(self.docs_dir, "historico.html")
        with open(historico_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ Página de histórico creada: {historico_path}")
        print(f"🌐 URL: {self.base_url}/historico.html")
        
        return historico_path
    
    def limpiar_archivos_antiguos_github(self, dias_mantener=60):
        """
        Limpia archivos históricos antiguos en GitHub Pages
        """
        print(f"🧹 Limpiando archivos históricos anteriores a {dias_mantener} días...")
        
        fecha_limite = datetime.now() - timedelta(days=dias_mantener)
        archivos_eliminados = 0
        
        if not os.path.exists(self.daily_dir):
            print("ℹ️ No hay directorio histórico para limpiar")
            return 0
        
        for dia_dir in os.listdir(self.daily_dir):
            dia_path = os.path.join(self.daily_dir, dia_dir)
            
            if os.path.isdir(dia_path):
                try:
                    fecha_dir = datetime.strptime(dia_dir, '%Y-%m-%d')
                    if fecha_dir < fecha_limite:
                        shutil.rmtree(dia_path)
                        archivos_eliminados += 1
                        print(f"🗑️ Eliminado: {dia_dir}")
                except ValueError:
                    continue
        
        print(f"✅ Limpieza GitHub Pages completada: {archivos_eliminados} días eliminados")
        return archivos_eliminados
    
    def commit_y_push_cambios(self, mensaje="Actualización histórico automática"):
        """
        Hace commit y push de los cambios en GitHub Pages
        """
        print("📤 Subiendo cambios a GitHub Pages...")
        
        try:
            # Añadir todos los archivos nuevos/modificados en docs/
            subprocess.run(['git', 'add', 'docs/'], check=True, capture_output=True)
            
            # Hacer commit
            commit_message = f"{mensaje} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            subprocess.run(['git', 'commit', '-m', commit_message], check=True, capture_output=True)
            
            # Push
            result = subprocess.run(['git', 'push', 'origin', 'main'], check=True, capture_output=True, text=True)
            
            print("✅ Cambios subidos a GitHub Pages correctamente")
            print(f"📝 Commit: {commit_message}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            if "nothing to commit" in str(e.stderr) or "nothing to commit" in str(e.stdout):
                print("ℹ️ No hay cambios para subir")
                return True
            else:
                print(f"❌ Error subiendo cambios: {e}")
                print(f"   stdout: {e.stdout}")
                print(f"   stderr: {e.stderr}")
                return False
        except Exception as e:
            print(f"❌ Error general: {e}")
            return False
    
    def proceso_completo_diario(self):
        """
        Ejecuta el proceso completo diario: organizar + actualizar + subir
        """
        print("🔄 PROCESO COMPLETO HISTÓRICO GITHUB PAGES")
        print("=" * 50)
        
        # 1. Organizar reporte del día
        metadata = self.organizar_reporte_diario_github()
        if not metadata:
            print("❌ No se pudo organizar el reporte diario")
            return False
        
        # 2. Actualizar index principal
        if not self.actualizar_index_historico():
            print("⚠️ Error actualizando index principal")
        
        # 3. Crear/actualizar página de histórico
        if not self.crear_index_historico_dedicado():
            print("⚠️ Error creando página de histórico")
        
        # 4. Subir cambios
        if not self.commit_y_push_cambios("Histórico diario"):
            print("❌ Error subiendo cambios")
            return False
        
        print("✅ Proceso completo finalizado exitosamente")
        print(f"🌐 Reporte del día disponible en:")
        print(f"   {metadata['url_historico']}")
        print(f"🌐 Histórico completo en:")
        print(f"   {self.base_url}/historico.html")
        
        return True

def main():
    """
    Función principal
    """
    import sys
    
    github_historico = GitHubPagesHistorico()
    
    if len(sys.argv) > 1:
        comando = sys.argv[1]
        
        if comando == "--organizar":
            metadata = github_historico.organizar_reporte_diario_github()
            if metadata:
                print(f"✅ Reporte organizado: {metadata['url_historico']}")
            
        elif comando == "--actualizar-index":
            github_historico.actualizar_index_historico()
            
        elif comando == "--crear-historico":
            github_historico.crear_index_historico_dedicado()
            
        elif comando == "--subir":
            github_historico.commit_y_push_cambios()
            
        elif comando == "--limpiar":
            dias = int(sys.argv[2]) if len(sys.argv) > 2 else 60
            github_historico.limpiar_archivos_antiguos_github(dias)
            
        elif comando == "--completo":
            github_historico.proceso_completo_diario()
            
        elif comando == "--help":
            print("""
🌐 SISTEMA DE HISTÓRICO GITHUB PAGES

Uso: python github_pages_historico.py [comando]

Comandos:
  --organizar         Organizar reporte del día en estructura histórica
  --actualizar-index  Actualizar index.html con histórico
  --crear-historico   Crear página dedicada de histórico
  --subir            Subir cambios a GitHub
  --limpiar [días]   Limpiar archivos anteriores a X días (defecto: 60)
  --completo         Ejecutar proceso completo diario
  --help             Mostrar esta ayuda

Ejemplos:
  python github_pages_historico.py --completo
  python github_pages_historico.py --limpiar 90
            """)
        else:
            print(f"❌ Comando no reconocido: {comando}")
    else:
        # Por defecto: proceso completo
        github_historico.proceso_completo_diario()

if __name__ == "__main__":
    main()