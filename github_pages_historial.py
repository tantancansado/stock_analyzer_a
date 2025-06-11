#!/usr/bin/env python3
"""
GitHub Pages Uploader con Historial y Análisis de Tendencias
Mantiene todos los reportes históricos para análisis de patrones de insider trading
"""

import os
import json
import shutil
from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path
import re

class GitHubPagesHistoricalUploader:
    def __init__(self, repo_path="docs"):
        self.repo_path = repo_path
        self.reports_dir = os.path.join(repo_path, "reports")
        self.data_dir = os.path.join(repo_path, "data") 
        self.index_file = os.path.join(repo_path, "index.html")
        self.manifest_file = os.path.join(repo_path, "reports_manifest.json")
        
        # Crear estructura de directorios
        self.setup_directory_structure()
        
    def setup_directory_structure(self):
        """Crear estructura de directorios para el historial"""
        directories = [
            self.repo_path,
            self.reports_dir,
            self.data_dir,
            os.path.join(self.reports_dir, "daily"),
            os.path.join(self.reports_dir, "weekly"),
            os.path.join(self.reports_dir, "monthly"),
            os.path.join(self.data_dir, "csv"),
            os.path.join(self.data_dir, "json")
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            
        print(f"✅ Estructura de directorios creada en: {self.repo_path}")
    
    def upload_historical_report(self, html_path, csv_path=None, title=None, description=None):
        """
        Sube un reporte manteniendo el historial completo
        """
        timestamp = datetime.now()
        date_str = timestamp.strftime('%Y-%m-%d')
        time_str = timestamp.strftime('%H-%M-%S')
        
        # Generar nombres únicos para archivos
        report_filename = f"insider_report_{date_str}_{time_str}.html"
        csv_filename = f"insider_data_{date_str}_{time_str}.csv"
        
        # Rutas de destino
        report_path = os.path.join(self.reports_dir, "daily", report_filename)
        csv_dest_path = os.path.join(self.data_dir, "csv", csv_filename)
        
        try:
            # Copiar archivos
            shutil.copy2(html_path, report_path)
            print(f"✅ Reporte copiado: {report_path}")
            
            if csv_path and os.path.exists(csv_path):
                shutil.copy2(csv_path, csv_dest_path)
                print(f"✅ CSV copiado: {csv_dest_path}")
            
            # Actualizar manifest
            report_metadata = self.update_manifest(
                report_filename, csv_filename, timestamp, title, description, csv_path
            )
            
            # Regenerar índice principal
            self.generate_main_index()
            
            # Generar página de análisis de tendencias
            self.generate_trends_analysis()
            
            # Generar páginas de resumen por período
            self.generate_period_summaries()
            
            result = {
                'success': True,
                'file_url': f"reports/daily/{report_filename}",
                'csv_url': f"data/csv/{csv_filename}" if csv_path else None,
                'index_url': "index.html",
                'trends_url': "trends.html",
                'metadata': report_metadata
            }
            
            print(f"🎉 Reporte subido exitosamente al historial")
            git_push(self.repo_path, mensaje=f"Reporte insider {date_str} {time_str}")
            return result
            
        except Exception as e:
            print(f"❌ Error subiendo reporte: {e}")
            return None
    
    def update_manifest(self, report_filename, csv_filename, timestamp, title, description, csv_path):
        """
        Actualiza el manifest con metadatos del nuevo reporte
        """
        # Cargar manifest existente
        manifest = self.load_manifest()
        
        # Extraer estadísticas del CSV si está disponible
        stats = self.extract_csv_statistics(csv_path) if csv_path else {}
        
        # Crear entrada del reporte
        report_entry = {
            'id': f"{timestamp.strftime('%Y%m%d_%H%M%S')}",
            'timestamp': timestamp.isoformat(),
            'date': timestamp.strftime('%Y-%m-%d'),
            'time': timestamp.strftime('%H:%M:%S'),
            'title': title or f"Reporte Insider Trading - {timestamp.strftime('%Y-%m-%d %H:%M')}",
            'description': description or "Análisis de actividad de insider trading",
            'html_file': f"reports/daily/{report_filename}",
            'csv_file': f"data/csv/{csv_filename}" if csv_path else None,
            'statistics': stats,
            'week_number': timestamp.isocalendar()[1],
            'month': timestamp.month,
            'year': timestamp.year
        }
        
        # Agregar al manifest
        manifest['reports'].append(report_entry)
        manifest['last_updated'] = timestamp.isoformat()
        manifest['total_reports'] = len(manifest['reports'])
        
        # Guardar manifest actualizado
        with open(self.manifest_file, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Manifest actualizado: {len(manifest['reports'])} reportes totales")
        return report_entry
    
    def load_manifest(self):
        """
        Carga el manifest existente o crea uno nuevo
        """
        if os.path.exists(self.manifest_file):
            try:
                with open(self.manifest_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Error cargando manifest: {e}")
        
        # Crear manifest nuevo
        return {
            'version': '1.0',
            'created': datetime.now().isoformat(),
            'last_updated': None,
            'total_reports': 0,
            'reports': []
        }
    
    def extract_csv_statistics(self, csv_path):
        """
        Extrae estadísticas del CSV para el manifest
        """
        try:
            df = pd.read_csv(csv_path)
            
            # Verificar si es el formato de oportunidades o datos raw
            if 'Ticker' in df.columns and 'FinalScore' in df.columns:
                # Formato de oportunidades
                stats = {
                    'total_opportunities': len(df),
                    'high_confidence': len(df[df['FinalScore'] > 60]) if 'FinalScore' in df.columns else 0,
                    'medium_confidence': len(df[(df['FinalScore'] > 30) & (df['FinalScore'] <= 60)]) if 'FinalScore' in df.columns else 0,
                    'avg_score': float(df['FinalScore'].mean()) if 'FinalScore' in df.columns else 0,
                    'top_ticker': df.iloc[0]['Ticker'] if len(df) > 0 else None,
                    'unique_tickers': df['Ticker'].nunique() if 'Ticker' in df.columns else 0,
                    'data_type': 'opportunities'
                }
            elif 'Insider' in df.columns:
                # Formato de datos raw de insider
                stats = {
                    'total_transactions': len(df),
                    'unique_tickers': df['Insider'].nunique() if 'Insider' in df.columns else 0,
                    'total_value': float(df['Price'].fillna(0) * df['Qty'].fillna(0)).sum() if 'Price' in df.columns and 'Qty' in df.columns else 0,
                    'avg_price': float(df['Price'].mean()) if 'Price' in df.columns else 0,
                    'data_type': 'raw_transactions'
                }
            else:
                stats = {'data_type': 'unknown', 'total_rows': len(df)}
            
            return stats
            
        except Exception as e:
            print(f"⚠️ Error extrayendo estadísticas: {e}")
            return {'error': str(e)}
    
    def generate_main_index(self):
        """
        Genera la página principal con historial de reportes
        """
        manifest = self.load_manifest()
        reports = manifest.get('reports', [])
        
        # Ordenar reportes por fecha (más reciente primero)
        reports_sorted = sorted(reports, key=lambda x: x['timestamp'], reverse=True)
        
        html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📊 Historial de Análisis Insider Trading</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 2.5em;
        }}
        
        .stats-bar {{
            background: #ecf0f1;
            padding: 20px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            text-align: center;
        }}
        
        .stat-item {{
            background: white;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }}
        
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #2c3e50;
        }}
        
        .stat-label {{
            color: #7f8c8d;
            margin-top: 5px;
        }}
        
        .navigation {{
            background: #34495e;
            padding: 15px 30px;
            display: flex;
            justify-content: center;
            gap: 20px;
            flex-wrap: wrap;
        }}
        
        .nav-link {{
            color: white;
            text-decoration: none;
            padding: 10px 20px;
            border-radius: 25px;
            background: rgba(255,255,255,0.1);
            transition: all 0.3s ease;
        }}
        
        .nav-link:hover {{
            background: rgba(255,255,255,0.2);
            transform: translateY(-2px);
        }}
        
        .reports-section {{
            padding: 30px;
        }}
        
        .section-title {{
            color: #2c3e50;
            font-size: 1.8em;
            margin-bottom: 20px;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        
        .reports-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        
        .report-card {{
            background: white;
            border: 1px solid #ecf0f1;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
        }}
        
        .report-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        }}
        
        .report-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        
        .report-date {{
            font-weight: bold;
            color: #2c3e50;
            font-size: 1.1em;
        }}
        
        .report-time {{
            color: #7f8c8d;
            font-size: 0.9em;
        }}
        
        .report-stats {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin: 15px 0;
            font-size: 0.9em;
        }}
        
        .report-stat {{
            display: flex;
            justify-content: space-between;
        }}
        
        .report-actions {{
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }}
        
        .btn {{
            padding: 8px 16px;
            border: none;
            border-radius: 5px;
            text-decoration: none;
            font-size: 0.9em;
            font-weight: bold;
            transition: all 0.3s ease;
            cursor: pointer;
        }}
        
        .btn-primary {{
            background: #3498db;
            color: white;
        }}
        
        .btn-secondary {{
            background: #95a5a6;
            color: white;
        }}
        
        .btn:hover {{
            transform: translateY(-2px);
            opacity: 0.9;
        }}
        
        @media (max-width: 768px) {{
            .stats-bar {{
                grid-template-columns: 1fr;
            }}
            
            .reports-grid {{
                grid-template-columns: 1fr;
            }}
            
            .navigation {{
                flex-direction: column;
                align-items: center;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Análisis Histórico Insider Trading</h1>
            <p>Seguimiento completo de actividad de insiders para análisis de tendencias</p>
        </div>
        
        <div class="stats-bar">
            <div class="stat-item">
                <div class="stat-number">{manifest.get('total_reports', 0)}</div>
                <div class="stat-label">Reportes Totales</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{len([r for r in reports if datetime.fromisoformat(r['timestamp']).date() >= (datetime.now() - timedelta(days=7)).date()])}</div>
                <div class="stat-label">Últimos 7 días</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{len([r for r in reports if datetime.fromisoformat(r['timestamp']).date() >= (datetime.now() - timedelta(days=30)).date()])}</div>
                <div class="stat-label">Último mes</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{manifest.get('last_updated', 'N/A')[:10] if manifest.get('last_updated') else 'N/A'}</div>
                <div class="stat-label">Última actualización</div>
            </div>
        </div>
        
        <div class="navigation">
            <a href="trends.html" class="nav-link">📈 Análisis de Tendencias</a>
            <a href="reports/weekly/" class="nav-link">📅 Resúmenes Semanales</a>
            <a href="reports/monthly/" class="nav-link">📊 Resúmenes Mensuales</a>
            <a href="cross_analysis.html" class="nav-link">🔍 Análisis Cruzado</a>
        </div>
        
        <div class="reports-section">
            <h2 class="section-title">🔥 Reportes Recientes</h2>
            <div class="reports-grid">
"""
        
        # Mostrar últimos 20 reportes
        for report in reports_sorted[:20]:
            timestamp = datetime.fromisoformat(report['timestamp'])
            stats = report.get('statistics', {})
            
            # Determinar tipo de reporte y estadísticas
            if stats.get('data_type') == 'opportunities':
                stat_content = f"""
                    <div class="report-stat">
                        <span>Oportunidades:</span>
                        <span><strong>{stats.get('total_opportunities', 0)}</strong></span>
                    </div>
                    <div class="report-stat">
                        <span>Alta confianza:</span>
                        <span><strong>{stats.get('high_confidence', 0)}</strong></span>
                    </div>
                    <div class="report-stat">
                        <span>Score promedio:</span>
                        <span><strong>{stats.get('avg_score', 0):.1f}</strong></span>
                    </div>
                    <div class="report-stat">
                        <span>Top ticker:</span>
                        <span><strong>{stats.get('top_ticker', 'N/A')}</strong></span>
                    </div>
                """
            else:
                stat_content = f"""
                    <div class="report-stat">
                        <span>Transacciones:</span>
                        <span><strong>{stats.get('total_transactions', 0)}</strong></span>
                    </div>
                    <div class="report-stat">
                        <span>Tickers únicos:</span>
                        <span><strong>{stats.get('unique_tickers', 0)}</strong></span>
                    </div>
                    <div class="report-stat">
                        <span>Valor total:</span>
                        <span><strong>${stats.get('total_value', 0):,.0f}</strong></span>
                    </div>
                    <div class="report-stat">
                        <span>Precio prom:</span>
                        <span><strong>${stats.get('avg_price', 0):.2f}</strong></span>
                    </div>
                """
            
            html_content += f"""
                <div class="report-card">
                    <div class="report-header">
                        <div class="report-date">{timestamp.strftime('%d %b %Y')}</div>
                        <div class="report-time">{timestamp.strftime('%H:%M')}</div>
                    </div>
                    <div class="report-stats">
                        {stat_content}
                    </div>
                    <div class="report-actions">
                        <a href="{report['html_file']}" class="btn btn-primary" target="_blank">
                            📊 Ver Reporte
                        </a>
                        {f'<a href="{report["csv_file"]}" class="btn btn-secondary" download>📄 Descargar CSV</a>' if report.get('csv_file') else ''}
                    </div>
                </div>
            """
        
        html_content += """
            </div>
        </div>
    </div>
</body>
</html>"""
        
        # Guardar página principal
        with open(self.index_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ Página principal generada: {self.index_file}")
    
    def generate_trends_analysis(self):
        """
        Genera página de análisis de tendencias
        """
        manifest = self.load_manifest()
        reports = manifest.get('reports', [])
        
        if len(reports) < 2:
            print("⚠️ No hay suficientes reportes para análisis de tendencias")
            return
        
        # Analizar tendencias
        trends_data = self.analyze_trends(reports)
        
        trends_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📈 Análisis de Tendencias - Insider Trading</title>
    <style>
        body {{
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .content {{
            padding: 30px;
        }}
        
        .trends-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        
        .trend-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            border-left: 5px solid #3498db;
        }}
        
        .trend-title {{
            color: #2c3e50;
            font-size: 1.3em;
            margin-bottom: 15px;
            font-weight: bold;
        }}
        
        .ticker-trend {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid #ecf0f1;
        }}
        
        .ticker-trend:last-child {{
            border-bottom: none;
        }}
        
        .ticker-name {{
            font-weight: bold;
            color: #2c3e50;
        }}
        
        .trend-count {{
            background: #3498db;
            color: white;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.8em;
        }}
        
        .navigation {{
            background: #34495e;
            padding: 15px 30px;
            text-align: center;
        }}
        
        .nav-link {{
            color: white;
            text-decoration: none;
            margin: 0 15px;
            padding: 10px 20px;
            border-radius: 25px;
            background: rgba(255,255,255,0.1);
            transition: all 0.3s ease;
        }}
        
        .nav-link:hover {{
            background: rgba(255,255,255,0.2);
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📈 Análisis de Tendencias Insider Trading</h1>
            <p>Patrones y tendencias detectadas en la actividad de insiders</p>
        </div>
        
        <div class="navigation">
            <a href="index.html" class="nav-link">🏠 Inicio</a>
            <a href="reports/weekly/" class="nav-link">📅 Semanales</a>
            <a href="reports/monthly/" class="nav-link">📊 Mensuales</a>
            <a href="cross_analysis.html" class="nav-link">🔍 Análisis Cruzado</a>
        </div>
        
        <div class="content">
            <div class="trends-grid">
                <div class="trend-card">
                    <div class="trend-title">🔥 Tickers Más Activos (Últimos 30 días)</div>
                    {self.generate_ticker_trends_html(trends_data.get('hot_tickers', []))}
                </div>
                
                <div class="trend-card">
                    <div class="trend-title">📈 Tendencias de Actividad</div>
                    <p><strong>Total reportes analizados:</strong> {len(reports)}</p>
                    <p><strong>Período:</strong> {trends_data.get('period_start', 'N/A')} - {trends_data.get('period_end', 'N/A')}</p>
                    <p><strong>Promedio oportunidades/día:</strong> {trends_data.get('avg_opportunities_per_day', 0):.1f}</p>
                </div>
                
                <div class="trend-card">
                    <div class="trend-title">⭐ Mejores Scores Históricos</div>
                    {self.generate_top_scores_html(trends_data.get('top_scores', []))}
                </div>
                
                <div class="trend-card">
                    <div class="trend-title">📊 Estadísticas Generales</div>
                    <p><strong>Total tickers únicos:</strong> {trends_data.get('total_unique_tickers', 0)}</p>
                    <p><strong>Score promedio histórico:</strong> {trends_data.get('avg_historical_score', 0):.1f}</p>
                    <p><strong>Días con actividad:</strong> {trends_data.get('active_days', 0)}</p>
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""
        
        trends_file = os.path.join(self.repo_path, "trends.html")
        with open(trends_file, 'w', encoding='utf-8') as f:
            f.write(trends_html)
        
        print(f"✅ Análisis de tendencias generado: {trends_file}")
    
    def analyze_trends(self, reports):
        """
        Analiza tendencias en los reportes históricos
        """
        # Filtrar reportes de los últimos 30 días
        cutoff_date = datetime.now() - timedelta(days=30)
        recent_reports = [
            r for r in reports 
            if datetime.fromisoformat(r['timestamp']) >= cutoff_date
        ]
        
        # Contar apariciones de tickers
        ticker_counts = {}
        all_scores = []
        total_opportunities = 0
        
        for report in recent_reports:
            stats = report.get('statistics', {})
            if stats.get('data_type') == 'opportunities':
                # Aquí necesitaríamos cargar el CSV para obtener tickers individuales
                # Por simplicidad, usamos el top_ticker si está disponible
                top_ticker = stats.get('top_ticker')
                if top_ticker:
                    ticker_counts[top_ticker] = ticker_counts.get(top_ticker, 0) + 1
                
                if 'avg_score' in stats:
                    all_scores.append(stats['avg_score'])
                
                total_opportunities += stats.get('total_opportunities', 0)
        
        # Calcular tendencias
        hot_tickers = sorted(ticker_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'hot_tickers': hot_tickers,
            'period_start': recent_reports[-1]['date'] if recent_reports else 'N/A',
            'period_end': recent_reports[0]['date'] if recent_reports else 'N/A',
            'avg_opportunities_per_day': total_opportunities / max(len(recent_reports), 1),
            'total_unique_tickers': len(ticker_counts),
            'avg_historical_score': sum(all_scores) / max(len(all_scores), 1) if all_scores else 0,
            'active_days': len(recent_reports),
            'top_scores': []  # Se podría implementar cargando CSVs individuales
        }
    
    def generate_ticker_trends_html(self, hot_tickers):
        """
        Genera HTML para tendencias de tickers
        """
        if not hot_tickers:
            return "<p>No hay datos suficientes para mostrar tendencias</p>"
        
        html = ""
        for ticker, count in hot_tickers:
            html += f"""
                <div class="ticker-trend">
                    <span class="ticker-name">{ticker}</span>
                    <span class="trend-count">{count} apariciones</span>
                </div>
            """
        return html
    
    def generate_top_scores_html(self, top_scores):
        """
        Genera HTML para mejores scores
        """
        if not top_scores:
            return "<p>Análisis de scores históricos disponible tras múltiples reportes</p>"
        
        html = ""
        for score_data in top_scores:
            html += f"""
                <div class="ticker-trend">
                    <span class="ticker-name">{score_data.get('ticker', 'N/A')}</span>
                    <span class="trend-count">Score: {score_data.get('score', 0):.1f}</span>
                </div>
            """
        return html
    
    def generate_period_summaries(self):
        """
        Genera resúmenes por período (semanal/mensual)
        """
        manifest = self.load_manifest()
        reports = manifest.get('reports', [])
        
        # Agrupar por semana
        weekly_groups = {}
        monthly_groups = {}
        
        for report in reports:
            timestamp = datetime.fromisoformat(report['timestamp'])
            
            # Agrupación semanal
            week_key = f"{timestamp.year}-W{timestamp.isocalendar()[1]:02d}"
            if week_key not in weekly_groups:
                weekly_groups[week_key] = []
            weekly_groups[week_key].append(report)
            
            # Agrupación mensual
            month_key = f"{timestamp.year}-{timestamp.month:02d}"
            if month_key not in monthly_groups:
                monthly_groups[month_key] = []
            monthly_groups[month_key].append(report)
        
        # Generar resúmenes semanales
        self.generate_weekly_summaries(weekly_groups)
        
        # Generar resúmenes mensuales
        self.generate_monthly_summaries(monthly_groups)
    
    def generate_weekly_summaries(self, weekly_groups):
        """
        Genera resúmenes semanales
        """
        weekly_dir = os.path.join(self.reports_dir, "weekly")
        os.makedirs(weekly_dir, exist_ok=True)
        
        # Generar índice semanal
        index_html = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>📅 Resúmenes Semanales</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #f5f7fa; margin: 0; padding: 20px; }
        .container { max-width: 1000px; margin: 0 auto; background: white; border-radius: 15px; padding: 30px; }
        .header { text-align: center; margin-bottom: 30px; color: #2c3e50; }
        .week-card { background: #ecf0f1; padding: 20px; margin: 15px 0; border-radius: 10px; border-left: 5px solid #3498db; }
        .week-title { font-size: 1.3em; font-weight: bold; color: #2c3e50; margin-bottom: 10px; }
        .week-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; }
        .stat { text-align: center; background: white; padding: 10px; border-radius: 8px; }
        .stat-number { font-size: 1.5em; font-weight: bold; color: #3498db; }
        .stat-label { color: #7f8c8d; font-size: 0.9em; }
        .btn { display: inline-block; background: #3498db; color: white; padding: 8px 16px; 
               text-decoration: none; border-radius: 5px; margin-top: 10px; }
        .nav { text-align: center; margin-bottom: 20px; }
        .nav-link { color: #3498db; text-decoration: none; margin: 0 15px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📅 Resúmenes Semanales de Insider Trading</h1>
            <p>Análisis agregado por semana para identificar patrones temporales</p>
        </div>
        
        <div class="nav">
            <a href="../index.html" class="nav-link">🏠 Inicio</a>
            <a href="../trends.html" class="nav-link">📈 Tendencias</a>
            <a href="../monthly/" class="nav-link">📊 Mensuales</a>
        </div>
"""
        
        for week_key in sorted(weekly_groups.keys(), reverse=True):
            week_reports = weekly_groups[week_key]
            
            # Calcular estadísticas de la semana
            total_reports = len(week_reports)
            total_opportunities = sum(r.get('statistics', {}).get('total_opportunities', 0) for r in week_reports)
            avg_score = sum(r.get('statistics', {}).get('avg_score', 0) for r in week_reports if r.get('statistics', {}).get('avg_score')) / max(len([r for r in week_reports if r.get('statistics', {}).get('avg_score')]), 1)
            
            # Fechas de la semana
            dates = [datetime.fromisoformat(r['timestamp']).date() for r in week_reports]
            start_date = min(dates).strftime('%d %b')
            end_date = max(dates).strftime('%d %b %Y')
            
            index_html += f"""
        <div class="week-card">
            <div class="week-title">Semana {week_key} ({start_date} - {end_date})</div>
            <div class="week-stats">
                <div class="stat">
                    <div class="stat-number">{total_reports}</div>
                    <div class="stat-label">Reportes</div>
                </div>
                <div class="stat">
                    <div class="stat-number">{total_opportunities}</div>
                    <div class="stat-label">Oportunidades</div>
                </div>
                <div class="stat">
                    <div class="stat-number">{avg_score:.1f}</div>
                    <div class="stat-label">Score Promedio</div>
                </div>
                <div class="stat">
                    <div class="stat-number">{total_opportunities/max(total_reports,1):.1f}</div>
                    <div class="stat-label">Oportunidades/Reporte</div>
                </div>
            </div>
        </div>
            """
        
        index_html += """
    </div>
</body>
</html>"""
        
        with open(os.path.join(weekly_dir, "index.html"), 'w', encoding='utf-8') as f:
            f.write(index_html)
        
        print(f"✅ Resúmenes semanales generados en: {weekly_dir}")
    
    def generate_monthly_summaries(self, monthly_groups):
        """
        Genera resúmenes mensuales similares a los semanales
        """
        monthly_dir = os.path.join(self.reports_dir, "monthly")
        os.makedirs(monthly_dir, exist_ok=True)
        
        # Generar índice mensual
        index_html = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>📊 Resúmenes Mensuales</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #f5f7fa; margin: 0; padding: 20px; }
        .container { max-width: 1000px; margin: 0 auto; background: white; border-radius: 15px; padding: 30px; }
        .header { text-align: center; margin-bottom: 30px; color: #2c3e50; }
        .month-card { background: #ecf0f1; padding: 20px; margin: 15px 0; border-radius: 10px; border-left: 5px solid #e74c3c; }
        .month-title { font-size: 1.3em; font-weight: bold; color: #2c3e50; margin-bottom: 10px; }
        .month-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; }
        .stat { text-align: center; background: white; padding: 10px; border-radius: 8px; }
        .stat-number { font-size: 1.5em; font-weight: bold; color: #e74c3c; }
        .stat-label { color: #7f8c8d; font-size: 0.9em; }
        .btn { display: inline-block; background: #e74c3c; color: white; padding: 8px 16px; 
               text-decoration: none; border-radius: 5px; margin-top: 10px; }
        .nav { text-align: center; margin-bottom: 20px; }
        .nav-link { color: #e74c3c; text-decoration: none; margin: 0 15px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Resúmenes Mensuales de Insider Trading</h1>
            <p>Análisis agregado por mes para identificar tendencias a largo plazo</p>
        </div>
        
        <div class="nav">
            <a href="../index.html" class="nav-link">🏠 Inicio</a>
            <a href="../trends.html" class="nav-link">📈 Tendencias</a>
            <a href="../weekly/" class="nav-link">📅 Semanales</a>
        </div>
"""
        
        for month_key in sorted(monthly_groups.keys(), reverse=True):
            month_reports = monthly_groups[month_key]
            
            # Calcular estadísticas del mes
            total_reports = len(month_reports)
            total_opportunities = sum(r.get('statistics', {}).get('total_opportunities', 0) for r in month_reports)
            avg_score = sum(r.get('statistics', {}).get('avg_score', 0) for r in month_reports if r.get('statistics', {}).get('avg_score')) / max(len([r for r in month_reports if r.get('statistics', {}).get('avg_score')]), 1)
            
            # Nombre del mes
            year, month = month_key.split('-')
            month_names = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                          'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
            month_name = f"{month_names[int(month)]} {year}"
            
            index_html += f"""
        <div class="month-card">
            <div class="month-title">{month_name}</div>
            <div class="month-stats">
                <div class="stat">
                    <div class="stat-number">{total_reports}</div>
                    <div class="stat-label">Reportes</div>
                </div>
                <div class="stat">
                    <div class="stat-number">{total_opportunities}</div>
                    <div class="stat-label">Oportunidades</div>
                </div>
                <div class="stat">
                    <div class="stat-number">{avg_score:.1f}</div>
                    <div class="stat-label">Score Promedio</div>
                </div>
                <div class="stat">
                    <div class="stat-number">{total_opportunities/max(total_reports,1):.1f}</div>
                    <div class="stat-label">Oportunidades/Reporte</div>
                </div>
            </div>
        </div>
            """
        
        index_html += """
    </div>
</body>
</html>"""
        
        with open(os.path.join(monthly_dir, "index.html"), 'w', encoding='utf-8') as f:
            f.write(index_html)
        
        print(f"✅ Resúmenes mensuales generados en: {monthly_dir}")
    
    def get_cross_analysis_data(self, days_back=30):
        """
        NUEVA FUNCIÓN: Obtiene datos para análisis cruzado de actividad de insiders
        """
        manifest = self.load_manifest()
        reports = manifest.get('reports', [])
        
        # Filtrar reportes de los últimos N días
        cutoff_date = datetime.now() - timedelta(days=days_back)
        recent_reports = [
            r for r in reports 
            if datetime.fromisoformat(r['timestamp']) >= cutoff_date
        ]
        
        # Cargar todos los CSVs para análisis detallado
        ticker_activity = {}
        
        for report in recent_reports:
            csv_file = report.get('csv_file')
            if csv_file and os.path.exists(csv_file):
                try:
                    df = pd.read_csv(csv_file)
                    
                    # Verificar formato del CSV
                    if 'Ticker' in df.columns:
                        for _, row in df.iterrows():
                            ticker = row.get('Ticker')
                            if ticker and ticker != 'N/A':
                                if ticker not in ticker_activity:
                                    ticker_activity[ticker] = {
                                        'appearances': 0,
                                        'total_score': 0,
                                        'best_score': 0,
                                        'dates': [],
                                        'avg_score': 0,
                                        'trend': 'stable'
                                    }
                                
                                # Actualizar estadísticas
                                score = row.get('FinalScore', row.get('InsiderConfidence', 0))
                                try:
                                    score = float(score) if pd.notna(score) else 0
                                except:
                                    score = 0
                                
                                ticker_activity[ticker]['appearances'] += 1
                                ticker_activity[ticker]['total_score'] += score
                                ticker_activity[ticker]['best_score'] = max(ticker_activity[ticker]['best_score'], score)
                                ticker_activity[ticker]['dates'].append(report['date'])
                                
                except Exception as e:
                    print(f"⚠️ Error procesando CSV {csv_file}: {e}")
        
        # Calcular promedios y tendencias
        for ticker in ticker_activity:
            data = ticker_activity[ticker]
            data['avg_score'] = data['total_score'] / max(data['appearances'], 1)
            
            # Determinar tendencia (simplificada)
            if data['appearances'] >= 3:
                if data['avg_score'] > 50:
                    data['trend'] = 'bullish'
                elif data['avg_score'] < 30:
                    data['trend'] = 'bearish'
                else:
                    data['trend'] = 'neutral'
        
        return ticker_activity
    
    def generate_cross_analysis_report(self, days_back=30):
        """
        NUEVA FUNCIÓN: Genera reporte de análisis cruzado para identificar patrones
        """
        print(f"📊 Generando análisis cruzado de últimos {days_back} días...")
        
        ticker_activity = self.get_cross_analysis_data(days_back)
        
        # Filtrar tickers con actividad significativa
        significant_tickers = {
            ticker: data for ticker, data in ticker_activity.items()
            if data['appearances'] >= 2  # Al menos 2 apariciones
        }
        
        # Ordenar por relevancia (apariciones * score promedio)
        sorted_tickers = sorted(
            significant_tickers.items(),
            key=lambda x: x[1]['appearances'] * x[1]['avg_score'],
            reverse=True
        )
        
        # Generar HTML de análisis cruzado
        cross_analysis_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔍 Análisis Cruzado - Patrones de Insider Trading</title>
    <style>
        body {{
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .summary {{
            background: #ecf0f1;
            padding: 20px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }}
        
        .summary-item {{
            background: white;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }}
        
        .summary-number {{
            font-size: 2em;
            font-weight: bold;
            color: #f39c12;
        }}
        
        .content {{
            padding: 30px;
        }}
        
        .section {{
            margin: 30px 0;
        }}
        
        .section-title {{
            color: #2c3e50;
            font-size: 1.8em;
            margin-bottom: 20px;
            border-bottom: 3px solid #f39c12;
            padding-bottom: 10px;
        }}
        
        .tickers-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }}
        
        .ticker-card {{
            background: #f8f9fa;
            border: 1px solid #ecf0f1;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
        }}
        
        .ticker-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        }}
        
        .ticker-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        
        .ticker-symbol {{
            font-size: 1.5em;
            font-weight: bold;
            color: #2c3e50;
        }}
        
        .trend-badge {{
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 0.8em;
            font-weight: bold;
            text-transform: uppercase;
        }}
        
        .trend-bullish {{
            background: #27ae60;
            color: white;
        }}
        
        .trend-neutral {{
            background: #f39c12;
            color: white;
        }}
        
        .trend-bearish {{
            background: #e74c3c;
            color: white;
        }}
        
        .ticker-stats {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin: 15px 0;
            font-size: 0.9em;
        }}
        
        .ticker-stat {{
            display: flex;
            justify-content: space-between;
            padding: 5px 0;
        }}
        
        .navigation {{
            background: #34495e;
            padding: 15px 30px;
            text-align: center;
        }}
        
        .nav-link {{
            color: white;
            text-decoration: none;
            margin: 0 15px;
            padding: 10px 20px;
            border-radius: 25px;
            background: rgba(255,255,255,0.1);
            transition: all 0.3s ease;
        }}
        
        .nav-link:hover {{
            background: rgba(255,255,255,0.2);
        }}
        
        .insights {{
            background: #e8f5e8;
            border-left: 5px solid #27ae60;
            padding: 20px;
            margin: 20px 0;
            border-radius: 0 10px 10px 0;
        }}
        
        .insights h3 {{
            color: #27ae60;
            margin-top: 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 Análisis Cruzado de Patrones</h1>
            <p>Actividad recurrente de insiders - Últimos {days_back} días</p>
        </div>
        
        <div class="navigation">
            <a href="index.html" class="nav-link">🏠 Inicio</a>
            <a href="trends.html" class="nav-link">📈 Tendencias</a>
            <a href="reports/weekly/" class="nav-link">📅 Semanales</a>
            <a href="reports/monthly/" class="nav-link">📊 Mensuales</a>
        </div>
        
        <div class="summary">
            <div class="summary-item">
                <div class="summary-number">{len(significant_tickers)}</div>
                <div>Tickers con actividad recurrente</div>
            </div>
            <div class="summary-item">
                <div class="summary-number">{sum(data['appearances'] for data in significant_tickers.values())}</div>
                <div>Total apariciones</div>
            </div>
            <div class="summary-item">
                <div class="summary-number">{len([t for t, d in significant_tickers.items() if d['avg_score'] > 50])}</div>
                <div>Con alta confianza</div>
            </div>
            <div class="summary-item">
                <div class="summary-number">{days_back}</div>
                <div>Días analizados</div>
            </div>
        </div>
        
        <div class="content">
            <div class="insights">
                <h3>💡 Insights Clave</h3>
                <ul>
                    <li><strong>Actividad Recurrente:</strong> Tickers que aparecen múltiples veces pueden indicar actividad sostenida de insiders</li>
                    <li><strong>Score Alto + Frecuencia:</strong> Combinación de score alto y múltiples apariciones sugiere oportunidades sólidas</li>
                    <li><strong>Tendencias:</strong> Patrones de bullish/bearish basados en scores y frecuencia de aparición</li>
                    <li><strong>Timing:</strong> Múltiples compras de insiders en período corto pueden señalar eventos importantes</li>
                </ul>
            </div>
            
            <div class="section">
                <h2 class="section-title">🎯 Tickers con Mayor Actividad</h2>
                <div class="tickers-grid">
"""

        # Generar cards para cada ticker significativo
        for ticker, data in sorted_tickers[:20]:  # Top 20
            trend_class = f"trend-{data['trend']}"
            
            # Calcular indicador de fuerza
            strength_score = (data['appearances'] * data['avg_score']) / 100
            
            cross_analysis_html += f"""
                    <div class="ticker-card">
                        <div class="ticker-header">
                            <div class="ticker-symbol">{ticker}</div>
                            <div class="trend-badge {trend_class}">{data['trend']}</div>
                        </div>
                        
                        <div class="ticker-stats">
                            <div class="ticker-stat">
                                <span>Apariciones:</span>
                                <span><strong>{data['appearances']}</strong></span>
                            </div>
                            <div class="ticker-stat">
                                <span>Score Promedio:</span>
                                <span><strong>{data['avg_score']:.1f}</strong></span>
                            </div>
                            <div class="ticker-stat">
                                <span>Mejor Score:</span>
                                <span><strong>{data['best_score']:.1f}</strong></span>
                            </div>
                            <div class="ticker-stat">
                                <span>Fuerza:</span>
                                <span><strong>{strength_score:.1f}</strong></span>
                            </div>
                        </div>
                        
                        <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #ecf0f1;">
                            <small><strong>Fechas de actividad:</strong><br>
                            {', '.join(sorted(set(data['dates'])))}</small>
                        </div>
                    </div>
            """
        
        cross_analysis_html += """
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""
        
        # Guardar análisis cruzado
        cross_analysis_file = os.path.join(self.repo_path, "cross_analysis.html")
        with open(cross_analysis_file, 'w', encoding='utf-8') as f:
            f.write(cross_analysis_html)
        
        print(f"✅ Análisis cruzado generado: {cross_analysis_file}")
        return cross_analysis_file


# Función de utilidad para migración
def migrar_reportes_existentes(source_dir="reports", target_uploader=None):
    """
    Migra reportes existentes al nuevo sistema de historial
    """
    if not target_uploader:
        target_uploader = GitHubPagesHistoricalUploader()
    
    print("🔄 Migrando reportes existentes al sistema de historial...")
    
    # Buscar archivos HTML existentes
    html_files = []
    csv_files = []
    
    if os.path.exists(source_dir):
        for file in os.listdir(source_dir):
            if file.endswith('.html'):
                html_files.append(os.path.join(source_dir, file))
            elif file.endswith('.csv'):
                csv_files.append(os.path.join(source_dir, file))
    
    migrated_count = 0
    
    for html_file in html_files:
        # Buscar CSV correspondiente
        base_name = os.path.splitext(os.path.basename(html_file))[0]
        corresponding_csv = None
        
        for csv_file in csv_files:
            if base_name in os.path.basename(csv_file):
                corresponding_csv = csv_file
                break
        
        # Migrar
        try:
            # Obtener fecha del archivo
            file_stat = os.stat(html_file)
            file_time = datetime.fromtimestamp(file_stat.st_mtime)
            
            title = f"📊 Reporte Migrado - {file_time.strftime('%Y-%m-%d %H:%M')}"
            description = f"Reporte migrado del sistema anterior - {base_name}"
            
            result = target_uploader.upload_historical_report(
                html_file, corresponding_csv, title, description
            )
            
            if result:
                migrated_count += 1
                print(f"✅ Migrado: {os.path.basename(html_file)}")
            else:
                print(f"⚠️ Error migrando: {os.path.basename(html_file)}")
                
        except Exception as e:
            print(f"❌ Error migrando {html_file}: {e}")
    
    print(f"🎉 Migración completada: {migrated_count} reportes migrados")
    return migrated_count


import subprocess

def git_push(repo_path, mensaje="Actualización automática de informes"):
    try:
        subprocess.run(["git", "-C", repo_path, "add", "."], check=True)
        subprocess.run(["git", "-C", repo_path, "commit", "-m", mensaje], check=True)
        subprocess.run(["git", "-C", repo_path, "push"], check=True)
        print("✅ Cambios subidos a GitHub Pages.")
    except Exception as e:
        print(f"❌ Error subiendo cambios a GitHub: {e}")

# Script principal de ejemplo
if __name__ == "__main__":
    print("🚀 Sistema de Historial GitHub Pages para Insider Trading")
    print("=" * 60)
    
    # Crear instancia del uploader
    uploader = GitHubPagesHistoricalUploader()
    
    # Ejemplo de uso
    print("📝 Ejemplo de funcionamiento:")
    print("1. Cada reporte se guarda con timestamp único")
    print("2. Se mantiene historial completo en GitHub Pages")
    print("3. Se genera análisis cruzado automáticamente")
    print("4. Se identifican patrones de actividad recurrente")
    print("5. Enlaces de Telegram incluyen historial completo")
    
    print("\n🔗 Integración con sistema existente:")
    print("- Reemplazar generar_reporte_completo_integrado()")
    print("- Usar generar_reporte_completo_integrado_con_historial()")
    print("- Los CSV antiguos se pueden migrar automáticamente")
    
    print("\n📊 Análisis cruzado permite:")
    print("- Identificar tickers con actividad sostenida")
    print("- Detectar patrones de compra recurrente")
    print("- Evaluar fuerza de señales por frecuencia")
    print("- Seguimiento de tendencias a largo plazo")