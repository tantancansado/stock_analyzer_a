#!/usr/bin/env python3
"""
BACKTEST DASHBOARD GENERATOR
Genera dashboard HTML con visualizaciones de resultados de backtest
"""
import json
import pandas as pd
from pathlib import Path
from datetime import datetime


class BacktestDashboardGenerator:
    """Generador de dashboard HTML para backtest results"""

    def __init__(self):
        self.template_dir = Path("docs/dashboard")
        self.template_dir.mkdir(parents=True, exist_ok=True)

    def generate_dashboard(self, metrics_file: str, trades_file: str,
                          equity_file: str, output_file: str = "docs/backtest_dashboard.html"):
        """
        Genera dashboard HTML completo

        Args:
            metrics_file: Path al JSON de métricas
            trades_file: Path al CSV de trades
            equity_file: Path al CSV de equity curve
            output_file: Path del HTML de salida
        """
        # Cargar datos
        with open(metrics_file, 'r') as f:
            metrics = json.load(f)

        trades_df = pd.read_csv(trades_file)
        equity_df = pd.read_csv(equity_file)

        # Generar HTML
        html = self._generate_html(metrics, trades_df, equity_df)

        # Guardar
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"✅ Dashboard generado: {output_file}")

    def _generate_html(self, metrics: dict, trades_df: pd.DataFrame,
                       equity_df: pd.DataFrame) -> str:
        """Genera HTML completo del dashboard"""

        # Preparar datos para charts
        equity_chart_data = self._prepare_equity_chart_data(equity_df)
        tier_chart_data = self._prepare_tier_chart_data(metrics)
        timing_chart_data = self._prepare_timing_chart_data(metrics)
        returns_distribution = self._prepare_returns_distribution(trades_df)

        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📊 Backtest Dashboard - 5D Strategy</title>
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
            max-width: 1400px;
            margin: 0 auto;
        }}

        .header {{
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }}

        .header h1 {{
            font-size: 3em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}

        .header .subtitle {{
            font-size: 1.2em;
            opacity: 0.9;
        }}

        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .metric-card {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            transition: transform 0.3s ease;
        }}

        .metric-card:hover {{
            transform: translateY(-5px);
        }}

        .metric-label {{
            font-size: 0.9em;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }}

        .metric-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #333;
        }}

        .metric-value.positive {{
            color: #10b981;
        }}

        .metric-value.negative {{
            color: #ef4444;
        }}

        .chart-container {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}

        .chart-title {{
            font-size: 1.5em;
            margin-bottom: 20px;
            color: #333;
        }}

        .chart-wrapper {{
            position: relative;
            height: 400px;
        }}

        .trades-table {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            overflow-x: auto;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
        }}

        th {{
            background: #667eea;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }}

        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #e5e7eb;
        }}

        tr:hover {{
            background: #f9fafb;
        }}

        .win {{
            color: #10b981;
            font-weight: bold;
        }}

        .loss {{
            color: #ef4444;
            font-weight: bold;
        }}

        .tier-badge {{
            padding: 4px 8px;
            border-radius: 5px;
            font-size: 0.9em;
            font-weight: bold;
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
            <a href="index.html" style="position: absolute; left: 20px; top: 20px; color: white; text-decoration: none; font-size: 1.2em; background: rgba(255,255,255,0.2); padding: 8px 16px; border-radius: 8px; transition: background 0.3s;" onmouseover="this.style.background='rgba(255,255,255,0.3)'" onmouseout="this.style.background='rgba(255,255,255,0.2)'">
                🏠 Volver
            </a>
            <h1>📊 Backtest Dashboard</h1>
            <div class="subtitle">5D Strategy Performance Analysis</div>
            <div class="subtitle" style="font-size: 0.9em; margin-top: 10px;">
                Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </div>
        </div>

        <!-- Métricas Principales -->
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">Total Trades</div>
                <div class="metric-value">{metrics['total_trades']}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Win Rate</div>
                <div class="metric-value positive">{metrics['win_rate']:.1f}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Avg Return</div>
                <div class="metric-value {'positive' if metrics['avg_return'] > 0 else 'negative'}">
                    {metrics['avg_return']:.2f}%
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Total Return</div>
                <div class="metric-value {'positive' if metrics['total_return'] > 0 else 'negative'}">
                    {metrics['total_return']:.2f}%
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Avg Hold Days</div>
                <div class="metric-value">{metrics['avg_hold_days']:.0f}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Avg Max DD</div>
                <div class="metric-value negative">{metrics['avg_max_drawdown']:.2f}%</div>
            </div>
        </div>

        <!-- Equity Curve -->
        <div class="chart-container">
            <div class="chart-title">📈 Equity Curve</div>
            <div class="chart-wrapper">
                <canvas id="equityChart"></canvas>
            </div>
        </div>

        <!-- Performance por Tier -->
        <div class="chart-container">
            <div class="chart-title">⭐ Performance por Tier</div>
            <div class="chart-wrapper">
                <canvas id="tierChart"></canvas>
            </div>
        </div>

        <!-- Timing Convergence Impact -->
        <div class="chart-container">
            <div class="chart-title">🔥 Timing Convergence Impact</div>
            <div class="chart-wrapper">
                <canvas id="timingChart"></canvas>
            </div>
        </div>

        <!-- Returns Distribution -->
        <div class="chart-container">
            <div class="chart-title">📊 Returns Distribution</div>
            <div class="chart-wrapper">
                <canvas id="returnsChart"></canvas>
            </div>
        </div>

        <!-- Top/Bottom Trades -->
        <div class="trades-table">
            <h2 style="margin-bottom: 20px;">🏆 Best Trades</h2>
            {self._generate_trades_table(trades_df.nlargest(10, 'return_pct'))}
        </div>

        <div class="trades-table" style="margin-top: 30px;">
            <h2 style="margin-bottom: 20px;">💔 Worst Trades</h2>
            {self._generate_trades_table(trades_df.nsmallest(10, 'return_pct'))}
        </div>

        <div class="footer">
            <p>🚀 Stock Analyzer 5D - Backtest Dashboard</p>
            <p style="font-size: 0.9em; margin-top: 5px;">
                Made with Claude Code
            </p>
        </div>
    </div>

    <script>
        // Equity Curve Chart
        const equityCtx = document.getElementById('equityChart').getContext('2d');
        new Chart(equityCtx, {{
            type: 'line',
            data: {{
                labels: {equity_chart_data['labels']},
                datasets: [{{
                    label: 'Portfolio Value',
                    data: {equity_chart_data['values']},
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        display: false
                    }}
                }},
                scales: {{
                    y: {{
                        ticks: {{
                            callback: function(value) {{
                                return '$' + value.toLocaleString();
                            }}
                        }}
                    }}
                }}
            }}
        }});

        // Tier Performance Chart
        const tierCtx = document.getElementById('tierChart').getContext('2d');
        new Chart(tierCtx, {{
            type: 'bar',
            data: {{
                labels: {tier_chart_data['labels']},
                datasets: [{{
                    label: 'Win Rate %',
                    data: {tier_chart_data['win_rates']},
                    backgroundColor: 'rgba(102, 126, 234, 0.8)',
                    borderColor: '#667eea',
                    borderWidth: 2,
                    yAxisID: 'y'
                }}, {{
                    label: 'Avg Return %',
                    data: {tier_chart_data['avg_returns']},
                    backgroundColor: 'rgba(16, 185, 129, 0.8)',
                    borderColor: '#10b981',
                    borderWidth: 2,
                    yAxisID: 'y1'
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {{
                            display: true,
                            text: 'Win Rate %'
                        }}
                    }},
                    y1: {{
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {{
                            display: true,
                            text: 'Avg Return %'
                        }},
                        grid: {{
                            drawOnChartArea: false
                        }}
                    }}
                }}
            }}
        }});

        // Timing Convergence Chart
        const timingCtx = document.getElementById('timingChart').getContext('2d');
        new Chart(timingCtx, {{
            type: 'bar',
            data: {{
                labels: {timing_chart_data['labels']},
                datasets: [{{
                    label: 'Win Rate %',
                    data: {timing_chart_data['win_rates']},
                    backgroundColor: ['rgba(239, 68, 68, 0.8)', 'rgba(16, 185, 129, 0.8)'],
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        display: false
                    }}
                }}
            }}
        }});

        // Returns Distribution
        const returnsCtx = document.getElementById('returnsChart').getContext('2d');
        new Chart(returnsCtx, {{
            type: 'bar',
            data: {{
                labels: {returns_distribution['labels']},
                datasets: [{{
                    label: 'Number of Trades',
                    data: {returns_distribution['counts']},
                    backgroundColor: 'rgba(102, 126, 234, 0.8)',
                    borderColor: '#667eea',
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    x: {{
                        title: {{
                            display: true,
                            text: 'Return %'
                        }}
                    }},
                    y: {{
                        title: {{
                            display: true,
                            text: 'Count'
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>"""

        return html

    def _prepare_equity_chart_data(self, equity_df: pd.DataFrame) -> dict:
        """Prepara datos para equity curve chart"""
        return {
            'labels': equity_df['date'].tolist(),
            'values': equity_df['equity'].round(2).tolist()
        }

    def _prepare_tier_chart_data(self, metrics: dict) -> dict:
        """Prepara datos para tier performance chart"""
        tier_metrics = metrics['tier_metrics']

        labels = []
        win_rates = []
        avg_returns = []

        for tier, data in sorted(tier_metrics.items()):
            labels.append(tier)
            win_rates.append(round(data['win_rate'], 2))
            avg_returns.append(round(data['avg_return'], 2))

        return {
            'labels': labels,
            'win_rates': win_rates,
            'avg_returns': avg_returns
        }

    def _prepare_timing_chart_data(self, metrics: dict) -> dict:
        """Prepara datos para timing convergence chart"""
        timing = metrics['timing_impact']

        return {
            'labels': ['Sin Timing', 'Con Timing'],
            'win_rates': [
                round(timing['without_timing']['win_rate'], 2),
                round(timing['with_timing']['win_rate'], 2)
            ]
        }

    def _prepare_returns_distribution(self, trades_df: pd.DataFrame) -> dict:
        """Prepara datos para distribución de returns"""
        # Crear bins para returns
        bins = [-100, -20, -10, -5, 0, 5, 10, 20, 50, 100, 500]
        labels = ['<-20%', '-20 to -10%', '-10 to -5%', '-5 to 0%',
                 '0 to 5%', '5 to 10%', '10 to 20%', '20 to 50%',
                 '50 to 100%', '>100%']

        counts, _ = pd.cut(trades_df['return_pct'], bins=bins, labels=labels,
                          retbins=True, include_lowest=True)

        distribution = counts.value_counts().sort_index()

        return {
            'labels': distribution.index.tolist(),
            'counts': distribution.values.tolist()
        }

    def _generate_trades_table(self, trades_df: pd.DataFrame) -> str:
        """Genera tabla HTML de trades"""
        rows = []
        for _, trade in trades_df.iterrows():
            win_class = 'win' if trade['return_pct'] > 0 else 'loss'
            rows.append(f"""
            <tr>
                <td><strong>{trade['ticker']}</strong></td>
                <td>{trade['entry_date']}</td>
                <td>{trade['exit_date']}</td>
                <td>${trade['entry_price']:.2f}</td>
                <td>${trade['exit_price']:.2f}</td>
                <td class="{win_class}">{trade['return_pct']:.2f}%</td>
                <td>{trade['hold_days']} días</td>
                <td><span class="tier-badge">{trade['tier']}</span></td>
                <td>{trade['score']:.0f}</td>
            </tr>
            """)

        return f"""
        <table>
            <thead>
                <tr>
                    <th>Ticker</th>
                    <th>Entry</th>
                    <th>Exit</th>
                    <th>Entry Price</th>
                    <th>Exit Price</th>
                    <th>Return</th>
                    <th>Hold</th>
                    <th>Tier</th>
                    <th>Score</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """


def main():
    """Main execution"""
    # Buscar archivos más recientes
    backtest_dir = Path("docs/backtest")

    if not backtest_dir.exists():
        print("❌ No se encontraron resultados de backtest")
        print("   Ejecuta primero: python3 backtest_engine.py")
        return

    # Obtener archivos más recientes
    metrics_files = list(backtest_dir.glob("metrics_*.json"))
    trades_files = list(backtest_dir.glob("trades_*.csv"))
    equity_files = list(backtest_dir.glob("equity_curve_*.csv"))

    if not metrics_files or not trades_files or not equity_files:
        print("❌ Archivos de backtest incompletos")
        return

    latest_metrics = sorted(metrics_files)[-1]
    latest_trades = sorted(trades_files)[-1]
    latest_equity = sorted(equity_files)[-1]

    print(f"📊 Generando dashboard desde:")
    print(f"   Metrics: {latest_metrics}")
    print(f"   Trades: {latest_trades}")
    print(f"   Equity: {latest_equity}")

    # Generar dashboard
    generator = BacktestDashboardGenerator()
    generator.generate_dashboard(
        str(latest_metrics),
        str(latest_trades),
        str(latest_equity)
    )


if __name__ == "__main__":
    main()
