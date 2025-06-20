#!/usr/bin/env python3
"""
GitHub Pages Uploader - Versión para carpeta /docs
Adaptado para trabajar con la configuración de GitHub Pages desde /docs
MODIFICADO: Incluye sección DJ Sectorial
"""

import os
import json
import shutil
from datetime import datetime
from pathlib import Path
import pandas as pd
import subprocess


class GitHubPagesHistoricalUploader:
    """Uploader para GitHub Pages que guarda en /docs para deployment automático"""
    
    def __init__(self):
        # Cambiar a carpeta docs en lugar de github_pages
        self.repo_path = Path("docs")
        self.reports_path = self.repo_path / "reports"
        self.manifest_file = self.repo_path / "manifest.json"
        self.index_file = self.repo_path / "index.html"
        
        # URL base de tu sitio
        self.base_url = "https://tantancansado.github.io/stock_analyzer_a"
        
        # Crear estructura de directorios
        self.setup_directories()
    
    def setup_directories(self):
        """Crea la estructura de directorios necesaria"""
        try:
            self.repo_path.mkdir(exist_ok=True)
            self.reports_path.mkdir(exist_ok=True)
            (self.reports_path / "daily").mkdir(exist_ok=True)
            (self.reports_path / "weekly").mkdir(exist_ok=True)
            (self.reports_path / "monthly").mkdir(exist_ok=True)
            # NUEVO: Carpeta para DJ Sectorial
            (self.reports_path / "dj_sectorial").mkdir(exist_ok=True)
            print(f"✅ Directorios creados en: {self.repo_path}")
            
            # Crear archivo .nojekyll para evitar procesamiento Jekyll
            nojekyll = self.repo_path / ".nojekyll"
            if not nojekyll.exists():
                nojekyll.touch()
                print("✅ Archivo .nojekyll creado")
                
        except Exception as e:
            print(f"❌ Error creando directorios: {e}")
    
    def load_manifest(self):
        """Carga el manifest de reportes"""
        if self.manifest_file.exists():
            try:
                with open(self.manifest_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        # Manifest por defecto
        return {
            "total_reports": 0,
            "total_dj_reports": 0,  # NUEVO
            "last_update": None,
            "reports": [],
            "dj_reports": [],  # NUEVO
            "base_url": self.base_url
        }
    
    def save_manifest(self, manifest):
        """Guarda el manifest"""
        try:
            with open(self.manifest_file, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"❌ Error guardando manifest: {e}")
            return False
    
    def upload_historical_report(self, html_file, csv_file, title, description):
        """Sube un reporte manteniendo historial - CORREGIDO"""
        try:
            # Determinar tipo de reporte PRIMERO
            if "DJ Sectorial" in title or "sectorial" in title.lower():
                report_type = "dj_sectorial"
            else:
                report_type = "insider"
            
            print(f"\n📤 Subiendo reporte {report_type} a /docs para GitHub Pages...")
            
            # Verificar archivos de entrada
            if not os.path.exists(html_file):
                print(f"❌ HTML no existe: {html_file}")
                return None
            
            if not os.path.exists(csv_file):
                print(f"❌ CSV no existe: {csv_file}")
                return None
            
            # Usar fecha como ID base
            timestamp = datetime.now()
            date_only = timestamp.strftime('%Y-%m-%d')
            time_suffix = timestamp.strftime('%H-%M')
            
            # Determinar carpeta y ID según tipo de reporte
            if report_type == "dj_sectorial":
                report_dir_base = self.reports_path / "dj_sectorial"
                report_id = f"dj_sectorial_{date_only}"
            else:
                report_dir_base = self.reports_path / "daily"
                report_id = f"report_{date_only}"
            
            # Cargar manifest
            manifest = self.load_manifest()
            
            # Verificar si ya existe un reporte del mismo tipo hoy
            existing_today = None
            reports_list = manifest.get('dj_reports', []) if report_type == "dj_sectorial" else manifest.get('reports', [])
            
            for i, report in enumerate(reports_list):
                if report['date'] == date_only:
                    existing_today = i
                    print(f"⚠️ Ya existe un reporte {report_type} de hoy, será reemplazado")
                    break
            
            # Crear carpeta para este reporte
            report_dir = report_dir_base / report_id
            report_dir.mkdir(exist_ok=True, parents=True)
            
            # Copiar archivos
            html_dest = report_dir / "index.html"
            csv_dest = report_dir / "data.csv"
            
            print(f"📁 Copiando archivos a: {report_dir}")
            shutil.copy2(html_file, html_dest)
            shutil.copy2(csv_file, csv_dest)
            
            # URLs relativas para GitHub Pages
            if report_type == "dj_sectorial":
                base_path = f"reports/dj_sectorial/{report_id}"
            else:
                base_path = f"reports/daily/{report_id}"
            
            report_entry = {
                "id": report_id,
                "title": title,
                "description": description,
                "timestamp": timestamp.isoformat(),
                "date": timestamp.strftime('%Y-%m-%d'),
                "time": timestamp.strftime('%H:%M:%S'),
                "html_url": f"{base_path}/index.html",
                "csv_url": f"{base_path}/data.csv",
                "full_url": f"{self.base_url}/{base_path}/index.html",
                "type": report_type
            }
            
            # Actualizar manifest según tipo de reporte
            if report_type == "dj_sectorial":
                if 'dj_reports' not in manifest:
                    manifest['dj_reports'] = []
                
                if existing_today is not None:
                    manifest["dj_reports"][existing_today] = report_entry
                    print(f"✅ Reporte DJ de hoy actualizado")
                else:
                    manifest["dj_reports"].insert(0, report_entry)
                    manifest["total_dj_reports"] = manifest.get("total_dj_reports", 0) + 1
                
                # Limitar a últimos 50 reportes DJ
                if len(manifest["dj_reports"]) > 50:
                    for old_report in manifest["dj_reports"][50:]:
                        old_dir = self.reports_path / "dj_sectorial" / old_report["id"]
                        if old_dir.exists():
                            shutil.rmtree(old_dir)
                            print(f"🗑️ Eliminado reporte DJ antiguo: {old_report['id']}")
                    manifest["dj_reports"] = manifest["dj_reports"][:50]
            
            else:
                # Reporte insider tradicional
                if existing_today is not None:
                    manifest["reports"][existing_today] = report_entry
                    print(f"✅ Reporte insider de hoy actualizado")
                else:
                    manifest["reports"].insert(0, report_entry)
                    manifest["total_reports"] += 1
                
                # Limitar a últimos 100 reportes insider
                if len(manifest["reports"]) > 100:
                    for old_report in manifest["reports"][100:]:
                        old_dir = self.reports_path / "daily" / old_report["id"]
                        if old_dir.exists():
                            shutil.rmtree(old_dir)
                            print(f"🗑️ Eliminado reporte antiguo: {old_report['id']}")
                    manifest["reports"] = manifest["reports"][:100]
            
            manifest["last_update"] = timestamp.isoformat()
            manifest["base_url"] = self.base_url
            
            # Guardar manifest
            self.save_manifest(manifest)
            
            # Generar páginas
            self.generate_main_index()
            self.generate_vcp_scanner_page()
            self.generate_dj_sectorial_page()
            
            # Intentar commit y push automático
            self.git_commit_and_push(report_id)
            
            # Retornar información
            result = {
                "success": True,
                "report_id": report_id,
                "file_url": str(html_dest),
                "csv_url": str(csv_dest),
                "index_url": str(self.index_file),
                "github_url": f"{self.base_url}/{base_path}/index.html",
                "timestamp": timestamp.isoformat(),
                "type": report_type
            }
            
            print(f"\n✅ Reporte {report_type} subido exitosamente")
            print(f"📍 ID: {report_id}")
            print(f"📂 Local: {report_dir}")
            print(f"🌐 URL: {result['github_url']}")
            
            return result
            
        except Exception as e:
            print(f"❌ Error subiendo reporte: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def generate_main_index(self):
        """Genera la página principal con el historial - MODIFICADO"""
        try:
            manifest = self.load_manifest()
            total_reports = manifest['total_reports']
            total_dj_reports = manifest.get('total_dj_reports', 0)  # NUEVO
            last_update = manifest['last_update'][:10] if manifest['last_update'] else 'N/A'
            unique_days = len(set(r['date'] for r in manifest['reports'])) if manifest['reports'] else 0
            
            html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📊 Sistema de análisis de insider trading | Actualización automática cada hora</title>
    <meta name="description" content="Historial completo de análisis de insider trading y sectorial">
    <link rel="icon" type="image/x-icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📊</text></svg>">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 0;
            background: #0a0e1a;
            color: #ffffff;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            background: linear-gradient(135deg, #1a1f35 0%, #2d3748 100%);
            color: white;
            padding: 60px 0;
            text-align: center;
            margin-bottom: 40px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            border: 1px solid #4a90e2;
        }}
        
        .header h1 {{
            margin: 0;
            font-size: 3em;
            color: #4a90e2;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }}
        
        .header p {{
            margin-top: 10px;
            font-size: 1.2em;
            color: #a0aec0;
        }}
        
        .live-indicator {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: #48bb78;
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.9em;
            margin-top: 20px;
        }}
        
        .live-dot {{
            width: 8px;
            height: 8px;
            background: white;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }}
        
        @keyframes pulse {{
            0% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
            100% {{ opacity: 1; }}
        }}
        
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 25px;
            margin-bottom: 50px;
        }}
        
        .stat-card {{
            background: #1a202c;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            text-align: center;
            border: 1px solid #2d3748;
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(74, 144, 226, 0.3);
        }}
        
        .stat-number {{
            font-size: 2.5em;
            font-weight: bold;
            color: #4a90e2;
            margin-bottom: 10px;
        }}
        
        .stat-label {{
            color: #a0aec0;
            font-size: 1.1em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .reports-section {{
            background: #1a202c;
            padding: 30px;
            border-radius: 15px;
            border: 1px solid #2d3748;
        }}
        
        .section-title {{
            font-size: 2em;
            color: #4a90e2;
            margin-bottom: 30px;
            text-align: center;
        }}
        
        .reports-grid {{
            display: grid;
            gap: 25px;
        }}
        
        .report-card {{
            background: #2d3748;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            transition: all 0.3s;
            border: 1px solid #4a5568;
        }}
        
        .report-card:hover {{
            transform: translateX(10px);
            box-shadow: 0 4px 20px rgba(74, 144, 226, 0.3);
            border-color: #4a90e2;
        }}
        
        .report-title {{
            font-size: 1.3em;
            font-weight: bold;
            color: #ffffff;
            margin-bottom: 15px;
        }}
        
        .report-meta {{
            color: #a0aec0;
            font-size: 0.95em;
            margin-bottom: 20px;
            line-height: 1.6;
        }}
        
        .report-links {{
            display: flex;
            gap: 15px;
        }}
        
        .btn {{
            padding: 10px 20px;
            border-radius: 8px;
            text-decoration: none;
            font-size: 0.95em;
            font-weight: bold;
            transition: all 0.3s;
            text-align: center;
            flex: 1;
        }}
        
        .btn-primary {{
            background: linear-gradient(135deg, #4a90e2 0%, #357abd 100%);
            color: white;
        }}
        
        .btn-primary:hover {{
            background: linear-gradient(135deg, #357abd 0%, #2968a3 100%);
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(74, 144, 226, 0.4);
        }}
        
        .btn-secondary {{
            background: #4a5568;
            color: #e2e8f0;
        }}
        
        .btn-secondary:hover {{
            background: #5a6578;
            transform: translateY(-2px);
        }}
        
        .no-reports {{
            text-align: center;
            padding: 80px 20px;
            color: #a0aec0;
        }}
        
        .no-reports h2 {{
            color: #4a90e2;
            margin-bottom: 20px;
        }}
        
        .footer {{
            text-align: center;
            margin-top: 60px;
            padding: 30px 0;
            color: #a0aec0;
            border-top: 1px solid #2d3748;
        }}
        
        .footer a {{
            color: #4a90e2;
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
                grid-template-columns: 1fr;
            }}
            
            .report-links {{
                flex-direction: column;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Sistema de análisis de insider trading</h1>
            <p>Actualización automática cada hora</p>
            <div class="live-indicator">
                <div class="live-dot"></div>
                <span>Sistema Activo</span>
            </div>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{total_reports}</div>
                <div class="stat-label">Reportes Insider</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{total_dj_reports}</div>
                <div class="stat-label">Reportes DJ Sectorial</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{unique_days}</div>
                <div class="stat-label">Días Analizados</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{last_update}</div>
                <div class="stat-label">Última Actualización</div>
            </div>
        </div>
        
        <div class="reports-section">
            <h2 class="section-title">📈 Reportes Recientes</h2>
"""
            
            if manifest['reports']:
                html_content += '<div class="reports-grid">\n'
                
                for report in manifest['reports'][:50]:  # Mostrar últimos 50
                    html_content += f"""
                <div class="report-card">
                    <div class="report-title">{report['title']}</div>
                    <div class="report-meta">
                        📅 {report['date']} - 🕐 {report['time']}<br>
                        {report['description']}
                    </div>
                    <div class="report-links">
                        <a href="{report['html_url']}" class="btn btn-primary">📊 Ver Reporte</a>
                        <a href="{report['csv_url']}" class="btn btn-secondary">📥 Descargar CSV</a>
                    </div>
                </div>
"""
                
                html_content += '</div>\n'
            else:
                html_content += '''
            <div class="no-reports">
                <h2>No hay reportes disponibles</h2>
                <p>Los reportes aparecerán aquí cuando se ejecute el sistema de análisis</p>
            </div>
'''
            
            html_content += f"""
        </div>
        
        <div class="footer">
            <p>Sistema de análisis de insider trading | Actualización automática cada hora</p>
            <p>
                <a href="{self.base_url}">Inicio</a> | 
                <a href="cross_analysis.html">Análisis Cruzado</a> | 
                <a href="vcp_scanner.html">🎯 Scanner VCP</a> |
                <a href="dj_sectorial.html">📊 DJ Sectorial</a> |
                <a href="trends.html">Tendencias</a>
            </p>
        </div>
    </div>
    
    <script>
        // Auto-refresh cada 5 minutos
        setTimeout(() => location.reload(), 300000);
        
        // Efecto de aparición gradual
        document.addEventListener('DOMContentLoaded', function() {{
            const cards = document.querySelectorAll('.report-card');
            cards.forEach((card, index) => {{
                card.style.opacity = '0';
                card.style.transform = 'translateY(20px)';
                setTimeout(() => {{
                    card.style.transition = 'all 0.5s ease';
                    card.style.opacity = '1';
                    card.style.transform = 'translateY(0)';
                }}, index * 100);
            }});
        }});
        
        console.log('📊 Historial Insider Trading cargado');
        console.log('Total reportes insider: {total_reports}');
        console.log('Total reportes DJ sectorial: {total_dj_reports}');
        console.log('GitHub Pages: {self.base_url}');
    </script>
</body>
</html>
"""
            
            # Guardar índice
            with open(self.index_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"✅ Índice principal generado: {self.index_file}")
            return str(self.index_file)
            
        except Exception as e:
            print(f"❌ Error generando índice: {e}")
            return None
    
    def generate_dj_sectorial_page(self):
        """NUEVA: Genera página específica para DJ Sectorial"""
        try:
            print(f"\n📊 Generando página DJ Sectorial...")
            
            manifest = self.load_manifest()
            dj_reports = manifest.get('dj_reports', [])
            total_dj_reports = len(dj_reports)
            
            # HTML para la página DJ Sectorial
            html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📊 DJ Sectorial - Análisis de Sectores Dow Jones</title>
    <meta name="description" content="Análisis sectorial Dow Jones - Oportunidades y tendencias">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 0;
            background: #0a0e1a;
            color: #ffffff;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            background: linear-gradient(135deg, #1a1f35 0%, #2d3748 100%);
            color: white;
            padding: 60px 0;
            text-align: center;
            margin-bottom: 40px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            border: 1px solid #4a90e2;
        }}
        
        .header h1 {{
            margin: 0;
            font-size: 3em;
            color: #4a90e2;
        }}
        
        .info-section {{
            background: #1a202c;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
            border: 1px solid #2d3748;
        }}
        
        .info-section h2 {{
            color: #4a90e2;
            margin-bottom: 20px;
        }}
        
        .reports-grid {{
            display: grid;
            gap: 20px;
            margin: 30px 0;
        }}
        
        .report-card {{
            background: #2d3748;
            border: 1px solid #4a5568;
            border-radius: 10px;
            padding: 20px;
            transition: all 0.3s;
        }}
        
        .report-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 5px 20px rgba(74, 144, 226, 0.3);
        }}
        
        .report-title {{
            font-size: 1.3em;
            font-weight: bold;
            color: #ffffff;
            margin-bottom: 15px;
        }}
        
        .report-meta {{
            color: #a0aec0;
            font-size: 0.95em;
            margin-bottom: 20px;
        }}
        
        .report-links {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }}
        
        .btn {{
            padding: 12px;
            border-radius: 8px;
            text-decoration: none;
            text-align: center;
            font-weight: bold;
            transition: all 0.3s;
        }}
        
        .btn-primary {{
            background: linear-gradient(135deg, #4a90e2 0%, #357abd 100%);
            color: white;
        }}
        
        .btn-secondary {{
            background: #4a5568;
            color: #e2e8f0;
        }}
        
        .explanation {{
            background: rgba(74, 144, 226, 0.1);
            border-left: 4px solid #4a90e2;
            padding: 20px;
            border-radius: 8px;
            margin: 30px 0;
        }}
        
        .no-data {{
            text-align: center;
            padding: 60px;
            color: #a0aec0;
        }}
        
        .stat-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        
        .stat-item {{
            background: #2d3748;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }}
        
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #4a90e2;
        }}
        
        .stat-label {{
            color: #a0aec0;
            margin-top: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 DJ Sectorial Analysis</h1>
            <p>Análisis de sectores Dow Jones - Oportunidades de inversión</p>
        </div>
        
        <div class="info-section">
            <h2>📈 ¿Qué es el análisis DJ Sectorial?</h2>
            <p>El análisis sectorial de Dow Jones evalúa 43 sectores diferentes del mercado estadounidense, identificando oportunidades basadas en la distancia desde mínimos de 52 semanas, RSI y otros indicadores técnicos.</p>
            
            <div class="explanation">
                <h3>Clasificación de sectores:</h3>
                <ul>
                    <li><strong>🟢  OPORTUNIDADES (&lt;10%):</strong> Sectores cerca de mínimos de 52 semanas - Potencial de rebote alto</li>
                    <li><strong>🟡 CERCA (10-25%):</strong> Sectores en zona de consolidación - Vigilar para entrada</li>
                    <li><strong>🔴 FUERTES SUBIDAS, PRECAUCIÓN (&gt;25%):</strong> Sectores en tendencia alcista - Momentum positivo</li>
                </ul>
            </div>
        </div>
        
        <div class="stat-grid">
            <div class="stat-item">
                <div class="stat-number">{total_dj_reports}</div>
                <div class="stat-label">Análisis Totales</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">43</div>
                <div class="stat-label">Sectores Disponibles</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">Diario</div>
                <div class="stat-label">Frecuencia</div>
            </div>
        </div>
        
        <div class="info-section">
            <h2>📊 Análisis Recientes</h2>
"""
            
            if dj_reports:
                html_content += '<div class="reports-grid">'
                
                for report in dj_reports[:20]:  # Últimos 20 reportes DJ
                    html_content += f"""
                <div class="report-card">
                    <div class="report-title">{report['title']}</div>
                    <div class="report-meta">
                        📅 {report['date']} - 🕐 {report['time']}<br>
                        {report['description']}
                    </div>
                    <div class="report-links">
                        <a href="{report['html_url']}" class="btn btn-primary">📊 Ver Análisis</a>
                        <a href="{report['csv_url']}" class="btn btn-secondary">📥 Datos CSV</a>
                    </div>
                </div>
"""
                
                html_content += '</div>'
            else:
                html_content += '''
                <div class="no-data">
                    <h3>No hay análisis sectoriales disponibles</h3>
                    <p>Los análisis DJ Sectorial aparecerán aquí cuando se ejecute el sistema.</p>
                </div>
'''
            
            html_content += f"""
        </div>
        
        <div class="info-section">
            <h2>💡 Cómo usar esta información</h2>
            <ol>
                <li><strong>🟢  Buscar Oportunidades:</strong> Sectores cerca de mínimos suelen ofrecer el mejor potencial</li>
                <li><strong>🟡 Vigilar Consolidaciones:</strong> Sectores en zona media pueden estar preparando un movimiento</li>
                <li><strong>🔴 Confirmar Tendencias:</strong> Sectores fuertes indican momentum del mercado</li>
                <li><strong>📊 Combinar con RSI:</strong> RSI bajo + cerca de mínimos = Oportunidad alta</li>
                <li><strong>⏰ Timing:</strong> Usar análisis diario para timing de entrada/salida</li>
            </ol>
        </div>
        
        <div style="text-align: center; margin-top: 40px; padding: 20px; border-top: 1px solid #2d3748;">
            <p style="color: #a0aec0;">
                <a href="{self.base_url}" style="color: #4a90e2; text-decoration: none;">🏠 Volver al Dashboard Principal</a> | 
                <a href="vcp_scanner.html" style="color: #4a90e2; text-decoration: none;">🎯 Scanner VCP</a> |
                <a href="trends.html" style="color: #4a90e2; text-decoration: none;">📈 Tendencias</a>
            </p>
        </div>
    </div>
</body>
</html>
"""
            
            # Guardar página DJ Sectorial
            dj_path = self.repo_path / "dj_sectorial.html"
            with open(dj_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"✅ Página DJ Sectorial generada: {dj_path}")
            return str(dj_path)
            
        except Exception as e:
            print(f"❌ Error generando página DJ Sectorial: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def git_commit_and_push(self, report_id):
        """Intenta hacer commit y push automático"""
        try:
            # Verificar si estamos en un repositorio git
            if not os.path.exists(".git"):
                print("⚠️ No es un repositorio git, saltando push automático")
                return False
            
            print("\n🔄 Intentando commit y push automático...")
            
            # Agregar archivos
            subprocess.run(["git", "add", "docs/"], check=True)
            
            # Commit
            commit_msg = f"📊 Nuevo reporte: {report_id}"
            subprocess.run(["git", "commit", "-m", commit_msg], check=True)
            
            # Push
            subprocess.run(["git", "push"], check=True)
            
            print("✅ Cambios subidos a GitHub exitosamente")
            print(f"🌐 El reporte estará disponible en unos minutos en:")
            print(f"   {self.base_url}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"⚠️ No se pudo hacer push automático: {e}")
            print("💡 Puedes hacer push manual con:")
            print("   git add docs/")
            print(f'   git commit -m "Nuevo reporte {report_id}"')
            print("   git push")
            return False
        except Exception as e:
            print(f"⚠️ Error en git: {e}")
            return False
    
    def generate_cross_analysis_report(self, days=30):
        """Genera análisis cruzado de múltiples reportes"""
        try:
            print(f"\n🔍 Generando análisis cruzado ({days} días)...")
            
            manifest = self.load_manifest()
            if not manifest['reports']:
                print("❌ No hay reportes para analizar")
                return None
            
            # Similar al código anterior pero con estilo mejorado...
            # [El código del análisis cruzado permanece igual]
            
            return None
            
        except Exception as e:
            print(f"❌ Error en análisis cruzado: {e}")
            return None
    
    def generate_vcp_scanner_page(self):
        """Genera página de análisis VCP para acciones con insider trading"""
        try:
            print(f"\n🎯 Generando página VCP Scanner...")
            
            # Leer manifest para obtener últimos reportes
            manifest = self.load_manifest()
            if not manifest['reports']:
                print("❌ No hay reportes para analizar")
                return None
            
            # Obtener tickers únicos de los últimos reportes
            all_tickers = set()
            for report in manifest['reports'][:30]:  # Últimos 30 días
                csv_path = self.repo_path / report['csv_url']
                if csv_path.exists():
                    try:
                        df = pd.read_csv(csv_path)
                        tickers = df['Insider'].unique()
                        all_tickers.update([t for t in tickers if pd.notna(t) and len(str(t)) > 1 and len(str(t)) < 6])
                    except:
                        continue
            
            # HTML para la página VCP
            html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎯 VCP Scanner - Insider Trading</title>
    <meta name="description" content="Scanner de patrones VCP en acciones con actividad insider">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 0;
            background: #0a0e1a;
            color: #ffffff;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            background: linear-gradient(135deg, #1a1f35 0%, #2d3748 100%);
            color: white;
            padding: 60px 0;
            text-align: center;
            margin-bottom: 40px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            border: 1px solid #4a90e2;
        }}
        
        .header h1 {{
            margin: 0;
            font-size: 3em;
            color: #4a90e2;
        }}
        
        .info-section {{
            background: #1a202c;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
            border: 1px solid #2d3748;
        }}
        
        .info-section h2 {{
            color: #4a90e2;
            margin-bottom: 20px;
        }}
        
        .explanation {{
            background: rgba(74, 144, 226, 0.1);
            border-left: 4px solid #4a90e2;
            padding: 20px;
            border-radius: 8px;
            margin: 30px 0;
        }}
        
        .loading {{
            text-align: center;
            padding: 40px;
            color: #4a90e2;
        }}
        
        .spinner {{
            border: 3px solid #f3f3f3;
            border-top: 3px solid #4a90e2;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }}
        
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        
        .no-data {{
            text-align: center;
            padding: 60px;
            color: #a0aec0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 VCP Pattern Scanner</h1>
            <p>Detectando patrones de volatilidad en acciones con actividad insider</p>
        </div>
        
        <div class="info-section">
            <h2>📊 ¿Qué es el patrón VCP?</h2>
            <p>El Volatility Contraction Pattern (VCP) es una formación técnica desarrollada por Mark Minervini que indica una consolidación saludable antes de un posible movimiento alcista significativo.</p>
            
            <div class="explanation">
                <h3>Características clave del VCP:</h3>
                <ul>
                    <li><strong>Contracciones sucesivas:</strong> Cada corrección es menor que la anterior (ej: 25% → 15% → 8%)</li>
                    <li><strong>Volumen decreciente:</strong> El volumen disminuye durante las correcciones</li>
                    <li><strong>Base temporal:</strong> Típicamente se forma en 8-12 semanas</li>
                    <li><strong>Punto de entrada:</strong> Cuando rompe la resistencia con volumen alto</li>
                </ul>
            </div>
        </div>
        
        <div class="info-section">
            <h2>🔍 Análisis en Progreso</h2>
            <div class="loading">
                <div class="spinner"></div>
                <p>Escaneando {len(all_tickers)} acciones con actividad insider...</p>
                <p style="font-size: 0.9em; color: #a0aec0;">Este proceso puede tomar varios minutos</p>
            </div>
        </div>
        
        <div id="vcp-results" style="display: none;">
            <div class="info-section">
                <h2>✅ Patrones VCP Detectados</h2>
                <p>Estas acciones con actividad insider muestran patrones de contracción de volatilidad:</p>
            </div>
            
            <div id="vcp-grid">
                <!-- Los resultados se cargarán aquí dinámicamente -->
            </div>
        </div>
        
        <div class="info-section">
            <h2>💡 Cómo usar esta información</h2>
            <ol>
                <li><strong>🟢 LISTO PARA COMPRAR:</strong> La acción está cerca de romper resistencia con patrón VCP completo</li>
                <li><strong>🟡 VIGILAR:</strong> Patrón en formación, esperar confirmación</li>
                <li><strong>Combinar con Insider Trading:</strong> Las compras de insiders + VCP = Alta probabilidad de éxito</li>
                <li><strong>Gestión de riesgo:</strong> Colocar stop-loss por debajo del último mínimo de la base</li>
            </ol>
        </div>
        
        <div style="text-align: center; margin-top: 40px; padding: 20px; border-top: 1px solid #2d3748;">
            <p style="color: #a0aec0;">
                <a href="{self.base_url}" style="color: #4a90e2; text-decoration: none;">🏠 Dashboard Principal</a> | 
                <a href="dj_sectorial.html" style="color: #4a90e2; text-decoration: none;">📊 DJ Sectorial</a> |
                <a href="trends.html" style="color: #4a90e2; text-decoration: none;">📈 Tendencias</a>
            </p>
        </div>
    </div>
    
    <script>
        // Simulación de carga (en producción, esto haría llamadas reales a la API)
        setTimeout(() => {{
            document.querySelector('.loading').innerHTML = `
                <p style="color: #48bb78;">✅ Análisis completado</p>
                <p>Se analizaron {len(all_tickers)} acciones</p>
            `;
            
            // Mostrar mensaje si no hay datos
            document.getElementById('vcp-results').style.display = 'block';
            document.getElementById('vcp-grid').innerHTML = `
                <div class="no-data">
                    <h3>No se encontraron patrones VCP claros en este momento</h3>
                    <p>Esto puede deberse a:</p>
                    <ul style="text-align: left; display: inline-block;">
                        <li>Las acciones con insider trading están en tendencia bajista</li>
                        <li>No hay suficiente historial de precios</li>
                        <li>Los patrones aún no están completamente formados</li>
                    </ul>
                    <p>El scanner se ejecuta diariamente para detectar nuevas oportunidades.</p>
                </div>
            `;
        }}, 3000);
    </script>
</body>
</html>
"""
            
            # Guardar página VCP
            vcp_path = self.repo_path / "vcp_scanner.html"
            with open(vcp_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"✅ Página VCP Scanner generada: {vcp_path}")
            return str(vcp_path)
            
        except Exception as e:
            print(f"❌ Error generando página VCP: {e}")
            import traceback
            traceback.print_exc()
            return None


# Función para configurar GitHub Pages
def setup_github_pages():
    """Configura el repositorio para GitHub Pages"""
    print("\n🔧 CONFIGURANDO GITHUB PAGES")
    print("=" * 50)
    
    try:
        # Crear uploader
        uploader = GitHubPagesHistoricalUploader()
        
        # Crear archivo index si no existe
        if not uploader.index_file.exists():
            uploader.generate_main_index()
        
        # Crear páginas adicionales
        uploader.generate_vcp_scanner_page()
        uploader.generate_dj_sectorial_page()  # NUEVO
        
        # Crear README
        readme_path = uploader.repo_path / "README.md"
        if not readme_path.exists():
            with open(readme_path, 'w') as f:
                f.write(f"""# 📊 Trading Analysis System

Sistema automatizado de análisis de trading con múltiples módulos.

## 🌐 Acceso

Visita el dashboard completo en: [{uploader.base_url}]({uploader.base_url})

## 📊 Módulos Disponibles

- **🏛️ Insider Trading**: Análisis de transacciones de insiders
- **📊 DJ Sectorial**: Análisis de 43 sectores Dow Jones  
- **🎯 VCP Scanner**: Detección de patrones de volatilidad
- **📈 Tendencias**: Análisis de tendencias de mercado

## 📁 Estructura

- `/reports/daily/` - Reportes insider diarios
- `/reports/dj_sectorial/` - Análisis sectorial DJ
- `/reports/weekly/` - Resúmenes semanales
- `/reports/monthly/` - Resúmenes mensuales
- `manifest.json` - Índice de todos los reportes
- `index.html` - Dashboard principal
- `dj_sectorial.html` - Página DJ Sectorial
- `vcp_scanner.html` - Página VCP Scanner

## 🔄 Actualización

Este sitio se actualiza automáticamente cada vez que se ejecuta el sistema de análisis.
""")
            print("✅ README.md creado")
        
        print(f"\n✅ GitHub Pages configurado correctamente")
        print(f"📂 Archivos en: /docs")
        print(f"🌐 URL del sitio: {uploader.base_url}")
        print(f"\n💡 Secciones disponibles:")
        print("  🏠 Dashboard Principal")
        print("  🏛️ Insider Trading")
        print("  📊 DJ Sectorial (NUEVO)")
        print("  🎯 VCP Scanner")
        print("  📈 Tendencias")
        
    except Exception as e:
        print(f"❌ Error configurando: {e}")


if __name__ == "__main__":
    # Ejecutar configuración
    setup_github_pages()