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

        # Load dual strategy data (new sections)
        value_data = self._load_value_opportunities()
        momentum_data = self._load_momentum_opportunities()

        # Generate integrated insights
        insights = self._generate_insights(sector_data, opportunities_data, backtest_data, vcp_repeaters)

        # Generate HTML
        html = self._generate_html(sector_data, opportunities_data, backtest_data, insights, vcp_metadata, value_data, momentum_data)

        # Save
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"✅ Super Dashboard generado: {output_file}")

    def _load_value_opportunities(self):
        """Carga oportunidades VALUE (Sección A - Principal)"""
        path = Path("docs/value_opportunities.csv")
        if not path.exists():
            return []
        try:
            df = pd.read_csv(path)
            df['value_score'] = pd.to_numeric(df.get('value_score', 0), errors='coerce').fillna(0)
            return df.sort_values('value_score', ascending=False).head(15).to_dict('records')
        except Exception:
            return []

    def _load_momentum_opportunities(self):
        """Carga oportunidades MOMENTUM (Sección B - Minervini)"""
        path = Path("docs/momentum_opportunities.csv")
        if not path.exists():
            return []
        try:
            df = pd.read_csv(path)
            df['momentum_score'] = pd.to_numeric(df.get('momentum_score', 0), errors='coerce').fillna(0)
            return df.sort_values('momentum_score', ascending=False).head(15).to_dict('records')
        except Exception:
            return []

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

            # Fill missing entry/exit prices from 5D data columns
            df = self._fill_missing_prices(df)

            # Rename super_score_ultimate to super_score_5d for compatibility
            if 'super_score_ultimate' in df.columns:
                df['super_score_5d'] = df['super_score_ultimate']

            # Store total count before filtering
            total_count = len(df)

            # Filter score >= 55 (GOOD o mejor)
            filtered = df[df['super_score_5d'] >= 55].copy()

            # If ultimate scores are on a different scale (all < 55), fall back to 5D file
            if len(filtered) == 0 and opps_5d_file.exists():
                print("⚠️  super_scores_ultimate has no rows >= 55 (different scale). Falling back to 5D file.")
                df = pd.read_csv(opps_5d_file)
                total_count = len(df)
                filtered = df[df['super_score_5d'] >= 55].copy()
                filtered = self._fill_missing_prices(filtered)

            filtered.attrs['total_count'] = total_count
            return filtered

        # Fallback to 5D-only if ultimate doesn't exist yet
        elif opps_5d_file.exists():
            df = pd.read_csv(opps_5d_file)
            total_count = len(df)
            df = df[df['super_score_5d'] >= 55].copy()
            df = self._fill_missing_prices(df)
            df.attrs['total_count'] = total_count
            return df

        return None

    def _fill_missing_prices(self, df):
        """Calculate entry/stop/target from 5D data when prices file data is missing"""
        import numpy as np

        if 'entry_price' not in df.columns:
            df['entry_price'] = np.nan
        if 'stop_loss' not in df.columns:
            df['stop_loss'] = np.nan
        if 'exit_price' not in df.columns:
            df['exit_price'] = np.nan
        if 'risk_reward' not in df.columns:
            df['risk_reward'] = np.nan

        mask = df['entry_price'].isna()
        if mask.any() and 'current_price' in df.columns:
            cp = df.loc[mask, 'current_price']

            # Target = best available analyst target
            if 'analyst_target' in df.columns:
                target = df.loc[mask, 'analyst_target']
                if 'price_target' in df.columns:
                    target = target.fillna(df.loc[mask, 'price_target'])
            elif 'price_target' in df.columns:
                target = df.loc[mask, 'price_target']
            else:
                target = pd.Series(np.nan, index=cp.index)

            # Only fill when target is above current price (positive upside)
            valid = mask & (
                df['current_price'].notna() &
                target.reindex(df.index).notna() &
                (target.reindex(df.index) > df['current_price'] * 1.03)  # at least 3% upside
            )

            if valid.any():
                cp_valid = df.loc[valid, 'current_price']
                tgt_valid = target.reindex(df.index).loc[valid]

                df.loc[valid, 'entry_price'] = cp_valid.round(2)
                df.loc[valid, 'stop_loss'] = (cp_valid * 0.92).round(2)
                df.loc[valid, 'exit_price'] = tgt_valid.round(2)

                risk = cp_valid - (cp_valid * 0.92)
                reward = tgt_valid - cp_valid
                df.loc[valid, 'risk_reward'] = (reward / risk.replace(0, np.nan)).round(2)

                print(f"✅ Calculated entry/exit prices for {valid.sum()} opportunities (positive upside only)")

        return df

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
        latest_csv_path = Path("docs/reports/vcp/latest.csv")

        # Buscar archivos timestamped en ubicación estandarizada
        vcp_files = list(Path("docs/reports/vcp").glob("vcp_calibrated_results_*.csv"))
        if not vcp_files:
            vcp_files = list(Path(".").glob("vcp_calibrated_results_*.csv"))

        # Decidir qué archivo usar: el más reciente por fecha de modificación
        # (compara timestamped vs latest.csv)
        use_latest_csv = False
        chosen_file = None

        if vcp_files:
            newest_timestamped = sorted(vcp_files)[-1]
            if latest_csv_path.exists():
                # Usar latest.csv si es más reciente que el último timestamped
                if latest_csv_path.stat().st_mtime > newest_timestamped.stat().st_mtime:
                    use_latest_csv = True
                    chosen_file = latest_csv_path
                else:
                    chosen_file = newest_timestamped
            else:
                chosen_file = newest_timestamped
        elif latest_csv_path.exists():
            use_latest_csv = True
            chosen_file = latest_csv_path

        if chosen_file:
            import os
            from datetime import datetime as dt
            df = pd.read_csv(chosen_file)

            if use_latest_csv:
                # Usar fecha de modificación del archivo
                mtime = chosen_file.stat().st_mtime
                scan_date = dt.fromtimestamp(mtime).strftime('%Y-%m-%d')
                scan_time = dt.fromtimestamp(mtime).strftime('%H:%M')
            else:
                # Extraer fecha del nombre: vcp_calibrated_results_YYYYMMDD_HHMMSS.csv
                filename = chosen_file.stem
                parts = filename.split('_')
                if len(parts) >= 4:
                    date_str = parts[3]
                    time_str = parts[4] if len(parts) > 4 else "000000"
                    scan_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                    scan_time = f"{time_str[:2]}:{time_str[2:4]}"
                else:
                    scan_date = "Unknown"
                    scan_time = ""

            return {
                'pattern_count': len(df),
                'scan_date': scan_date,
                'scan_time': scan_time,
                'filename': chosen_file.name
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

    def _generate_html(self, sector_data, opportunities_data, backtest_data, insights, vcp_metadata=None, value_data=None, momentum_data=None):
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

        <!-- DUAL STRATEGY SECTIONS -->
        {self._generate_dual_strategy_html(value_data or [], momentum_data or [])}

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

        <!-- Buscar Ticker -->
        <div class="section-card" id="buscar-ticker-section">
            <h2 class="section-title">🔍 Analizar Ticker</h2>
            <p style="color: #666; margin-bottom: 20px; font-size: 0.95em;">
                Introduce cualquier ticker para obtener su puntuación y tesis de inversión completa
                (VCP + ML + Fundamentales + filtros Minervini).
                En local requiere ejecutar <code style="background:#f1f5f9; padding:2px 6px; border-radius:4px;">python3 ticker_api.py</code> en una terminal.
            </p>

            <!-- Formulario de búsqueda -->
            <div style="display: flex; gap: 12px; flex-wrap: wrap; align-items: center; margin-bottom: 20px;">
                <input
                    id="tickerInput"
                    type="text"
                    placeholder="AAPL, NVDA, MSFT…"
                    maxlength="10"
                    style="flex: 1; min-width: 180px; max-width: 280px; padding: 12px 16px; font-size: 1.1em; font-weight: bold; border: 2px solid #667eea; border-radius: 10px; outline: none; text-transform: uppercase; letter-spacing: 1px;"
                    onkeydown="if(event.key==='Enter') analyzeTickerBtn();"
                />
                <button
                    onclick="analyzeTickerBtn()"
                    id="analyzeBtn"
                    style="padding: 12px 28px; background: #667eea; color: white; border: none; border-radius: 10px; font-size: 1em; font-weight: bold; cursor: pointer; transition: background 0.2s;"
                    onmouseover="this.style.background='#5a67d8'"
                    onmouseout="this.style.background='#667eea'"
                >
                    🔍 Analizar
                </button>
                <button
                    onclick="document.getElementById('tickerResult').style.display='none'; document.getElementById('tickerInput').value='';"
                    style="padding: 12px 16px; background: #e2e8f0; color: #4a5568; border: none; border-radius: 10px; font-size: 0.9em; cursor: pointer;"
                >
                    ✕ Limpiar
                </button>
            </div>

            <!-- Estado / loading -->
            <div id="tickerStatus" style="display:none; color:#667eea; font-style:italic; margin-bottom:10px;">
                ⏳ Analizando… (30-60 segundos)
            </div>
            <div id="tickerError" style="display:none; color:#e53e3e; background:#fff5f5; border:1px solid #feb2b2; border-radius:8px; padding:12px; margin-bottom:10px;"></div>

            <!-- Resultado -->
            <div id="tickerResult" style="display:none;"></div>
        </div>

        <script>
        // ── Configuración de API ─────────────────────────────────────────
        // Si tienes la API desplegada en Railway/Render, pon la URL aquí:
        const DEPLOYED_API_URL = 'https://web-production-26e95.up.railway.app';
        const LOCAL_API_URL    = 'http://localhost:5002';

        function getApiBase() {{
            const isLocal = window.location.hostname === 'localhost' ||
                            window.location.hostname === '127.0.0.1' ||
                            window.location.protocol === 'file:';
            if (isLocal) return LOCAL_API_URL;
            if (DEPLOYED_API_URL) return DEPLOYED_API_URL;
            return LOCAL_API_URL;  // fallback: localhost funciona en browsers modernos
        }}

        async function analyzeTickerBtn() {{
            const input = document.getElementById('tickerInput');
            const ticker = input.value.trim().toUpperCase();
            const statusEl = document.getElementById('tickerStatus');
            const errorEl  = document.getElementById('tickerError');
            const resultEl = document.getElementById('tickerResult');
            const btn      = document.getElementById('analyzeBtn');

            if (!ticker || !/^[A-Z0-9.\-]{{1,10}}$/.test(ticker)) {{
                errorEl.textContent = '⚠️ Introduce un ticker válido (ej: AAPL, NVDA, BRK.B)';
                errorEl.style.display = 'block';
                resultEl.style.display = 'none';
                return;
            }}

            const apiBase = getApiBase();

            // Estado loading
            btn.disabled = true;
            btn.textContent = '⏳ Analizando…';
            statusEl.style.display = 'block';
            errorEl.style.display  = 'none';
            resultEl.style.display = 'none';

            try {{
                const res = await fetch(`${{apiBase}}/api/analyze/${{ticker}}`);
                if (!res.ok) {{
                    const err = await res.json().catch(() => ({{}}));
                    throw new Error(err.error || `HTTP ${{res.status}}`);
                }}
                const d = await res.json();
                resultEl.innerHTML = buildResultHTML(d);
                resultEl.style.display = 'block';
            }} catch(e) {{
                let msg = e.message;
                if (msg.includes('Failed to fetch') || msg.includes('NetworkError') || msg.includes('ERR_CONNECTION_REFUSED')) {{
                    const isRemote = !apiBase.includes('localhost');
                    msg = isRemote
                        ? '❌ No se puede conectar a la API desplegada.<br>Verifica que el servidor esté activo o ejecuta <code>python3 ticker_api.py</code> en local.'
                        : '❌ No se puede conectar al servidor local.<br>Ejecuta: <code>python3 ticker_api.py</code>';
                }} else {{
                    msg = `❌ Error: ${{msg}}`;
                }}
                errorEl.innerHTML = msg;
                errorEl.style.display = 'block';
            }} finally {{
                btn.disabled = false;
                btn.textContent = '🔍 Analizar';
                statusEl.style.display = 'none';
            }}
        }}

        function pct(v) {{
            if (v == null) return '—';
            const n = parseFloat(v);
            return isNaN(n) ? '—' : (n >= 0 ? '+' : '') + n.toFixed(1) + '%';
        }}
        function fmt(v, dec=1) {{
            if (v == null) return '—';
            const n = parseFloat(v);
            return isNaN(n) ? '—' : n.toFixed(dec);
        }}
        function price(v) {{
            if (v == null) return '—';
            const n = parseFloat(v);
            return isNaN(n) ? '—' : '$' + n.toFixed(2);
        }}
        function scoreColor(s) {{
            if (s == null) return '#a0aec0';
            if (s >= 75) return '#10b981';
            if (s >= 60) return '#f59e0b';
            if (s >= 40) return '#667eea';
            return '#e53e3e';
        }}
        function adIcon(sig) {{
            const m = {{
                'STRONG_ACCUMULATION': '🟢',
                'ACCUMULATION': '✅',
                'NEUTRAL': '⚪',
                'DISTRIBUTION': '🔴',
                'STRONG_DISTRIBUTION': '🔴🔴',
            }};
            return sig ? (m[sig] || '⚪') : '—';
        }}
        function momIcon(m) {{
            return m === 'improving' ? '📈' : m === 'leading' ? '🚀' : m === 'declining' ? '📉' : '➡️';
        }}
        function maLabel(passes, checks) {{
            if (passes === true)  return '✅ PASA' + (checks ? ' (' + checks + ')' : '');
            if (passes === false) return '❌ NO PASA' + (checks ? ' (' + checks + ')' : '');
            return '—';
        }}
        function rsLineLabel(at_high, trend, pct) {{
            if (at_high === true)             return '🔥 Máximos 52s';
            if (pct != null && pct >= 75)     return '📈 Zona alta';
            if (trend === 'up')               return '↗️ Alcista';
            if (pct != null && pct <= 25)     return '↘️ Zona débil';
            if (pct == null && trend == null) return '—';
            return '➡️ Neutral';
        }}
        function accelLabel(eps_acc, rev_acc, eps_pct, rev_pct) {{
            const epsStr = eps_pct != null ? (eps_pct > 0 ? '+' : '') + eps_pct.toFixed(0) + '% EPS' : null;
            const revStr = rev_pct != null ? (rev_pct > 0 ? '+' : '') + rev_pct.toFixed(0) + '% Rev' : null;
            if (eps_acc === true && rev_acc === true)
                return '🚀 Acelerando ' + [epsStr, revStr].filter(Boolean).join(' · ');
            if (eps_acc === true) return '📈 EPS acelerando' + (epsStr ? ' ' + epsStr : '');
            if (rev_acc === true) return '📈 Rev acelerando' + (revStr ? ' ' + revStr : '');
            if (eps_acc === false && rev_acc === false) return '⚠️ Sin aceleración';
            return '—';
        }}
        function groupRankLabel(rank, total, pct, label) {{
            if (rank == null) return '—';
            const emoji = pct >= 90 ? '🏆' : pct >= 75 ? '📈' : pct <= 25 ? '↘️' : '➡️';
            return `${{emoji}} #${{rank}}/${{total}} (${{label}})`;
        }}

        function trendTemplateLabel(score, pass_) {{
            if (score == null) return '—';
            const color = score >= 7 ? '#10b981' : score >= 5 ? '#f59e0b' : '#e53e3e';
            const emoji = score === 8 ? '⭐' : score >= 7 ? '✅' : score >= 5 ? '⚠️' : '❌';
            return `<span style="color:${{color}}">${{emoji}} ${{score}}/8 criterios${{pass_ ? ' — Stage 2' : ''}}</span>`;
        }}

        function buildResultHTML(d) {{
            const scoreC = scoreColor(d.final_score);
            const hasScore = d.final_score != null;
            const thesisLines = (d.thesis || '').split('\\n').map(l =>
                `<div style="margin:2px 0;">${{l}}</div>`
            ).join('');

            return `
            <div style="border-top:3px solid ${{scoreC}}; padding-top:20px; margin-top:10px;">

                <!-- Header: nombre + score -->
                <div style="display:flex; flex-wrap:wrap; gap:20px; align-items:flex-start; margin-bottom:20px;">
                    <div style="flex:1; min-width:200px;">
                        <div style="font-size:1.6em; font-weight:800; color:#2d3748;">${{d.ticker}}</div>
                        <div style="color:#718096; font-size:0.9em; margin-top:2px;">${{d.company_name}}</div>
                        <div style="margin-top:8px; font-size:0.95em; color:#4a5568;">
                            Precio: <strong>${{price(d.current_price)}}</strong>
                            ${{d.price_target ? '&nbsp;→ Objetivo: <strong>' + price(d.price_target) + '</strong> (<span style="color:' + (d.upside_percent >= 0 ? '#10b981' : '#e53e3e') + '">' + pct(d.upside_percent) + '</span>)' : ''}}
                        </div>
                    </div>
                    <div style="text-align:center; background:${{scoreC}}; color:white; border-radius:16px; padding:16px 28px; min-width:140px;">
                        <div style="font-size:2.2em; font-weight:900; line-height:1;">${{hasScore ? d.final_score.toFixed(1) : '—'}}</div>
                        <div style="font-size:0.75em; opacity:0.9; margin-top:4px;">${{hasScore ? '/ 100' : ''}}</div>
                        <div style="font-size:1em; margin-top:6px;">${{d.tier_emoji || ''}} ${{d.tier_label || ''}}</div>
                    </div>
                </div>

                <!-- Desglose -->
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(160px,1fr)); gap:12px; margin-bottom:20px;">
                    <div style="background:#fef3c7; border-radius:10px; padding:14px; text-align:center;">
                        <div style="font-size:1.5em; font-weight:800; color:#92400e;">${{fmt(d.vcp_score)}}</div>
                        <div style="font-size:0.8em; color:#92400e;">📊 VCP (40%)</div>
                        <div style="font-size:0.75em; color:#b45309; margin-top:4px;">${{d.vcp_contribution != null ? 'contribuye ' + fmt(d.vcp_contribution) + ' pts' : 'sin datos VCP'}}</div>
                    </div>
                    <div style="background:#ede9fe; border-radius:10px; padding:14px; text-align:center;">
                        <div style="font-size:1.5em; font-weight:800; color:#5b21b6;">${{fmt(d.ml_score)}}</div>
                        <div style="font-size:0.8em; color:#5b21b6;">🤖 ML (30%)</div>
                        <div style="font-size:0.75em; color:#7c3aed; margin-top:4px;">${{d.ml_contribution != null ? 'contribuye ' + fmt(d.ml_contribution) + ' pts' : 'sin datos ML'}}</div>
                    </div>
                    <div style="background:#d1fae5; border-radius:10px; padding:14px; text-align:center;">
                        <div style="font-size:1.5em; font-weight:800; color:#065f46;">${{fmt(d.fund_score)}}</div>
                        <div style="font-size:0.8em; color:#065f46;">📈 Fund. (30%)</div>
                        <div style="font-size:0.75em; color:#047857; margin-top:4px;">${{d.fund_contribution != null ? 'contribuye ' + fmt(d.fund_contribution) + ' pts' : 'sin datos fund.'}}</div>
                    </div>
                    ${{d.penalty > 0 ? `<div style="background:#fee2e2; border-radius:10px; padding:14px; text-align:center;">
                        <div style="font-size:1.5em; font-weight:800; color:#991b1b;">-${{d.penalty}}</div>
                        <div style="font-size:0.8em; color:#991b1b;">⚠️ Penalización</div>
                        <div style="font-size:0.75em; color:#b91c1c; margin-top:4px;">filtros técnicos</div>
                    </div>` : ''}}
                </div>

                <!-- Filtros + detalles en grid -->
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(250px,1fr)); gap:16px; margin-bottom:20px;">

                    <!-- Filtros técnicos -->
                    <div style="background:#f7fafc; border-radius:10px; padding:16px;">
                        <div style="font-weight:700; color:#2d3748; margin-bottom:10px;">🛡️ Filtros Técnicos</div>
                        <table style="width:100%; font-size:0.88em; border-collapse:collapse;">
                            <tr><td style="padding:4px 0; color:#718096;">Minervini Template</td>
                                <td style="text-align:right;">${{maLabel(d.ma_passes, d.ma_checks)}}</td></tr>
                            <tr><td style="padding:4px 0; color:#718096;">Acum./Distribución</td>
                                <td style="text-align:right;">${{adIcon(d.ad_signal)}} ${{d.ad_signal || '—'}}</td></tr>
                            <tr><td style="padding:4px 0; color:#718096;">RS Line (Minervini)</td>
                                <td style="text-align:right;">${{rsLineLabel(d.rs_line_at_high, d.rs_line_trend, d.rs_line_percentile)}}</td></tr>
                            <tr><td style="padding:4px 0; color:#718096;">Sector</td>
                                <td style="text-align:right;">${{d.sector_name || '—'}} ${{d.sector_score != null ? '(' + fmt(d.sector_score, 0) + ')' : ''}}</td></tr>
                            <tr><td style="padding:4px 0; color:#718096;">Sector momentum</td>
                                <td style="text-align:right;">${{momIcon(d.sector_momentum)}} ${{d.sector_momentum}}</td></tr>
                            <tr><td style="padding:4px 0; color:#718096;">Grupo Industrial</td>
                                <td style="text-align:right;">${{groupRankLabel(d.industry_group_rank, d.industry_group_total, d.industry_group_percentile, d.industry_group_label)}}</td></tr>
                            <tr><td style="padding:4px 0; color:#718096;">Trend Template</td>
                                <td style="text-align:right;">${{trendTemplateLabel(d.trend_template_score, d.trend_template_pass)}}</td></tr>
                        </table>
                    </div>

                    <!-- VCP -->
                    <div style="background:#f7fafc; border-radius:10px; padding:16px;">
                        <div style="font-weight:700; color:#2d3748; margin-bottom:10px;">📊 VCP / Técnico</div>
                        <table style="width:100%; font-size:0.88em; border-collapse:collapse;">
                            <tr><td style="padding:4px 0; color:#718096;">Estado</td>
                                <td style="text-align:right;">${{d.vcp_ready ? '✅ Listo para compra' : '⏳ En formación'}}</td></tr>
                            <tr><td style="padding:4px 0; color:#718096;">Contracciones</td>
                                <td style="text-align:right;">${{d.vcp_contractions}}</td></tr>
                            ${{d.vcp_breakout_potential != null ? `<tr><td style="padding:4px 0; color:#718096;">Potencial BK</td><td style="text-align:right;">${{fmt(d.vcp_breakout_potential)}}%</td></tr>` : ''}}
                            ${{d.vcp_stage ? `<tr><td style="padding:4px 0; color:#718096;">Stage</td><td style="text-align:right;">${{d.vcp_stage}}</td></tr>` : ''}}
                            ${{d.ml_quality ? `<tr><td style="padding:4px 0; color:#718096;">ML Quality</td><td style="text-align:right;">${{d.ml_quality}}</td></tr>` : ''}}
                            ${{d.entry_score != null ? `<tr><td style="padding:4px 0; color:#718096;">Entry score</td><td style="text-align:right;">${{fmt(d.entry_score)}}/100</td></tr>` : ''}}
                        </table>
                    </div>

                    <!-- Fundamentales -->
                    <div style="background:#f7fafc; border-radius:10px; padding:16px;">
                        <div style="font-weight:700; color:#2d3748; margin-bottom:10px;">📈 Fundamentales</div>
                        <table style="width:100%; font-size:0.88em; border-collapse:collapse;">
                            ${{d.forward_pe != null ? `<tr><td style="padding:4px 0; color:#718096;">Forward P/E</td><td style="text-align:right;">${{fmt(d.forward_pe)}}x</td></tr>` : ''}}
                            ${{d.peg_ratio != null ? `<tr><td style="padding:4px 0; color:#718096;">PEG Ratio</td><td style="text-align:right;">${{fmt(d.peg_ratio, 2)}}</td></tr>` : ''}}
                            ${{d.roe != null ? `<tr><td style="padding:4px 0; color:#718096;">ROE</td><td style="text-align:right;">${{pct(d.roe * 100)}}</td></tr>` : ''}}
                            ${{d.revenue_growth != null ? `<tr><td style="padding:4px 0; color:#718096;">Revenue Growth</td><td style="text-align:right;">${{pct(d.revenue_growth * 100)}}</td></tr>` : ''}}
                            ${{d.fcf_yield != null ? `<tr><td style="padding:4px 0; color:#718096;">FCF Yield</td><td style="text-align:right;">${{fmt(d.fcf_yield)}}%</td></tr>` : ''}}
                            ${{d.debt_to_equity != null ? `<tr><td style="padding:4px 0; color:#718096;">Deuda/Capital</td><td style="text-align:right;">${{fmt(d.debt_to_equity, 2)}}</td></tr>` : ''}}
                            <tr><td style="padding:4px 0; color:#718096;">Aceleración (CANSLIM A)</td>
                                <td style="text-align:right;">${{accelLabel(d.eps_accelerating, d.rev_accelerating, d.eps_growth_yoy, d.rev_growth_yoy)}}</td></tr>
                            ${{d.short_percent_float != null ? `<tr><td style="padding:4px 0; color:#718096;">Short Interest</td>
                                <td style="text-align:right;">${{d.short_percent_float.toFixed(1)}}% float${{d.short_squeeze_potential ? ' 🔥' : ''}}</td></tr>` : ''}}
                            ${{d.proximity_to_52w_high != null ? `<tr><td style="padding:4px 0; color:#718096;">Dist. Máx. 52s</td>
                                <td style="text-align:right; color:${{d.proximity_to_52w_high >= -10 ? '#10b981' : d.proximity_to_52w_high >= -25 ? '#f59e0b' : '#e53e3e'}}">
                                ${{d.proximity_to_52w_high.toFixed(1)}}%${{d.proximity_to_52w_high >= -5 ? ' 🎯' : d.proximity_to_52w_high >= -15 ? ' 📈' : d.proximity_to_52w_high < -30 ? ' ⚠️' : ''}}</td></tr>` : ''}}
                        </table>
                    </div>
                </div>

                <!-- Tesis -->
                <div style="background:#f0f4ff; border-left:4px solid #667eea; border-radius:0 10px 10px 0; padding:16px; margin-bottom:12px;">
                    <div style="font-weight:700; color:#434190; margin-bottom:8px;">💡 Tesis de Inversión</div>
                    <div style="font-size:0.9em; color:#4a5568; line-height:1.6;">${{thesisLines}}</div>
                </div>

                <div style="font-size:0.78em; color:#a0aec0; text-align:right;">
                    Análisis generado: ${{d.analysis_time}} · Tiempo: ${{d.elapsed_seconds}}s ·
                    ⚠️ Solo fines educativos, no es consejo financiero.
                </div>
            </div>`;
        }}
        </script>

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

    def _fmt_price(self, price) -> str:
        """Formatea precio o devuelve '—'"""
        try:
            return f'${float(price):.2f}' if price not in ['', None] else '—'
        except (ValueError, TypeError):
            return '—'

    def _fmt_optional(self, val, fmt: str) -> str:
        """Formatea un valor opcional o devuelve '—'"""
        try:
            return fmt.format(float(val)) if val not in ['', None] else '—'
        except (ValueError, TypeError):
            return '—'

    def _score_bar(self, score: float, color: str) -> str:
        """Mini barra de progreso para score"""
        pct = min(max(float(score), 0), 100)
        return f'<div style="height:6px;background:#e2e8f0;border-radius:3px;margin-top:4px;"><div style="width:{pct:.0f}%;height:100%;background:{color};border-radius:3px;"></div></div>'

    def _value_row_html(self, d: dict) -> str:
        """Genera fila HTML para una oportunidad value"""
        ticker  = d.get('ticker', '')
        company = str(d.get('company_name', ticker))[:22]
        score   = float(d.get('value_score', 0))
        sector  = str(d.get('sector', ''))[:18]
        options = d.get('sentiment', '')
        mr      = '✓' if float(d.get('mr_bonus', 0) or 0) > 0 else ''
        sect_b  = '✓' if float(d.get('sector_bonus', 0) or 0) > 0 else ''

        if options == 'BULLISH':
            options_badge = '<span style="color:#10b981;font-size:0.75em;">▲ CALL</span>'
        elif options == 'BEARISH':
            options_badge = '<span style="color:#ef4444;font-size:0.75em;">▼ PUT</span>'
        else:
            options_badge = ''

        if score >= 40:
            color = '#10b981'
        elif score >= 30:
            color = '#f59e0b'
        else:
            color = '#94a3b8'

        price_str = self._fmt_price(d.get('current_price', ''))

        return f'''<tr style="border-bottom:1px solid #f1f5f9;">
            <td style="padding:10px 8px;font-weight:700;color:#1e293b;">{ticker}</td>
            <td style="padding:10px 8px;color:#64748b;font-size:0.85em;">{company}</td>
            <td style="padding:10px 8px;">{price_str}</td>
            <td style="padding:10px 8px;min-width:90px;">
                <span style="font-weight:700;color:{color};">{score:.1f}</span>
                {self._score_bar(score, color)}
            </td>
            <td style="padding:10px 8px;color:#64748b;font-size:0.82em;">{sector}</td>
            <td style="padding:10px 8px;text-align:center;">{options_badge}</td>
            <td style="padding:10px 8px;text-align:center;color:#8b5cf6;font-size:0.82em;">{sect_b}</td>
            <td style="padding:10px 8px;text-align:center;color:#f59e0b;font-size:0.82em;">{mr}</td>
        </tr>'''

    def _momentum_row_html(self, d: dict) -> str:
        """Genera fila HTML para un setup de momentum"""
        ticker  = d.get('ticker', '')
        company = str(d.get('company_name', ticker))[:22]
        score   = float(d.get('momentum_score', 0))
        vcp     = float(d.get('vcp_score', 0) or 0)

        if score >= 75:
            color = '#10b981'
        elif score >= 65:
            color = '#f59e0b'
        else:
            color = '#94a3b8'

        price_str = self._fmt_price(d.get('current_price', ''))
        prox_str  = self._fmt_optional(d.get('proximity_to_52w_high', ''), '{:.1f}%')
        trend_str = self._fmt_optional(d.get('trend_template_score', ''), '{:.0f}/8')

        return f'''<tr style="border-bottom:1px solid #f1f5f9;">
            <td style="padding:10px 8px;font-weight:700;color:#1e293b;">{ticker}</td>
            <td style="padding:10px 8px;color:#64748b;font-size:0.85em;">{company}</td>
            <td style="padding:10px 8px;">{price_str}</td>
            <td style="padding:10px 8px;min-width:90px;">
                <span style="font-weight:700;color:{color};">{score:.1f}</span>
                {self._score_bar(score, color)}
            </td>
            <td style="padding:10px 8px;text-align:center;color:#6366f1;font-weight:600;">{vcp:.0f}</td>
            <td style="padding:10px 8px;text-align:center;color:#64748b;font-size:0.85em;">{prox_str}</td>
            <td style="padding:10px 8px;text-align:center;color:#64748b;font-size:0.85em;">{trend_str}</td>
        </tr>'''

    def _generate_dual_strategy_html(self, value_data: list, momentum_data: list) -> str:
        """Genera HTML para las 2 secciones: Value Opportunities + Momentum Plays"""

        if value_data:
            value_rows = ''.join(self._value_row_html(d) for d in value_data)
        else:
            value_rows = '<tr><td colspan="8" style="padding:20px;text-align:center;color:#94a3b8;">No hay oportunidades value en este momento</td></tr>'

        if momentum_data:
            momentum_rows = ''.join(self._momentum_row_html(d) for d in momentum_data)
        else:
            momentum_rows = '<tr><td colspan="7" style="padding:20px;text-align:center;color:#94a3b8;">No hay setups de momentum en este momento</td></tr>'

        return f'''
        <!-- ═══════════════════════════════════════════════════════════ -->
        <!-- DUAL STRATEGY SECTION                                       -->
        <!-- ═══════════════════════════════════════════════════════════ -->
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px;">

            <!-- SECTION A: VALUE OPPORTUNITIES -->
            <div class="section-card" style="border-top:3px solid #10b981;">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
                    <div>
                        <h2 class="section-title" style="margin:0;color:#065f46;">Oportunidades Value</h2>
                        <p style="margin:4px 0 0;font-size:0.82em;color:#64748b;">Empresas sólidas con precio circunstancialmente bajo · Insiders + Institucionales + Sector</p>
                    </div>
                    <span style="background:#d1fae5;color:#065f46;padding:4px 10px;border-radius:20px;font-size:0.82em;font-weight:600;">{len(value_data)} candidatas</span>
                </div>
                <div style="overflow-x:auto;">
                    <table style="width:100%;border-collapse:collapse;font-size:0.88em;">
                        <thead>
                            <tr style="background:#f8fafc;border-bottom:2px solid #e2e8f0;">
                                <th style="padding:8px;text-align:left;color:#475569;font-weight:600;">Ticker</th>
                                <th style="padding:8px;text-align:left;color:#475569;font-weight:600;">Empresa</th>
                                <th style="padding:8px;text-align:left;color:#475569;font-weight:600;">Precio</th>
                                <th style="padding:8px;text-align:left;color:#475569;font-weight:600;">Score</th>
                                <th style="padding:8px;text-align:left;color:#475569;font-weight:600;">Sector</th>
                                <th style="padding:8px;text-align:center;color:#475569;font-weight:600;">Opciones</th>
                                <th style="padding:8px;text-align:center;color:#475569;font-weight:600;" title="Sector rotation bonus">S.Rot</th>
                                <th style="padding:8px;text-align:center;color:#475569;font-weight:600;" title="Mean reversion signal">M.Rev</th>
                            </tr>
                        </thead>
                        <tbody>{value_rows}</tbody>
                    </table>
                </div>
            </div>

            <!-- SECTION B: MOMENTUM PLAYS -->
            <div class="section-card" style="border-top:3px solid #6366f1;">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
                    <div>
                        <h2 class="section-title" style="margin:0;color:#3730a3;">Momentum Plays</h2>
                        <p style="margin:4px 0 0;font-size:0.82em;color:#64748b;">Patrones VCP · Breakouts · Tendencias confirmadas (backtest en proceso)</p>
                    </div>
                    <span style="background:#e0e7ff;color:#3730a3;padding:4px 10px;border-radius:20px;font-size:0.82em;font-weight:600;">{len(momentum_data)} setups</span>
                </div>
                <div style="overflow-x:auto;">
                    <table style="width:100%;border-collapse:collapse;font-size:0.88em;">
                        <thead>
                            <tr style="background:#f8fafc;border-bottom:2px solid #e2e8f0;">
                                <th style="padding:8px;text-align:left;color:#475569;font-weight:600;">Ticker</th>
                                <th style="padding:8px;text-align:left;color:#475569;font-weight:600;">Empresa</th>
                                <th style="padding:8px;text-align:left;color:#475569;font-weight:600;">Precio</th>
                                <th style="padding:8px;text-align:left;color:#475569;font-weight:600;">Score</th>
                                <th style="padding:8px;text-align:center;color:#475569;font-weight:600;">VCP</th>
                                <th style="padding:8px;text-align:center;color:#475569;font-weight:600;">Dist.Máx</th>
                                <th style="padding:8px;text-align:center;color:#475569;font-weight:600;">Tendencia</th>
                            </tr>
                        </thead>
                        <tbody>{momentum_rows}</tbody>
                    </table>
                </div>
            </div>

        </div>
        '''

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
            rs_at_high = opp.get('rs_line_at_new_high', False)
            rs_line_badge = '<span title="RS Line en máximos 52 semanas (Minervini)">📡</span>' if rs_at_high is True else ''
            both_accel = (opp.get('eps_accelerating') is True and opp.get('rev_accelerating') is True)
            canslim_badge = '<span title="EPS + Revenue acelerando (CANSLIM A)">🚀</span>' if both_accel else ''
            tt_score = opp.get('trend_template_score')
            tt_badge = '<span title="Minervini Trend Template 8/8 — Stage 2 perfecto">⭐</span>' if tt_score == 8 else ''

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

            # Entry/Exit prices (if available)
            entry_price = opp.get('entry_price')
            stop_loss = opp.get('stop_loss')
            exit_price = opp.get('exit_price')
            risk_reward = opp.get('risk_reward')
            entry_timing = opp.get('entry_timing', '')

            # Format entry/exit columns
            if entry_price and not pd.isna(entry_price):
                entry_cell = f'<span class="price-cell" title="{entry_timing}">${entry_price:.2f}</span>'
                stop_cell = f'<span class="price-cell" style="color: var(--danger);">${stop_loss:.2f}</span>' if stop_loss else 'N/A'
                exit_cell = f'<span class="price-cell" style="color: var(--success);">${exit_price:.2f}</span>' if exit_price else 'N/A'
                rr_class = 'good-rr' if risk_reward and risk_reward >= 3 else 'poor-rr'
                rr_cell = f'<span class="{rr_class}">{risk_reward:.1f}:1</span>' if risk_reward else 'N/A'
            else:
                entry_cell = stop_cell = exit_cell = rr_cell = '<span style="color: var(--text-muted);">-</span>'

            rows.append(f"""
            <tr>
                <td>{ticker_display}</td>
                <td><span class="score-badge {score_class}">{score:.1f}</span></td>
                <td>{opp.get('tier', 'N/A')}</td>
                <td>{sector}</td>
                <td><span class="component-score" title="VCP Pattern (40%)">{vcp_score:.0f}</span></td>
                <td><span class="component-score" title="ML Predictive (30%)">{ml_score:.0f}</span></td>
                <td><span class="component-score" title="Fundamentals (30%)">{fundamental_score:.0f}</span></td>
                <td>{entry_cell}</td>
                <td>{stop_cell}</td>
                <td>{exit_cell}</td>
                <td>{rr_cell}</td>
                <td><span title="{ma_reason}">{ma_badge}</span></td>
                <td><span title="{ad_signal}">{ad_emoji}</span></td>
                <td><span title="{filter_tooltip}">{filters_passed}</span></td>
                <td>{insiders_score:.0f}</td>
                <td>{validation_badge}</td>
                <td>{timing_badge} {repeater_badge} {rs_line_badge} {canslim_badge} {tt_badge}</td>
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
                <div style="background: var(--glass-primary-dim); padding: 0.25rem 0.5rem; border-radius: 4px;"><strong>Entry:</strong> Precio óptimo de entrada (VCP pivot + soporte)</div>
                <div style="background: var(--glass-primary-dim); padding: 0.25rem 0.5rem; border-radius: 4px;"><strong>Stop:</strong> Stop loss técnico (máx 8%)</div>
                <div style="background: var(--glass-primary-dim); padding: 0.25rem 0.5rem; border-radius: 4px;"><strong>Target:</strong> Precio objetivo (fair value + resistencia)</div>
                <div style="background: var(--glass-primary-dim); padding: 0.25rem 0.5rem; border-radius: 4px;"><strong>R/R:</strong> Ratio Risk/Reward (mín 3:1 recomendado)</div>
                <div><strong>MA:</strong> Minervini Trend Template - ✅ Pass | ❌ Fail</div>
                <div><strong>A/D:</strong> Acumulación/Distribución - 🟢 Strong Acc | 🟡 Acc | ⚪ Neutral | 🟠 Dist | 🔴 Strong Dist</div>
                <div><strong>Filt:</strong> Filtros pasados (Market + MA + A/D) - X/3</div>
                <div><strong>Ins:</strong> Actividad insider trading</div>
                <div><strong>Val:</strong> Validación web - ✅ BUY (good entry) | ⚠️ HOLD (wait) | ❌ AVOID (near ATH)</div>
                <div><strong>Timing:</strong> 🔥 Timing convergencia | 🔁 VCP recurrente | 📡 RS Line en máximos 52s | 🚀 EPS+Rev acelerando (CANSLIM A) | ⭐ Trend Template 8/8</div>
                <div><strong>Timing:</strong> 🔥 Convergencia temporal | 🔁 VCP recurrente</div>
            </div>
        </div>
        """

        return legend_html + f"""
        <div class="opportunities-table-container" style="overflow-x: auto; -webkit-overflow-scrolling: touch;">
            <table class="opportunities-table" style="min-width: 1100px;">
                <thead>
                    <tr>
                        <th>Ticker / Company</th>
                        <th title="Super Score Ultimate with Filters Applied">Score</th>
                        <th title="Quality Tier">Tier</th>
                        <th>Sector</th>
                        <th title="VCP Pattern Score (40%)">VCP</th>
                        <th title="ML Predictive Score (30%)">ML</th>
                        <th title="Fundamental Score (30%)">Fund</th>
                        <th title="Optimal entry price (VCP pivot + support)" style="background: #8b9cf4;">Entry</th>
                        <th title="Stop loss (technical support, max 8%)" style="background: #8b9cf4;">Stop</th>
                        <th title="Target exit price (fair value + resistance)" style="background: #8b9cf4;">Target</th>
                        <th title="Risk/Reward ratio (min 3:1)" style="background: #8b9cf4;">R/R</th>
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
