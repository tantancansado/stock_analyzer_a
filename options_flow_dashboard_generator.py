#!/usr/bin/env python3
"""
OPTIONS FLOW DASHBOARD GENERATOR
Genera dashboard HTML interactivo para visualizar flujo institucional de opciones
"""
import json
from pathlib import Path
from datetime import datetime


def generate_dashboard():
    """Generate HTML dashboard from Options Flow data"""

    # Load data
    json_path = Path("docs/options_flow.json")

    if not json_path.exists():
        print("❌ No hay datos de Options Flow. Ejecutar options_flow_detector.py primero")
        return False

    with open(json_path, 'r') as f:
        data = json.load(f)

    flows = data.get('flows', [])
    scan_date = data.get('scan_date', 'Unknown')
    total_flows = data.get('total_flows', 0)
    sentiment = data.get('sentiment_breakdown', {})
    total_premium = data.get('total_premium', 0)

    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📊 Options Flow Dashboard</title>
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
            max-width: 1600px;
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
        }}

        .timestamp {{
            text-align: center;
            color: white;
            opacity: 0.8;
            margin-bottom: 30px;
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

        .explanation-section h3 {{
            color: #333;
            margin: 20px 0 15px 0;
            font-size: 1.3em;
        }}

        .explanation-section p {{
            color: #555;
            line-height: 1.6;
            margin-bottom: 15px;
        }}

        .concept-box {{
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            border-radius: 12px;
            padding: 20px;
            margin: 15px 0;
            border-left: 5px solid #667eea;
        }}

        .concept-box h4 {{
            color: #333;
            margin-bottom: 10px;
        }}

        .concept-box ul {{
            list-style: none;
            padding-left: 0;
        }}

        .concept-box li {{
            color: #555;
            margin-bottom: 8px;
            padding-left: 20px;
            position: relative;
        }}

        .concept-box li:before {{
            content: "→";
            position: absolute;
            left: 0;
            color: #667eea;
            font-weight: bold;
        }}

        .flows-section {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 30px;
        }}

        .flows-section h2 {{
            color: #667eea;
            margin-bottom: 25px;
            font-size: 1.8em;
        }}

        .flow-card {{
            background: white;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            border-left: 5px solid;
        }}

        .flow-card.bullish {{
            border-color: #10b981;
        }}

        .flow-card.bearish {{
            border-color: #ef4444;
        }}

        .flow-card.neutral {{
            border-color: #f59e0b;
        }}

        .flow-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }}

        .flow-ticker {{
            font-size: 1.5em;
            font-weight: bold;
            color: #333;
        }}

        .flow-company {{
            color: #666;
            font-size: 0.9em;
            margin-top: 5px;
        }}

        .flow-score {{
            font-size: 1.8em;
            font-weight: bold;
            color: #667eea;
        }}

        .flow-metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin: 15px 0;
        }}

        .metric {{
            text-align: center;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 8px;
        }}

        .metric-label {{
            color: #666;
            font-size: 0.85em;
            margin-bottom: 5px;
        }}

        .metric-value {{
            color: #333;
            font-weight: bold;
            font-size: 1.2em;
        }}

        .sentiment-badge {{
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.9em;
            margin-top: 10px;
        }}

        .sentiment-bullish {{
            background: #d4edda;
            color: #155724;
        }}

        .sentiment-bearish {{
            background: #f8d7da;
            color: #721c24;
        }}

        .sentiment-neutral {{
            background: #fff3cd;
            color: #856404;
        }}

        .options-detail {{
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #eee;
        }}

        .options-detail h4 {{
            color: #667eea;
            margin-bottom: 10px;
            font-size: 1.1em;
        }}

        .option-item {{
            background: #f8f9fa;
            padding: 10px;
            border-radius: 6px;
            margin-bottom: 8px;
        }}

        .option-item strong {{
            color: #333;
        }}

        .thesis-section {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}

        .thesis-section h2 {{
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.8em;
        }}

        .thesis-card {{
            background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 15px;
            border-left: 5px solid #f59e0b;
        }}

        .thesis-card h3 {{
            color: #92400e;
            margin-bottom: 10px;
        }}

        .thesis-card p {{
            color: #78350f;
            line-height: 1.6;
        }}

        /* Responsive */
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

            .flow-header {{
                flex-direction: column;
                align-items: flex-start;
            }}

            .flow-metrics {{
                grid-template-columns: 1fr;
            }}
        }}

        @media (max-width: 480px) {{
            .header h1 {{
                font-size: 1.6em;
            }}

            .stat-value {{
                font-size: 2em;
            }}

            .nav-button {{
                min-height: 44px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <a href="index.html" class="nav-button">🏠 Volver</a>

        <div class="header">
            <h1>📊 Options Flow Dashboard</h1>
            <div class="subtitle">Detecta Movimientos Institucionales y Whale Activity</div>
        </div>

        <div class="timestamp">
            📅 Última actualización: {scan_date}
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{total_flows}</div>
                <div class="stat-label">Flujos Inusuales</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${total_premium/1000000:.1f}M</div>
                <div class="stat-label">Premium Total</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{sentiment.get('bullish', 0)}</div>
                <div class="stat-label">🟢 Bullish</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{sentiment.get('bearish', 0)}</div>
                <div class="stat-label">🔴 Bearish</div>
            </div>
        </div>

        <div class="explanation-section">
            <h2>💡 ¿Qué es Options Flow Analysis?</h2>

            <p>
                <strong>Options Flow</strong> detecta movimientos grandes de dinero institucional en el mercado de opciones.
                Cuando whales (institucionales/fondos) toman posiciones significativas, deja huellas detectables que
                pueden anticipar movimientos del stock subyacente.
            </p>

            <h3>🔍 Conceptos Clave</h3>

            <div class="concept-box">
                <h4>📊 Unusual Options Activity (UOA)</h4>
                <ul>
                    <li>Volumen de opciones significativamente mayor que el Open Interest normal</li>
                    <li>Indica entrada de dinero fresco (no cierre de posiciones existentes)</li>
                    <li>Ratio Vol/OI &gt; 3x = señal de actividad inusual</li>
                    <li>Volumen &gt; 100 contratos = movimiento significativo</li>
                </ul>
            </div>

            <div class="concept-box">
                <h4>💰 Premium (Dinero en Juego)</h4>
                <ul>
                    <li>Premium = Precio de la opción × Volumen × 100 (shares por contrato)</li>
                    <li>&gt; $10K = Retail significativo</li>
                    <li>&gt; $100K = Posible institucional</li>
                    <li>&gt; $1M = WHALE ACTIVITY confirmada</li>
                    <li>Más premium = más convicción en la dirección</li>
                </ul>
            </div>

            <div class="concept-box">
                <h4>📈 Put/Call Ratio</h4>
                <ul>
                    <li>Ratio = Premium en Puts ÷ Premium en Calls</li>
                    <li>&gt; 2.0 = BEARISH (comprando protección/apostando a caída)</li>
                    <li>&lt; 0.5 = BULLISH (apostando a subida)</li>
                    <li>0.5 - 2.0 = NEUTRAL (balanceado)</li>
                    <li>Extremos indican convicción fuerte</li>
                </ul>
            </div>

            <div class="concept-box">
                <h4>🐋 Whale Positioning</h4>
                <ul>
                    <li>Institucionales mueven $1M+ en single trades</li>
                    <li>Múltiples strikes = hedging sofisticado</li>
                    <li>Near-the-money = especulación direccional</li>
                    <li>Out-of-money = apuestas de alto riesgo/retorno</li>
                    <li>Seguir el dinero inteligente puede anticipar movimientos</li>
                </ul>
            </div>

            <h3>🎯 Cómo Usar Esta Información</h3>

            <div class="concept-box">
                <h4>Señales Bullish 🟢</h4>
                <ul>
                    <li>Mucho premium en CALLS (especialmente near-the-money)</li>
                    <li>Put/Call ratio &lt; 0.5</li>
                    <li>Strikes progresivamente más altos (apostando a subida fuerte)</li>
                    <li><strong>Tesis:</strong> Institucionales esperan movimiento alcista</li>
                </ul>
            </div>

            <div class="concept-box">
                <h4>Señales Bearish 🔴</h4>
                <ul>
                    <li>Mucho premium en PUTS (protección o apuesta bajista)</li>
                    <li>Put/Call ratio &gt; 2.0</li>
                    <li>Puts at-the-money = máxima protección</li>
                    <li><strong>Tesis:</strong> Institucionales se protegen o apuestan a caída</li>
                </ul>
            </div>
        </div>

        <div class="thesis-section">
            <h2>📋 Market Thesis Actual</h2>
"""

    # Generate market thesis based on current flows
    bearish_count = sentiment.get('bearish', 0)
    bullish_count = sentiment.get('bullish', 0)
    total = bearish_count + bullish_count + sentiment.get('neutral', 0)

    if total > 0:
        bearish_pct = (bearish_count / total) * 100
        bullish_pct = (bullish_count / total) * 100

        if bearish_pct > 60:
            thesis = f"""
            <div class="thesis-card">
                <h3>🔴 Sesgo Bearish Dominante ({bearish_pct:.0f}% de flujos)</h3>
                <p>
                    <strong>Interpretación:</strong> Institucionales están comprando protección masivamente o apostando a caídas.
                    Esto sugiere expectativas de volatilidad bajista o corrección en el corto plazo.
                </p>
                <p>
                    <strong>Implicaciones:</strong> Considerar reducir exposición, comprar puts para protección, o esperar
                    confirmación antes de entradas largas. El dinero inteligente está cauteloso.
                </p>
                <p>
                    <strong>Contrarian View:</strong> Si el mercado NO cae a pesar de este positioning, podría indicar
                    un fondo formándose (whales equivocados o hedging exagerado).
                </p>
            </div>
"""
        elif bullish_pct > 60:
            thesis = f"""
            <div class="thesis-card">
                <h3>🟢 Sesgo Bullish Dominante ({bullish_pct:.0f}% de flujos)</h3>
                <p>
                    <strong>Interpretación:</strong> Institucionales están posicionándose para movimiento alcista.
                    Flujo significativo en calls indica expectativas de apreciación.
                </p>
                <p>
                    <strong>Implicaciones:</strong> Alinearse con el flujo puede ser favorable. Considerar entradas
                    en stocks con strong call flow. El dinero inteligente está optimista.
                </p>
                <p>
                    <strong>Riesgo:</strong> Exceso de optimismo puede indicar techo cercano. Monitorear si
                    el stock sigue la dirección esperada.
                </p>
            </div>
"""
        else:
            thesis = f"""
            <div class="thesis-card">
                <h3>🟡 Sesgo Mixto ({bearish_pct:.0f}% bearish, {bullish_pct:.0f}% bullish)</h3>
                <p>
                    <strong>Interpretación:</strong> Mercado dividido. Algunos institucionales protegiendo mientras
                    otros apuestan alcista. Indica incertidumbre o diferentes timeframes.
                </p>
                <p>
                    <strong>Implicaciones:</strong> Analizar cada stock individualmente. Flujos mixtos pueden
                    preceder breakouts en cualquier dirección. Esperar confirmación de precio.
                </p>
                <p>
                    <strong>Estrategia:</strong> Range trading o esperar resolución direccional clara antes de
                    tomar posiciones significativas.
                </p>
            </div>
"""
    else:
        thesis = """
            <div class="thesis-card">
                <h3>ℹ️ Sin Flujos Significativos</h3>
                <p>No se detectó actividad inusual suficiente para generar tesis de mercado.</p>
            </div>
"""

    html += thesis + """
        </div>

        <div class="flows-section">
            <h2>🔥 Flujos Institucionales Detectados</h2>
"""

    # Add flow cards
    for i, flow in enumerate(flows[:15], 1):
        sentiment_class = flow['sentiment'].lower()
        sentiment_badge_class = f"sentiment-{sentiment_class}"

        top_calls_html = ""
        if flow.get('top_calls') and len(flow['top_calls']) > 0:
            top_calls_html = "<h4>📈 Top Calls</h4>"
            for call in flow['top_calls'][:2]:
                itm_status = "ITM" if call['itm'] else "OTM"
                top_calls_html += f"""
                <div class="option-item">
                    <strong>${call['strike']:.2f}</strong> strike |
                    Vol: {call['volume']} |
                    Premium: ${call['premium']/1000:.0f}K |
                    {itm_status}
                </div>
"""

        top_puts_html = ""
        if flow.get('top_puts') and len(flow['top_puts']) > 0:
            top_puts_html = "<h4>📉 Top Puts</h4>"
            for put in flow['top_puts'][:2]:
                itm_status = "ITM" if put['itm'] else "OTM"
                top_puts_html += f"""
                <div class="option-item">
                    <strong>${put['strike']:.2f}</strong> strike |
                    Vol: {put['volume']} |
                    Premium: ${put['premium']/1000:.0f}K |
                    {itm_status}
                </div>
"""

        html += f"""
            <div class="flow-card {sentiment_class}">
                <div class="flow-header">
                    <div>
                        <div class="flow-ticker">{i}. {flow['ticker']}</div>
                        <div class="flow-company">{flow['company_name']}</div>
                        <span class="sentiment-badge {sentiment_badge_class}">
                            {flow['sentiment_emoji']} {flow['sentiment']}
                        </span>
                    </div>
                    <div class="flow-score">{flow['flow_score']:.0f}/100</div>
                </div>

                <div style="color: #666; margin: 10px 0;">
                    {flow['quality']}
                </div>

                <div class="flow-metrics">
                    <div class="metric">
                        <div class="metric-label">Precio Actual</div>
                        <div class="metric-value">${flow['current_price']:.2f}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Premium Total</div>
                        <div class="metric-value">${flow['total_premium']/1000:.0f}K</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Put/Call Ratio</div>
                        <div class="metric-value">{'∞' if flow['put_call_ratio'] >= 100 else f"{flow['put_call_ratio']:.2f}"}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Contratos Inusuales</div>
                        <div class="metric-value">{flow['unusual_calls']}C / {flow['unusual_puts']}P</div>
                    </div>
                </div>

                <div class="options-detail">
                    {top_calls_html}
                    {top_puts_html}
                </div>
            </div>
"""

    html += """
        </div>

        <div style="text-align: center; color: white; opacity: 0.8; padding: 20px 0;">
            <p>🤖 Generated by Stock Analyzer System</p>
            <p style="margin-top: 5px;">Options Flow Detector - Institutional Money Tracking</p>
        </div>
    </div>
</body>
</html>
"""

    # Save HTML
    output_path = Path("docs/options_flow_dashboard.html")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ Dashboard generado: {output_path}")
    print(f"📊 {len(flows)} flujos incluidos")

    return True


if __name__ == "__main__":
    print("=" * 80)
    print("📊 OPTIONS FLOW DASHBOARD GENERATOR")
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
