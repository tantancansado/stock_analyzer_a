#!/usr/bin/env python3
"""
SUPER DASHBOARD INTEGRADO
Unifica Sector Rotation + 5D Opportunities + Backtest + Timing Convergence
"""
import json
import pandas as pd
from pathlib import Path
from datetime import datetime


class SuperDashboardGenerator:
    """Generador de dashboard maestro integrado"""

    def generate_dashboard(self, output_file: str = "docs/super_dashboard.html"):
        """
        Genera super dashboard unificado

        Args:
            output_file: Path del HTML de salida
        """
        # Load all data sources
        sector_data = self._load_sector_rotation()
        opportunities_data = self._load_5d_opportunities()
        backtest_data = self._load_backtest_metrics()

        # Generate integrated insights
        insights = self._generate_insights(sector_data, opportunities_data, backtest_data)

        # Generate HTML
        html = self._generate_html(sector_data, opportunities_data, backtest_data, insights)

        # Save
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"✅ Super Dashboard generado: {output_file}")

    def _load_sector_rotation(self):
        """Carga datos de sector rotation"""
        scan_file = Path("docs/sector_rotation/latest_scan.json")
        if scan_file.exists():
            with open(scan_file, 'r') as f:
                return json.load(f)
        return None

    def _load_5d_opportunities(self):
        """Carga oportunidades 5D"""
        csv_file = Path("docs/super_opportunities_5d_complete.csv")
        if csv_file.exists():
            df = pd.read_csv(csv_file)
            # Filter score >= 55 (BUENA o mejor)
            df = df[df['super_score_5d'] >= 55].copy()
            return df
        return None

    def _load_backtest_metrics(self):
        """Carga métricas de backtest"""
        metrics_dir = Path("docs/backtest")
        if metrics_dir.exists():
            metrics_files = list(metrics_dir.glob("metrics_*.json"))
            if metrics_files:
                latest = sorted(metrics_files)[-1]
                with open(latest, 'r') as f:
                    return json.load(f)
        return None

    def _generate_insights(self, sector_data, opportunities_data, backtest_data):
        """Genera insights integrados cruzando datos"""
        insights = []

        if sector_data and opportunities_data is not None:
            # Cross-reference: 5D opportunities en sectores LEADING
            leading_sectors = [s for s in sector_data.get('results', [])
                             if s['status'] == 'LEADING']

            for sector in leading_sectors:
                sector_name = sector['sector']
                # Find opportunities in this sector
                sector_opps = opportunities_data[
                    opportunities_data['sector_name'] == sector_name
                ]

                if len(sector_opps) > 0:
                    insights.append({
                        'type': 'HIGH_PROBABILITY',
                        'title': f"🔥 {len(sector_opps)} oportunidades 5D en {sector_name} (LEADING)",
                        'description': f"Sector con velocity {sector['velocity']:+.2f} y RS {sector['relative_strength']:.1f}",
                        'tickers': sector_opps['ticker'].tolist()[:5],
                        'priority': 'CRITICAL'
                    })

            # Timing convergence + EMERGING sectors
            if 'timing_convergence' in opportunities_data.columns:
                emerging_sectors = [s for s in sector_data.get('results', [])
                                   if s['status'] == 'IMPROVING']

                for sector in emerging_sectors:
                    sector_name = sector['sector']
                    sector_opps = opportunities_data[
                        (opportunities_data['sector_name'] == sector_name) &
                        (opportunities_data['timing_convergence'] == True)
                    ]

                    if len(sector_opps) > 0:
                        insights.append({
                            'type': 'EARLY_ENTRY',
                            'title': f"⚡ {len(sector_opps)} setups con timing perfecto en {sector_name} (EMERGING)",
                            'description': f"Sector saliendo de debilidad + timing convergence",
                            'tickers': sector_opps['ticker'].tolist()[:5],
                            'priority': 'HIGH'
                        })

        # Backtest validation
        if backtest_data:
            win_rate = backtest_data.get('win_rate', 0)
            if win_rate >= 70:
                insights.append({
                    'type': 'VALIDATION',
                    'title': f"✅ Estrategia validada: {win_rate:.1f}% win rate",
                    'description': f"Backtest histórico confirma efectividad del sistema",
                    'priority': 'INFO'
                })

        return insights

    def _generate_html(self, sector_data, opportunities_data, backtest_data, insights):
        """Genera HTML del super dashboard"""

        # Prepare data
        top_opportunities = []
        if opportunities_data is not None:
            top_opportunities = opportunities_data.nlargest(10, 'super_score_5d').to_dict('records')

        sector_alerts = []
        if sector_data:
            sector_alerts = sector_data.get('alerts', [])

        backtest_summary = {}
        if backtest_data:
            backtest_summary = {
                'win_rate': backtest_data.get('win_rate', 0),
                'avg_return': backtest_data.get('avg_return', 0),
                'total_trades': backtest_data.get('total_trades', 0)
            }

        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎯 Super Dashboard - Sistema 5D Integrado</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}

        .container {{
            max-width: 1800px;
            margin: 0 auto;
        }}

        .header {{
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }}

        .header h1 {{
            font-size: 3.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}

        .header .subtitle {{
            font-size: 1.3em;
            opacity: 0.9;
        }}

        .quick-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .stat-card {{
            background: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            text-align: center;
        }}

        .stat-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }}

        .stat-label {{
            color: #666;
            text-transform: uppercase;
            font-size: 0.9em;
            letter-spacing: 1px;
        }}

        .insights-section {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}

        .insight-item {{
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 10px;
            border-left: 5px solid;
        }}

        .insight-CRITICAL {{
            background: #fef3c7;
            border-color: #f59e0b;
        }}

        .insight-HIGH {{
            background: #dbeafe;
            border-color: #3b82f6;
        }}

        .insight-INFO {{
            background: #d1fae5;
            border-color: #10b981;
        }}

        .insight-title {{
            font-size: 1.3em;
            font-weight: bold;
            margin-bottom: 10px;
        }}

        .insight-desc {{
            color: #666;
            margin-bottom: 10px;
        }}

        .ticker-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 10px;
        }}

        .ticker-badge {{
            background: #667eea;
            color: white;
            padding: 5px 12px;
            border-radius: 5px;
            font-weight: bold;
            font-size: 0.9em;
        }}

        .grid-2 {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(800px, 1fr));
            gap: 30px;
            margin-bottom: 30px;
        }}

        .section-card {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}

        .section-title {{
            font-size: 1.8em;
            margin-bottom: 20px;
            color: #333;
        }}

        .opportunities-table {{
            width: 100%;
            border-collapse: collapse;
        }}

        .opportunities-table th {{
            background: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}

        .opportunities-table td {{
            padding: 12px;
            border-bottom: 1px solid #e5e7eb;
        }}

        .opportunities-table tr:hover {{
            background: #f9fafb;
        }}

        .score-badge {{
            display: inline-block;
            padding: 5px 10px;
            border-radius: 5px;
            font-weight: bold;
            color: white;
        }}

        .score-high {{
            background: #10b981;
        }}

        .score-medium {{
            background: #3b82f6;
        }}

        .timing-badge {{
            background: #f59e0b;
            color: white;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 0.8em;
            font-weight: bold;
        }}

        .alert-list {{
            list-style: none;
        }}

        .alert-list li {{
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 8px;
            background: #f9fafb;
            border-left: 4px solid #667eea;
        }}

        .footer {{
            text-align: center;
            color: white;
            margin-top: 50px;
            opacity: 0.8;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Super Dashboard</h1>
            <div class="subtitle">Sistema 5D Integrado - Análisis Completo del Mercado</div>
            <div style="margin-top: 10px; font-size: 0.9em;">
                {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </div>
        </div>

        <!-- Quick Stats -->
        <div class="quick-stats">
            <div class="stat-card">
                <div class="stat-value">{len(top_opportunities) if opportunities_data is not None else 0}</div>
                <div class="stat-label">5D Opportunities</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(sector_alerts)}</div>
                <div class="stat-label">Sector Alerts</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{backtest_summary.get('win_rate', 0):.0f}%</div>
                <div class="stat-label">Win Rate</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{backtest_summary.get('avg_return', 0):.1f}%</div>
                <div class="stat-label">Avg Return</div>
            </div>
        </div>

        <!-- AI Insights -->
        {self._generate_insights_html(insights)}

        <!-- Main Content Grid -->
        <div class="grid-2">
            <!-- Top Opportunities -->
            <div class="section-card">
                <h2 class="section-title">🏆 Top 5D Opportunities</h2>
                {self._generate_opportunities_table(top_opportunities)}
            </div>

            <!-- Sector Alerts -->
            <div class="section-card">
                <h2 class="section-title">🔄 Sector Rotation Alerts</h2>
                {self._generate_alerts_html(sector_alerts)}
            </div>
        </div>

        <!-- Quick Links -->
        <div class="section-card">
            <h2 class="section-title">🔗 Dashboards Especializados</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; margin-top: 20px;">
                <a href="sector_rotation_dashboard.html" style="display: block; padding: 20px; background: #667eea; color: white; text-decoration: none; border-radius: 10px; text-align: center; font-weight: bold;">
                    🔄 Sector Rotation
                </a>
                <a href="backtest_dashboard.html" style="display: block; padding: 20px; background: #10b981; color: white; text-decoration: none; border-radius: 10px; text-align: center; font-weight: bold;">
                    📊 Backtest Performance
                </a>
                <a href="super_opportunities_4d.html" style="display: block; padding: 20px; background: #f59e0b; color: white; text-decoration: none; border-radius: 10px; text-align: center; font-weight: bold;">
                    ⭐ 5D Complete Analysis
                </a>
            </div>
        </div>

        <div class="footer">
            <p>🚀 Stock Analyzer 5D - Super Dashboard Integrado</p>
            <p style="font-size: 0.9em; margin-top: 5px;">Made with Claude Code</p>
        </div>
    </div>
</body>
</html>"""

        return html

    def _generate_insights_html(self, insights):
        """Genera HTML de insights"""
        if not insights:
            return ""

        items = []
        for insight in insights:
            priority_class = f"insight-{insight['priority']}"
            tickers_html = ""
            if 'tickers' in insight:
                tickers_html = '<div class="ticker-list">' + \
                    ''.join([f'<span class="ticker-badge">{t}</span>'
                            for t in insight['tickers'][:10]]) + \
                    '</div>'

            items.append(f"""
            <div class="insight-item {priority_class}">
                <div class="insight-title">{insight['title']}</div>
                <div class="insight-desc">{insight['description']}</div>
                {tickers_html}
            </div>
            """)

        return f"""
        <div class="insights-section">
            <h2 class="section-title">💡 AI Insights - Oportunidades Integradas</h2>
            {''.join(items)}
        </div>
        """

    def _generate_opportunities_table(self, opportunities):
        """Genera tabla de oportunidades"""
        if not opportunities:
            return "<p>No hay oportunidades disponibles</p>"

        rows = []
        for opp in opportunities[:10]:
            score = opp.get('super_score_5d', 0)
            score_class = 'score-high' if score >= 70 else 'score-medium'
            timing_badge = '🔥' if opp.get('timing_convergence', False) else ''

            rows.append(f"""
            <tr>
                <td><strong>{opp.get('ticker', 'N/A')}</strong></td>
                <td><span class="score-badge {score_class}">{score:.1f}</span></td>
                <td>{opp.get('tier', 'N/A')}</td>
                <td>{opp.get('sector_name', 'N/A')}</td>
                <td>{opp.get('vcp_score', 0):.0f}</td>
                <td>{opp.get('insiders_score', 0):.0f}</td>
                <td>{timing_badge}</td>
            </tr>
            """)

        return f"""
        <table class="opportunities-table">
            <thead>
                <tr>
                    <th>Ticker</th>
                    <th>Score 5D</th>
                    <th>Tier</th>
                    <th>Sector</th>
                    <th>VCP</th>
                    <th>Insiders</th>
                    <th>Timing</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """

    def _generate_alerts_html(self, alerts):
        """Genera HTML de alertas"""
        if not alerts:
            return "<p>No hay alertas activas</p>"

        items = []
        for alert in alerts[:10]:
            icon = '💚' if alert.get('type') == 'ROTATION_IN' else \
                   '🔴' if alert.get('type') == 'ROTATION_OUT' else '⚡'

            items.append(f"""
            <li>
                <strong>{icon} {alert.get('message', '')}</strong><br>
                <span style="color: #666; font-size: 0.9em;">→ {alert.get('action', '')}</span>
            </li>
            """)

        return f'<ul class="alert-list">{"".join(items)}</ul>'


def main():
    """Main execution"""
    generator = SuperDashboardGenerator()
    generator.generate_dashboard()


if __name__ == "__main__":
    main()
