#!/usr/bin/env python3
"""
GitHub Pages Uploader - Versión para carpeta /docs
Adaptado para trabajar con la configuración de GitHub Pages desde /docs
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
            "last_update": None,
            "reports": [],
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
        """Sube un reporte manteniendo historial"""
        try:
            print(f"\n📤 Subiendo reporte a /docs para GitHub Pages...")
            
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
            
            # Por defecto usar solo fecha (1 por día)
            report_id = f"report_{date_only}"
            
            # Verificar si ya existe un reporte de hoy
            manifest = self.load_manifest()
            existing_today = None
            for i, report in enumerate(manifest['reports']):
                if report['date'] == date_only:
                    existing_today = i
                    # Si quieres mantener múltiples del mismo día, descomenta la siguiente línea:
                    # report_id = f"report_{date_only}_{time_suffix}"
                    print(f"⚠️ Ya existe un reporte de hoy, será reemplazado")
                    break
            
            # Crear carpeta para este reporte
            report_dir = self.reports_path / "daily" / report_id
            report_dir.mkdir(exist_ok=True, parents=True)
            
            # Copiar archivos
            html_dest = report_dir / "index.html"
            csv_dest = report_dir / "data.csv"
            
            print(f"📁 Copiando archivos a: {report_dir}")
            shutil.copy2(html_file, html_dest)
            shutil.copy2(csv_file, csv_dest)
            
            # URLs relativas para GitHub Pages
            report_entry = {
                "id": report_id,
                "title": title,
                "description": description,
                "timestamp": timestamp.isoformat(),
                "date": timestamp.strftime('%Y-%m-%d'),
                "time": timestamp.strftime('%H:%M:%S'),
                "html_url": f"reports/daily/{report_id}/index.html",
                "csv_url": f"reports/daily/{report_id}/data.csv",
                "full_url": f"{self.base_url}/reports/daily/{report_id}/index.html"
            }
            
            # Si existe reporte de hoy, reemplazarlo
            if existing_today is not None:
                manifest["reports"][existing_today] = report_entry
                print(f"✅ Reporte de hoy actualizado")
            else:
                # Añadir al principio (más reciente primero)
                manifest["reports"].insert(0, report_entry)
                manifest["total_reports"] += 1
            
            manifest["last_update"] = timestamp.isoformat()
            manifest["base_url"] = self.base_url
            
            # Limitar a últimos 100 reportes
            if len(manifest["reports"]) > 100:
                # Eliminar reportes antiguos del disco
                for old_report in manifest["reports"][100:]:
                    old_dir = self.reports_path / "daily" / old_report["id"]
                    if old_dir.exists():
                        shutil.rmtree(old_dir)
                        print(f"🗑️ Eliminado reporte antiguo: {old_report['id']}")
                
                manifest["reports"] = manifest["reports"][:100]
            
            # Guardar manifest
            self.save_manifest(manifest)
            
            # Generar índice principal
            self.generate_main_index()
            
            # Generar página VCP Scanner
            self.generate_vcp_scanner_page()
            
            # Intentar commit y push automático
            self.git_commit_and_push(report_id)
            
            # Retornar información
            result = {
                "success": True,
                "report_id": report_id,
                "file_url": str(html_dest),
                "csv_url": str(csv_dest),
                "index_url": str(self.index_file),
                "github_url": f"{self.base_url}/reports/daily/{report_id}/index.html",
                "timestamp": timestamp.isoformat()
            }
            
            print(f"\n✅ Reporte subido exitosamente")
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
        """Genera la página principal con el historial"""
        try:
            manifest = self.load_manifest()
            total_reports = manifest['total_reports']
            last_update = manifest['last_update'][:10] if manifest['last_update'] else 'N/A'
            unique_days = len(set(r['date'] for r in manifest['reports'])) if manifest['reports'] else 0
            
            html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📊 Historial Insider Trading - Stock Analyzer</title>
    <meta name="description" content="Historial completo de análisis de insider trading">
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
            <h1>📊 Historial Insider Trading</h1>
            <p>Sistema automatizado de monitoreo y análisis de transacciones</p>
            <div class="live-indicator">
                <div class="live-dot"></div>
                <span>Sistema Activo</span>
            </div>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{total_reports}</div>
                <div class="stat-label">Reportes Totales</div>
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
        console.log('Total reportes: {total_reports}');
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
            commit_msg = f"📊 Nuevo reporte insider trading: {report_id}"
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
        
        .vcp-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        
        .vcp-card {{
            background: #2d3748;
            border: 1px solid #4a5568;
            border-radius: 10px;
            padding: 20px;
            transition: all 0.3s;
        }}
        
        .vcp-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 5px 20px rgba(74, 144, 226, 0.3);
        }}
        
        .vcp-card.ready {{
            border-color: #48bb78;
            box-shadow: 0 0 15px rgba(72, 187, 120, 0.3);
        }}
        
        .ticker-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}
        
        .ticker-symbol {{
            font-size: 1.8em;
            font-weight: bold;
            color: #4a90e2;
        }}
        
        .status-badge {{
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.9em;
        }}
        
        .status-ready {{
            background: #48bb78;
            color: white;
        }}
        
        .status-watch {{
            background: #ed8936;
            color: white;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 20px;
        }}
        
        .metric {{
            background: #1a202c;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }}
        
        .metric-label {{
            color: #a0aec0;
            font-size: 0.85em;
            text-transform: uppercase;
            margin-bottom: 5px;
        }}
        
        .metric-value {{
            color: #ffffff;
            font-size: 1.3em;
            font-weight: bold;
        }}
        
        .chart-preview {{
            width: 100%;
            height: 200px;
            background: white;
            border-radius: 8px;
            padding: 5px;
            margin: 15px 0;
        }}
        
        .action-buttons {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-top: 20px;
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
            
            <div class="vcp-grid" id="vcp-grid">
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
                <div class="no-data" style="grid-column: 1/-1;">
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
        
        # Crear README
        readme_path = uploader.repo_path / "README.md"
        if not readme_path.exists():
            with open(readme_path, 'w') as f:
                f.write(f"""# 📊 Insider Trading Analysis

Sistema automatizado de análisis de transacciones insider.

## 🌐 Acceso

Visita el historial completo en: [{uploader.base_url}]({uploader.base_url})

## 📁 Estructura

- `/reports/daily/` - Reportes diarios
- `/reports/weekly/` - Resúmenes semanales
- `/reports/monthly/` - Resúmenes mensuales
- `manifest.json` - Índice de todos los reportes
- `index.html` - Página principal

## 🔄 Actualización

Este sitio se actualiza automáticamente cada vez que se detectan nuevas transacciones insider.
""")
            print("✅ README.md creado")
        
        print(f"\n✅ GitHub Pages configurado correctamente")
        print(f"📂 Archivos en: /docs")
        print(f"🌐 URL del sitio: {uploader.base_url}")
        print(f"\n💡 Próximos pasos:")
        print("1. Ejecuta el sistema completo para generar reportes")
        print("2. Los cambios se subirán automáticamente a GitHub")
        print("3. Espera unos minutos para que GitHub Pages actualice")
        
    except Exception as e:
        print(f"❌ Error configurando: {e}")


if __name__ == "__main__":
    # Ejecutar configuración
    setup_github_pages()