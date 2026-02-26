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
        eu_value_data = self._load_eu_value_opportunities()
        tracker_data = self._load_tracker_summary()

        # Generate integrated insights
        insights = self._generate_insights(sector_data, opportunities_data, backtest_data, vcp_repeaters)

        # Generate HTML
        html = self._generate_html(sector_data, opportunities_data, backtest_data, insights, vcp_metadata, value_data, momentum_data, tracker_data, eu_value_data)

        # Save
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"✅ Dashboard generado: {output_file}")

    def _load_tracker_summary(self) -> dict:
        """Load portfolio tracker summary"""
        path = Path('docs/portfolio_tracker/summary.json')
        if path.exists():
            try:
                with open(path) as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _load_theses(self) -> dict:
        """Carga tesis de inversión desde docs/theses.json"""
        theses_path = Path("docs/theses.json")
        if not theses_path.exists():
            return {}
        try:
            with open(theses_path) as f:
                return json.load(f)
        except Exception:
            return {}

    def _load_value_opportunities(self):
        """
        Carga oportunidades VALUE (Sección A - Principal)
        Prioriza el archivo filtrado por IA si existe
        """
        # Try AI-filtered version first (high-quality opportunities only)
        filtered_path = Path("docs/value_opportunities_filtered.csv")
        if filtered_path.exists():
            print("📊 Using AI-filtered VALUE opportunities")
            path = filtered_path
        else:
            print("⚠️  Using unfiltered VALUE opportunities (run ai_quality_filter.py)")
            path = Path("docs/value_opportunities.csv")

        if not path.exists():
            return []
        try:
            df = pd.read_csv(path)
            df['value_score'] = pd.to_numeric(df.get('value_score', 0), errors='coerce').fillna(0)
            records = df.sort_values('value_score', ascending=False).head(15).to_dict('records')
            theses = self._load_theses()
            for r in records:
                ticker = r.get('ticker', '')
                # Buscar tesis VALUE específica primero, luego genérica
                t = theses.get(f'{ticker}__value', theses.get(ticker, {}))
                r['thesis_narrative'] = t.get('thesis_narrative', '')
                r['thesis_signals'] = t.get('technical', {}).get('signals', [])
                r['thesis_catalysts_insiders'] = t.get('catalysts', {}).get('insiders', [])
            return records
        except Exception:
            return []

    def _load_momentum_opportunities(self):
        """Prioriza el archivo filtrado por IA si existe"""
        filtered_path = Path("docs/momentum_opportunities_filtered.csv")
        if filtered_path.exists():
            print("📊 Using AI-filtered MOMENTUM opportunities")
            path = filtered_path
        else:
            print("⚠️  Using unfiltered MOMENTUM opportunities")
            path = Path("docs/momentum_opportunities.csv")

        if not path.exists():
            return []
        try:
            df = pd.read_csv(path)
            df['momentum_score'] = pd.to_numeric(df.get('momentum_score', 0), errors='coerce').fillna(0)
            records = df.sort_values('momentum_score', ascending=False).head(15).to_dict('records')
            theses = self._load_theses()
            for r in records:
                ticker = r.get('ticker', '')
                # Buscar tesis MOMENTUM específica primero, luego genérica
                t = theses.get(f'{ticker}__momentum', theses.get(ticker, {}))
                r['thesis_narrative'] = t.get('thesis_narrative', '')
                r['thesis_signals'] = t.get('technical', {}).get('signals', [])
                r['thesis_catalysts_insiders'] = t.get('catalysts', {}).get('insiders', [])
            return records
        except Exception:
            return []

    def _load_eu_value_opportunities(self):
        """Carga oportunidades VALUE europeas"""
        filtered_path = Path("docs/european_value_opportunities_filtered.csv")
        if filtered_path.exists():
            print("📊 Using AI-filtered EUROPEAN VALUE opportunities")
            path = filtered_path
        else:
            path = Path("docs/european_value_opportunities.csv")

        if not path.exists():
            return []
        try:
            df = pd.read_csv(path)
            df['value_score'] = pd.to_numeric(df.get('value_score', 0), errors='coerce').fillna(0)
            return df.sort_values('value_score', ascending=False).head(15).to_dict('records')
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
        Carga oportunidades del sistema integrado (VCP + ML + Fundamental)

        Strategy: Hybrid merge
        1. Load super_scores_ultimate.csv (VCP + ML + Fundamental combined)
        2. Merge with super_opportunities_5d_complete.csv for enrichment
        3. Merge with super_opportunities_with_prices.csv for entry/exit (if exists)
        4. Use ultimate score as PRIMARY while keeping 5D features
        """
        ultimate_file = Path("docs/super_scores_ultimate.csv")
        opps_5d_file = Path("docs/super_opportunities_5d_complete.csv")

        # Try to load integrated score data (preferred)
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

            if len(filtered) == 0:
                print("ℹ️  No hay oportunidades con score >= 55 en super_scores_ultimate.")

            filtered.attrs['total_count'] = total_count
            return filtered

        elif opps_5d_file.exists():
            df = pd.read_csv(opps_5d_file)
            total_count = len(df)
            filtered = df[df['super_score_5d'] >= 55].copy()
            filtered = self._fill_missing_prices(filtered)
            filtered.attrs['total_count'] = total_count
            return filtered

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
                    'title': f"{len(repeater_opps)} VCP Recurrentes — Historial comprobado",
                    'description': f"Estos stocks formaron patrones VCP múltiples veces. Mayor probabilidad de éxito.",
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
                        'title': f"{len(sector_opps)} oportunidades 5D en {sector_name} (sector líder)",
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
                            'title': f"{len(sector_opps)} setups con buen timing en {sector_name} (sector emergente)",
                            'description': f"Sector saliendo de debilidad con convergencia temporal",
                            'tickers': sector_opps['ticker'].tolist()[:5],
                            'priority': 'HIGH'
                        })

        # Backtest validation
        if backtest_data:
            win_rate = backtest_data.get('win_rate', 0)
            if win_rate >= 70:
                insights.append({
                    'type': 'VALIDATION',
                    'title': f"Estrategia validada: {win_rate:.1f}% win rate",
                    'description': f"El backtest histórico confirma la efectividad del sistema",
                    'priority': 'INFO'
                })

        return insights

    def _generate_html(self, sector_data, opportunities_data, backtest_data, insights, vcp_metadata=None, value_data=None, momentum_data=None, tracker_data=None, eu_value_data=None):
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
    <title>Stock Analyzer — Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0e27;
            background-image:
                radial-gradient(at 20% 30%, rgba(120, 119, 198, 0.12) 0px, transparent 50%),
                radial-gradient(at 80% 70%, rgba(99, 102, 241, 0.12) 0px, transparent 50%);
            min-height: 100vh;
            padding: 20px;
            color: #ffffff;
        }}

        .container {{
            max-width: 1800px;
            margin: 0 auto;
        }}

        .header {{
            text-align: center;
            color: white;
            margin-bottom: 40px;
            padding: 20px 0;
        }}

        .header h1 {{
            font-size: 3em;
            margin-bottom: 16px;
            font-weight: 800;
            letter-spacing: -0.04em;
            color: #ffffff;
            text-shadow: 0 4px 30px rgba(99, 102, 241, 0.5);
        }}

        .header .subtitle {{
            font-size: 1.3em;
            color: rgba(255, 255, 255, 0.7);
            font-weight: 500;
        }}

        .quick-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .stat-card {{
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(40px) saturate(180%);
            -webkit-backdrop-filter: blur(40px) saturate(180%);
            border: 1px solid rgba(255, 255, 255, 0.18);
            border-radius: 24px;
            padding: 28px;
            box-shadow:
                0 8px 32px rgba(0, 0, 0, 0.37),
                inset 0 1px 0 rgba(255, 255, 255, 0.1);
            text-align: center;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        }}

        .stat-card:hover {{
            transform: translateY(-6px);
            box-shadow:
                0 20px 60px rgba(0, 0, 0, 0.5),
                inset 0 1px 0 rgba(255, 255, 255, 0.15);
            background: rgba(255, 255, 255, 0.08);
            border-color: rgba(255, 255, 255, 0.25);
        }}

        .stat-value {{
            font-size: 3em;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 10px;
            letter-spacing: -0.03em;
            text-shadow: 0 2px 20px rgba(99, 102, 241, 0.5);
        }}

        .stat-label {{
            color: rgba(255, 255, 255, 0.65);
            text-transform: uppercase;
            font-size: 0.8em;
            letter-spacing: 2px;
            font-weight: 600;
        }}

        .insights-section {{
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(40px) saturate(180%);
            -webkit-backdrop-filter: blur(40px) saturate(180%);
            border: 1px solid rgba(255, 255, 255, 0.18);
            border-radius: 24px;
            padding: 36px;
            margin-bottom: 30px;
            box-shadow:
                0 8px 32px rgba(0, 0, 0, 0.37),
                inset 0 1px 0 rgba(255, 255, 255, 0.1);
        }}

        .insight-item {{
            padding: 22px;
            margin-bottom: 16px;
            border-radius: 14px;
            border-left: 5px solid;
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(5px);
            transition: all 0.3s ease;
        }}

        .insight-item:hover {{
            transform: translateX(4px);
            background: rgba(255, 255, 255, 0.06);
        }}

        .insight-CRITICAL {{
            background: rgba(251, 191, 36, 0.1);
            border-color: #fbbf24;
            box-shadow: 0 0 20px rgba(251, 191, 36, 0.15);
        }}

        .insight-HIGH {{
            background: rgba(59, 130, 246, 0.1);
            border-color: #3b82f6;
            box-shadow: 0 0 20px rgba(59, 130, 246, 0.15);
        }}

        .insight-INFO {{
            background: rgba(16, 185, 129, 0.1);
            border-color: #10b981;
            box-shadow: 0 0 20px rgba(16, 185, 129, 0.15);
        }}

        .insight-title {{
            font-size: 1.4em;
            font-weight: 700;
            margin-bottom: 14px;
            color: #ffffff;
            letter-spacing: -0.02em;
        }}

        .insight-desc {{
            color: rgba(255, 255, 255, 0.75);
            margin-bottom: 14px;
            line-height: 1.7;
            font-size: 1em;
        }}

        .ticker-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 10px;
        }}

        .ticker-badge {{
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            color: white;
            padding: 6px 14px;
            border-radius: 18px;
            font-weight: 700;
            font-size: 0.88em;
            box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
            transition: all 0.2s ease;
            display: inline-block;
        }}

        .ticker-badge:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
        }}

        .grid-2 {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(800px, 1fr));
            gap: 30px;
            margin-bottom: 30px;
        }}

        .section-card {{
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(40px) saturate(180%);
            -webkit-backdrop-filter: blur(40px) saturate(180%);
            border: 1px solid rgba(255, 255, 255, 0.18);
            border-radius: 24px;
            padding: 36px;
            box-shadow:
                0 8px 32px rgba(0, 0, 0, 0.37),
                inset 0 1px 0 rgba(255, 255, 255, 0.1);
            transition: all 0.4s ease;
        }}

        .section-card:hover {{
            box-shadow:
                0 20px 60px rgba(0, 0, 0, 0.5),
                inset 0 1px 0 rgba(255, 255, 255, 0.15);
            border-color: rgba(255, 255, 255, 0.25);
        }}

        .section-title {{
            font-size: 2em;
            margin-bottom: 28px;
            color: #ffffff;
            font-weight: 700;
            letter-spacing: -0.03em;
            display: flex;
            align-items: center;
            gap: 14px;
        }}

        .section-title::before {{
            content: '';
            width: 5px;
            height: 36px;
            background: linear-gradient(180deg, #6366f1, #8b5cf6);
            border-radius: 3px;
            box-shadow: 0 0 20px rgba(99, 102, 241, 0.6);
        }}

        .opportunities-table {{
            width: 100%;
            border-collapse: collapse;
        }}

        .opportunities-table {{
            background: rgba(255, 255, 255, 0.02);
            border-radius: 16px;
            overflow: hidden;
        }}

        .opportunities-table th {{
            background: rgba(99, 102, 241, 0.15);
            backdrop-filter: blur(10px);
            color: #ffffff;
            padding: 18px 16px;
            text-align: left;
            font-weight: 700;
            font-size: 0.85em;
            text-transform: uppercase;
            letter-spacing: 1px;
            border-bottom: 1px solid rgba(99, 102, 241, 0.3);
        }}

        .opportunities-table th:first-child {{
            border-top-left-radius: 16px;
        }}

        .opportunities-table th:last-child {{
            border-top-right-radius: 16px;
        }}

        .opportunities-table td {{
            padding: 16px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.06);
            color: rgba(255, 255, 255, 0.9);
            font-size: 0.95em;
            font-weight: 500;
        }}

        .opportunities-table tr {{
            transition: all 0.3s ease;
        }}

        .opportunities-table tr:hover {{
            background: rgba(99, 102, 241, 0.08);
        }}

        .opportunities-table tbody tr:last-child td {{
            border-bottom: none;
        }}

        .score-badge {{
            display: inline-block;
            padding: 8px 16px;
            border-radius: 12px;
            font-weight: 700;
            font-size: 0.95em;
            color: #ffffff;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
            transition: all 0.3s ease;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }}

        .score-badge:hover {{
            transform: translateY(-3px);
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.35);
        }}

        .score-high {{
            background: linear-gradient(135deg, #10b981, #059669);
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4);
        }}

        .score-medium {{
            background: linear-gradient(135deg, #3b82f6, #2563eb);
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
        }}

        .timing-badge {{
            background: linear-gradient(135deg, #f59e0b, #d97706);
            color: white;
            padding: 4px 10px;
            border-radius: 16px;
            font-size: 0.8em;
            font-weight: 700;
            box-shadow: 0 2px 6px rgba(245, 158, 11, 0.3);
        }}

        .alert-list {{
            list-style: none;
        }}

        .alert-list li {{
            padding: 16px 18px;
            margin-bottom: 12px;
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.05);
            border-left: 4px solid #6366f1;
            color: #e2e8f0;
            transition: all 0.3s ease;
        }}

        .alert-list li:hover {{
            background: rgba(255, 255, 255, 0.08);
            transform: translateX(4px);
        }}

        .footer {{
            text-align: center;
            color: #cbd5e1;
            margin-top: 60px;
            opacity: 0.7;
            font-size: 0.95em;
        }}

        /* === ANIMATIONS === */
        @keyframes fadeInUp {{
            from {{
                opacity: 0;
                transform: translateY(30px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}

        .stat-card, .section-card, .insights-section {{
            animation: fadeInUp 0.6s ease-out backwards;
        }}

        .stat-card:nth-child(1) {{ animation-delay: 0.1s; }}
        .stat-card:nth-child(2) {{ animation-delay: 0.2s; }}
        .stat-card:nth-child(3) {{ animation-delay: 0.3s; }}
        .stat-card:nth-child(4) {{ animation-delay: 0.4s; }}

        /* === SCROLLBAR STYLING === */
        ::-webkit-scrollbar {{
            width: 10px;
        }}

        ::-webkit-scrollbar-track {{
            background: rgba(255, 255, 255, 0.05);
        }}

        ::-webkit-scrollbar-thumb {{
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            border-radius: 10px;
        }}

        ::-webkit-scrollbar-thumb:hover {{
            background: linear-gradient(135deg, #4f46e5, #7c3aed);
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
                Inicio
            </a>
            <h1>Stock Analyzer</h1>
            <div class="subtitle">Análisis integrado — Value, Momentum, Fundamentales</div>
            <div style="margin-top: 10px; font-size: 0.9em;">
                {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </div>
        </div>

        <!-- Quick Stats -->
        <div class="quick-stats">
            <div class="stat-card" style="background: linear-gradient(135deg, #fef3c7, #fbbf24);">
                <div class="stat-value" style="color: #92400e;">{vcp_metadata['pattern_count'] if vcp_metadata else 0}</div>
                <div class="stat-label" style="color: #92400e;">VCP Patterns</div>
                <div style="font-size: 0.8em; color: #92400e; margin-top: 5px;">{vcp_metadata['scan_date'] if vcp_metadata else 'N/A'}</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{total_opportunities}</div>
                <div class="stat-label">Total 5D Opps</div>
                <div style="font-size: 0.8em; color: rgba(255,255,255,0.5); margin-top: 5px;">Calidad buena+: {filtered_count}</div>
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

        <!-- EUROPEAN VALUE SECTION -->
        {self._generate_eu_value_html(eu_value_data or [])}

        <!-- PORTFOLIO TRACKER -->
        {self._generate_tracker_html(tracker_data or {})}

        <!-- Main Content Grid -->
        <div class="grid-2">
            <!-- Top Opportunities -->
            <div class="section-card">
                <h2 class="section-title">Top Oportunidades 5D</h2>
                {self._generate_opportunities_table(top_opportunities)}
            </div>

            <!-- Sector Alerts -->
            <div class="section-card">
                <h2 class="section-title">Alertas de Rotación Sectorial</h2>
                {self._generate_alerts_html(sector_alerts)}
            </div>
        </div>

        <!-- Buscar Ticker -->
        <div class="section-card" id="buscar-ticker-section">
            <h2 class="section-title">Analizar Ticker</h2>
            <p style="color: rgba(255,255,255,0.6); margin-bottom: 20px; font-size: 0.95em;">
                Introduce cualquier ticker para obtener su puntuación y tesis de inversión completa
                (VCP + ML + Fundamentales + filtros Minervini).
                En local requiere ejecutar <code style="background:rgba(255,255,255,0.1); padding:2px 6px; border-radius:4px; color:#a5b4fc;">python3 ticker_api.py</code> en una terminal.
            </p>

            <!-- Formulario de búsqueda -->
            <div style="display: flex; gap: 12px; flex-wrap: wrap; align-items: center; margin-bottom: 20px;">
                <input
                    id="tickerInput"
                    type="text"
                    placeholder="AAPL, NVDA, MSFT…"
                    maxlength="10"
                    style="flex: 1; min-width: 180px; max-width: 280px; padding: 12px 16px; font-size: 1.1em; font-weight: bold; border: 2px solid rgba(99,102,241,0.5); border-radius: 10px; outline: none; text-transform: uppercase; letter-spacing: 1px; background: rgba(255,255,255,0.05); color: #ffffff;"
                    onkeydown="if(event.key==='Enter') analyzeTickerBtn();"
                />
                <button
                    onclick="analyzeTickerBtn()"
                    id="analyzeBtn"
                    style="padding: 12px 28px; background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; border: none; border-radius: 10px; font-size: 1em; font-weight: bold; cursor: pointer; transition: all 0.3s;"
                    onmouseover="this.style.opacity='0.85'"
                    onmouseout="this.style.opacity='1'"
                >
                    🔍 Analizar
                </button>
                <button
                    onclick="document.getElementById('tickerResult').style.display='none'; document.getElementById('tickerInput').value='';"
                    style="padding: 12px 16px; background: rgba(255,255,255,0.1); color: rgba(255,255,255,0.7); border: 1px solid rgba(255,255,255,0.15); border-radius: 10px; font-size: 0.9em; cursor: pointer;"
                >
                    ✕ Limpiar
                </button>
            </div>

            <!-- Estado / loading -->
            <div id="tickerStatus" style="display:none; color:#a5b4fc; font-style:italic; margin-bottom:10px;">
                ⏳ Analizando… (30-60 segundos)
            </div>
            <div id="tickerError" style="display:none; color:#fca5a5; background:rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.3); border-radius:8px; padding:12px; margin-bottom:10px;"></div>

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
            if (s >= 40) return '#6366f1';
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
                        <div style="font-size:1.6em; font-weight:800; color:#ffffff;">${{d.ticker}}</div>
                        <div style="color:rgba(255,255,255,0.6); font-size:0.9em; margin-top:2px;">${{d.company_name}}</div>
                        <div style="margin-top:8px; font-size:0.95em; color:rgba(255,255,255,0.8);">
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
                    <div style="background:rgba(251,191,36,0.1); border:1px solid rgba(251,191,36,0.2); border-radius:10px; padding:14px; text-align:center;">
                        <div style="font-size:1.5em; font-weight:800; color:#fbbf24;">${{fmt(d.vcp_score)}}</div>
                        <div style="font-size:0.8em; color:#fbbf24;">📊 VCP (40%)</div>
                        <div style="font-size:0.75em; color:rgba(251,191,36,0.7); margin-top:4px;">${{d.vcp_contribution != null ? 'contribuye ' + fmt(d.vcp_contribution) + ' pts' : 'sin datos VCP'}}</div>
                    </div>
                    <div style="background:rgba(139,92,246,0.1); border:1px solid rgba(139,92,246,0.2); border-radius:10px; padding:14px; text-align:center;">
                        <div style="font-size:1.5em; font-weight:800; color:#a78bfa;">${{fmt(d.ml_score)}}</div>
                        <div style="font-size:0.8em; color:#a78bfa;">🤖 ML (30%)</div>
                        <div style="font-size:0.75em; color:rgba(167,139,250,0.7); margin-top:4px;">${{d.ml_contribution != null ? 'contribuye ' + fmt(d.ml_contribution) + ' pts' : 'sin datos ML'}}</div>
                    </div>
                    <div style="background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.2); border-radius:10px; padding:14px; text-align:center;">
                        <div style="font-size:1.5em; font-weight:800; color:#34d399;">${{fmt(d.fund_score)}}</div>
                        <div style="font-size:0.8em; color:#34d399;">📈 Fund. (30%)</div>
                        <div style="font-size:0.75em; color:rgba(52,211,153,0.7); margin-top:4px;">${{d.fund_contribution != null ? 'contribuye ' + fmt(d.fund_contribution) + ' pts' : 'sin datos fund.'}}</div>
                    </div>
                    ${{d.penalty > 0 ? `<div style="background:rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.2); border-radius:10px; padding:14px; text-align:center;">
                        <div style="font-size:1.5em; font-weight:800; color:#f87171;">-${{d.penalty}}</div>
                        <div style="font-size:0.8em; color:#f87171;">⚠️ Penalización</div>
                        <div style="font-size:0.75em; color:rgba(248,113,113,0.7); margin-top:4px;">filtros técnicos</div>
                    </div>` : ''}}
                </div>

                <!-- Filtros + detalles en grid -->
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(250px,1fr)); gap:16px; margin-bottom:20px;">

                    <!-- Filtros técnicos -->
                    <div style="background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.1); border-radius:10px; padding:16px;">
                        <div style="font-weight:700; color:#ffffff; margin-bottom:10px;">🛡️ Filtros Técnicos</div>
                        <table style="width:100%; font-size:0.88em; border-collapse:collapse;">
                            <tr><td style="padding:4px 0; color:rgba(255,255,255,0.5);">Minervini Template</td>
                                <td style="text-align:right;">${{maLabel(d.ma_passes, d.ma_checks)}}</td></tr>
                            <tr><td style="padding:4px 0; color:rgba(255,255,255,0.5);">Acum./Distribución</td>
                                <td style="text-align:right;">${{adIcon(d.ad_signal)}} ${{d.ad_signal || '—'}}</td></tr>
                            <tr><td style="padding:4px 0; color:rgba(255,255,255,0.5);">RS Line (Minervini)</td>
                                <td style="text-align:right;">${{rsLineLabel(d.rs_line_at_high, d.rs_line_trend, d.rs_line_percentile)}}</td></tr>
                            <tr><td style="padding:4px 0; color:rgba(255,255,255,0.5);">Sector</td>
                                <td style="text-align:right;">${{d.sector_name || '—'}} ${{d.sector_score != null ? '(' + fmt(d.sector_score, 0) + ')' : ''}}</td></tr>
                            <tr><td style="padding:4px 0; color:rgba(255,255,255,0.5);">Sector momentum</td>
                                <td style="text-align:right;">${{momIcon(d.sector_momentum)}} ${{d.sector_momentum}}</td></tr>
                            <tr><td style="padding:4px 0; color:rgba(255,255,255,0.5);">Grupo Industrial</td>
                                <td style="text-align:right;">${{groupRankLabel(d.industry_group_rank, d.industry_group_total, d.industry_group_percentile, d.industry_group_label)}}</td></tr>
                            <tr><td style="padding:4px 0; color:rgba(255,255,255,0.5);">Trend Template</td>
                                <td style="text-align:right;">${{trendTemplateLabel(d.trend_template_score, d.trend_template_pass)}}</td></tr>
                        </table>
                    </div>

                    <!-- VCP -->
                    <div style="background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.1); border-radius:10px; padding:16px;">
                        <div style="font-weight:700; color:#ffffff; margin-bottom:10px;">📊 VCP / Técnico</div>
                        <table style="width:100%; font-size:0.88em; border-collapse:collapse;">
                            <tr><td style="padding:4px 0; color:rgba(255,255,255,0.5);">Estado</td>
                                <td style="text-align:right;">${{d.vcp_ready ? '✅ Listo para compra' : '⏳ En formación'}}</td></tr>
                            <tr><td style="padding:4px 0; color:rgba(255,255,255,0.5);">Contracciones</td>
                                <td style="text-align:right;">${{d.vcp_contractions}}</td></tr>
                            ${{d.vcp_breakout_potential != null ? `<tr><td style="padding:4px 0; color:rgba(255,255,255,0.5);">Potencial BK</td><td style="text-align:right;">${{fmt(d.vcp_breakout_potential)}}%</td></tr>` : ''}}
                            ${{d.vcp_stage ? `<tr><td style="padding:4px 0; color:rgba(255,255,255,0.5);">Stage</td><td style="text-align:right;">${{d.vcp_stage}}</td></tr>` : ''}}
                            ${{d.ml_quality ? `<tr><td style="padding:4px 0; color:rgba(255,255,255,0.5);">ML Quality</td><td style="text-align:right;">${{d.ml_quality}}</td></tr>` : ''}}
                            ${{d.entry_score != null ? `<tr><td style="padding:4px 0; color:rgba(255,255,255,0.5);">Entry score</td><td style="text-align:right;">${{fmt(d.entry_score)}}/100</td></tr>` : ''}}
                        </table>
                    </div>

                    <!-- Fundamentales -->
                    <div style="background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.1); border-radius:10px; padding:16px;">
                        <div style="font-weight:700; color:#ffffff; margin-bottom:10px;">📈 Fundamentales</div>
                        <table style="width:100%; font-size:0.88em; border-collapse:collapse;">
                            ${{d.forward_pe != null ? `<tr><td style="padding:4px 0; color:rgba(255,255,255,0.5);">Forward P/E</td><td style="text-align:right;">${{fmt(d.forward_pe)}}x</td></tr>` : ''}}
                            ${{d.peg_ratio != null ? `<tr><td style="padding:4px 0; color:rgba(255,255,255,0.5);">PEG Ratio</td><td style="text-align:right;">${{fmt(d.peg_ratio, 2)}}</td></tr>` : ''}}
                            ${{d.roe != null ? `<tr><td style="padding:4px 0; color:rgba(255,255,255,0.5);">ROE</td><td style="text-align:right;">${{pct(d.roe * 100)}}</td></tr>` : ''}}
                            ${{d.revenue_growth != null ? `<tr><td style="padding:4px 0; color:rgba(255,255,255,0.5);">Revenue Growth</td><td style="text-align:right;">${{pct(d.revenue_growth * 100)}}</td></tr>` : ''}}
                            ${{d.fcf_yield != null ? `<tr><td style="padding:4px 0; color:rgba(255,255,255,0.5);">FCF Yield</td><td style="text-align:right;"><span style="color:${{d.fcf_yield >= 5 ? '#10b981' : d.fcf_yield >= 3 ? '#f59e0b' : d.fcf_yield < 0 ? '#ef4444' : 'rgba(255,255,255,0.8)'}};font-weight:600;">${{fmt(d.fcf_yield)}}%</span></td></tr>` : ''}}
                            ${{d.dividend_yield != null && d.dividend_yield > 0 ? `<tr><td style="padding:4px 0; color:rgba(255,255,255,0.5);">Dividendo</td><td style="text-align:right;"><span style="color:#8b5cf6;">${{fmt(d.dividend_yield)}}%</span>${{d.payout_ratio != null ? ' <span style="font-size:0.78em;color:rgba(255,255,255,0.4);">payout ' + fmt(d.payout_ratio) + '%</span>' : ''}}</td></tr>` : ''}}
                            ${{d.buyback_active ? `<tr><td style="padding:4px 0; color:rgba(255,255,255,0.5);">Recompra acciones</td><td style="text-align:right;"><span style="color:#10b981;">Activa</span>${{d.shares_change != null ? ' <span style="font-size:0.78em;color:rgba(255,255,255,0.4);">' + fmt(d.shares_change) + '%</span>' : ''}}</td></tr>` : ''}}
                            ${{d.interest_coverage != null ? `<tr><td style="padding:4px 0; color:rgba(255,255,255,0.5);">Cobertura Intereses</td><td style="text-align:right;"><span style="color:${{d.interest_coverage >= 5 ? '#10b981' : d.interest_coverage >= 2 ? '#f59e0b' : '#ef4444'}};">${{fmt(d.interest_coverage)}}x</span></td></tr>` : ''}}
                            ${{d.risk_reward != null ? `<tr><td style="padding:4px 0; color:rgba(255,255,255,0.5);">Risk/Reward</td><td style="text-align:right;"><span style="color:${{d.risk_reward >= 2 ? '#10b981' : d.risk_reward >= 1 ? '#f59e0b' : '#ef4444'}};font-weight:600;">${{fmt(d.risk_reward)}}:1</span></td></tr>` : ''}}
                            ${{d.days_to_earnings != null ? `<tr><td style="padding:4px 0; color:rgba(255,255,255,0.5);">Earnings</td><td style="text-align:right;"><span style="color:${{d.days_to_earnings <= 7 ? '#ef4444' : d.days_to_earnings <= 21 ? '#f59e0b' : 'rgba(255,255,255,0.6)'}};${{d.days_to_earnings <= 7 ? 'font-weight:700;' : ''}}">${{d.days_to_earnings}}d${{d.days_to_earnings <= 7 ? ' ⚠️' : d.days_to_earnings <= 21 ? ' 🎯' : ''}}</span></td></tr>` : ''}}
                            ${{d.analyst_revision != null ? `<tr><td style="padding:4px 0; color:rgba(255,255,255,0.5);">Revision Momentum</td><td style="text-align:right;"><span style="color:${{d.analyst_revision > 5 ? '#10b981' : d.analyst_revision < -5 ? '#ef4444' : 'rgba(255,255,255,0.6)'}};">${{d.analyst_revision > 0 ? '+' : ''}}${{fmt(d.analyst_revision)}}%</span></td></tr>` : ''}}
                            ${{d.debt_to_equity != null ? `<tr><td style="padding:4px 0; color:rgba(255,255,255,0.5);">Deuda/Capital</td><td style="text-align:right;">${{fmt(d.debt_to_equity, 2)}}</td></tr>` : ''}}
                            <tr><td style="padding:4px 0; color:rgba(255,255,255,0.5);">Aceleración (CANSLIM A)</td>
                                <td style="text-align:right;">${{accelLabel(d.eps_accelerating, d.rev_accelerating, d.eps_growth_yoy, d.rev_growth_yoy)}}</td></tr>
                            ${{d.short_percent_float != null ? `<tr><td style="padding:4px 0; color:rgba(255,255,255,0.5);">Short Interest</td>
                                <td style="text-align:right;">${{d.short_percent_float.toFixed(1)}}% float${{d.short_squeeze_potential ? ' 🔥' : ''}}</td></tr>` : ''}}
                            ${{d.proximity_to_52w_high != null ? `<tr><td style="padding:4px 0; color:rgba(255,255,255,0.5);">Dist. Máx. 52s</td>
                                <td style="text-align:right; color:${{d.proximity_to_52w_high >= -10 ? '#10b981' : d.proximity_to_52w_high >= -25 ? '#f59e0b' : '#e53e3e'}}">
                                ${{d.proximity_to_52w_high.toFixed(1)}}%${{d.proximity_to_52w_high >= -5 ? ' 🎯' : d.proximity_to_52w_high >= -15 ? ' 📈' : d.proximity_to_52w_high < -30 ? ' ⚠️' : ''}}</td></tr>` : ''}}
                            ${{d.target_price_analyst != null ? `<tr><td style="padding:4px 0; color:rgba(255,255,255,0.5);">Obj. Analistas</td>
                                <td style="text-align:right;"><strong>${{d.target_price_analyst.toFixed(2)}}</strong>
                                <span style="color:${{d.analyst_upside_pct >= 15 ? '#10b981' : d.analyst_upside_pct >= 0 ? '#f59e0b' : '#e53e3e'}}">
                                (${{d.analyst_upside_pct != null ? (d.analyst_upside_pct > 0 ? '+' : '') + d.analyst_upside_pct.toFixed(1) + '%' : ''}})</span>
                                ${{d.analyst_count ? '<span style="color:#94a3b8;font-size:0.78em;">' + d.analyst_count + ' analistas</span>' : ''}}
                                ${{d.analyst_recommendation ? '<span style="color:#6366f1;font-size:0.78em;text-transform:capitalize;"> · ' + d.analyst_recommendation.replace('_',' ') + '</span>' : ''}}</td></tr>` : ''}}
                            ${{d.target_price_dcf != null ? `<tr><td style="padding:4px 0; color:rgba(255,255,255,0.5);">Obj. DCF</td>
                                <td style="text-align:right; color:rgba(255,255,255,0.6);">${{d.target_price_dcf.toFixed(2)}}
                                <span style="font-size:0.78em;">(${{d.target_price_dcf_upside_pct != null ? (d.target_price_dcf_upside_pct > 0 ? '+' : '') + d.target_price_dcf_upside_pct.toFixed(1) + '%' : ''}})</span></td></tr>` : ''}}
                            ${{d.target_price_pe != null ? `<tr><td style="padding:4px 0; color:rgba(255,255,255,0.5);">Obj. P/E justo</td>
                                <td style="text-align:right; color:rgba(255,255,255,0.6);">${{d.target_price_pe.toFixed(2)}}
                                <span style="font-size:0.78em;">(${{d.target_price_pe_upside_pct != null ? (d.target_price_pe_upside_pct > 0 ? '+' : '') + d.target_price_pe_upside_pct.toFixed(1) + '%' : ''}})</span></td></tr>` : ''}}
                        </table>
                    </div>
                </div>

                <!-- Tesis -->
                <div style="background:rgba(99,102,241,0.08); border-left:4px solid #6366f1; border-radius:0 10px 10px 0; padding:16px; margin-bottom:12px;">
                    <div style="font-weight:700; color:#ffffff; margin-bottom:8px;">💡 Tesis de Inversión</div>
                    <div style="font-size:0.9em; color:rgba(255,255,255,0.8); line-height:1.6;">${{thesisLines}}</div>
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
            <h2 class="section-title">Dashboards Especializados</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; margin-top: 20px;">
                <a href="sector_rotation_dashboard.html" style="display: block; padding: 20px; background: rgba(99,102,241,0.15); border: 1px solid rgba(99,102,241,0.3); color: #a5b4fc; text-decoration: none; border-radius: 12px; text-align: center; font-weight: bold; transition: all 0.3s;" onmouseover="this.style.background='rgba(99,102,241,0.25)'" onmouseout="this.style.background='rgba(99,102,241,0.15)'">
                    Rotación Sectorial
                </a>
                <a href="backtest_dashboard.html" style="display: block; padding: 20px; background: rgba(16,185,129,0.15); border: 1px solid rgba(16,185,129,0.3); color: #34d399; text-decoration: none; border-radius: 12px; text-align: center; font-weight: bold; transition: all 0.3s;" onmouseover="this.style.background='rgba(16,185,129,0.25)'" onmouseout="this.style.background='rgba(16,185,129,0.15)'">
                    Rendimiento Backtest
                </a>
                <a href="super_opportunities_4d.html" style="display: block; padding: 20px; background: rgba(245,158,11,0.15); border: 1px solid rgba(245,158,11,0.3); color: #fbbf24; text-decoration: none; border-radius: 12px; text-align: center; font-weight: bold; transition: all 0.3s;" onmouseover="this.style.background='rgba(245,158,11,0.25)'" onmouseout="this.style.background='rgba(245,158,11,0.15)'">
                    Análisis 5D Completo
                </a>
            </div>
        </div>

        <div class="footer">
            <p>Stock Analyzer — Value + Momentum + Fundamentales</p>
            <p style="font-size: 0.9em; margin-top: 5px;">Generado automáticamente</p>
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
        return f'<div style="height:6px;background:rgba(255,255,255,0.1);border-radius:3px;margin-top:4px;"><div style="width:{pct:.0f}%;height:100%;background:{color};border-radius:3px;"></div></div>'

    def _format_thesis_html(self, narrative: str, signals: list, insiders: list) -> str:
        """Formatea thesis_narrative como HTML (convierte **bold** y \\n)"""
        import re
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', narrative)
        text = text.replace('\n\n', '</p><p style="margin:6px 0 0;">').replace('\n', '<br>')
        signals_html = ''
        if signals:
            items = ''.join(f'<span style="margin-right:10px;">{s}</span>' for s in signals[:4])
            signals_html = f'<div style="margin-top:8px;font-size:0.8em;">{items}</div>'
        insiders_html = ''
        if insiders:
            items = ''.join(f'<span style="margin-right:10px;color:#7c3aed;">{s}</span>' for s in insiders[:2])
            insiders_html = f'<div style="margin-top:4px;font-size:0.8em;">{items}</div>'
        return f'<p style="margin:0;">{text}</p>{signals_html}{insiders_html}'

    def _value_row_html(self, d: dict) -> str:
        """Genera fila HTML para una oportunidad value"""
        ticker  = d.get('ticker', '')
        company = str(d.get('company_name', ticker))[:22]
        score   = float(d.get('value_score', 0) or 0)
        if pd.isna(score): score = 0
        sector  = str(d.get('sector', ''))[:18]
        # FCF Yield
        fcf = d.get('fcf_yield_pct')
        if fcf is not None and not pd.isna(fcf):
            fcf_val = float(fcf)
            fcf_color = '#10b981' if fcf_val >= 5 else ('#f59e0b' if fcf_val >= 3 else ('#ef4444' if fcf_val < 0 else 'rgba(255,255,255,0.5)'))
            fcf_str = f'<span style="color:{fcf_color};font-weight:600;">{fcf_val:.1f}%</span>'
        else:
            fcf_str = '<span style="color:#94a3b8;">-</span>'

        # Risk/Reward
        rr = d.get('risk_reward_ratio')
        if rr is not None and not pd.isna(rr):
            rr_val = float(rr)
            rr_color = '#10b981' if rr_val >= 2.0 else ('#f59e0b' if rr_val >= 1.0 else '#ef4444')
            rr_str = f'<span style="color:{rr_color};font-weight:600;">{rr_val:.1f}</span>'
        else:
            rr_str = '<span style="color:#94a3b8;">-</span>'

        # Dividend + Buyback
        div_yield = d.get('dividend_yield_pct')
        buyback = d.get('buyback_active')
        div_parts = []
        if div_yield is not None and not pd.isna(div_yield) and float(div_yield) > 0:
            div_parts.append(f'{float(div_yield):.1f}%')
        if buyback == True:
            div_parts.append('BB')
        div_str = f'<span style="color:#8b5cf6;font-size:0.82em;">{"+".join(div_parts)}</span>' if div_parts else '<span style="color:#94a3b8;">-</span>'

        # Earnings date
        days_earn = d.get('days_to_earnings')
        earn_warning = d.get('earnings_warning', False)
        if days_earn is not None and not pd.isna(days_earn):
            days_val = int(days_earn)
            if earn_warning:
                earn_str = f'<span style="color:#ef4444;font-weight:700;" title="Earnings en {days_val}d - RIESGO">{days_val}d !</span>'
            elif days_val <= 21:
                earn_str = f'<span style="color:#f59e0b;" title="Earnings como catalizador">{days_val}d</span>'
            else:
                earn_str = f'<span style="color:rgba(255,255,255,0.5);">{days_val}d</span>'
        else:
            earn_str = '<span style="color:#94a3b8;">-</span>'

        if score >= 40:
            color = '#10b981'
        elif score >= 30:
            color = '#f59e0b'
        else:
            color = '#94a3b8'

        price_str = self._fmt_price(d.get('current_price', ''))

        # Target price: analyst consensus with upside %
        tp = d.get('target_price_analyst')
        tp_upside = d.get('analyst_upside_pct')
        tp_count = d.get('analyst_count')
        if tp is not None and tp_upside is not None:
            up_color = '#10b981' if tp_upside >= 10 else ('#f59e0b' if tp_upside >= 0 else '#ef4444')
            count_str = f' <span style="color:#94a3b8;font-size:0.75em;">({int(tp_count)})</span>' if tp_count and not pd.isna(tp_count) else ''
            target_cell = (f'<span style="font-weight:600;">${tp:.0f}</span>'
                           f'{count_str}<br>'
                           f'<span style="color:{up_color};font-size:0.8em;">{tp_upside:+.1f}%</span>')
        else:
            target_cell = '<span style="color:#94a3b8;font-size:0.8em;">N/A</span>'

        # Thesis collapsible row
        thesis_narrative = d.get('thesis_narrative', '')
        thesis_signals = d.get('thesis_signals', [])
        thesis_insiders = d.get('thesis_catalysts_insiders', [])
        thesis_id = f'thesis-v-{ticker}'
        if thesis_narrative:
            thesis_html = self._format_thesis_html(thesis_narrative, thesis_signals, thesis_insiders)
            ticker_cell = (f'<td style="padding:10px 8px;font-weight:800;color:#ffffff;cursor:pointer;font-size:1.05em;" '
                           f'onclick="var r=document.getElementById(\'{thesis_id}\');'
                           f'r.style.display=r.style.display===\'none\'?\'table-row\':\'none\'">'
                           f'{ticker} <span style="font-size:0.65em;color:#a5b4fc;vertical-align:middle;" title="Ver tesis">&#9432;</span></td>')
            thesis_row = (f'<tr id="{thesis_id}" style="display:none;background:rgba(99,102,241,0.08);">'
                          f'<td colspan="9" style="padding:12px 20px 14px;border-bottom:1px solid rgba(255,255,255,0.1);">'
                          f'<div style="border-left:3px solid #6366f1;padding-left:12px;'
                          f'color:rgba(255,255,255,0.85);font-size:0.9em;line-height:1.7;">'
                          f'<div style="font-weight:700;color:#ffffff;margin-bottom:8px;">💡 Tesis de Inversión</div>'
                          f'{thesis_html}</div></td></tr>')
        else:
            ticker_cell = f'<td style="padding:10px 8px;font-weight:800;color:#ffffff;font-size:1.05em;">{ticker}</td>'
            thesis_row = ''

        return (f'<tr style="border-bottom:1px solid rgba(255,255,255,0.06);">'
                f'{ticker_cell}'
                f'<td style="padding:10px 8px;color:rgba(255,255,255,0.65);font-size:0.9em;">{company}</td>'
                f'<td style="padding:10px 8px;">{price_str}</td>'
                f'<td style="padding:10px 8px;min-width:90px;">'
                f'<span style="font-weight:700;color:{color};">{score:.1f}</span>'
                f'{self._score_bar(score, color)}</td>'
                f'<td style="padding:10px 8px;color:rgba(255,255,255,0.5);font-size:0.82em;">{sector}</td>'
                f'<td style="padding:10px 8px;text-align:right;font-size:0.82em;">{target_cell}</td>'
                f'<td style="padding:10px 8px;text-align:center;font-size:0.82em;">{fcf_str}</td>'
                f'<td style="padding:10px 8px;text-align:center;font-size:0.82em;">{rr_str}</td>'
                f'<td style="padding:10px 8px;text-align:center;font-size:0.82em;">{div_str}</td>'
                f'<td style="padding:10px 8px;text-align:center;font-size:0.82em;">{earn_str}</td>'
                f'</tr>{thesis_row}')

    def _momentum_row_html(self, d: dict) -> str:
        """Genera fila HTML para un setup de momentum"""
        ticker  = d.get('ticker', '')
        company = str(d.get('company_name', ticker))[:22]
        score   = float(d.get('momentum_score', 0) or 0)
        if pd.isna(score): score = 0
        vcp     = float(d.get('vcp_score', 0) or 0)
        if pd.isna(vcp): vcp = 0

        if score >= 75:
            color = '#10b981'
        elif score >= 65:
            color = '#f59e0b'
        else:
            color = '#94a3b8'

        price_str = self._fmt_price(d.get('current_price', ''))
        prox_str  = self._fmt_optional(d.get('proximity_to_52w_high', ''), '{:.1f}%')
        trend_str = self._fmt_optional(d.get('trend_template_score', ''), '{:.0f}/8')

        # Analyst target for momentum too
        tp = d.get('target_price_analyst')
        tp_upside = d.get('analyst_upside_pct')
        if tp is not None and tp_upside is not None:
            up_color = '#10b981' if tp_upside >= 10 else ('#f59e0b' if tp_upside >= 0 else '#ef4444')
            target_cell = (f'<span style="font-weight:600;">${tp:.0f}</span><br>'
                           f'<span style="color:{up_color};font-size:0.8em;">{tp_upside:+.1f}%</span>')
        else:
            target_cell = '<span style="color:#94a3b8;font-size:0.8em;">N/A</span>'

        # Thesis collapsible row
        thesis_narrative = d.get('thesis_narrative', '')
        thesis_signals = d.get('thesis_signals', [])
        thesis_insiders = d.get('thesis_catalysts_insiders', [])
        thesis_id = f'thesis-m-{ticker}'
        if thesis_narrative:
            thesis_html = self._format_thesis_html(thesis_narrative, thesis_signals, thesis_insiders)
            ticker_cell = (f'<td style="padding:10px 8px;font-weight:800;color:#ffffff;cursor:pointer;font-size:1.05em;" '
                           f'onclick="var r=document.getElementById(\'{thesis_id}\');'
                           f'r.style.display=r.style.display===\'none\'?\'table-row\':\'none\'">'
                           f'{ticker} <span style="font-size:0.65em;color:#a5b4fc;vertical-align:middle;" title="Ver tesis">&#9432;</span></td>')
            thesis_row = (f'<tr id="{thesis_id}" style="display:none;background:rgba(99,102,241,0.08);">'
                          f'<td colspan="8" style="padding:12px 20px 14px;border-bottom:1px solid rgba(255,255,255,0.1);">'
                          f'<div style="border-left:3px solid #6366f1;padding-left:12px;'
                          f'color:rgba(255,255,255,0.85);font-size:0.9em;line-height:1.7;">'
                          f'<div style="font-weight:700;color:#ffffff;margin-bottom:8px;">💡 Tesis de Inversión</div>'
                          f'{thesis_html}</div></td></tr>')
        else:
            ticker_cell = f'<td style="padding:10px 8px;font-weight:800;color:#ffffff;font-size:1.05em;">{ticker}</td>'
            thesis_row = ''

        return (f'<tr style="border-bottom:1px solid rgba(255,255,255,0.06);">'
                f'{ticker_cell}'
                f'<td style="padding:10px 8px;color:rgba(255,255,255,0.65);font-size:0.9em;">{company}</td>'
                f'<td style="padding:10px 8px;">{price_str}</td>'
                f'<td style="padding:10px 8px;min-width:90px;">'
                f'<span style="font-weight:700;color:{color};">{score:.1f}</span>'
                f'{self._score_bar(score, color)}</td>'
                f'<td style="padding:10px 8px;text-align:center;color:#a5b4fc;font-weight:600;">{vcp:.0f}</td>'
                f'<td style="padding:10px 8px;text-align:center;color:rgba(255,255,255,0.6);font-size:0.85em;">{prox_str}</td>'
                f'<td style="padding:10px 8px;text-align:center;color:rgba(255,255,255,0.6);font-size:0.85em;">{trend_str}</td>'
                f'<td style="padding:10px 8px;text-align:right;font-size:0.82em;">{target_cell}</td>'
                f'</tr>{thesis_row}')

    def _generate_dual_strategy_html(self, value_data: list, momentum_data: list) -> str:
        """Genera HTML para las 2 secciones: Value Opportunities + Momentum Plays"""

        # Sector concentration analysis
        sector_warning_html = ''
        if value_data:
            from collections import Counter
            sectors = [d.get('sector', 'N/A') for d in value_data if d.get('sector')]
            sector_counts = Counter(sectors)
            concentrated = [(s, c) for s, c in sector_counts.most_common() if c >= 3]
            if concentrated:
                pills = ' '.join(
                    f'<span style="background:rgba(245,158,11,0.15);color:#f59e0b;padding:2px 8px;border-radius:10px;font-size:0.78em;margin-right:4px;">{s}: {c}</span>'
                    for s, c in concentrated
                )
                sector_warning_html = (
                    f'<div style="background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.25);border-radius:8px;padding:8px 12px;margin-bottom:12px;font-size:0.82em;">'
                    f'<span style="color:#f59e0b;font-weight:600;">Concentracion sectorial:</span> {pills}'
                    f' <span style="color:rgba(255,255,255,0.5);">Diversifica para reducir riesgo</span></div>'
                )
            value_rows = ''.join(self._value_row_html(d) for d in value_data)
        else:
            value_rows = '<tr><td colspan="10" style="padding:20px;text-align:center;color:#94a3b8;">No hay oportunidades value en este momento</td></tr>'

        if momentum_data:
            momentum_rows = ''.join(self._momentum_row_html(d) for d in momentum_data)
        else:
            momentum_rows = '<tr><td colspan="8" style="padding:20px;text-align:center;color:#94a3b8;">No hay setups de momentum (mercado en correccion o sin patrones VCP)</td></tr>'

        return f'''
        <!-- ═══════════════════════════════════════════════════════════ -->
        <!-- DUAL STRATEGY SECTION                                       -->
        <!-- ═══════════════════════════════════════════════════════════ -->
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px;">

            <!-- SECTION A: VALUE OPPORTUNITIES -->
            <div class="section-card" style="border-top:3px solid #10b981;">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
                    <div>
                        <h2 class="section-title" style="margin:0;color:#34d399;">Oportunidades Value</h2>
                        <p style="margin:4px 0 0;font-size:0.82em;color:rgba(255,255,255,0.5);">Empresas sólidas con precio circunstancialmente bajo · Insiders + Institucionales + Sector</p>
                    </div>
                    <span style="background:rgba(16,185,129,0.15);color:#34d399;padding:4px 10px;border-radius:20px;font-size:0.82em;font-weight:600;border:1px solid rgba(16,185,129,0.3);">{len(value_data)} candidatas</span>
                </div>
                {sector_warning_html}
                <div style="overflow-x:auto;">
                    <table style="width:100%;border-collapse:collapse;font-size:0.88em;">
                        <thead>
                            <tr style="background:rgba(255,255,255,0.05);border-bottom:1px solid rgba(255,255,255,0.1);">
                                <th style="padding:8px;text-align:left;color:rgba(255,255,255,0.6);font-weight:600;font-size:0.85em;text-transform:uppercase;letter-spacing:0.5px;">Ticker</th>
                                <th style="padding:8px;text-align:left;color:rgba(255,255,255,0.6);font-weight:600;font-size:0.85em;text-transform:uppercase;letter-spacing:0.5px;">Empresa</th>
                                <th style="padding:8px;text-align:left;color:rgba(255,255,255,0.6);font-weight:600;font-size:0.85em;text-transform:uppercase;letter-spacing:0.5px;">Precio</th>
                                <th style="padding:8px;text-align:left;color:rgba(255,255,255,0.6);font-weight:600;font-size:0.85em;text-transform:uppercase;letter-spacing:0.5px;">Score</th>
                                <th style="padding:8px;text-align:left;color:rgba(255,255,255,0.6);font-weight:600;font-size:0.85em;text-transform:uppercase;letter-spacing:0.5px;">Sector</th>
                                <th style="padding:8px;text-align:right;color:rgba(255,255,255,0.6);font-weight:600;font-size:0.85em;text-transform:uppercase;letter-spacing:0.5px;" title="Precio objetivo analistas + upside">Objetivo</th>
                                <th style="padding:8px;text-align:center;color:rgba(255,255,255,0.6);font-weight:600;font-size:0.85em;text-transform:uppercase;letter-spacing:0.5px;" title="FCF Yield = Free Cash Flow / Market Cap">FCF%</th>
                                <th style="padding:8px;text-align:center;color:rgba(255,255,255,0.6);font-weight:600;font-size:0.85em;text-transform:uppercase;letter-spacing:0.5px;" title="Risk/Reward ratio (upside / 8% stop)">R:R</th>
                                <th style="padding:8px;text-align:center;color:rgba(255,255,255,0.6);font-weight:600;font-size:0.85em;text-transform:uppercase;letter-spacing:0.5px;" title="Dividend yield + buyback">Div/BB</th>
                                <th style="padding:8px;text-align:center;color:rgba(255,255,255,0.6);font-weight:600;font-size:0.85em;text-transform:uppercase;letter-spacing:0.5px;" title="Dias hasta earnings">Earn</th>
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
                        <h2 class="section-title" style="margin:0;color:#a5b4fc;">Momentum Plays</h2>
                        <p style="margin:4px 0 0;font-size:0.82em;color:rgba(255,255,255,0.5);">Patrones VCP · Breakouts · Tendencias confirmadas (backtest en proceso)</p>
                    </div>
                    <span style="background:rgba(99,102,241,0.15);color:#a5b4fc;padding:4px 10px;border-radius:20px;font-size:0.82em;font-weight:600;border:1px solid rgba(99,102,241,0.3);">{len(momentum_data)} setups</span>
                </div>
                <div style="overflow-x:auto;">
                    <table style="width:100%;border-collapse:collapse;font-size:0.88em;">
                        <thead>
                            <tr style="background:rgba(255,255,255,0.05);border-bottom:1px solid rgba(255,255,255,0.1);">
                                <th style="padding:8px;text-align:left;color:rgba(255,255,255,0.6);font-weight:600;font-size:0.85em;text-transform:uppercase;letter-spacing:0.5px;">Ticker</th>
                                <th style="padding:8px;text-align:left;color:rgba(255,255,255,0.6);font-weight:600;font-size:0.85em;text-transform:uppercase;letter-spacing:0.5px;">Empresa</th>
                                <th style="padding:8px;text-align:left;color:rgba(255,255,255,0.6);font-weight:600;font-size:0.85em;text-transform:uppercase;letter-spacing:0.5px;">Precio</th>
                                <th style="padding:8px;text-align:left;color:rgba(255,255,255,0.6);font-weight:600;font-size:0.85em;text-transform:uppercase;letter-spacing:0.5px;">Score</th>
                                <th style="padding:8px;text-align:center;color:rgba(255,255,255,0.6);font-weight:600;font-size:0.85em;text-transform:uppercase;letter-spacing:0.5px;">VCP</th>
                                <th style="padding:8px;text-align:center;color:rgba(255,255,255,0.6);font-weight:600;font-size:0.85em;text-transform:uppercase;letter-spacing:0.5px;">Dist.Máx</th>
                                <th style="padding:8px;text-align:center;color:rgba(255,255,255,0.6);font-weight:600;font-size:0.85em;text-transform:uppercase;letter-spacing:0.5px;">Tendencia</th>
                                <th style="padding:8px;text-align:right;color:rgba(255,255,255,0.6);font-weight:600;font-size:0.85em;text-transform:uppercase;letter-spacing:0.5px;" title="Precio objetivo analistas + upside">Objetivo</th>
                            </tr>
                        </thead>
                        <tbody>{momentum_rows}</tbody>
                    </table>
                </div>
            </div>

        </div>
        '''

    def _generate_eu_value_html(self, eu_data: list) -> str:
        """Genera HTML para la seccion European VALUE"""
        if not eu_data:
            return ''

        # Sector concentration analysis
        sector_warning_html = ''
        from collections import Counter
        sectors = [d.get('sector', 'N/A') for d in eu_data if d.get('sector')]
        sector_counts = Counter(sectors)
        concentrated = [(s, c) for s, c in sector_counts.most_common() if c >= 3]
        if concentrated:
            pills = ' '.join(
                f'<span style="background:rgba(59,130,246,0.15);color:#60a5fa;padding:2px 8px;border-radius:10px;font-size:0.78em;margin-right:4px;">{s}: {c}</span>'
                for s, c in concentrated
            )
            sector_warning_html = (
                f'<div style="background:rgba(59,130,246,0.08);border:1px solid rgba(59,130,246,0.25);border-radius:8px;padding:8px 12px;margin-bottom:12px;font-size:0.82em;">'
                f'<span style="color:#60a5fa;font-weight:600;">Concentracion sectorial:</span> {pills}'
                f' <span style="color:rgba(255,255,255,0.5);">Diversifica entre mercados</span></div>'
            )

        # Market breakdown
        market_counts = Counter(d.get('market', '?') for d in eu_data)
        market_pills = ' '.join(
            f'<span style="background:rgba(255,255,255,0.06);color:rgba(255,255,255,0.6);padding:2px 6px;border-radius:8px;font-size:0.72em;">{m}:{c}</span>'
            for m, c in market_counts.most_common()
        )

        # EU market regime
        eu_regime_html = ''
        try:
            regime_path = Path("docs/european_market_regime.json")
            if regime_path.exists():
                import json
                with open(regime_path) as f:
                    eu_regime = json.load(f)
                regime = eu_regime.get('regime', 'UNKNOWN')
                regime_color = '#10b981' if 'UPTREND' in regime else ('#f59e0b' if 'PRESSURE' in regime else '#ef4444')
                eu_regime_html = f'<span style="color:{regime_color};font-size:0.78em;margin-left:8px;">STOXX50: {regime}</span>'
        except:
            pass

        rows = ''.join(self._eu_value_row_html(d) for d in eu_data)

        return f'''
        <div class="section-card" style="border-top:3px solid #3b82f6;margin-bottom:20px;">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
                <div>
                    <h2 class="section-title" style="margin:0;color:#60a5fa;">European Value</h2>
                    <p style="margin:4px 0 0;font-size:0.82em;color:rgba(255,255,255,0.5);">Blue chips europeos con fundamentales solidos · DAX, FTSE, CAC, IBEX, AEX, SMI, MIB{eu_regime_html}</p>
                </div>
                <div style="text-align:right;">
                    <span style="background:rgba(59,130,246,0.15);color:#60a5fa;padding:4px 10px;border-radius:20px;font-size:0.82em;font-weight:600;border:1px solid rgba(59,130,246,0.3);">{len(eu_data)} candidatas</span>
                    <div style="margin-top:4px;">{market_pills}</div>
                </div>
            </div>
            {sector_warning_html}
            <div style="overflow-x:auto;">
                <table style="width:100%;border-collapse:collapse;font-size:0.88em;">
                    <thead>
                        <tr style="background:rgba(255,255,255,0.05);border-bottom:1px solid rgba(255,255,255,0.1);">
                            <th style="padding:8px;text-align:left;color:rgba(255,255,255,0.6);font-weight:600;font-size:0.85em;text-transform:uppercase;letter-spacing:0.5px;">Ticker</th>
                            <th style="padding:8px;text-align:left;color:rgba(255,255,255,0.6);font-weight:600;font-size:0.85em;text-transform:uppercase;letter-spacing:0.5px;">Empresa</th>
                            <th style="padding:8px;text-align:left;color:rgba(255,255,255,0.6);font-weight:600;font-size:0.85em;text-transform:uppercase;letter-spacing:0.5px;">Mercado</th>
                            <th style="padding:8px;text-align:left;color:rgba(255,255,255,0.6);font-weight:600;font-size:0.85em;text-transform:uppercase;letter-spacing:0.5px;">Precio</th>
                            <th style="padding:8px;text-align:left;color:rgba(255,255,255,0.6);font-weight:600;font-size:0.85em;text-transform:uppercase;letter-spacing:0.5px;">Score</th>
                            <th style="padding:8px;text-align:left;color:rgba(255,255,255,0.6);font-weight:600;font-size:0.85em;text-transform:uppercase;letter-spacing:0.5px;">Sector</th>
                            <th style="padding:8px;text-align:right;color:rgba(255,255,255,0.6);font-weight:600;font-size:0.85em;text-transform:uppercase;letter-spacing:0.5px;" title="Precio objetivo analistas + upside">Objetivo</th>
                            <th style="padding:8px;text-align:center;color:rgba(255,255,255,0.6);font-weight:600;font-size:0.85em;text-transform:uppercase;letter-spacing:0.5px;" title="FCF Yield">FCF%</th>
                            <th style="padding:8px;text-align:center;color:rgba(255,255,255,0.6);font-weight:600;font-size:0.85em;text-transform:uppercase;letter-spacing:0.5px;" title="Dividend yield + buyback">Div/BB</th>
                            <th style="padding:8px;text-align:center;color:rgba(255,255,255,0.6);font-weight:600;font-size:0.85em;text-transform:uppercase;letter-spacing:0.5px;" title="Risk/Reward ratio">R:R</th>
                        </tr>
                    </thead>
                    <tbody>{rows}</tbody>
                </table>
            </div>
        </div>
        '''

    def _eu_value_row_html(self, d: dict) -> str:
        """Genera fila HTML para una oportunidad value europea"""
        ticker  = d.get('ticker', '')
        company = str(d.get('company_name', ticker))[:22]
        score   = float(d.get('value_score', 0) or 0)
        if pd.isna(score): score = 0
        sector  = str(d.get('sector', ''))[:18]
        market  = str(d.get('market', ''))

        # Currency symbol based on market
        suffix = ticker.split('.')[-1] if '.' in ticker else ''
        currency = {'DE': 'EUR', 'PA': 'EUR', 'MC': 'EUR', 'AS': 'EUR', 'MI': 'EUR',
                     'L': 'GBP', 'SW': 'CHF'}.get(suffix, 'EUR')
        curr_sym = {'EUR': '\u20ac', 'GBP': '\u00a3', 'CHF': 'CHF '}.get(currency, '')

        # Price
        price = d.get('current_price', 0)
        if price and not pd.isna(price):
            price_str = f'<span style="font-weight:600;">{curr_sym}{float(price):,.2f}</span>'
        else:
            price_str = '-'

        # Score color
        if score >= 40:
            color = '#10b981'
        elif score >= 30:
            color = '#60a5fa'
        else:
            color = '#94a3b8'

        # FCF Yield
        fcf = d.get('fcf_yield_pct')
        if fcf is not None and not pd.isna(fcf):
            fcf_val = float(fcf)
            fcf_color = '#10b981' if fcf_val >= 5 else ('#f59e0b' if fcf_val >= 3 else ('#ef4444' if fcf_val < 0 else 'rgba(255,255,255,0.5)'))
            fcf_str = f'<span style="color:{fcf_color};font-weight:600;">{fcf_val:.1f}%</span>'
        else:
            fcf_str = '<span style="color:#94a3b8;">-</span>'

        # Dividend + Buyback
        div_yield = d.get('dividend_yield_pct')
        buyback = d.get('buyback_active')
        div_parts = []
        if div_yield is not None and not pd.isna(div_yield) and float(div_yield) > 0:
            div_parts.append(f'{float(div_yield):.1f}%')
        if buyback == True:
            div_parts.append('BB')
        div_str = f'<span style="color:#8b5cf6;font-size:0.82em;">{"+".join(div_parts)}</span>' if div_parts else '<span style="color:#94a3b8;">-</span>'

        # Risk/Reward
        rr = d.get('risk_reward_ratio')
        if rr is not None and not pd.isna(rr):
            rr_val = float(rr)
            rr_color = '#10b981' if rr_val >= 2.0 else ('#f59e0b' if rr_val >= 1.0 else '#ef4444')
            rr_str = f'<span style="color:{rr_color};font-weight:600;">{rr_val:.1f}</span>'
        else:
            rr_str = '<span style="color:#94a3b8;">-</span>'

        # Target price
        tp = d.get('target_price_analyst')
        tp_upside = d.get('analyst_upside_pct')
        tp_count = d.get('analyst_count')
        if tp is not None and tp_upside is not None and not pd.isna(tp) and not pd.isna(tp_upside):
            up_color = '#10b981' if tp_upside >= 10 else ('#f59e0b' if tp_upside >= 0 else '#ef4444')
            count_str = f' <span style="color:#94a3b8;font-size:0.75em;">({int(tp_count)})</span>' if tp_count and not pd.isna(tp_count) else ''
            target_cell = (f'<span style="font-weight:600;">{curr_sym}{tp:.0f}</span>'
                           f'{count_str}<br>'
                           f'<span style="color:{up_color};font-size:0.8em;">{tp_upside:+.1f}%</span>')
        else:
            target_cell = '<span style="color:#94a3b8;font-size:0.8em;">N/A</span>'

        # Market badge color
        market_colors = {
            'DAX40': '#fbbf24', 'FTSE100': '#ef4444', 'CAC40': '#3b82f6',
            'IBEX35': '#f97316', 'AEX25': '#f43f5e', 'SMI20': '#ef4444',
            'FTSEMIB': '#22c55e'
        }
        m_color = market_colors.get(market, '#94a3b8')
        market_badge = f'<span style="color:{m_color};font-size:0.78em;font-weight:600;">{market}</span>'

        return (f'<tr style="border-bottom:1px solid rgba(255,255,255,0.06);">'
                f'<td style="padding:10px 8px;font-weight:800;color:#ffffff;font-size:1.05em;">{ticker}</td>'
                f'<td style="padding:10px 8px;color:rgba(255,255,255,0.65);font-size:0.9em;">{company}</td>'
                f'<td style="padding:10px 8px;">{market_badge}</td>'
                f'<td style="padding:10px 8px;">{price_str}</td>'
                f'<td style="padding:10px 8px;min-width:80px;">'
                f'<span style="font-weight:700;color:{color};">{score:.1f}</span>'
                f'{self._score_bar(min(score / 82 * 100, 100), color)}</td>'
                f'<td style="padding:10px 8px;color:rgba(255,255,255,0.5);font-size:0.82em;">{sector}</td>'
                f'<td style="padding:10px 8px;text-align:right;font-size:0.82em;">{target_cell}</td>'
                f'<td style="padding:10px 8px;text-align:center;font-size:0.82em;">{fcf_str}</td>'
                f'<td style="padding:10px 8px;text-align:center;font-size:0.82em;">{div_str}</td>'
                f'<td style="padding:10px 8px;text-align:center;font-size:0.82em;">{rr_str}</td>'
                f'</tr>')

    def _generate_tracker_html(self, tracker: dict) -> str:
        """Genera HTML del Portfolio Tracker - performance real de las recomendaciones"""
        if not tracker or tracker.get('total_signals', 0) == 0:
            return ''

        overall = tracker.get('overall', {})
        value_s = tracker.get('value_strategy', {})

        def stat_card(label, period_data, period_name):
            if not period_data or period_data.get('count', 0) == 0:
                return ''
            wr = period_data.get('win_rate')
            avg = period_data.get('avg_return')
            n = period_data.get('count', 0)
            if wr is None:
                return ''
            wr_color = '#10b981' if wr >= 60 else ('#f59e0b' if wr >= 45 else '#ef4444')
            avg_color = '#10b981' if avg and avg > 0 else '#ef4444'
            return (
                f'<div style="background:rgba(255,255,255,0.04);border-radius:8px;padding:12px;text-align:center;">'
                f'<div style="font-size:0.75em;color:rgba(255,255,255,0.5);text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">{label} ({period_name})</div>'
                f'<div style="font-size:1.5em;font-weight:800;color:{wr_color};">{wr:.0f}%</div>'
                f'<div style="font-size:0.78em;color:rgba(255,255,255,0.5);">win rate</div>'
                f'<div style="font-size:0.9em;font-weight:600;color:{avg_color};margin-top:4px;">{avg:+.1f}% avg</div>'
                f'<div style="font-size:0.72em;color:rgba(255,255,255,0.4);">n={n}</div>'
                f'</div>'
            )

        cards = []
        for period in ['7d', '14d', '30d']:
            card = stat_card('Overall', overall.get(period, {}), period)
            if card:
                cards.append(card)

        # Score correlation insight
        corr = tracker.get('score_correlation')
        corr_html = ''
        if corr is not None:
            if corr > 0.1:
                corr_html = f'<span style="color:#10b981;">Score correlacion: {corr:.2f} — Scores altos predicen mejores retornos</span>'
            elif corr < -0.1:
                corr_html = f'<span style="color:#ef4444;">Score correlacion: {corr:.2f} — Scores altos NO predicen mejores retornos</span>'

        # Top/worst performers
        top = tracker.get('top_performers', [])
        worst = tracker.get('worst_performers', [])
        perf_rows = ''
        for t in (top[:3] + worst[:2]):
            ret = t.get('return_14d', 0) or 0
            ret_color = '#10b981' if ret > 0 else '#ef4444'
            sig_date = str(t.get('signal_date', ''))[:10]
            perf_rows += (
                f'<div style="display:flex;justify-content:space-between;padding:3px 0;font-size:0.82em;">'
                f'<span style="color:#ffffff;font-weight:600;">{t["ticker"]}</span>'
                f'<span style="color:rgba(255,255,255,0.4);">{sig_date}</span>'
                f'<span style="color:{ret_color};font-weight:600;">{ret:+.1f}%</span>'
                f'</div>'
            )

        dd = tracker.get('avg_max_drawdown')
        dd_html = f'<div style="font-size:0.78em;color:rgba(255,255,255,0.5);margin-top:8px;">Avg Max Drawdown: <span style="color:#ef4444;">{dd:.1f}%</span></div>' if dd is not None else ''

        return f'''
        <div class="section-card" style="border-top:3px solid #8b5cf6;margin-bottom:20px;">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
                <div>
                    <h2 class="section-title" style="margin:0;color:#c4b5fd;">Portfolio Tracker</h2>
                    <p style="margin:4px 0 0;font-size:0.82em;color:rgba(255,255,255,0.5);">Rendimiento real de las recomendaciones · {tracker.get('total_signals', 0)} senales rastreadas</p>
                </div>
                <span style="background:rgba(139,92,246,0.15);color:#c4b5fd;padding:4px 10px;border-radius:20px;font-size:0.82em;font-weight:600;border:1px solid rgba(139,92,246,0.3);">{tracker.get('date_range', '')}</span>
            </div>
            <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(140px, 1fr));gap:12px;margin-bottom:12px;">
                {"".join(cards)}
            </div>
            {f'<div style="margin-bottom:8px;font-size:0.82em;">{corr_html}</div>' if corr_html else ''}
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
                <div>
                    <div style="font-size:0.78em;color:rgba(255,255,255,0.5);text-transform:uppercase;margin-bottom:6px;">Top/Worst Performers (14d)</div>
                    {perf_rows}
                </div>
                <div>
                    {dd_html}
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
            <h2 class="section-title">Insights — Oportunidades Integradas</h2>
            {''.join(items)}
        </div>
        """

    def _generate_opportunities_table(self, opportunities):
        """Genera tabla de oportunidades 5D"""
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
            <h4 style="color: var(--glass-primary); margin-bottom: 0.75rem;">Guía de Columnas</h4>
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
                        <th title="Puntuación integrada con filtros aplicados">Score</th>
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


def validate_dashboard_js(html_path: str = "docs/super_dashboard.html") -> bool:
    """Valida sintaxis JavaScript en el dashboard generado"""
    import re
    from pathlib import Path

    html = Path(html_path).read_text()
    errors = []

    # Check for comma instead of semicolon in onclick
    onclicks = re.findall(r'onclick="([^"]+)"', html)
    for oc in onclicks:
        if '),var ' in oc or '),r.' in oc or '),d.' in oc:
            errors.append(f"onclick uses comma: {oc[:60]}...")

    if errors:
        print("❌ DASHBOARD VALIDATION FAILED:")
        for err in errors[:3]:
            print(f"  {err}")
        raise ValueError("Dashboard has JavaScript syntax errors")

    print("✅ Dashboard JavaScript validated")
    return True


def main():
    """Main execution"""
    generator = SuperDashboardGenerator()
    generator.generate_dashboard()
    validate_dashboard_js()


if __name__ == "__main__":
    main()
