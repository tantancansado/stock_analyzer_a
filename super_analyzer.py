#!/usr/bin/env python3
"""
SUPER ANALYZER - Análisis Triple Dimensional
Cruza: VCP Patterns + Recurring Insiders + Estado Sectorial
Identifica SUPER OPORTUNIDADES con señales técnicas + fundamentales + sectoriales
"""
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def load_vcp_data():
    """Carga datos VCP desde CSV"""
    vcp_csv = "docs/reports/vcp/vcp_scan_20250711_103128/data.csv"
    if Path(vcp_csv).exists():
        df = pd.read_csv(vcp_csv)
        print(f"✅ VCP Data: {len(df)} patrones cargados")
        return df
    return pd.DataFrame()

def load_recurring_insiders_data():
    """Carga datos de Recurring Insiders"""
    recurring_csv = "docs/recurring_insiders.csv"
    if Path(recurring_csv).exists():
        df = pd.read_csv(recurring_csv)
        print(f"✅ Recurring Insiders: {len(df)} tickers cargados")
        return df
    return pd.DataFrame()

def load_dj_sectorial_data():
    """Carga datos DJ Sectorial más recientes"""
    # Buscar el CSV más reciente
    import glob
    csv_files = glob.glob("docs/reports/dj_sectorial/dj_sectorial_*/data.csv")
    if csv_files:
        latest_csv = sorted(csv_files)[-1]
        df = pd.read_csv(latest_csv)
        print(f"✅ DJ Sectorial: {len(df)} sectores cargados")
        return df
    return pd.DataFrame()

def analyze_sector_state(sector_name, dj_data):
    """Analiza el estado de un sector"""
    if dj_data.empty:
        return {"state": "UNKNOWN", "score": 50, "details": "Sin datos"}

    # Buscar sector relacionado (matching aproximado)
    sector_keywords = {
        'Technology': ['Tech', 'Software', 'Computer', 'Internet', 'Semi'],
        'Healthcare': ['Health', 'Pharma', 'Bio', 'Medical'],
        'Financial Services': ['Bank', 'Financial', 'Insurance'],
        'Energy': ['Oil', 'Gas', 'Energy'],
        'Consumer Cyclical': ['Consumer', 'Retail', 'Auto'],
        'Consumer Defensive': ['Food', 'Beverage', 'Household'],
        'Industrials': ['Industrial', 'Aerospace', 'Defense', 'Transport'],
        'Basic Materials': ['Materials', 'Chemical', 'Mining', 'Steel'],
        'Real Estate': ['Real Estate', 'REIT'],
        'Communication Services': ['Media', 'Telecom', 'Entertainment'],
        'Utilities': ['Utilities', 'Electric', 'Water']
    }

    # Buscar keywords en DJ data
    matching_sectors = []
    keywords = sector_keywords.get(sector_name, [sector_name])

    for _, row in dj_data.iterrows():
        sector_dj = row['Sector']
        for keyword in keywords:
            if keyword.lower() in sector_dj.lower():
                matching_sectors.append(row)
                break

    if not matching_sectors:
        return {"state": "NO_DATA", "score": 50, "details": "Sector no encontrado"}

    # Analizar sectores matching
    avg_distance = sum(s['DistanceFromMin'] for s in matching_sectors) / len(matching_sectors)
    avg_rsi = sum(s['RSI'] for s in matching_sectors) / len(matching_sectors)

    # Scoring del sector
    sector_score = 0
    state = ""
    details = ""

    # Distancia de mínimos (cerca = oportunidad)
    if avg_distance < 10:
        sector_score += 40
        state = "🟢 MÍNIMOS"
        details = f"Subió {avg_distance:.1f}% desde mínimos - GRAN OPORTUNIDAD"
    elif avg_distance < 25:
        sector_score += 30
        state = "🟡 RECUPERACIÓN"
        details = f"Subió {avg_distance:.1f}% desde mínimos - Recuperándose"
    elif avg_distance < 50:
        sector_score += 20
        state = "🔵 NEUTRAL"
        details = f"Subió {avg_distance:.1f}% desde mínimos - Zona media"
    else:
        sector_score += 10
        state = "🔴 MÁXIMOS"
        details = f"Subió {avg_distance:.1f}% desde mínimos - Zona alta"

    # RSI (sobreventa = oportunidad)
    if avg_rsi < 30:
        sector_score += 20
        details += f" | RSI {avg_rsi:.1f} (sobreventa)"
    elif avg_rsi < 50:
        sector_score += 15
        details += f" | RSI {avg_rsi:.1f} (neutral-bajo)"
    elif avg_rsi < 70:
        sector_score += 10
        details += f" | RSI {avg_rsi:.1f} (neutral-alto)"
    else:
        sector_score += 5
        details += f" | RSI {avg_rsi:.1f} (sobrecompra)"

    return {
        "state": state,
        "score": sector_score,
        "details": details,
        "distance_from_min": avg_distance,
        "rsi": avg_rsi,
        "matching_sectors": len(matching_sectors)
    }

def find_super_opportunities(vcp_data, recurring_data, dj_data):
    """Encuentra SUPER OPORTUNIDADES cruzando las tres dimensiones"""
    print("\n🚀 ANALIZANDO SUPER OPORTUNIDADES")
    print("=" * 80)

    super_opportunities = []

    # Crear diccionarios para búsqueda rápida
    recurring_dict = {row['ticker']: row for _, row in recurring_data.iterrows()}

    for _, vcp_row in vcp_data.iterrows():
        ticker = vcp_row['ticker']

        # Check si tiene VCP de calidad
        if vcp_row['calidad_patron'] not in ['Excellent', 'Good']:
            continue

        # Check si está en recurring insiders
        if ticker not in recurring_dict:
            continue

        recurring_info = recurring_dict[ticker]

        # Analizar estado del sector
        sector = vcp_row['sector']
        sector_analysis = analyze_sector_state(sector, dj_data)

        # Calcular SUPER SCORE (0-100)
        vcp_score = vcp_row['vcp_score']  # 0-100
        recurring_score = min(recurring_info['confidence_score'] * 0.5, 50)  # 0-50
        sector_score = sector_analysis['score']  # 0-60

        super_score = (vcp_score * 0.4 + recurring_score * 0.3 + sector_score * 0.3)

        # Clasificar oportunidad
        if super_score >= 80:
            classification = "⭐⭐⭐ ÉPICA"
            color = "#48bb78"
        elif super_score >= 70:
            classification = "⭐⭐ EXCELENTE"
            color = "#4299e1"
        elif super_score >= 60:
            classification = "⭐ BUENA"
            color = "#f6ad55"
        else:
            classification = "📊 INTERESANTE"
            color = "#a0aec0"

        super_opportunities.append({
            'ticker': ticker,
            'super_score': super_score,
            'classification': classification,
            'color': color,

            # VCP Info
            'vcp_score': vcp_score,
            'vcp_quality': vcp_row['calidad_patron'],
            'vcp_contractions': vcp_row['num_contracciones'],
            'vcp_ready_to_buy': vcp_row['listo_comprar'],
            'price': vcp_row['precio'],

            # Recurring Insiders Info
            'recurring_purchases': recurring_info['purchase_count'],
            'recurring_insiders': recurring_info['unique_insiders'],
            'recurring_confidence': recurring_info['confidence_score'],
            'recurring_days_span': recurring_info['days_span'],

            # Sector Info
            'sector': sector,
            'sector_state': sector_analysis['state'],
            'sector_score': sector_analysis['score'],
            'sector_details': sector_analysis['details'],
            'sector_distance_min': sector_analysis.get('distance_from_min', 0),
            'sector_rsi': sector_analysis.get('rsi', 50)
        })

    # Ordenar por super_score
    super_opportunities.sort(key=lambda x: x['super_score'], reverse=True)

    print(f"✅ Encontradas {len(super_opportunities)} SUPER OPORTUNIDADES")

    return super_opportunities

def generate_super_opportunities_html(opportunities):
    """Genera reporte HTML de Super Oportunidades"""
    print("\n📊 GENERANDO REPORTE HTML")
    print("=" * 80)

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

    # Contar por clasificación
    epic_count = len([o for o in opportunities if '⭐⭐⭐' in o['classification']])
    excellent_count = len([o for o in opportunities if '⭐⭐' in o['classification'] and '⭐⭐⭐' not in o['classification']])
    good_count = len([o for o in opportunities if '⭐' in o['classification'] and '⭐⭐' not in o['classification']])

    # Generar tabla
    rows_html = ""
    for i, opp in enumerate(opportunities[:100], 1):
        vcp_icon = "🟢" if opp['vcp_ready_to_buy'] else "🟡"

        rows_html += f"""
        <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.05);">
            <td style="padding: 1rem; text-align: center; font-weight: 700; font-size: 1.1rem;">{i}</td>
            <td style="padding: 1rem; font-weight: 700; font-size: 1.2rem; color: var(--glass-accent);">{opp['ticker']}</td>
            <td style="padding: 1rem; text-align: center;">
                <div style="font-size: 1.5rem; font-weight: 900; color: {opp['color']};">{opp['super_score']:.1f}</div>
                <div style="font-size: 0.8rem; color: {opp['color']};">{opp['classification']}</div>
            </td>
            <td style="padding: 1rem;">
                <div>{vcp_icon} VCP {opp['vcp_score']:.0f}% ({opp['vcp_quality']})</div>
                <div style="font-size: 0.85rem; color: var(--text-secondary);">{opp['vcp_contractions']} contracciones</div>
            </td>
            <td style="padding: 1rem;">
                <div>🔁 {opp['recurring_purchases']} compras</div>
                <div style="font-size: 0.85rem; color: var(--text-secondary);">{opp['recurring_insiders']} insiders • {opp['recurring_days_span']} días</div>
            </td>
            <td style="padding: 1rem;">
                <div>{opp['sector_state']}</div>
                <div style="font-size: 0.85rem; color: var(--text-secondary);">{opp['sector']}</div>
                <div style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 0.25rem;">{opp['sector_details'][:50]}...</div>
            </td>
            <td style="padding: 1rem; text-align: right; font-weight: 600;">${opp['price']:.2f}</td>
        </tr>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>⭐ Super Opportunities | Triple Analysis</title>
    <style>
        :root {{
            --glass-primary: rgba(99, 102, 241, 0.8);
            --glass-secondary: rgba(139, 92, 246, 0.7);
            --glass-accent: rgba(59, 130, 246, 0.9);
            --glass-bg: rgba(255, 255, 255, 0.03);
            --glass-border: rgba(255, 255, 255, 0.1);
            --text-primary: rgba(255, 255, 255, 0.95);
            --text-secondary: rgba(255, 255, 255, 0.7);
        }}

        * {{ box-sizing: border-box; margin: 0; padding: 0; }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', Roboto, sans-serif;
            background: #020617;
            color: var(--text-primary);
            line-height: 1.6;
            padding: 2rem;
        }}

        .container {{ max-width: 2000px; margin: 0 auto; }}

        .glass-card {{
            background: var(--glass-bg);
            backdrop-filter: blur(20px) saturate(180%);
            border: 1px solid var(--glass-border);
            border-radius: 24px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }}

        h1 {{
            font-size: 3rem;
            font-weight: 900;
            background: linear-gradient(135deg, #ffd700, #ff8c00, #ff1493);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 1rem;
            text-align: center;
        }}

        .subtitle {{
            text-align: center;
            color: var(--text-secondary);
            font-size: 1.1rem;
            margin-bottom: 0.5rem;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1.5rem;
            margin: 2rem 0;
        }}

        .stat-box {{
            background: var(--glass-bg);
            border: 1px solid var(--glass-border);
            border-radius: 16px;
            padding: 1.5rem;
            text-align: center;
        }}

        .stat-number {{
            font-size: 2.5rem;
            font-weight: 900;
            background: linear-gradient(135deg, var(--glass-accent), var(--glass-primary));
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }}

        .stat-label {{
            color: var(--text-secondary);
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
        }}

        th {{
            padding: 1rem;
            text-align: left;
            border-bottom: 2px solid var(--glass-border);
            color: var(--text-primary);
            font-weight: 700;
            text-transform: uppercase;
            font-size: 0.85rem;
            letter-spacing: 0.5px;
        }}

        .back-link {{
            display: inline-block;
            padding: 0.75rem 1.5rem;
            background: linear-gradient(135deg, var(--glass-primary), var(--glass-accent));
            color: white;
            text-decoration: none;
            border-radius: 12px;
            font-weight: 600;
            margin-bottom: 2rem;
            transition: all 0.3s ease;
        }}

        .back-link:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(99, 102, 241, 0.3);
        }}

        .methodology {{
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(139, 92, 246, 0.1));
            border-left: 4px solid var(--glass-accent);
            padding: 1.5rem;
            border-radius: 12px;
            margin: 2rem 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <a href="https://tantancansado.github.io/stock_analyzer_a" class="back-link">🏠 Volver al Dashboard</a>

        <div class="glass-card">
            <h1>⭐ SUPER OPPORTUNITIES</h1>
            <p class="subtitle">Análisis Triple Dimensional: VCP + Recurring Insiders + Estado Sectorial</p>
            <p style="text-align: center; color: var(--text-secondary); font-size: 0.9rem;">📅 {timestamp}</p>
        </div>

        <div class="stats-grid">
            <div class="stat-box">
                <div class="stat-number">{len(opportunities)}</div>
                <div class="stat-label">Total Oportunidades</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{epic_count}</div>
                <div class="stat-label">⭐⭐⭐ ÉPICAS</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{excellent_count}</div>
                <div class="stat-label">⭐⭐ EXCELENTES</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{good_count}</div>
                <div class="stat-label">⭐ BUENAS</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">3x</div>
                <div class="stat-label">Dimensiones</div>
            </div>
        </div>

        <div class="glass-card methodology">
            <h3 style="color: var(--text-primary); margin-bottom: 1rem;">🧠 Metodología del Super Score</h3>
            <p style="color: var(--text-secondary); margin-bottom: 1rem;">
                El <strong>Super Score</strong> combina tres análisis independientes:
            </p>
            <ul style="color: var(--text-secondary); margin-left: 2rem; line-height: 2;">
                <li><strong>40% - VCP Score:</strong> Patrón técnico de volatilidad (Minervini) - Contracciones sucesivas + Stage 2</li>
                <li><strong>30% - Recurring Insiders:</strong> Compras múltiples de insiders - Señal de confianza interna</li>
                <li><strong>30% - Estado Sectorial:</strong> Posición vs mínimos + RSI - Contexto macro favorable</li>
            </ul>
            <p style="color: var(--text-secondary); margin-top: 1rem;">
                <strong>⭐⭐⭐ ÉPICA (≥80):</strong> Triple confirmación - Técnica + Insiders + Sector óptimo<br>
                <strong>⭐⭐ EXCELENTE (≥70):</strong> Doble confirmación fuerte + contexto favorable<br>
                <strong>⭐ BUENA (≥60):</strong> Señales positivas en las tres dimensiones
            </p>
        </div>

        <div class="glass-card">
            <h2 style="color: var(--text-primary); margin-bottom: 1.5rem;">🏆 Top Super Oportunidades</h2>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th style="text-align: center;">#</th>
                            <th>Ticker</th>
                            <th style="text-align: center;">Super Score</th>
                            <th>VCP Pattern</th>
                            <th>Recurring Insiders</th>
                            <th>Estado Sectorial</th>
                            <th style="text-align: right;">Precio</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="glass-card" style="text-align: center; color: var(--text-secondary);">
            <p style="font-size: 1.1rem; font-weight: 600; margin-bottom: 1rem;">⭐ Super Opportunities Analysis • Triple Dimensional Screening</p>
            <p style="font-size: 0.85rem;">
                VCP Scanner • Recurring Insiders • DJ Sectorial • Market Breadth • Enhanced Opportunities
            </p>
        </div>
    </div>
</body>
</html>"""

    output_path = Path("docs/super_opportunities.html")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"✅ Reporte HTML generado: {output_path}")

    # Guardar CSV
    csv_output = Path("docs/super_opportunities.csv")
    df = pd.DataFrame(opportunities)
    df.to_csv(csv_output, index=False)
    print(f"✅ Datos CSV guardados: {csv_output}")

    return str(output_path)

if __name__ == "__main__":
    print("🚀 SUPER ANALYZER - Análisis Triple Dimensional")
    print("=" * 80)

    # Cargar datos
    vcp_data = load_vcp_data()
    recurring_data = load_recurring_insiders_data()
    dj_data = load_dj_sectorial_data()

    if vcp_data.empty or recurring_data.empty:
        print("❌ Error: Faltan datos necesarios")
        exit(1)

    # Analizar super oportunidades
    opportunities = find_super_opportunities(vcp_data, recurring_data, dj_data)

    if opportunities:
        # Generar reporte
        html_path = generate_super_opportunities_html(opportunities)

        # Mostrar top 10
        print(f"\n🏆 TOP 10 SUPER OPORTUNIDADES:")
        print("-" * 80)
        for i, opp in enumerate(opportunities[:10], 1):
            print(f"{i:2}. {opp['ticker']:6} - Score: {opp['super_score']:5.1f} {opp['classification']}")
            print(f"    VCP: {opp['vcp_score']:.0f}% | Recurring: {opp['recurring_purchases']} compras | "
                  f"Sector: {opp['sector_state']}")

        print(f"\n🎉 ANÁLISIS COMPLETADO")
        print(f"   📊 Reporte: {html_path}")
        print(f"   ⭐⭐⭐ ÉPICAS: {len([o for o in opportunities if '⭐⭐⭐' in o['classification']])}")
        print(f"   ⭐⭐ EXCELENTES: {len([o for o in opportunities if '⭐⭐' in o['classification'] and '⭐⭐⭐' not in o['classification']])}")
    else:
        print("\n⚠️  No se encontraron super oportunidades")
