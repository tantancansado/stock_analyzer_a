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
        vcp_metadata = self._load_vcp_metadata()
        vcp_repeaters = self._load_vcp_repeaters()

        # Generate integrated insights
        insights = self._generate_insights(sector_data, opportunities_data, backtest_data, vcp_repeaters)

        # Generate HTML
        html = self._generate_html(sector_data, opportunities_data, backtest_data, insights, vcp_metadata)

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
        """
        Carga oportunidades con Super Score Ultimate (VCP + ML + Fundamental)

        Strategy: Hybrid merge
        1. Load super_scores_ultimate.csv (VCP + ML + Fundamental combined)
        2. Merge with super_opportunities_5d_complete.csv for enrichment
        3. Merge with super_opportunities_with_prices.csv for entry/exit (if exists)
        4. Use ultimate score as PRIMARY while keeping 5D features
        """
        ultimate_file = Path("docs/super_scores_ultimate.csv")
        opps_5d_file = Path("docs/super_opportunities_5d_complete.csv")

        # Try to load Super Score Ultimate (preferred)
        if ultimate_file.exists():
            ultimate_df = pd.read_csv(ultimate_file)

            # If 5D data available, enrich with insiders/institutional/timing
            if opps_5d_file.exists():
                opps_5d = pd.read_csv(opps_5d_file)

                # Merge to get enrichment data from 5D
                enrichment_cols = [
                    'ticker', 'insiders_score', 'institutional_score',
                    'timing_convergence', 'timing_reason', 'vcp_repeater',
                    'repeat_count', 'consistency_score', 'sector_name',
                    'sector_momentum', 'price_target', 'analyst_target',
                    'upside_percent', 'top_whales', 'num_whales'
                ]

                # Only keep columns that exist in 5D data
                available_enrichment = [col for col in enrichment_cols if col in opps_5d.columns]

                df = ultimate_df.merge(
                    opps_5d[available_enrichment],
                    on='ticker',
                    how='left',
                    validate='1:1'
                )
            else:
                df = ultimate_df.copy()

            # Merge with entry/exit prices if available
            prices_file = Path("docs/super_opportunities_with_prices.csv")
            if prices_file.exists():
                prices_df = pd.read_csv(prices_file)
                price_cols = [
                    'ticker', 'entry_price', 'entry_range', 'stop_loss',
                    'exit_price', 'exit_range', 'risk_reward', 'risk_pct',
                    'reward_pct', 'entry_timing', 'meets_risk_reward'
                ]
                available_price_cols = [col for col in price_cols if col in prices_df.columns]

                df = df.merge(
                    prices_df[available_price_cols],
                    on='ticker',
                    how='left',
                    validate='1:1'
                )
                print(f"✅ Merged entry/exit prices for {df['entry_price'].notna().sum()} opportunities")

            # Rename super_score_ultimate to super_score_5d for compatibility
            if 'super_score_ultimate' in df.columns:
                df['super_score_5d'] = df['super_score_ultimate']

            # Store total count before filtering
            total_count = len(df)

            # Filter score >= 55 (GOOD o mejor)
            df = df[df['super_score_5d'] >= 55].copy()

            # Add total count as attribute
            df.attrs['total_count'] = total_count

            return df

        # Fallback to 5D-only if ultimate doesn't exist yet
        elif opps_5d_file.exists():
            df = pd.read_csv(opps_5d_file)
            total_count = len(df)
            df = df[df['super_score_5d'] >= 55].copy()
            df.attrs['total_count'] = total_count
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

    def _load_vcp_metadata(self):
        """Carga metadata del último scan VCP"""
        # Buscar archivos VCP en ubicación estandarizada
        vcp_files = list(Path("docs/reports/vcp").glob("vcp_calibrated_results_*.csv"))

        # Fallback a root directory para backward compatibility
        if not vcp_files:
            vcp_files = list(Path(".").glob("vcp_calibrated_results_*.csv"))

        if vcp_files:
            latest_vcp = sorted(vcp_files)[-1]
            df = pd.read_csv(latest_vcp)

            # Extraer fecha del nombre del archivo
            # Formato: vcp_calibrated_results_YYYYMMDD_HHMMSS.csv
            filename = latest_vcp.stem  # Remove .csv
            parts = filename.split('_')
            if len(parts) >= 4:
                date_str = parts[3]  # YYYYMMDD
                time_str = parts[4] if len(parts) > 4 else "000000"  # HHMMSS
                scan_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                scan_time = f"{time_str[:2]}:{time_str[2:4]}"
            else:
                scan_date = "Unknown"
                scan_time = ""

            return {
                'pattern_count': len(df),
                'scan_date': scan_date,
                'scan_time': scan_time,
                'filename': latest_vcp.name
            }

        return None

    def _load_vcp_repeaters(self):
        """Carga datos de VCP repeaters"""
        repeater_file = Path("docs/vcp_repeaters.json")
        if repeater_file.exists():
            with open(repeater_file, 'r') as f:
                data = json.load(f)
                return data.get('repeaters', {})
        return None

    def _generate_insights(self, sector_data, opportunities_data, backtest_data, vcp_repeaters=None):
        """Genera insights integrados cruzando datos"""
        insights = []

        # VCP Repeaters insight (PRIORITY #1)
        if vcp_repeaters and opportunities_data is not None and 'vcp_repeater' in opportunities_data.columns:
            repeater_opps = opportunities_data[opportunities_data['vcp_repeater'] == True]

            if len(repeater_opps) > 0:
                top_repeaters = repeater_opps.nlargest(5, 'repeat_count')
                insights.append({
                    'type': 'VCP_REPEATERS',
                    'title': f"🔁 {len(repeater_opps)} VCP REPEATERS - Stocks con Historial Comprobado",
                    'description': f"Estos stocks formaron VCP patterns múltiples veces. Mayor probabilidad de éxito.",
                    'tickers': top_repeaters['ticker'].tolist(),
                    'priority': 'CRITICAL'
                })

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

    def _generate_html(self, sector_data, opportunities_data, backtest_data, insights, vcp_metadata=None):
        """Genera HTML del super dashboard"""

        # Prepare data
        top_opportunities = []
        total_opportunities = 0
        filtered_count = 0
        if opportunities_data is not None:
            # Get total count from attrs (before filtering)
            total_opportunities = opportunities_data.attrs.get('total_count', len(opportunities_data))
            # Get filtered count (score >= 55)
            filtered_count = len(opportunities_data)
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
    <title>🎯 Super Dashboard Ultimate - VCP + ML + Fundamentals</title>
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

        /* === RESPONSIVE DESIGN - MOBILE OPTIMIZED === */

        /* Tablets */
        @media (max-width: 1024px) {{
            .container {{
                padding: 1.5rem;
            }}

            .opportunities-table {{
                font-size: 0.9rem;
            }}
        }}

        /* Mobile Large */
        @media (max-width: 768px) {{
            .container {{
                padding: 1rem;
            }}

            .header {{
                padding: 2rem 1rem;
            }}

            .header h1 {{
                font-size: 2rem;
            }}

            .header a {{
                font-size: 1rem !important;
                padding: 6px 12px !important;
            }}

            .stats-grid {{
                grid-template-columns: repeat(2, 1fr) !important;
                gap: 1rem;
            }}

            .stat-card {{
                padding: 1.5rem;
            }}

            .opportunities-table-container {{
                overflow-x: auto;
                -webkit-overflow-scrolling: touch;
            }}

            .opportunities-table {{
                font-size: 0.85rem;
                min-width: 600px;
            }}

            .opportunities-table th,
            .opportunities-table td {{
                padding: 0.6rem 0.5rem;
            }}
        }}

        /* Mobile Small */
        @media (max-width: 480px) {{
            .container {{
                padding: 0.75rem;
                margin: 0.5rem;
            }}

            .header {{
                padding: 1.5rem 0.75rem;
                position: relative;
            }}

            .header h1 {{
                font-size: 1.75rem;
                margin-top: 2.5rem;
            }}

            .header a {{
                position: absolute !important;
                left: 0.75rem !important;
                top: 0.75rem !important;
                font-size: 0.9rem !important;
                padding: 6px 10px !important;
            }}

            .stats-grid {{
                grid-template-columns: 1fr !important;
                gap: 0.75rem;
            }}

            .stat-card {{
                padding: 1.25rem;
            }}

            .stat-value {{
                font-size: 1.75rem;
            }}

            .opportunities-table {{
                font-size: 0.8rem;
                min-width: 500px;
            }}

            .opportunities-table th,
            .opportunities-table td {{
                padding: 0.5rem 0.4rem;
            }}

            button, a {{
                min-height: 44px;
            }}
        }}

        /* Ultra Small */
        @media (max-width: 360px) {{
            .header h1 {{
                font-size: 1.5rem;
            }}

            .stat-value {{
                font-size: 1.5rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <a href="index.html" style="position: absolute; left: 20px; top: 20px; color: white; text-decoration: none; font-size: 1.2em; background: rgba(255,255,255,0.2); padding: 8px 16px; border-radius: 8px; transition: background 0.3s;" onmouseover="this.style.background='rgba(255,255,255,0.3)'" onmouseout="this.style.background='rgba(255,255,255,0.2)'">
                🏠 Volver
            </a>
            <h1>🎯 Super Dashboard Ultimate</h1>
            <p style="font-size: 0.9em; color: #cbd5e0; margin-top: 5px;">VCP Pattern + ML Predictions + Fundamental Analysis</p>
            <div class="subtitle">Sistema 5D Integrado - Análisis Completo del Mercado</div>
            <div style="margin-top: 10px; font-size: 0.9em;">
                {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </div>
        </div>

        <!-- Quick Stats -->
        <div class="quick-stats">
            <div class="stat-card" style="background: linear-gradient(135deg, #fef3c7, #fbbf24);">
                <div class="stat-value" style="color: #92400e;">{vcp_metadata['pattern_count'] if vcp_metadata else 0}</div>
                <div class="stat-label" style="color: #92400e;">🎯 VCP Patterns</div>
                <div style="font-size: 0.8em; color: #92400e; margin-top: 5px;">{vcp_metadata['scan_date'] if vcp_metadata else 'N/A'}</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{total_opportunities}</div>
                <div class="stat-label">Total 5D Opps</div>
                <div style="font-size: 0.8em; color: #666; margin-top: 5px;">⭐ BUENA+: {filtered_count}</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(sector_alerts)}</div>
                <div class="stat-label">Sector Alerts</div>
            </div>
            <div class="stat-card" style="background: linear-gradient(135deg, #d1fae5, #10b981);">
                <div class="stat-value" style="color: #065f46;">{backtest_summary.get('win_rate', 0):.0f}%</div>
                <div class="stat-label" style="color: #065f46;">Win Rate</div>
                <div style="font-size: 0.8em; color: #065f46; margin-top: 5px;">Avg: {backtest_summary.get('avg_return', 0):.1f}%</div>
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
            <p>🚀 Stock Analyzer Ultimate - Super Dashboard (VCP + ML + Fundamental)</p>
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
        """Genera tabla de oportunidades con Super Score Ultimate"""
        if not opportunities:
            return "<p>No hay oportunidades disponibles</p>"

        rows = []
        for opp in opportunities[:10]:
            score = opp.get('super_score_5d', 0)
            score_class = 'score-high' if score >= 70 else 'score-medium'
            timing_badge = '🔥' if opp.get('timing_convergence', False) else ''
            repeater_badge = '🔁' if opp.get('vcp_repeater', False) else ''

            # Company name display
            ticker = opp.get('ticker', 'N/A')
            company_name = opp.get('company_name', ticker)

            # Show ticker + company name (shortened if too long)
            company_short = company_name[:25] + '...' if len(company_name) > 25 else company_name
            ticker_display = f'<div><strong>{ticker}</strong><br><span style="font-size: 0.75em; color: var(--text-muted);">{company_short}</span></div>' if company_name != ticker else f'<strong>{ticker}</strong>'

            # Component scores
            vcp_score = opp.get('vcp_score', 0)
            ml_score = opp.get('ml_score', 0)
            fundamental_score = opp.get('fundamental_score', 0)

            # Insider score - handle NaN
            insiders_score = opp.get('insiders_score', 0)
            if pd.isna(insiders_score):
                insiders_score = 0

            # Sector (prefer sector_name, fallback to sector) - handle NaN
            sector_name = opp.get('sector_name')
            sector_fallback = opp.get('sector', 'N/A')

            if pd.isna(sector_name):
                sector = sector_fallback if not pd.isna(sector_fallback) else 'N/A'
            else:
                sector = sector_name

            # Validation status badge
            validation_status = opp.get('validation_status', '')
            validation_reason = opp.get('validation_reason', 'Not validated')
            price_vs_ath = opp.get('price_vs_ath')

            validation_emoji = {
                'BUY': '✅',
                'HOLD': '⚠️',
                'AVOID': '❌'
            }.get(validation_status, '')

            # Build validation tooltip
            validation_tooltip = validation_reason
            if price_vs_ath is not None:
                validation_tooltip += f" | {price_vs_ath:+.1f}% vs ATH"

            validation_badge = f'<span title="{validation_tooltip}">{validation_emoji}</span>' if validation_emoji else ''

            # Filter badges
            ma_filter_pass = opp.get('ma_filter_pass', False)
            ma_badge = '✅' if ma_filter_pass else '❌'
            ma_reason = opp.get('ma_filter_reason', 'N/A')

            ad_signal = opp.get('ad_signal', 'NEUTRAL')
            ad_emoji = {
                'STRONG_ACCUMULATION': '🟢',
                'ACCUMULATION': '🟡',
                'NEUTRAL': '⚪',
                'DISTRIBUTION': '🟠',
                'STRONG_DISTRIBUTION': '🔴'
            }.get(ad_signal, '⚪')

            filters_passed = opp.get('filters_passed', 'N/A')
            filter_penalty = opp.get('filter_penalty', 0)
            filter_tooltip = f"Penalty: -{filter_penalty:.0f} points"

            rows.append(f"""
            <tr>
                <td>{ticker_display}</td>
                <td><span class="score-badge {score_class}">{score:.1f}</span></td>
                <td>{opp.get('tier', 'N/A')}</td>
                <td>{sector}</td>
                <td><span class="component-score" title="VCP Pattern (40%)">{vcp_score:.0f}</span></td>
                <td><span class="component-score" title="ML Predictive (30%)">{ml_score:.0f}</span></td>
                <td><span class="component-score" title="Fundamentals (30%)">{fundamental_score:.0f}</span></td>
                <td><span title="{ma_reason}">{ma_badge}</span></td>
                <td><span title="{ad_signal}">{ad_emoji}</span></td>
                <td><span title="{filter_tooltip}">{filters_passed}</span></td>
                <td>{insiders_score:.0f}</td>
                <td>{validation_badge}</td>
                <td>{timing_badge} {repeater_badge}</td>
            </tr>
            """)

        legend_html = """
        <div style="background: var(--glass-bg); border: 1px solid var(--glass-border); border-radius: 12px; padding: 1rem; margin-bottom: 1.5rem; backdrop-filter: blur(10px);">
            <h4 style="color: var(--glass-primary); margin-bottom: 0.75rem;">📖 Guía de Columnas</h4>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 0.5rem; font-size: 0.85em;">
                <div><strong>Score:</strong> Puntuación final con filtros aplicados</div>
                <div><strong>Tier:</strong> Clasificación por calidad (⭐⭐⭐⭐ ELITE = top)</div>
                <div><strong>VCP:</strong> Setup técnico (patrón volatilidad)</div>
                <div><strong>ML:</strong> Predicción momentum/tendencia</div>
                <div><strong>Fund:</strong> Análisis fundamental (earnings, growth, salud)</div>
                <div><strong>MA:</strong> Minervini Trend Template - ✅ Pass | ❌ Fail</div>
                <div><strong>A/D:</strong> Acumulación/Distribución - 🟢 Strong Acc | 🟡 Acc | ⚪ Neutral | 🟠 Dist | 🔴 Strong Dist</div>
                <div><strong>Filt:</strong> Filtros pasados (Market + MA + A/D) - X/3</div>
                <div><strong>Ins:</strong> Actividad insider trading</div>
                <div><strong>Val:</strong> Validación web - ✅ BUY (good entry) | ⚠️ HOLD (wait) | ❌ AVOID (near ATH)</div>
                <div><strong>Timing:</strong> 🔥 Convergencia temporal | 🔁 VCP recurrente</div>
            </div>
        </div>
        """

        return legend_html + f"""
        <div class="opportunities-table-container">
            <table class="opportunities-table">
                <thead>
                    <tr>
                        <th>Ticker / Company</th>
                        <th title="Super Score Ultimate with Filters Applied">Score</th>
                        <th title="Quality Tier">Tier</th>
                        <th>Sector</th>
                        <th title="VCP Pattern Score (40%)">VCP</th>
                        <th title="ML Predictive Score (30%)">ML</th>
                        <th title="Fundamental Score (30%)">Fund</th>
                        <th title="Moving Average Filter (Minervini)">MA</th>
                        <th title="Accumulation/Distribution">A/D</th>
                        <th title="Filters Passed (Market + MA + A/D)">Filt</th>
                        <th title="Insider Trading Activity">Ins</th>
                        <th title="Web Validation: ✅ BUY | ⚠️ HOLD | ❌ AVOID">Val</th>
                        <th title="🔥 Timing Convergence | 🔁 VCP Repeater">Timing</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
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
