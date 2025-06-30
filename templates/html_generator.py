#!/usr/bin/env python3
"""
HTML Generator - Templates para el Sistema Trading Unificado
Mantiene todo el HTML/CSS separado de la lógica de negocio
"""

from datetime import datetime
import pandas as pd

class HTMLGenerator:
    """Generador de HTML para todos los reportes del sistema"""
    
    def __init__(self):
        self.base_css = self._get_base_css()
    
    def _get_base_css(self):
        """CSS base común para todos los reportes"""
        return """
        :root {
            --bg-dark: #0a0e1a;
            --bg-card: #1a202c;
            --bg-card-light: #2d3748;
            --border-color: #4a5568;
            --primary: #4a90e2;
            --text-primary: #ffffff;
            --text-secondary: #a0aec0;
            --success: #48bb78;
            --warning: #ffd700;
            --danger: #f56565;
        }
        
        * { box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-dark);
            color: var(--text-primary);
            margin: 0;
            padding: 0;
            line-height: 1.6;
        }
        
        .header {
            background: linear-gradient(135deg, #1a1f35 0%, #2d3748 100%);
            padding: 20px;
            text-align: center;
            border-bottom: 2px solid var(--primary);
        }
        
        .header h1 {
            color: var(--primary);
            font-size: 2em;
            margin: 0 0 10px 0;
        }
        
        @media (max-width: 768px) {
            .header h1 {
                font-size: 1.5em;
            }
            
            .header {
                padding: 15px 10px;
            }
        }
        """
    
    def _get_base_html_structure(self, title, custom_css=""):
        """Estructura HTML base"""
        return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        {self.base_css}
        {custom_css}
    </style>
</head>
<body>
"""

    def generate_dj_sectorial_html(self, results, timestamp=None):
        """Genera HTML para el análisis DJ Sectorial"""
        if not timestamp:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        # Estadísticas
        total_sectores = len(results) if results else 0
        oportunidades = len([r for r in results if r['classification'] == 'OPORTUNIDAD']) if results else 0
        cerca = len([r for r in results if r['classification'] == 'CERCA']) if results else 0
        fuertes = len([r for r in results if r['classification'] == 'FUERTE']) if results else 0
        
        # CSS específico para DJ Sectorial
        dj_css = """
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 15px;
            padding: 20px;
            background: var(--bg-card);
        }
        
        .stat-card {
            background: var(--bg-card-light);
            padding: 15px;
            border-radius: 12px;
            text-align: center;
            border-left: 4px solid var(--primary);
        }
        
        .stat-number {
            font-size: 1.8em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .stat-label {
            color: var(--text-secondary);
            font-size: 0.9em;
        }
        
        .oportunidad { color: var(--success); }
        .cerca { color: var(--warning); }
        .fuerte { color: var(--danger); }
        
        .sectors-container {
            padding: 20px;
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }
        
        .sector-card {
            background: var(--bg-card);
            border-radius: 12px;
            padding: 20px;
            border-left: 4px solid var(--primary);
            transition: transform 0.2s ease;
        }
        
        .sector-card:hover {
            transform: translateY(-2px);
        }
        
        .sector-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .sector-ticker {
            font-size: 1.3em;
            font-weight: bold;
            color: var(--primary);
        }
        
        .sector-status {
            font-size: 1.5em;
        }
        
        .sector-name {
            color: var(--text-secondary);
            margin-bottom: 15px;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        
        .metric {
            background: var(--bg-card-light);
            padding: 10px;
            border-radius: 8px;
        }
        
        .metric-label {
            font-size: 0.8em;
            color: var(--text-secondary);
            margin-bottom: 3px;
        }
        
        .metric-value {
            font-weight: bold;
        }
        
        @media (max-width: 768px) {
            .sectors-container {
                grid-template-columns: 1fr;
                padding: 10px;
            }
            
            .stats-grid {
                grid-template-columns: repeat(2, 1fr);
                padding: 10px;
            }
        }
        """
        
        # Construir HTML
        html = self._get_base_html_structure("📊 DJ Sectorial Dashboard", dj_css)
        
        html += f"""
    <div class="header">
        <h1>📊 Dow Jones Sectorial Dashboard</h1>
        <p>Análisis completo de sectores • {timestamp}</p>
    </div>
    
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-number">{total_sectores}</div>
            <div class="stat-label">Total Sectores</div>
        </div>
        <div class="stat-card">
            <div class="stat-number oportunidad">{oportunidades}</div>
            <div class="stat-label">🟢 Oportunidades</div>
        </div>
        <div class="stat-card">
            <div class="stat-number cerca">{cerca}</div>
            <div class="stat-label">🟡 Cerca</div>
        </div>
        <div class="stat-card">
            <div class="stat-number fuerte">{fuertes}</div>
            <div class="stat-label">🔴 Fuertes</div>
        </div>
    </div>
    
    <div class="sectors-container">
"""
        
        # Generar cards de sectores
        if results:
            results_sorted = sorted(results, key=lambda x: x['distance_pct'])
            
            for r in results_sorted:
                # Color según clasificación
                if r['classification'] == 'OPORTUNIDAD':
                    border_color = 'var(--success)'
                elif r['classification'] == 'CERCA':
                    border_color = 'var(--warning)'
                else:
                    border_color = 'var(--danger)'
                
                rsi_value = 'N/A' if not pd.notna(r['rsi']) or r['rsi'] is None else f'{r["rsi"]:.1f}'
                
                html += f"""
        <div class="sector-card" style="border-left-color: {border_color}">
            <div class="sector-header">
                <div class="sector-ticker">{r['ticker']}</div>
                <div class="sector-status">{r['estado']}</div>
            </div>
            <div class="sector-name">{r['sector']}</div>
            
            <div class="metrics-grid">
                <div class="metric">
                    <div class="metric-label">Precio Actual</div>
                    <div class="metric-value">${r['current_price']:.2f}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Min 52s</div>
                    <div class="metric-value">${r['min_52w']:.2f}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Distancia Min</div>
                    <div class="metric-value">{r['distance_pct']:.1f}%</div>
                </div>
                <div class="metric">
                    <div class="metric-label">RSI</div>
                    <div class="metric-value">{rsi_value}</div>
                </div>
            </div>
        </div>
"""
        else:
            html += """
        <div class="sector-card">
            <div class="sector-header">
                <div class="sector-ticker">Sin Datos</div>
                <div class="sector-status">⚠️</div>
            </div>
            <div class="sector-name">No se pudieron obtener datos de sectores</div>
        </div>
"""
        
        html += """
    </div>
</body>
</html>
"""
        
        return html
    
    def generate_insider_trading_html(self, df, timestamp=None):
        """Genera HTML para el reporte de Insider Trading"""
        if not timestamp:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        # CSS específico para Insider Trading
        insider_css = """
        .summary {
            background: var(--bg-card);
            padding: 20px;
            margin: 20px;
            border-radius: 12px;
            border-left: 4px solid var(--primary);
        }
        
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        
        .summary-item {
            background: var(--bg-card-light);
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }
        
        .summary-number {
            font-size: 1.5em;
            font-weight: bold;
            color: var(--primary);
        }
        
        .table-container {
            margin: 20px;
            background: var(--bg-card);
            border-radius: 12px;
            overflow: hidden;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th {
            background: var(--primary);
            color: white;
            padding: 12px 8px;
            text-align: left;
            font-weight: bold;
        }
        
        td {
            padding: 10px 8px;
            border-bottom: 1px solid var(--border-color);
        }
        
        tr:nth-child(even) {
            background: var(--bg-card-light);
        }
        
        tr:hover {
            background: var(--border-color);
        }
        
        .no-data {
            text-align: center;
            padding: 40px;
            color: var(--text-secondary);
            font-style: italic;
        }
        
        @media (max-width: 768px) {
            .summary, .table-container {
                margin: 10px;
            }
            
            .summary-grid {
                grid-template-columns: repeat(2, 1fr);
            }
            
            table {
                font-size: 0.9em;
            }
            
            th, td {
                padding: 8px 6px;
            }
        }
        """
        
        # Construir HTML
        html = self._get_base_html_structure("🏛️ Insider Trading Report", insider_css)
        
        # Estadísticas
        total_transactions = len(df) if df is not None and len(df) > 0 else 0
        unique_companies = df['Insider'].nunique() if df is not None and 'Insider' in df.columns and len(df) > 0 else 0
        
        html += f"""
    <div class="header">
        <h1>🏛️ Insider Trading Report</h1>
        <p>Análisis de transacciones • {timestamp}</p>
    </div>
    
    <div class="summary">
        <h2>📊 Resumen Ejecutivo</h2>
        <div class="summary-grid">
            <div class="summary-item">
                <div class="summary-number">{total_transactions}</div>
                <div>Transacciones</div>
            </div>
            <div class="summary-item">
                <div class="summary-number">{unique_companies}</div>
                <div>Empresas</div>
            </div>
            <div class="summary-item">
                <div class="summary-number">{'✅' if total_transactions > 0 else '⚪'}</div>
                <div>Estado</div>
            </div>
        </div>
    </div>
    
    <div class="table-container">
"""
        
        if df is not None and len(df) > 0:
            # Tabla con datos
            html += """
        <table>
            <thead>
                <tr>
                    <th>Ticker</th>
                    <th>Company</th>
                    <th>Price</th>
                    <th>Qty</th>
                    <th>Value</th>
                    <th>Type</th>
                </tr>
            </thead>
            <tbody>
"""
            
            for _, row in df.head(50).iterrows():
                html += f"""
                <tr>
                    <td>{row.get('Insider', 'N/A')}</td>
                    <td>{row.get('Title', 'N/A')}</td>
                    <td>{row.get('Price', 'N/A')}</td>
                    <td>{row.get('Qty', 'N/A')}</td>
                    <td>{row.get('Value', 'N/A')}</td>
                    <td>{row.get('Type', 'N/A')}</td>
                </tr>
"""
            
            html += """
            </tbody>
        </table>
"""
        else:
            # Sin datos
            html += """
        <div class="no-data">
            <h3>📭 No hay transacciones detectadas</h3>
            <p>El monitoreo está activo, pero no se encontraron transacciones recientes.</p>
        </div>
"""
        
        html += """
    </div>
</body>
</html>
"""
        
        return html
    
    def generate_vcp_scanner_html(self, results, timestamp=None):
        """Genera HTML para el VCP Scanner (para futuro uso)"""
        if not timestamp:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        # CSS específico para VCP Scanner
        vcp_css = """
        .vcp-container {
            padding: 20px;
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 15px;
        }
        
        .vcp-card {
            background: var(--bg-card);
            border-radius: 12px;
            padding: 15px;
            border-left: 4px solid var(--success);
        }
        
        .vcp-ticker {
            font-size: 1.2em;
            font-weight: bold;
            color: var(--primary);
            margin-bottom: 10px;
        }
        
        .vcp-metrics {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            font-size: 0.9em;
        }
        """
        
        html = self._get_base_html_structure("🎯 VCP Scanner Results", vcp_css)
        
        html += f"""
    <div class="header">
        <h1>🎯 VCP Scanner Results</h1>
        <p>Market scan completed • {timestamp}</p>
    </div>
    
    <div class="vcp-container">
"""
        
        if results and len(results) > 0:
            for result in results:
                html += f"""
        <div class="vcp-card">
            <div class="vcp-ticker">{result.get('ticker', 'N/A')}</div>
            <div class="vcp-metrics">
                <div>Score: {result.get('score', 'N/A')}</div>
                <div>Volume: {result.get('volume', 'N/A')}</div>
            </div>
        </div>
"""
        else:
            html += """
        <div class="vcp-card">
            <div class="vcp-ticker">No Results</div>
            <div>No VCP patterns detected in current scan</div>
        </div>
"""
        
        html += """
    </div>
</body>
</html>
"""
        
        return html

# Función de conveniencia para uso directo
def generate_html_report(report_type, data, timestamp=None, file_path=None):
    """
    Función utilitaria para generar reportes HTML
    
    Args:
        report_type (str): 'dj_sectorial', 'insider_trading', 'vcp_scanner'
        data: Los datos del reporte
        timestamp (str): Timestamp opcional
        file_path (str): Ruta donde guardar el archivo
    
    Returns:
        str: HTML generado o ruta del archivo si se especifica file_path
    """
    generator = HTMLGenerator()
    
    if report_type == 'dj_sectorial':
        html = generator.generate_dj_sectorial_html(data, timestamp)
    elif report_type == 'insider_trading':
        html = generator.generate_insider_trading_html(data, timestamp)
    elif report_type == 'vcp_scanner':
        html = generator.generate_vcp_scanner_html(data, timestamp)
    else:
        raise ValueError(f"Tipo de reporte no soportado: {report_type}")
    
    if file_path:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html)
        return file_path
    
    return html