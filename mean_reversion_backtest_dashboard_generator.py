#!/usr/bin/env python3
"""
MEAN REVERSION BACKTEST DASHBOARD GENERATOR
Genera dashboard HTML para visualizar resultados del backtest
"""
import json
from pathlib import Path
from datetime import datetime


def generate_dashboard():
    """Generate HTML dashboard from backtest results"""

    # Load backtest data
    json_path = Path("docs/backtest/mean_reversion_backtest_latest.json")

    if not json_path.exists():
        print("❌ No hay resultados de backtest. Ejecutar mean_reversion_backtester.py primero")
        return False

    with open(json_path, 'r') as f:
        data = json.load(f)

    metrics = data.get('metrics', {})
    trades = data.get('trades', [])
    backtest_date = data.get('backtest_date', 'Unknown')

    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📊 Mean Reversion Backtest Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            min-height: 100vh;
            padding: 20px;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            position: relative;
        }}

        .nav-button {{
            position: absolute;
            left: 0;
            top: 0;
            background: rgba(255, 255, 255, 0.2);
            color: white;
            padding: 12px 24px;
            border-radius: 10px;
            text-decoration: none;
            font-size: 1.1em;
            font-weight: 600;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }}

        .nav-button:hover {{
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-2px);
        }}

        .header {{
            text-align: center;
            color: white;
            margin-bottom: 30px;
            padding-top: 10px;
        }}

        .header h1 {{
            font-size: 3em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}

        .header .subtitle {{
            font-size: 1.2em;
            opacity: 0.9;
            margin-bottom: 5px;
        }}

        .timestamp {{
            text-align: center;
            color: white;
            opacity: 0.8;
            margin-bottom: 30px;
            font-size: 0.95em;
        }}

        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .metric-card {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            transition: transform 0.3s ease;
        }}

        .metric-card:hover {{
            transform: translateY(-5px);
        }}

        .metric-value {{
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 10px;
        }}

        .metric-value.positive {{
            color: #10b981;
        }}

        .metric-value.negative {{
            color: #ef4444;
        }}

        .metric-value.neutral {{
            color: #3b82f6;
        }}

        .metric-label {{
            color: #666;
            font-size: 1em;
            font-weight: 500;
        }}

        .chart-section {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}

        .chart-section h2 {{
            color: #1e3c72;
            margin-bottom: 25px;
            font-size: 1.8em;
        }}

        .chart-wrapper {{
            position: relative;
            height: 400px;
        }}

        .strategy-comparison {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .strategy-card {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}

        .strategy-card h3 {{
            color: #1e3c72;
            margin-bottom: 20px;
            font-size: 1.5em;
        }}

        .strategy-stat {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 1px solid #eee;
        }}

        .strategy-stat:last-child {{
            border-bottom: none;
        }}

        .stat-label {{
            color: #666;
            font-weight: 500;
        }}

        .stat-value {{
            font-weight: bold;
            color: #333;
        }}

        .trades-section {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 30px;
        }}

        .trades-section h2 {{
            color: #1e3c72;
            margin-bottom: 25px;
            font-size: 1.8em;
        }}

        .trades-table {{
            width: 100%;
            border-collapse: collapse;
            overflow-x: auto;
        }}

        .trades-table th {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 15px 10px;
            text-align: left;
            font-weight: 600;
            position: sticky;
            top: 0;
        }}

        .trades-table td {{
            padding: 15px 10px;
            border-bottom: 1px solid #eee;
        }}

        .trades-table tr:hover {{
            background: #f8f9fa;
        }}

        .ticker-cell {{
            font-weight: bold;
            color: #1e3c72;
            font-size: 1.1em;
        }}

        .profit-positive {{
            color: #10b981;
            font-weight: 600;
        }}

        .profit-negative {{
            color: #ef4444;
            font-weight: 600;
        }}

        .badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 5px;
            font-size: 0.85em;
            font-weight: 600;
        }}

        .badge-target {{
            background: #d4edda;
            color: #155724;
        }}

        .badge-stop {{
            background: #f8d7da;
            color: #721c24;
        }}

        .badge-holding {{
            background: #fff3cd;
            color: #856404;
        }}

        .badge-oversold {{
            background: #fef3c7;
            color: #92400e;
        }}

        .badge-bullflag {{
            background: #dbeafe;
            color: #1e40af;
        }}

        /* Responsive Design */
        @media (max-width: 1024px) {{
            .header h1 {{
                font-size: 2.5em;
            }}

            .metrics-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
        }}

        @media (max-width: 768px) {{
            body {{
                padding: 15px;
            }}

            .header h1 {{
                font-size: 2em;
            }}

            .nav-button {{
                position: static;
                display: block;
                margin-bottom: 20px;
                text-align: center;
            }}

            .metrics-grid {{
                grid-template-columns: 1fr;
            }}

            .strategy-comparison {{
                grid-template-columns: 1fr;
            }}

            .trades-table {{
                font-size: 0.85em;
            }}

            .trades-table th,
            .trades-table td {{
                padding: 10px 5px;
            }}
        }}

        @media (max-width: 480px) {{
            .header h1 {{
                font-size: 1.6em;
            }}

            .metric-value {{
                font-size: 2em;
            }}

            .nav-button, button, a {{
                min-height: 44px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <a href="mean_reversion_dashboard.html" class="nav-button">🔄 Mean Reversion</a>

        <div class="header">
            <h1>📊 Mean Reversion Backtest</h1>
            <div class="subtitle">Validación Histórica de Estrategias</div>
        </div>

        <div class="timestamp">
            📅 Backtest ejecutado: {backtest_date}
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value neutral">{metrics['total_trades']}</div>
                <div class="metric-label">Total Trades</div>
            </div>
            <div class="metric-card">
                <div class="metric-value positive">{metrics['win_rate']:.1f}%</div>
                <div class="metric-label">Win Rate</div>
            </div>
            <div class="metric-card">
                <div class="metric-value positive">+{metrics['avg_win']:.2f}%</div>
                <div class="metric-label">Avg Win</div>
            </div>
            <div class="metric-card">
                <div class="metric-value negative">{metrics['avg_loss']:.2f}%</div>
                <div class="metric-label">Avg Loss</div>
            </div>
            <div class="metric-card">
                <div class="metric-value positive">{metrics['profit_factor']:.2f}</div>
                <div class="metric-label">Profit Factor</div>
            </div>
            <div class="metric-card">
                <div class="metric-value positive">+{metrics['total_return_pct']:.2f}%</div>
                <div class="metric-label">Total Return</div>
            </div>
            <div class="metric-card">
                <div class="metric-value negative">{metrics['max_drawdown']:.2f}%</div>
                <div class="metric-label">Max Drawdown</div>
            </div>
            <div class="metric-card">
                <div class="metric-value neutral">{metrics['target_hits']}/{metrics['total_trades']}</div>
                <div class="metric-label">Target Hits</div>
            </div>
        </div>

        <div class="strategy-comparison">
"""

    # Strategy cards
    for strategy_name, strategy_data in metrics['strategies'].items():
        emoji = "📉" if strategy_name == "Oversold Bounce" else "📊"
        html += f"""
            <div class="strategy-card">
                <h3>{emoji} {strategy_name}</h3>
                <div class="strategy-stat">
                    <span class="stat-label">Total Trades</span>
                    <span class="stat-value">{strategy_data['total_trades']}</span>
                </div>
                <div class="strategy-stat">
                    <span class="stat-label">Win Rate</span>
                    <span class="stat-value">{strategy_data['win_rate']:.1f}%</span>
                </div>
                <div class="strategy-stat">
                    <span class="stat-label">Avg Profit</span>
                    <span class="stat-value">{strategy_data['avg_profit']:+.2f}%</span>
                </div>
                <div class="strategy-stat">
                    <span class="stat-label">Total Profit</span>
                    <span class="stat-value">{strategy_data['total_profit']:+.2f}%</span>
                </div>
            </div>
"""

    html += """
        </div>

        <div class="chart-section">
            <h2>📈 Equity Curve</h2>
            <div class="chart-wrapper">
                <canvas id="equityChart"></canvas>
            </div>
        </div>

        <div class="trades-section">
            <h2>🏆 Top 10 Best Trades</h2>
            <table class="trades-table">
                <thead>
                    <tr>
                        <th>Ticker</th>
                        <th>Strategy</th>
                        <th>Entry</th>
                        <th>Exit</th>
                        <th>P/L %</th>
                        <th>Exit Reason</th>
                        <th>Holding Days</th>
                    </tr>
                </thead>
                <tbody>
"""

    # Sort trades by profit
    sorted_trades = sorted(trades, key=lambda x: x['profit_loss_pct'], reverse=True)

    # Top 10 best trades
    for trade in sorted_trades[:10]:
        strategy_class = 'badge-oversold' if trade['strategy'] == 'Oversold Bounce' else 'badge-bullflag'
        exit_class = {
            'TARGET': 'badge-target',
            'STOP_LOSS': 'badge-stop',
            'HOLDING_PERIOD': 'badge-holding'
        }.get(trade['exit_reason'], '')

        profit_class = 'profit-positive' if trade['profit_loss_pct'] > 0 else 'profit-negative'

        html += f"""
                    <tr>
                        <td class="ticker-cell">{trade['ticker']}</td>
                        <td><span class="badge {strategy_class}">{trade['strategy']}</span></td>
                        <td>${trade['entry_price']:.2f}</td>
                        <td>${trade['exit_price']:.2f}</td>
                        <td class="{profit_class}">{trade['profit_loss_pct']:+.2f}%</td>
                        <td><span class="badge {exit_class}">{trade['exit_reason']}</span></td>
                        <td>{trade['holding_days']}</td>
                    </tr>
"""

    html += """
                </tbody>
            </table>
        </div>

        <div style="text-align: center; color: white; opacity: 0.8; padding: 20px 0;">
            <p>🤖 Generated by Stock Analyzer System</p>
            <p style="margin-top: 5px;">Mean Reversion Backtest Engine</p>
        </div>
    </div>

    <script>
        // Equity Curve Chart
        const equityCurve = """ + json.dumps(metrics['equity_curve']) + """;

        const ctx = document.getElementById('equityChart').getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: equityCurve.map(point => point.entry_date),
                datasets: [{
                    label: 'Cumulative Return (%)',
                    data: equityCurve.map(point => point.cumulative_return * 100),
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Date'
                        },
                        ticks: {
                            maxRotation: 45,
                            minRotation: 45
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Cumulative Return (%)'
                        }
                    }
                }
            }
        });
    </script>
</body>
</html>
"""

    # Save HTML
    output_path = Path("docs/mean_reversion_backtest_dashboard.html")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ Dashboard generado: {output_path}")

    return True


if __name__ == "__main__":
    print("=" * 80)
    print("📊 MEAN REVERSION BACKTEST DASHBOARD GENERATOR")
    print("=" * 80)
    print()

    if generate_dashboard():
        print()
        print("=" * 80)
        print("✅ Dashboard completado exitosamente")
        print("=" * 80)
    else:
        print()
        print("=" * 80)
        print("❌ Error generando dashboard")
        print("=" * 80)
