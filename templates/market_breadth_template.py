#!/usr/bin/env python3
"""
Market Breadth HTML Template Generator
Para usar en templates/market_breadth_template.py
"""

def generate_market_breadth_template(analysis_result):
    """
    Genera template HTML para Market Breadth con diseño Liquid Glass
    
    Args:
        analysis_result: Resultado del análisis de MarketBreadthAnalyzer
        
    Returns:
        str: HTML completo con diseño Liquid Glass
    """
    
    if not analysis_result:
        return generate_empty_breadth_template()
    
    summary = analysis_result['summary']
    signals = analysis_result['signals']
    indicators = analysis_result['indicators']
    breadth_data = analysis_result['breadth_data']
    timestamp = analysis_result['analysis_date']
    
    # Determinar clase CSS del estado del mercado
    market_class = "alcista" if "ALCISTA" in summary['market_bias'] else \
                  "bajista" if "BAJISTA" in summary['market_bias'] else "neutral"
    
    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📈 Market Breadth Analysis | Trading Analytics</title>
    <meta name="description" content="Análisis avanzado de amplitud de mercado con 8 indicadores técnicos clave">
    <link rel="icon" type="image/x-icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📈</text></svg>">
    <style>
        {get_market_breadth_css()}
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
</head>
<body>
    <div class="glass-container">
        <header class="liquid-header glass-card floating-element">
            <h1>📈 Market Breadth Analysis</h1>
            <p>Análisis completo de amplitud de mercado con 8 indicadores técnicos clave</p>
            <div class="market-status {market_class}">
                <div class="pulse-dot"></div>
                <span>{summary['bias_emoji']} {summary['market_bias']} • Confianza {summary['confidence']}</span>
            </div>
        </header>
        
        <section class="stats-liquid">
            <div class="stat-glass fade-in-up" style="animation-delay: 0.1s">
                <div class="stat-number">{summary['bullish_signals']}</div>
                <div class="stat-label">Señales Alcistas</div>
            </div>
            <div class="stat-glass fade-in-up" style="animation-delay: 0.2s">
                <div class="stat-number">{summary['bearish_signals']}</div>
                <div class="stat-label">Señales Bajistas</div>
            </div>
            <div class="stat-glass fade-in-up" style="animation-delay: 0.3s">
                <div class="stat-number">{summary['neutral_signals']}</div>
                <div class="stat-label">Señales Neutrales</div>
            </div>
            <div class="stat-glass fade-in-up" style="animation-delay: 0.4s">
                <div class="stat-number">{summary['strength_score']}</div>
                <div class="stat-label">Puntuación Fuerza</div>
            </div>
        </section>
        
        <main class="content-liquid glass-card">
            <h2 class="section-title">🎯 Indicadores de Amplitud</h2>
            
            <div class="indicators-grid">
                {generate_indicators_html(signals)}
            </div>
        </main>
        
        <section class="charts-section glass-card">
            <h2 class="section-title">📈 Gráficos Interactivos</h2>
            <div class="charts-grid">
                <div class="chart-container">
                    <h3 class="chart-title">Línea Avance-Declive</h3>
                    <canvas id="adLineChart"></canvas>
                </div>
                <div class="chart-container">
                    <h3 class="chart-title">Oscilador McClellan</h3>
                    <canvas id="mcclellanChart"></canvas>
                </div>
                <div class="chart-container">
                    <h3 class="chart-title">Índice TRIN</h3>
                    <canvas id="trinChart"></canvas>
                </div>
                <div class="chart-container">
                    <h3 class="chart-title">% Acciones sobre MA50</h3>
                    <canvas id="ma50Chart"></canvas>
                </div>
            </div>
        </section>
        
        <section class="content-liquid glass-card">
            <h2 class="section-title">💡 Interpretación de Señales</h2>
            <div class="interpretation-grid">
                <div class="explanation-liquid">
                    <h3>🎯 Cómo Interpretar las Señales</h3>
                    <ul>
                        <li><strong>🟢 Señales Alcistas:</strong> Indican fortaleza amplia del mercado y momentum positivo</li>
                        <li><strong>🔴 Señales Bajistas:</strong> Sugieren debilidad subyacente y presión vendedora</li>
                        <li><strong>🟡 Señales Neutrales:</strong> Mercado en equilibrio, esperar confirmación direccional</li>
                        <li><strong>⚡ Confluencia:</strong> 4+ indicadores en la misma dirección = señal fuerte</li>
                    </ul>
                </div>
                
                <div class="explanation-liquid">
                    <h3>⚡ Estrategias de Trading</h3>
                    <ul>
                        <li><strong>Confluencia Alcista:</strong> 4+ indicadores alcistas = Sesgo comprador</li>
                        <li><strong>Divergencias:</strong> Índices subiendo con breadth débil = Precaución</li>
                        <li><strong>Extremos McClellan:</strong> >+100 o <-100 para timing de reversiones</li>
                        <li><strong>TRIN Extremo:</strong> <0.8 o >1.2 para confirmación intraday</li>
                        <li><strong>Gestión Riesgo:</strong> Breadth débil = reducir exposición</li>
                    </ul>
                </div>
            </div>
        </section>
        
        <footer class="footer-liquid">
            <p>📈 Market Breadth Analysis • Powered by Advanced Technical Analysis</p>
            <p>
                <a href="index.html">🏠 Dashboard Principal</a> • 
                <a href="dj_sectorial.html">📊 DJ Sectorial</a> • 
                <a href="insider_trading.html">🏛️ Insider Trading</a> • 
                <a href="vcp_scanner.html">🎯 VCP Scanner</a>
            </p>
        </footer>
    </div>
    
    <script>
        // Datos para gráficos
        const chartData = {{
            dates: {breadth_data['dates']},
            ad_line: {indicators['ad_line']},
            mcclellan: {indicators['mcclellan']},
            trin: {indicators['trin']},
            ma50_percent: {indicators['ma50_percent']}
        }};
        
        // Configuración común de gráficos
        const chartConfig = {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                legend: {{ labels: {{ color: 'white', font: {{ size: 12 }} }} }}
            }},
            scales: {{
                x: {{ 
                    ticks: {{ color: 'white', font: {{ size: 10 }} }}, 
                    grid: {{ color: 'rgba(255,255,255,0.1)' }} 
                }},
                y: {{ 
                    ticks: {{ color: 'white', font: {{ size: 10 }} }}, 
                    grid: {{ color: 'rgba(255,255,255,0.1)' }} 
                }}
            }}
        }};
        
        // Función para inicializar gráficos
        function initCharts() {{
            // A/D Line Chart
            new Chart(document.getElementById('adLineChart'), {{
                type: 'line',
                data: {{
                    labels: chartData.dates,
                    datasets: [{{
                        label: 'Línea A/D',
                        data: chartData.ad_line,
                        borderColor: '#4ade80',
                        backgroundColor: 'rgba(74, 222, 128, 0.1)',
                        tension: 0.4,
                        borderWidth: 2,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }}]
                }},
                options: chartConfig
            }});
            
            // McClellan Oscillator
            new Chart(document.getElementById('mcclellanChart'), {{
                type: 'line',
                data: {{
                    labels: chartData.dates,
                    datasets: [{{
                        label: 'McClellan',
                        data: chartData.mcclellan,
                        borderColor: '#fbbf24',
                        backgroundColor: 'rgba(251, 191, 36, 0.1)',
                        tension: 0.4,
                        borderWidth: 2,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }}]
                }},
                options: chartConfig
            }});
            
            // TRIN Chart
            new Chart(document.getElementById('trinChart'), {{
                type: 'line',
                data: {{
                    labels: chartData.dates,
                    datasets: [{{
                        label: 'TRIN',
                        data: chartData.trin,
                        borderColor: '#f87171',
                        backgroundColor: 'rgba(248, 113, 113, 0.1)',
                        tension: 0.4,
                        borderWidth: 2,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }}]
                }},
                options: chartConfig
            }});
            
            // MA50 Percent Chart
            new Chart(document.getElementById('ma50Chart'), {{
                type: 'line',
                data: {{
                    labels: chartData.dates,
                    datasets: [{{
                        label: '% sobre MA50',
                        data: chartData.ma50_percent,
                        borderColor: '#8b5cf6',
                        backgroundColor: 'rgba(139, 92, 246, 0.1)',
                        tension: 0.4,
                        borderWidth: 2,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }}]
                }},
                options: chartConfig
            }});
        }}
        
        // Inicializar cuando carga la página
        window.addEventListener('load', initCharts);
        
        // Animaciones de entrada escalonadas
        document.addEventListener('DOMContentLoaded', function() {{
            const elements = document.querySelectorAll('.fade-in-up');
            elements.forEach((el, index) => {{
                el.style.animationDelay = `${{index * 0.1}}s`;
            }});
            
            // Animar las cards de indicadores
            const indicatorCards = document.querySelectorAll('.indicator-card');
            indicatorCards.forEach((card, index) => {{
                card.style.animationDelay = `${{index * 0.2}}s`;
                card.classList.add('fade-in-up');
            }});
        }});
        
        // Console logs para debugging
        console.log('📈 Market Breadth Analysis - Liquid Glass Dashboard Loaded');
        console.log('🎯 Market Bias: {summary["market_bias"]}');
        console.log('💪 Strength Score: {summary["strength_score"]}');
        console.log('📊 Indicators: 8 technical indicators active');
        console.log('🚀 Charts: 4 interactive charts initialized');
    </script>
</body>
</html>"""
    
    return html_content

def generate_empty_breadth_template():
    """Template para cuando no hay datos de Market Breadth"""
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📈 Market Breadth Analysis | Sin Datos</title>
    <style>
        {get_market_breadth_css()}
    </style>
</head>
<body>
    <div class="glass-container">
        <header class="liquid-header glass-card">
            <h1>📈 Market Breadth Analysis</h1>
            <p>Sistema de análisis de amplitud de mercado</p>
            <div class="market-status neutral">
                <div class="pulse-dot"></div>
                <span>🟡 Sin datos disponibles</span>
            </div>
        </header>
        
        <main class="content-liquid glass-card">
            <div class="no-data-liquid">
                <h2>🔄 Preparando Análisis</h2>
                <p>El sistema de Market Breadth se está configurando...</p>
                <div class="spinner-liquid"></div>
            </div>
        </main>
    </div>
</body>
</html>"""

def generate_indicators_html(signals):
    """Genera HTML para los indicadores"""
    if not signals:
        return "<p>No hay señales disponibles</p>"
    
    html = ""
    
    indicator_configs = {
        'ad_line': {
            'name': 'Línea Avance-Declive',
            'description': 'Tendencia de participación del mercado'
        },
        'mcclellan': {
            'name': 'Oscilador McClellan',
            'description': 'Momentum de corto plazo'
        },
        'trin': {
            'name': 'Índice TRIN',
            'description': 'Presión compradora vs vendedora'
        },
        'ma50_percent': {
            'name': '% Acciones sobre MA50',
            'description': 'Fortaleza general del mercado'
        },
        'nh_nl_diff': {
            'name': 'Nuevos Máximos - Mínimos',
            'description': 'Confirmación de tendencia'
        },
        'volume_ratio': {
            'name': 'Ratio Volumen',
            'description': 'Demanda vs oferta institucional'
        }
    }
    
    for indicator, config in indicator_configs.items():
        if indicator in signals:
            signal_data = signals[indicator]
            strength_class = get_strength_class(signal_data['signal'], signal_data['strength'])
            
            html += f"""
            <div class="indicator-card">
                <div class="indicator-header">
                    <div class="indicator-name">{config['name']}</div>
                    <div class="indicator-value {strength_class}">{signal_data['value']:.2f}</div>
                </div>
                <div class="indicator-signal {strength_class}">
                    <strong>{signal_data['signal']}</strong>
                </div>
                <div class="indicator-strength">
                    Fuerza: {signal_data['strength']}
                </div>
                <div class="indicator-description">
                    {config['description']}
                </div>
            </div>
            """
    
    return html

def get_strength_class(signal, strength):
    """Determina la clase CSS según la señal y fuerza"""
    signal_lower = signal.lower()
    
    if any(word in signal_lower for word in ['alcista', 'fuerte', 'compradora', 'demanda']):
        return 'signal-strong'
    elif any(word in signal_lower for word in ['bajista', 'débil', 'vendedora', 'debilidad']):
        return 'signal-bearish'
    elif strength.lower() == 'moderada':
        return 'signal-moderate'
    else:
        return 'signal-weak'

def get_market_breadth_css():
    """CSS completo para Market Breadth con diseño Liquid Glass"""
    return """
        /* === LIQUID GLASS CSS PARA MARKET BREADTH === */
        
        :root {
            /* Colores principales - Market Breadth */
            --glass-primary: rgba(99, 102, 241, 0.9);
            --glass-secondary: rgba(139, 92, 246, 0.8);
            --glass-accent: rgba(59, 130, 246, 1);
            --glass-success: rgba(72, 187, 120, 0.9);
            --glass-warning: rgba(251, 191, 36, 0.9);
            --glass-danger: rgba(239, 68, 68, 0.9);
            
            /* Glassmorphism backgrounds */
            --glass-bg: rgba(255, 255, 255, 0.05);
            --glass-bg-hover: rgba(255, 255, 255, 0.12);
            --glass-border: rgba(255, 255, 255, 0.15);
            --glass-shadow: 0 8px 32px rgba(0, 0, 0, 0.37);
            --glass-shadow-hover: 0 16px 64px rgba(99, 102, 241, 0.3);
            
            /* Texto */
            --text-primary: rgba(255, 255, 255, 0.95);
            --text-secondary: rgba(255, 255, 255, 0.75);
            --text-muted: rgba(255, 255, 255, 0.6);
            
            /* Transiciones */
            --transition-smooth: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            --transition-bounce: all 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }
        
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', Roboto, sans-serif;
            background: #020617;
            background-image: 
                radial-gradient(ellipse at top, rgba(16, 23, 42, 0.9) 0%, rgba(2, 6, 23, 0.95) 50%, rgba(0, 0, 0, 0.98) 100%),
                radial-gradient(circle at 20% 80%, rgba(99, 102, 241, 0.08) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(139, 92, 246, 0.08) 0%, transparent 50%);
            background-attachment: fixed;
            color: var(--text-primary);
            line-height: 1.6;
            overflow-x: hidden;
            min-height: 100vh;
        }
        
        /* Floating particles animation */
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: 
                radial-gradient(circle at 25% 25%, rgba(99, 102, 241, 0.05) 0%, transparent 50%),
                radial-gradient(circle at 75% 75%, rgba(139, 92, 246, 0.05) 0%, transparent 50%);
            pointer-events: none;
            z-index: -1;
            animation: float 20s ease-in-out infinite;
        }
        
        @keyframes float {
            0%, 100% { transform: translateY(0px) rotate(0deg); }
            33% { transform: translateY(-15px) rotate(0.5deg); }
            66% { transform: translateY(-8px) rotate(-0.5deg); }
        }
        
        .glass-container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        .glass-card {
            background: var(--glass-bg);
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
            border: 1px solid var(--glass-border);
            border-radius: 24px;
            box-shadow: var(--glass-shadow);
            transition: var(--transition-smooth);
            position: relative;
            overflow: hidden;
        }
        
        .glass-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
            animation: shimmer 3s ease-in-out infinite;
        }
        
        @keyframes shimmer {
            0%, 100% { opacity: 0; }
            50% { opacity: 1; }
        }
        
        .glass-card:hover {
            background: var(--glass-bg-hover);
            transform: translateY(-4px);
            box-shadow: var(--glass-shadow-hover);
        }
        
        /* === HEADER === */
        .liquid-header {
            text-align: center;
            padding: 4rem 2rem;
            margin-bottom: 3rem;
        }
        
        .liquid-header h1 {
            font-size: clamp(2.5rem, 5vw, 4rem);
            font-weight: 800;
            background: linear-gradient(135deg, var(--glass-primary), var(--glass-secondary), var(--glass-accent));
            background-size: 200% 200%;
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 1rem;
            animation: gradient-shift 4s ease-in-out infinite;
            text-shadow: 0 0 40px rgba(99, 102, 241, 0.3);
        }
        
        @keyframes gradient-shift {
            0%, 100% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
        }
        
        .liquid-header p {
            font-size: 1.25rem;
            color: var(--text-secondary);
            margin-bottom: 2rem;
            font-weight: 300;
        }
        
        .market-status {
            display: inline-flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.75rem 1.5rem;
            border-radius: 50px;
            font-weight: 600;
            backdrop-filter: blur(10px);
            border: 1px solid;
            transition: var(--transition-smooth);
        }
        
        .market-status.alcista {
            background: rgba(72, 187, 120, 0.1);
            border-color: rgba(72, 187, 120, 0.3);
            color: var(--glass-success);
        }
        
        .market-status.bajista {
            background: rgba(239, 68, 68, 0.1);
            border-color: rgba(239, 68, 68, 0.3);
            color: var(--glass-danger);
        }
        
        .market-status.neutral {
            background: rgba(251, 191, 36, 0.1);
            border-color: rgba(251, 191, 36, 0.3);
            color: var(--glass-warning);
        }
        
        .pulse-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            animation: pulse-glow 2s ease-in-out infinite;
        }
        
        .alcista .pulse-dot { 
            background: #48bb78; 
            box-shadow: 0 0 10px rgba(72, 187, 120, 0.8); 
        }
        .bajista .pulse-dot { 
            background: #ef4444; 
            box-shadow: 0 0 10px rgba(239, 68, 68, 0.8); 
        }
        .neutral .pulse-dot { 
            background: #fbbf24; 
            box-shadow: 0 0 10px rgba(251, 191, 36, 0.8); 
        }
        
        @keyframes pulse-glow {
            0%, 100% { 
                opacity: 1; 
                transform: scale(1);
            }
            50% { 
                opacity: 0.3; 
                transform: scale(1.2);
            }
        }
        
        /* === STATS GRID === */
        .stats-liquid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 2rem;
            margin-bottom: 3rem;
        }
        
        .stat-glass {
            background: var(--glass-bg);
            backdrop-filter: blur(16px);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            padding: 2rem;
            text-align: center;
            transition: var(--transition-bounce);
            position: relative;
            overflow: hidden;
        }
        
        .stat-glass::after {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: linear-gradient(45deg, transparent, rgba(255, 255, 255, 0.03), transparent);
            transform: rotate(45deg);
            transition: var(--transition-smooth);
            opacity: 0;
        }
        
        .stat-glass:hover {
            transform: translateY(-12px) scale(1.05);
            border-color: var(--glass-primary);
            box-shadow: 0 20px 60px rgba(99, 102, 241, 0.3);
        }
        
        .stat-glass:hover::after {
            opacity: 1;
            animation: slide-shine 0.8s ease-out;
        }
        
        @keyframes slide-shine {
            from { transform: translateX(-100%) rotate(45deg); }
            to { transform: translateX(100%) rotate(45deg); }
        }
        
        .stat-number {
            font-size: 3rem;
            font-weight: 900;
            background: linear-gradient(135deg, var(--glass-accent), var(--glass-primary));
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
            display: block;
        }
        
        .stat-label {
            color: var(--text-secondary);
            font-size: 0.95rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 500;
        }
        
        /* === CONTENT SECTIONS === */
        .content-liquid {
            padding: 2.5rem;
            margin-bottom: 2rem;
        }
        
        .section-title {
            font-size: 2rem;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 2rem;
            text-align: center;
            position: relative;
        }
        
        .section-title::after {
            content: '';
            position: absolute;
            bottom: -10px;
            left: 50%;
            transform: translateX(-50%);
            width: 60px;
            height: 3px;
            background: linear-gradient(90deg, var(--glass-primary), var(--glass-secondary));
            border-radius: 2px;
        }
        
        /* === INDICATORS GRID === */
        .indicators-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 1.5rem;
            margin-bottom: 3rem;
        }
        
        .indicator-card {
            background: var(--glass-bg);
            backdrop-filter: blur(16px);
            border: 1px solid var(--glass-border);
            border-radius: 16px;
            padding: 1.5rem;
            transition: var(--transition-smooth);
            position: relative;
            overflow: hidden;
        }
        
        .indicator-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.05), rgba(139, 92, 246, 0.05));
            opacity: 0;
            transition: var(--transition-smooth);
        }
        
        .indicator-card:hover {
            transform: translateY(-4px) scale(1.02);
            background: var(--glass-bg-hover);
            border-color: var(--glass-accent);
            box-shadow: 0 16px 48px rgba(59, 130, 246, 0.25);
        }
        
        .indicator-card:hover::before {
            opacity: 1;
        }
        
        .indicator-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }
        
        .indicator-name {
            font-weight: 700;
            color: var(--text-primary);
            font-size: 1.1rem;
        }
        
        .indicator-value {
            font-weight: 600;
            font-size: 1.2rem;
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.1);
        }
        
        .indicator-signal {
            margin-bottom: 0.5rem;
            font-weight: 600;
            font-size: 1rem;
        }
        
        .indicator-strength {
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin-bottom: 1rem;
        }
        
        .indicator-description {
            color: var(--text-muted);
            font-size: 0.85rem;
            line-height: 1.4;
        }
        
        /* Signal colors */
        .signal-strong { color: var(--glass-success); }
        .signal-moderate { color: var(--glass-warning); }
        .signal-weak { color: var(--text-secondary); }
        .signal-bearish { color: var(--glass-danger); }
        
        /* === CHARTS SECTION === */
        .charts-section {
            padding: 2.5rem;
            margin-bottom: 2rem;
        }
        
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
            gap: 2rem;
        }
        
        .chart-container {
            background: rgba(255, 255, 255, 0.02);
            border-radius: 16px;
            padding: 1.5rem;
            border: 1px solid var(--glass-border);
            transition: var(--transition-smooth);
        }
        
        .chart-container:hover {
            background: rgba(255, 255, 255, 0.05);
            border-color: var(--glass-primary);
        }
        
        .chart-title {
            color: var(--glass-primary);
            font-weight: 600;
            margin-bottom: 1rem;
            text-align: center;
            font-size: 1.1rem;
        }
        
        canvas {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            height: 280px !important;
            width: 100% !important;
        }
        
        /* === INTERPRETATION SECTION === */
        .interpretation-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 2rem;
        }
        
        .explanation-liquid {
            background: rgba(99, 102, 241, 0.05);
            backdrop-filter: blur(8px);
            border: 1px solid rgba(99, 102, 241, 0.2);
            border-radius: 16px;
            padding: 1.5rem;
        }
        
        .explanation-liquid h3 {
            color: var(--glass-primary);
            margin-bottom: 1rem;
            font-size: 1.2rem;
        }
        
        .explanation-liquid ul {
            list-style: none;
            padding-left: 0;
        }
        
        .explanation-liquid li {
            margin-bottom: 0.75rem;
            padding-left: 1.5rem;
            position: relative;
            color: var(--text-secondary);
            line-height: 1.5;
        }
        
        .explanation-liquid li::before {
            content: '→';
            position: absolute;
            left: 0;
            color: var(--glass-accent);
            font-weight: bold;
        }
        
        /* === NO DATA STATE === */
        .no-data-liquid {
            text-align: center;
            padding: 4rem 2rem;
            color: var(--text-muted);
        }
        
        .no-data-liquid h2 {
            color: var(--text-secondary);
            margin-bottom: 1rem;
            font-size: 1.5rem;
        }
        
        .spinner-liquid {
            width: 40px;
            height: 40px;
            border: 3px solid rgba(255, 255, 255, 0.1);
            border-top: 3px solid var(--glass-primary);
            border-radius: 50%;
            animation: spin-liquid 1s linear infinite;
            margin: 20px auto;
        }
        
        @keyframes spin-liquid {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        /* === FLOATING ANIMATIONS === */
        .floating-element {
            animation: float-gentle 6s ease-in-out infinite;
        }
        
        @keyframes float-gentle {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-10px); }
        }
        
        .fade-in-up {
            opacity: 0;
            transform: translateY(30px);
            animation: fadeInUp 0.8s ease-out forwards;
        }
        
        @keyframes fadeInUp {
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        /* === FOOTER === */
        .footer-liquid {
            text-align: center;
            margin-top: 4rem;
            padding: 2rem 0;
            border-top: 1px solid var(--glass-border);
            color: var(--text-muted);
        }
        
        .footer-liquid a {
            color: var(--glass-accent);
            text-decoration: none;
            transition: var(--transition-smooth);
        }
        
        .footer-liquid a:hover {
            color: var(--glass-primary);
            text-shadow: 0 0 10px rgba(99, 102, 241, 0.5);
        }
        
        /* === RESPONSIVE DESIGN === */
        @media (max-width: 768px) {
            .glass-container {
                padding: 1rem;
            }
            
            .liquid-header {
                padding: 2rem 1rem;
            }
            
            .liquid-header h1 {
                font-size: 2.5rem;
            }
            
            .stats-liquid {
                grid-template-columns: repeat(2, 1fr);
                gap: 1rem;
            }
            
            .stat-glass {
                padding: 1.5rem;
            }
            
            .charts-grid {
                grid-template-columns: 1fr;
            }
            
            .indicators-grid {
                grid-template-columns: 1fr;
            }
            
            .interpretation-grid {
                grid-template-columns: 1fr;
            }
            
            .content-liquid {
                padding: 1.5rem;
            }
        }
        
        /* === ACCESSIBILITY === */
        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
            }
        }
    """

# Función principal para generar el HTML desde el sistema
def generate_market_breadth_html(analysis_result):
    """
    Función principal que llama el sistema para generar HTML
    
    Args:
        analysis_result: Resultado del MarketBreadthAnalyzer
        
    Returns:
        str: HTML completo
    """
    return generate_market_breadth_template(analysis_result)

# Para compatibilidad con el sistema existente
def crear_html_market_breadth(analysis_result, output_path="reports/market_breadth_report.html"):
    """
    Crea archivo HTML de Market Breadth en el path especificado
    
    Args:
        analysis_result: Resultado del análisis
        output_path: Ruta donde guardar el HTML
        
    Returns:
        str: Path del archivo generado
    """
    html_content = generate_market_breadth_template(analysis_result)
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"✅ HTML Market Breadth generado: {output_path}")
        return output_path
    except Exception as e:
        print(f"❌ Error generando HTML Market Breadth: {e}")
        return None

if __name__ == "__main__":
    # Test del template
    print("🧪 Testing Market Breadth Template")
    
    # Crear datos de ejemplo para test
    example_data = {
        'summary': {
            'market_bias': '🟢 ALCISTA',
            'bias_emoji': '🚀',
            'confidence': 'Alta',
            'bullish_signals': 6,
            'bearish_signals': 1,
            'neutral_signals': 1,
            'strength_score': 8
        },
        'signals': {
            'ad_line': {'value': 2847, 'signal': 'Tendencia Alcista', 'strength': 'Alta'},
            'mcclellan': {'value': 67.4, 'signal': 'Momentum Positivo', 'strength': 'Moderada'},
            'trin': {'value': 0.73, 'signal': 'Presión Compradora', 'strength': 'Alta'},
            'ma50_percent': {'value': 74.2, 'signal': 'Mercado Fuerte', 'strength': 'Alta'}
        },
        'indicators': {
            'ad_line': [100, 250, 500, 800, 1200, 1500, 2000, 2500, 2847],
            'mcclellan': [-20, 10, 35, 45, 55, 60, 65, 67, 67.4],
            'trin': [1.2, 0.95, 0.88, 0.76, 0.82, 0.79, 0.75, 0.73, 0.73],
            'ma50_percent': [45, 52, 58, 62, 67, 69, 71, 73, 74.2]
        },
        'breadth_data': {
            'dates': ['2025-06-22', '2025-06-23', '2025-06-24', '2025-06-25', '2025-06-26', '2025-06-27', '2025-06-28', '2025-06-29', '2025-06-30']
        },
        'analysis_date': '2025-06-30'
    }
    
    # Generar HTML de test
    test_html = generate_market_breadth_template(example_data)
    
    # Guardar archivo de test
    with open("test_market_breadth_template.html", "w", encoding="utf-8") as f:
        f.write(test_html)
    
    print("✅ Template de test generado: test_market_breadth_template.html")