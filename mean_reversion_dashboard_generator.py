#!/usr/bin/env python3
"""
MEAN REVERSION DASHBOARD GENERATOR
Genera dashboard HTML para visualizar oportunidades de reversión a la media
"""
import json
from pathlib import Path
from datetime import datetime


def generate_dashboard():
    """Generate HTML dashboard from Mean Reversion data"""

    # Load data
    json_path = Path("docs/mean_reversion_opportunities.json")

    if not json_path.exists():
        print("❌ No hay datos de Mean Reversion. Ejecutar mean_reversion_detector.py primero")
        return False

    with open(json_path, 'r') as f:
        data = json.load(f)

    opportunities = data.get('opportunities', [])
    scan_date = data.get('scan_date', 'Unknown')
    total = data.get('total_opportunities', 0)
    oversold = data['strategies'].get('oversold_bounce', 0)
    bull_flag = data['strategies'].get('bull_flag_pullback', 0)

    # Filter for quality opportunities (score >= 60)
    quality_opps = [opp for opp in opportunities if opp['reversion_score'] >= 60]

    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔄 Mean Reversion Dashboard</title>
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

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .stat-card {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            transition: transform 0.3s ease;
        }}

        .stat-card:hover {{
            transform: translateY(-5px);
        }}

        .stat-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 10px;
        }}

        .stat-label {{
            color: #666;
            font-size: 1em;
            font-weight: 500;
        }}

        .explanation-section {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}

        .explanation-section h2 {{
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.8em;
        }}

        .strategy-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}

        .strategy-card {{
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            border-radius: 12px;
            padding: 20px;
            border-left: 5px solid #667eea;
        }}

        .strategy-card h3 {{
            color: #333;
            margin-bottom: 15px;
            font-size: 1.3em;
        }}

        .strategy-card ul {{
            list-style: none;
            padding-left: 0;
        }}

        .strategy-card li {{
            color: #555;
            margin-bottom: 8px;
            padding-left: 20px;
            position: relative;
        }}

        .strategy-card li:before {{
            content: "✓";
            position: absolute;
            left: 0;
            color: #667eea;
            font-weight: bold;
        }}

        .opportunities-section {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 30px;
        }}

        .opportunities-section h2 {{
            color: #667eea;
            margin-bottom: 25px;
            font-size: 1.8em;
        }}

        .opportunities-table {{
            width: 100%;
            border-collapse: collapse;
            overflow-x: auto;
        }}

        .opportunities-table th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 10px;
            text-align: left;
            font-weight: 600;
            position: sticky;
            top: 0;
        }}

        .opportunities-table td {{
            padding: 15px 10px;
            border-bottom: 1px solid #eee;
        }}

        .opportunities-table tr:hover {{
            background: #f8f9fa;
        }}

        .ticker-cell {{
            font-weight: bold;
            color: #667eea;
            font-size: 1.1em;
        }}

        .company-name {{
            color: #666;
            font-size: 0.9em;
            margin-top: 3px;
        }}

        .score-badge {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.9em;
        }}

        .score-excellent {{
            background: #d4edda;
            color: #155724;
        }}

        .score-very-good {{
            background: #d1ecf1;
            color: #0c5460;
        }}

        .score-good {{
            background: #fff3cd;
            color: #856404;
        }}

        .strategy-badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 5px;
            font-size: 0.85em;
            font-weight: 600;
        }}

        .strategy-oversold {{
            background: #fef3c7;
            color: #92400e;
        }}

        .strategy-bullflag {{
            background: #dbeafe;
            color: #1e40af;
        }}

        .price-info {{
            font-size: 0.9em;
        }}

        .price-current {{
            font-weight: bold;
            color: #333;
        }}

        .price-target {{
            color: #10b981;
            margin-left: 5px;
        }}

        .upside-positive {{
            color: #10b981;
            font-weight: 600;
        }}

        .rr-good {{
            color: #10b981;
            font-weight: 600;
        }}

        .rr-moderate {{
            color: #f59e0b;
            font-weight: 600;
        }}

        /* Responsive Design */
        @media (max-width: 1024px) {{
            .header h1 {{
                font-size: 2.5em;
            }}

            .stats-grid {{
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

            .stats-grid {{
                grid-template-columns: 1fr;
            }}

            .strategy-cards {{
                grid-template-columns: 1fr;
            }}

            .opportunities-table {{
                font-size: 0.85em;
            }}

            .opportunities-table th,
            .opportunities-table td {{
                padding: 10px 5px;
            }}
        }}

        @media (max-width: 480px) {{
            .header h1 {{
                font-size: 1.6em;
            }}

            .stat-value {{
                font-size: 2em;
            }}

            .opportunities-section,
            .explanation-section {{
                padding: 20px;
            }}

            /* Make table scrollable horizontally on very small screens */
            .table-wrapper {{
                overflow-x: auto;
            }}

            .nav-button, button, a {{
                min-height: 44px; /* WCAG 2.1 touch target */
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <a href="index.html" class="nav-button">🏠 Volver</a>

        <div class="header">
            <h1>🔄 Mean Reversion Dashboard</h1>
            <div class="subtitle">Oportunidades de Compra en Dips de Calidad</div>
        </div>

        <div class="timestamp">
            📅 Última actualización: {scan_date}
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{total}</div>
                <div class="stat-label">Total Oportunidades</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(quality_opps)}</div>
                <div class="stat-label">Alta Calidad (≥60)</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{oversold}</div>
                <div class="stat-label">📉 Oversold Bounce</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{bull_flag}</div>
                <div class="stat-label">📊 Bull Flag Pullback</div>
            </div>
        </div>

        <div class="explanation-section">
            <h2>💡 ¿Qué es Mean Reversion?</h2>
            <p style="color: #555; line-height: 1.6; margin-bottom: 20px;">
                <strong>Mean Reversion</strong> es la estrategia de comprar stocks de alta calidad cuando
                caen significativamente por debajo de su valor promedio, anticipando que revertirán a la media.
                Complementa la estrategia VCP (breakouts) permitiendo entradas en dips controlados.
            </p>

            <div class="strategy-cards">
                <div class="strategy-card">
                    <h3>📉 Oversold Bounce</h3>
                    <p style="color: #666; margin-bottom: 15px;">
                        Stocks sobrevendidos con fundamentos sólidos listos para recuperación
                    </p>
                    <ul>
                        <li>RSI &lt; 30 (oversold)</li>
                        <li>Caída &gt; 20% desde máximo reciente</li>
                        <li>Cerca de nivel de soporte técnico</li>
                        <li>Volumen incrementando en bounce</li>
                        <li><strong>Ideal para:</strong> Entradas en pánico del mercado</li>
                    </ul>
                </div>

                <div class="strategy-card">
                    <h3>📊 Bull Flag Pullback</h3>
                    <p style="color: #666; margin-bottom: 15px;">
                        Retrocesos saludables en tendencias alcistas fuertes
                    </p>
                    <ul>
                        <li>Rally previo &gt; 30%</li>
                        <li>Pullback ordenado 10-15%</li>
                        <li>Tendencia mayor alcista (SMA50 &gt; SMA200)</li>
                        <li>Volumen decreciente en pullback</li>
                        <li><strong>Ideal para:</strong> Entradas en consolidaciones</li>
                    </ul>
                </div>
            </div>
        </div>

        <div class="opportunities-section">
            <h2>🏆 Top Oportunidades de Reversión</h2>
            <div class="table-wrapper">
                <table class="opportunities-table">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Ticker / Company</th>
                            <th>Estrategia</th>
                            <th>Score</th>
                            <th>Precio Actual</th>
                            <th>Target</th>
                            <th>Upside %</th>
                            <th>R/R</th>
                            <th>Entry Zone</th>
                        </tr>
                    </thead>
                    <tbody>
"""

    # Add top 30 opportunities
    for i, opp in enumerate(quality_opps[:30], 1):
        ticker = opp.get('ticker', 'N/A')
        company = opp.get('company_name', ticker)
        strategy = opp.get('strategy', 'N/A')
        score = opp.get('reversion_score', 0)
        quality = opp.get('quality', '')
        current = opp.get('current_price', 0)
        target = opp.get('target', 0)
        entry_zone = opp.get('entry_zone', 'N/A')
        rr = opp.get('risk_reward', 0)

        # Calculate upside
        upside_pct = ((target - current) / current * 100) if current > 0 else 0

        # Score badge class
        if score >= 80:
            score_class = 'score-excellent'
        elif score >= 70:
            score_class = 'score-very-good'
        else:
            score_class = 'score-good'

        # Strategy badge
        strategy_class = 'strategy-oversold' if strategy == 'Oversold Bounce' else 'strategy-bullflag'
        strategy_emoji = '📉' if strategy == 'Oversold Bounce' else '📊'

        # R/R class
        rr_class = 'rr-good' if rr >= 2 else 'rr-moderate'

        html += f"""
                        <tr>
                            <td>{i}</td>
                            <td>
                                <div class="ticker-cell">{ticker}</div>
                                <div class="company-name">{company}</div>
                            </td>
                            <td>
                                <span class="strategy-badge {strategy_class}">
                                    {strategy_emoji} {strategy}
                                </span>
                            </td>
                            <td>
                                <span class="score-badge {score_class}">
                                    {score:.0f}/100
                                </span>
                            </td>
                            <td class="price-current">${current:.2f}</td>
                            <td class="price-target">${target:.2f}</td>
                            <td class="upside-positive">+{upside_pct:.1f}%</td>
                            <td class="{rr_class}">{rr:.1f}:1</td>
                            <td style="font-size: 0.9em;">{entry_zone}</td>
                        </tr>
"""

    html += """
                    </tbody>
                </table>
            </div>
        </div>

        <div style="text-align: center; color: white; opacity: 0.8; padding: 20px 0;">
            <p>🤖 Generated by Stock Analyzer System</p>
            <p style="margin-top: 5px;">Mean Reversion Detector - Buy the Dip Strategy</p>
        </div>
    </div>
</body>
</html>
"""

    # Save HTML
    output_path = Path("docs/mean_reversion_dashboard.html")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ Dashboard generado: {output_path}")
    print(f"📊 {len(quality_opps)} oportunidades de alta calidad incluidas")

    return True


if __name__ == "__main__":
    print("=" * 80)
    print("📊 MEAN REVERSION DASHBOARD GENERATOR")
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
