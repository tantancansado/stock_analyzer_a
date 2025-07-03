#!/usr/bin/env python3
"""
Market Breadth HTML Generator - ACTUALIZADO para NYSE
Generador HTML actualizado para mostrar datos NYSE reales del NYSEDataExtractor
Mantiene funcionalidad original + nueva sección NYSE
"""

import json
from datetime import datetime


class MarketBreadthHTMLGenerator:
    """Generador HTML actualizado para análisis completo con NYSE"""
    
    def __init__(self, base_url="https://tantancansado.github.io/stock_analyzer_a"):
        self.base_url = base_url
        self.finviz_chart_base = "https://finviz.com/chart.ashx?t={ticker}&ty=c&ta=1&p=d&s=l"
    
    def generate_finviz_chart_url(self, symbol):
        """Genera URL del gráfico de Finviz para un ticker específico"""
        return self.finviz_chart_base.format(ticker=symbol)
    
    def generate_breadth_html(self, analysis_result):
        """Genera HTML para análisis completo - ACTUALIZADO para NYSE"""
        if not analysis_result or 'indices_data' not in analysis_result:
            return None
        
        indices_data = analysis_result['indices_data']
        summary = analysis_result['summary']
        timestamp = analysis_result['analysis_date']
        
        # NUEVA FUNCIONALIDAD: Detectar datos NYSE
        nyse_data = analysis_result.get('nyse_data', {})
        has_nyse_data = len(nyse_data) > 0
        
        # Título dinámico según datos disponibles
        title_suffix = "COMPLETO - Índices + NYSE" if has_nyse_data else "por Índices"
        
        html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📊 Market Breadth {title_suffix} | Dashboard</title>
    <meta name="description" content="Análisis de {len(indices_data)} índices{'+ ' + str(len(nyse_data)) + ' indicadores NYSE' if has_nyse_data else ''} con métricas técnicas y gráficos Finviz">
    <style>
        {self._get_complete_css()}
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
</head>
<body>
    <div class="glass-container">
        <header class="liquid-header glass-card floating-element">
            <h1>📊 Market Breadth Analysis {'COMPLETO' if has_nyse_data else 'por Índices'}</h1>
            <p>Análisis de {len(indices_data)} índices{' + ' + str(len(nyse_data)) + ' indicadores NYSE reales' if has_nyse_data else ''}</p>
            <div class="market-status">
                <div class="pulse-dot"></div>
                <span>{summary['market_bias']} • {summary['bullish_percentage']:.1f}% Alcistas</span>
                <div class="score-badge">Score: {summary['strength_score']}</div>
            </div>
        </header>
        
        <section class="stats-liquid">
            <div class="stat-glass fade-in-up" style="animation-delay: 0.1s">
                <div class="stat-number">{summary.get('combined_bullish_signals', summary['bullish_signals'])}</div>
                <div class="stat-label">Señales Alcistas</div>
                <div class="stat-percent">Combinadas</div>
            </div>
            <div class="stat-glass fade-in-up" style="animation-delay: 0.2s">
                <div class="stat-number">{len(indices_data)}</div>
                <div class="stat-label">Índices</div>
                <div class="stat-percent">Analizados</div>
            </div>
            {'<div class="stat-glass fade-in-up" style="animation-delay: 0.25s"><div class="stat-number">' + str(len(nyse_data)) + '</div><div class="stat-label">Indicadores NYSE</div><div class="stat-percent">Reales</div></div>' if has_nyse_data else ''}
            <div class="stat-glass fade-in-up" style="animation-delay: 0.3s">
                <div class="stat-number">{summary['avg_rsi']:.0f}</div>
                <div class="stat-label">RSI Promedio</div>
                <div class="stat-percent">Índices</div>
            </div>
            <div class="stat-glass fade-in-up" style="animation-delay: 0.4s">
                <div class="stat-number">{summary['avg_ma200_distance']:+.1f}%</div>
                <div class="stat-label">Distancia MA200</div>
                <div class="stat-percent">Promedio</div>
            </div>
        </section>
        
        {self._generate_nyse_section_if_available(nyse_data, summary)}
        
        <main class="indices-analysis glass-card">
            <h2 class="section-title">📊 Análisis Detallado por Índice con Gráficos</h2>
            <div class="indices-grid">
                {self._generate_detailed_indices_with_charts_html(indices_data)}
            </div>
        </main>
        
        <section class="performers-section glass-card">
            <h2 class="section-title">🏆 Mejores y Peores Performers</h2>
            <div class="performers-grid">
                {self._generate_performers_html(summary, indices_data)}
            </div>
        </section>
        
        <section class="charts-section glass-card">
            <h2 class="section-title">📈 Análisis Visual Comparativo</h2>
            <div class="charts-grid">
                <div class="chart-container">
                    <h3 class="chart-title">Rendimiento 20 Días</h3>
                    <canvas id="performanceChart"></canvas>
                </div>
                <div class="chart-container">
                    <h3 class="chart-title">RSI de Índices</h3>
                    <canvas id="rsiChart"></canvas>
                </div>
                <div class="chart-container">
                    <h3 class="chart-title">Distancia de MA200</h3>
                    <canvas id="ma200Chart"></canvas>
                </div>
                {'<div class="chart-container"><h3 class="chart-title">Indicadores NYSE</h3><canvas id="nyseChart"></canvas></div>' if has_nyse_data else '<div class="chart-container"><h3 class="chart-title">Volatilidad 20D</h3><canvas id="volatilityChart"></canvas></div>'}
            </div>
        </section>
        
        <footer class="footer-liquid">
            <p>📊 Market Breadth Analysis {'COMPLETO' if has_nyse_data else 'por Índices'} • Métricas Técnicas Reales • Gráficos Finviz</p>
            <p>
                <a href="{self.base_url}">🏠 Dashboard Principal</a> • 
                <a href="dj_sectorial.html">📊 DJ Sectorial</a> • 
                <a href="insider_trading.html">🏛️ Insider Trading</a>
            </p>
        </footer>
    </div>
    
    <script>
        // Datos para gráficos
        const chartData = {json.dumps(self._prepare_chart_data(indices_data, nyse_data))};
        
        // Inicializar gráficos
        {self._generate_charts_js(has_nyse_data)}
        
        // Funcionalidad de modal para gráficos Finviz
        {self._generate_chart_modal_js()}
        
        console.log('📊 Market Breadth {'COMPLETO' if has_nyse_data else 'por Índices'} Loaded');
        console.log('📊 Índices analizados: {len(indices_data)}');
        {'console.log("🏛️ Indicadores NYSE: ' + str(len(nyse_data)) + '");' if has_nyse_data else ''}
        console.log('📈 Alcistas: {summary["bullish_percentage"]:.1f}%');
        console.log('💪 Strength Score: {summary["strength_score"]}');
    </script>
</body>
</html>"""
        
        return html_content
    
    def _generate_nyse_section_if_available(self, nyse_data, summary):
        """NUEVA FUNCIÓN: Genera sección NYSE solo si hay datos disponibles"""
        if not nyse_data:
            return ""
        
        return f"""
        <!-- SECCIÓN NYSE DATOS REALES -->
        <section class="nyse-breadth-section glass-card">
            <h2 class="section-title">🏛️ Indicadores NYSE (Datos Reales)</h2>
            
            <div class="nyse-summary-card">
                <div class="nyse-summary-header">
                    <span class="nyse-status">📊 {len(nyse_data)} Indicadores Obtenidos</span>
                    <span class="nyse-confidence">Datos en tiempo real de stockcharts.com</span>
                </div>
                <div class="nyse-signals">
                    <span class="signal-count bullish">🟢 {summary['nyse_signals']['bullish']}</span>
                    <span class="signal-count bearish">🔴 {summary['nyse_signals']['bearish']}</span>
                    <span class="signal-count neutral">🟡 {summary['nyse_signals']['neutral']}</span>
                </div>
            </div>
            
            <div class="nyse-indicators-grid">
                {self._generate_nyse_indicators_by_category(nyse_data)}
            </div>
        </section>
        """
    
    def _generate_nyse_indicators_by_category(self, nyse_data):
        """NUEVA FUNCIÓN: Organiza indicadores NYSE por categorías"""
        # Categorías de indicadores NYSE
        categories = {
            'McClellan': {
                'indicators': ['NYMO', 'NYMOT', 'NYSI', 'NAMO', 'NASI'],
                'icon': '🌊',
                'description': 'Osciladores de Amplitud'
            },
            'Advance-Decline': {
                'indicators': ['SPXADP', 'MIDADP', 'SMLADP', 'NAADP', 'NYADL', 'NAADL'],
                'icon': '📈',
                'description': 'Líneas de Avance-Declive'
            },
            'Arms Index': {
                'indicators': ['TRIN', 'TRINQ'],
                'icon': '⚖️',
                'description': 'Índices de Arms (TRIN)'
            },
            '% sobre Medias': {
                'indicators': ['NYA50R', 'NYA200R', 'SPXA50R', 'SPXA200R', 'NAA50R', 'NAA200R'],
                'icon': '📏',
                'description': 'Porcentajes sobre MAs'
            },
            'Bullish Percent': {
                'indicators': ['BPSPX', 'BPNDX', 'BPNYA', 'BPCOMPQ'],
                'icon': '📊',
                'description': 'Índices Bullish Percent'
            },
            'Sentimiento': {
                'indicators': ['VIX', 'VXN', 'RVX', 'CPC', 'CPCE', 'CPCN'],
                'icon': '😱',
                'description': 'Volatilidad y Put/Call'
            },
            'Nuevos Máx/Mín': {
                'indicators': ['NYHGH', 'NYLOW', 'NAHGH', 'NALOW', 'NYHL', 'NAHL'],
                'icon': '🎯',
                'description': 'Nuevos Máximos/Mínimos'
            },
            'Otros': {
                'indicators': ['TICK', 'TICKQ', 'NYTO', 'NATO', 'TNX', 'TYX', 'DXY', 'GOLD', 'WTIC'],
                'icon': '📋',
                'description': 'Otros Indicadores'
            }
        }
        
        html = ""
        
        for category, config in categories.items():
            # Filtrar indicadores disponibles en esta categoría
            available_indicators = [ind for ind in config['indicators'] if ind in nyse_data]
            
            if not available_indicators:
                continue
            
            html += f"""
            <div class="nyse-category-card">
                <div class="category-header">
                    <h3>{config['icon']} {category}</h3>
                    <span class="category-description">{config['description']}</span>
                    <span class="category-count">{len(available_indicators)} indicadores</span>
                </div>
                <div class="category-indicators">
            """
            
            for indicator in available_indicators:
                data = nyse_data[indicator]
                value = data['current_price']
                change_pct = data['change_pct'] or 0
                symbol = data['symbol']
                
                # Determinar clase CSS según el indicador
                signal_class = self._get_nyse_indicator_signal_class(indicator, value)
                
                html += f"""
                <div class="nyse-indicator-item {signal_class}">
                    <div class="indicator-header">
                        <span class="indicator-name">{indicator}</span>
                        <span class="indicator-symbol">{symbol}</span>
                    </div>
                    <div class="indicator-value">
                        <span class="value">{value:.2f}</span>
                        <span class="change {'positive' if change_pct > 0 else 'negative'}">{change_pct:+.2f}%</span>
                    </div>
                    <div class="indicator-signal">{self._get_nyse_indicator_interpretation(indicator, value)}</div>
                </div>
                """
            
            html += """
                </div>
            </div>
            """
        
        return html
    
    def _get_nyse_indicator_signal_class(self, indicator, value):
        """Determina clase CSS según señal del indicador NYSE"""
        if indicator in ['VIX', 'VXN', 'RVX']:
            return "bearish" if value > 25 else "neutral"
        elif indicator in ['TRIN', 'TRINQ']:
            return "bullish" if value > 1.2 else "bearish" if value < 0.8 else "neutral"
        elif indicator in ['NYMO', 'NYMOT', 'NAMO']:
            return "bullish" if value > 50 else "bearish" if value < -50 else "neutral"
        elif indicator in ['SPXADP', 'MIDADP', 'SMLADP', 'NAADP']:
            return "bullish" if value > 0 else "bearish"
        elif indicator in ['NYA50R', 'NYA200R', 'SPXA50R', 'SPXA200R', 'NAA50R', 'NAA200R']:
            return "bullish" if value > 50 else "bearish"
        elif indicator in ['BPSPX', 'BPNDX', 'BPNYA', 'BPCOMPQ']:
            return "bullish" if value > 50 else "bearish"
        elif indicator in ['CPC', 'CPCE', 'CPCN']:
            return "bullish" if value > 1.2 else "bearish" if value < 0.8 else "neutral"
        else:
            return "neutral"
    
    def _get_nyse_indicator_interpretation(self, indicator, value):
        """Interpreta señal del indicador NYSE"""
        if indicator in ['VIX', 'VXN', 'RVX']:
            if value > 30: return "🔴 Alta Volatilidad"
            elif value < 15: return "🟡 Complacencia"
            else: return "🟢 Normal"
        elif indicator in ['TRIN', 'TRINQ']:
            if value > 1.5: return "🟢 Muy Sobrevendido"
            elif value > 1.2: return "🟢 Sobrevendido"
            elif value < 0.8: return "🔴 Sobrecomprado"
            else: return "🟡 Neutral"
        elif indicator in ['NYMO', 'NYMOT', 'NAMO']:
            if value > 100: return "🔴 Muy Sobrecomprado"
            elif value > 50: return "🟡 Sobrecomprado"
            elif value < -100: return "🟢 Muy Sobrevendido"
            elif value < -50: return "🟡 Sobrevendido"
            else: return "🟡 Neutral"
        elif indicator in ['SPXADP', 'MIDADP', 'SMLADP', 'NAADP']:
            if value > 0: return "🟢 Más Subidas"
            else: return "🔴 Más Bajadas"
        elif indicator in ['NYA50R', 'NYA200R', 'SPXA50R', 'SPXA200R']:
            if value > 70: return "🟢 Amplitud Fuerte"
            elif value > 50: return "🟢 Amplitud Positiva"
            elif value < 30: return "🔴 Amplitud Débil"
            else: return "🟡 Amplitud Mixta"
        elif indicator in ['BPSPX', 'BPNDX', 'BPNYA']:
            if value > 70: return "🔴 Muy Alcista"
            elif value > 50: return "🟢 Alcista"
            elif value < 30: return "🟢 Bajista"
            else: return "🟡 Neutral"
        else:
            return "📊 " + str(value)
    
    def _generate_detailed_indices_with_charts_html(self, indices_data):
        """Genera HTML detallado para cada índice CON GRÁFICOS de Finviz (ORIGINAL)"""
        html = ""
        for symbol, data in indices_data.items():
            
            # Determinar clases CSS según señales
            overall_class = "bullish" if "🟢" in data['overall_signal'] else "bearish" if "🔴" in data['overall_signal'] else "neutral"
            
            # URL del gráfico de Finviz
            chart_url = self.generate_finviz_chart_url(symbol)
            
            html += f"""
            <div class="index-detailed-card-with-chart {overall_class}">
                <div class="index-header">
                    <div class="index-info">
                        <span class="index-symbol">{symbol}</span>
                        <span class="index-name">{data['name']}</span>
                    </div>
                    <div class="index-price">
                        <span class="price">${data['current_price']}</span>
                        <span class="change-20d {('positive' if data['price_change_20d'] > 0 else 'negative')}">{data['price_change_20d']:+.1f}%</span>
                    </div>
                </div>
                
                <div class="chart-section">
                    <div class="chart-wrapper">
                        <img src="{chart_url}" 
                             alt="Gráfico {symbol}" 
                             class="finviz-chart"
                             loading="lazy"
                             onclick="openChartModal('{symbol}', '{chart_url}')"
                             onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                        <div class="chart-fallback" style="display: none;">
                            <div class="fallback-content">
                                <span class="fallback-icon">📊</span>
                                <span class="fallback-text">Gráfico no disponible</span>
                                <a href="{chart_url}" target="_blank" class="fallback-link">Ver en Finviz →</a>
                            </div>
                        </div>
                        <div class="chart-overlay">
                            <span class="chart-expand">🔍 Click para ampliar</span>
                        </div>
                    </div>
                </div>
                
                <div class="signals-section">
                    <div class="signal-row">
                        <span class="signal-label">Tendencia:</span>
                        <span class="signal-value">{data['trend_signal']}</span>
                    </div>
                    <div class="signal-row">
                        <span class="signal-label">Momentum:</span>
                        <span class="signal-value">{data['momentum_signal']}</span>
                    </div>
                    <div class="signal-row">
                        <span class="signal-label">Posición:</span>
                        <span class="signal-value">{data['position_signal']}</span>
                    </div>
                    <div class="signal-row overall">
                        <span class="signal-label">General:</span>
                        <span class="signal-value overall">{data['overall_signal']}</span>
                    </div>
                </div>
                
                <div class="metrics-grid">
                    <div class="metric-item">
                        <span class="metric-label">RSI 14:</span>
                        <span class="metric-value">{data['rsi_14']:.1f}</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">MA200:</span>
                        <span class="metric-value {('positive' if data['percent_above_ma200'] > 0 else 'negative')}">{data['percent_above_ma200']:+.1f}%</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">52W High:</span>
                        <span class="metric-value">{data['distance_from_52w_high']:+.1f}%</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">Volatilidad:</span>
                        <span class="metric-value">{data['volatility_20d']:.1f}%</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">Volumen:</span>
                        <span class="metric-value">{data['volume_ratio_20d']:.1f}x</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">Bollinger:</span>
                        <span class="metric-value">{data['bollinger_position']:.0f}%</span>
                    </div>
                </div>
            </div>
            """
        
        return html
    
    def _generate_performers_html(self, summary, indices_data):
        """Genera HTML para mejores y peores performers (ORIGINAL)"""
        
        # Ordenar por performance 20d
        sorted_indices = sorted(indices_data.items(), key=lambda x: x[1]['price_change_20d'], reverse=True)
        
        best_performers = sorted_indices[:3]
        worst_performers = sorted_indices[-3:]
        
        html = f"""
        <div class="performers-column">
            <h3 class="performers-title">🚀 Mejores Performers (20d)</h3>
            <div class="performers-list">
        """
        
        for symbol, data in best_performers:
            html += f"""
                <div class="performer-item best">
                    <span class="performer-symbol">{symbol}</span>
                    <span class="performer-change">{data['price_change_20d']:+.1f}%</span>
                </div>
            """
        
        html += """
            </div>
        </div>
        
        <div class="performers-column">
            <h3 class="performers-title">📉 Peores Performers (20d)</h3>
            <div class="performers-list">
        """
        
        for symbol, data in worst_performers:
            html += f"""
                <div class="performer-item worst">
                    <span class="performer-symbol">{symbol}</span>
                    <span class="performer-change">{data['price_change_20d']:+.1f}%</span>
                </div>
            """
        
        html += """
            </div>
        </div>
        """
        
        return html
    
    def _prepare_chart_data(self, indices_data, nyse_data):
        """Prepara datos para gráficos - ACTUALIZADO para NYSE"""
        symbols = list(indices_data.keys())
        
        chart_data = {
            'symbols': symbols,
            'performance_20d': [indices_data[s]['price_change_20d'] for s in symbols],
            'rsi_values': [indices_data[s]['rsi_14'] for s in symbols],
            'ma200_distance': [indices_data[s]['percent_above_ma200'] for s in symbols],
            'volatility': [indices_data[s]['volatility_20d'] for s in symbols],
            'prices': [indices_data[s]['current_price'] for s in symbols]
        }
        
        # NUEVO: Añadir datos NYSE para gráfico
        if nyse_data:
            nyse_indicators = []
            nyse_values = []
            
            # Seleccionar indicadores clave para el gráfico
            key_nyse = ['NYMO', 'VIX', 'TRIN', 'SPXA200R', 'SPXADP']
            for indicator in key_nyse:
                if indicator in nyse_data and nyse_data[indicator]['current_price'] is not None:
                    nyse_indicators.append(indicator)
                    value = nyse_data[indicator]['current_price']
                    
                    # Normalizar valores para gráfico
                    if indicator == 'VIX':
                        normalized = min(100, value * 3)  # VIX * 3 para escala
                    elif indicator == 'TRIN':
                        normalized = min(100, value * 50)  # TRIN * 50 para escala
                    elif indicator in ['SPXA200R', 'SPXADP']:
                        normalized = max(0, value)  # Ya está en escala 0-100
                    else:  # NYMO
                        normalized = 50 + value  # Centrar en 50
                    
                    nyse_values.append(normalized)
            
            chart_data['nyse_indicators'] = nyse_indicators
            chart_data['nyse_values'] = nyse_values
        
        return chart_data
    
    def _generate_charts_js(self, has_nyse_data):
        """Genera JavaScript para gráficos - ACTUALIZADO para NYSE"""
        base_config = """
        const chartConfig = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { labels: { color: 'white' } } },
            scales: {
                x: { ticks: { color: 'white' }, grid: { color: 'rgba(255,255,255,0.1)' } },
                y: { ticks: { color: 'white' }, grid: { color: 'rgba(255,255,255,0.1)' } }
            }
        };
        """
        
        if has_nyse_data:
            return base_config + """
        window.addEventListener('load', function() {
            // Performance Chart
            new Chart(document.getElementById('performanceChart'), {
                type: 'bar',
                data: {
                    labels: chartData.symbols,
                    datasets: [{
                        label: 'Rendimiento 20d (%)',
                        data: chartData.performance_20d,
                        backgroundColor: chartData.performance_20d.map(val => 
                            val > 0 ? 'rgba(34, 197, 94, 0.8)' : 'rgba(239, 68, 68, 0.8)'
                        )
                    }]
                },
                options: chartConfig
            });
            
            // RSI Chart
            new Chart(document.getElementById('rsiChart'), {
                type: 'bar',
                data: {
                    labels: chartData.symbols,
                    datasets: [{
                        label: 'RSI 14',
                        data: chartData.rsi_values,
                        backgroundColor: chartData.rsi_values.map(val => 
                            val > 70 ? 'rgba(239, 68, 68, 0.8)' : 
                            val < 30 ? 'rgba(34, 197, 94, 0.8)' : 
                            'rgba(99, 102, 241, 0.8)'
                        )
                    }]
                },
                options: chartConfig
            });
            
            // MA200 Chart
            new Chart(document.getElementById('ma200Chart'), {
                type: 'bar',
                data: {
                    labels: chartData.symbols,
                    datasets: [{
                        label: 'Distancia MA200 (%)',
                        data: chartData.ma200_distance,
                        backgroundColor: chartData.ma200_distance.map(val => 
                            val > 0 ? 'rgba(34, 197, 94, 0.8)' : 'rgba(239, 68, 68, 0.8)'
                        )
                    }]
                },
                options: chartConfig
            });
            
            // NYSE Chart (NUEVO)
            if (chartData.nyse_indicators && chartData.nyse_values) {
                new Chart(document.getElementById('nyseChart'), {
                    type: 'radar',
                    data: {
                        labels: chartData.nyse_indicators,
                        datasets: [{
                            label: 'Indicadores NYSE (Normalizados)',
                            data: chartData.nyse_values,
                            backgroundColor: 'rgba(99, 102, 241, 0.2)',
                            borderColor: 'rgba(99, 102, 241, 0.8)',
                            borderWidth: 2,
                            pointBackgroundColor: 'rgba(99, 102, 241, 1)',
                            pointBorderColor: '#fff',
                            pointHoverBackgroundColor: '#fff',
                            pointHoverBorderColor: 'rgba(99, 102, 241, 1)'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { labels: { color: 'white' } } },
                        scales: {
                            r: {
                                angleLines: { color: 'rgba(255,255,255,0.1)' },
                                grid: { color: 'rgba(255,255,255,0.1)' },
                                pointLabels: { color: 'white' },
                                ticks: { color: 'white', backdropColor: 'transparent' }
                            }
                        }
                    }
                });
            }
        });
        """
        else:
            return base_config + """
        window.addEventListener('load', function() {
            // Performance Chart
            new Chart(document.getElementById('performanceChart'), {
                type: 'bar',
                data: {
                    labels: chartData.symbols,
                    datasets: [{
                        label: 'Rendimiento 20d (%)',
                        data: chartData.performance_20d,
                        backgroundColor: chartData.performance_20d.map(val => 
                            val > 0 ? 'rgba(34, 197, 94, 0.8)' : 'rgba(239, 68, 68, 0.8)'
                        )
                    }]
                },
                options: chartConfig
            });
            
            // RSI Chart
            new Chart(document.getElementById('rsiChart'), {
                type: 'bar',
                data: {
                    labels: chartData.symbols,
                    datasets: [{
                        label: 'RSI 14',
                        data: chartData.rsi_values,
                        backgroundColor: chartData.rsi_values.map(val => 
                            val > 70 ? 'rgba(239, 68, 68, 0.8)' : 
                            val < 30 ? 'rgba(34, 197, 94, 0.8)' : 
                            'rgba(99, 102, 241, 0.8)'
                        )
                    }]
                },
                options: chartConfig
            });
            
            // MA200 Chart
            new Chart(document.getElementById('ma200Chart'), {
                type: 'bar',
                data: {
                    labels: chartData.symbols,
                    datasets: [{
                        label: 'Distancia MA200 (%)',
                        data: chartData.ma200_distance,
                        backgroundColor: chartData.ma200_distance.map(val => 
                            val > 0 ? 'rgba(34, 197, 94, 0.8)' : 'rgba(239, 68, 68, 0.8)'
                        )
                    }]
                },
                options: chartConfig
            });
            
            // Volatility Chart (cuando no hay NYSE)
            new Chart(document.getElementById('volatilityChart'), {
                type: 'bar',
                data: {
                    labels: chartData.symbols,
                    datasets: [{
                        label: 'Volatilidad 20d (%)',
                        data: chartData.volatility,
                        backgroundColor: 'rgba(251, 191, 36, 0.8)'
                    }]
                },
                options: chartConfig
            });
        });
        """
    
    def _generate_chart_modal_js(self):
        """Genera JavaScript para modal de gráficos Finviz (ORIGINAL)"""
        return """
        // Modal para gráficos Finviz
        function openChartModal(symbol, chartUrl) {
            // Crear modal si no existe
            let modal = document.getElementById('chartModal');
            if (!modal) {
                modal = document.createElement('div');
                modal.id = 'chartModal';
                modal.className = 'chart-modal';
                modal.innerHTML = `
                    <div class="modal-backdrop" onclick="closeChartModal()"></div>
                    <div class="modal-content">
                        <div class="modal-header">
                            <h3 id="modalTitle">Gráfico</h3>
                            <button class="modal-close" onclick="closeChartModal()">×</button>
                        </div>
                        <div class="modal-body">
                            <img id="modalChart" src="" alt="Gráfico ampliado" />
                            <div class="modal-actions">
                                <a id="finvizLink" href="" target="_blank" class="btn-finviz">
                                    Ver en Finviz →
                                </a>
                            </div>
                        </div>
                    </div>
                `;
                document.body.appendChild(modal);
            }
            
            // Actualizar contenido del modal
            document.getElementById('modalTitle').textContent = `Gráfico ${symbol}`;
            document.getElementById('modalChart').src = chartUrl;
            document.getElementById('finvizLink').href = chartUrl;
            
            // Mostrar modal
            modal.style.display = 'flex';
            document.body.style.overflow = 'hidden';
        }
        
        function closeChartModal() {
            const modal = document.getElementById('chartModal');
            if (modal) {
                modal.style.display = 'none';
                document.body.style.overflow = 'auto';
            }
        }
        
        // Cerrar modal con ESC
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closeChartModal();
            }
        });
        """
    
    def _get_complete_css(self):
        """CSS completo para análisis original + NYSE"""
        return """
        /* CSS COMPLETO para análisis por índices + indicadores NYSE */
        :root {
            --glass-primary: rgba(99, 102, 241, 0.9);
            --glass-secondary: rgba(139, 92, 246, 0.8);
            --glass-accent: rgba(59, 130, 246, 1);
            --glass-bg: rgba(255, 255, 255, 0.05);
            --glass-bg-hover: rgba(255, 255, 255, 0.12);
            --glass-border: rgba(255, 255, 255, 0.15);
            --glass-shadow: 0 8px 32px rgba(0, 0, 0, 0.37);
            --text-primary: rgba(255, 255, 255, 0.95);
            --text-secondary: rgba(255, 255, 255, 0.75);
            --success: rgba(72, 187, 120, 0.9);
            --warning: rgba(251, 191, 36, 0.9);
            --danger: rgba(239, 68, 68, 0.9);
        }
        
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif;
            background: #020617;
            background-image: radial-gradient(ellipse at top, rgba(16, 23, 42, 0.9) 0%, rgba(2, 6, 23, 0.95) 50%, rgba(0, 0, 0, 0.98) 100%);
            background-attachment: fixed;
            color: var(--text-primary);
            line-height: 1.6;
            overflow-x: hidden;
            min-height: 100vh;
        }
        
        .glass-container { max-width: 1600px; margin: 0 auto; padding: 2rem; }
        .glass-card {
            background: var(--glass-bg);
            backdrop-filter: blur(20px) saturate(180%);
            border: 1px solid var(--glass-border);
            border-radius: 24px;
            box-shadow: var(--glass-shadow);
            transition: all 0.4s ease;
            position: relative;
            overflow: hidden;
        }
        
        .liquid-header { text-align: center; padding: 3rem 2rem; margin-bottom: 2rem; }
        .liquid-header h1 {
            font-size: clamp(2rem, 5vw, 3.5rem);
            font-weight: 800;
            background: linear-gradient(135deg, var(--glass-primary), var(--glass-secondary));
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 1rem;
        }
        
        .market-status {
            display: inline-flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.75rem 1.5rem;
            border-radius: 50px;
            font-weight: 600;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(72, 187, 120, 0.3);
            background: rgba(72, 187, 120, 0.1);
            color: var(--success);
        }
        
        .score-badge {
            background: rgba(255, 255, 255, 0.1);
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-size: 0.9rem;
            margin-left: 0.5rem;
        }
        
        .pulse-dot {
            width: 8px;
            height: 8px;
            background: #48bb78;
            border-radius: 50%;
            animation: pulse 2s ease-in-out infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.3; transform: scale(1.2); }
        }
        
        .stats-liquid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
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
            transition: all 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }
        
        .stat-glass:hover {
            transform: translateY(-12px) scale(1.05);
            box-shadow: 0 20px 60px rgba(99, 102, 241, 0.3);
        }
        
        .stat-number {
            font-size: 3rem;
            font-weight: 900;
            background: linear-gradient(135deg, var(--glass-accent), var(--glass-primary));
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }
        
        .stat-label {
            color: var(--text-secondary);
            font-size: 0.95rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 500;
        }
        
        .stat-percent {
            color: var(--glass-accent);
            font-size: 0.9rem;
            font-weight: 600;
            margin-top: 0.25rem;
        }
        
        /* === NUEVA SECCIÓN NYSE === */
        .nyse-breadth-section {
            padding: 2.5rem;
            margin: 2rem 0;
        }
        
        .nyse-summary-card {
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(139, 92, 246, 0.1));
            border: 1px solid rgba(99, 102, 241, 0.3);
            border-radius: 16px;
            padding: 2rem;
            margin-bottom: 2rem;
            text-align: center;
        }
        
        .nyse-summary-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
            flex-wrap: wrap;
            gap: 1rem;
        }
        
        .nyse-status {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--text-primary);
        }
        
        .nyse-confidence {
            background: rgba(255, 255, 255, 0.1);
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.9rem;
            color: var(--text-secondary);
        }
        
        .nyse-signals {
            display: flex;
            justify-content: center;
            gap: 2rem;
            flex-wrap: wrap;
        }
        
        .signal-count {
            font-size: 1.2rem;
            font-weight: 600;
            padding: 0.5rem 1rem;
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.05);
        }
        
        .nyse-indicators-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 2rem;
        }
        
        .nyse-category-card {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--glass-border);
            border-radius: 16px;
            padding: 1.5rem;
            transition: all 0.3s ease;
        }
        
        .nyse-category-card:hover {
            transform: translateY(-4px);
            background: rgba(255, 255, 255, 0.05);
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.3);
        }
        
        .category-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--glass-border);
            flex-wrap: wrap;
            gap: 0.5rem;
        }
        
        .category-header h3 {
            color: var(--glass-primary);
            font-size: 1.2rem;
            font-weight: 600;
            margin: 0;
        }
        
        .category-description {
            font-size: 0.8rem;
            color: var(--text-secondary);
            font-style: italic;
        }
        
        .category-count {
            background: rgba(255, 255, 255, 0.1);
            padding: 0.25rem 0.5rem;
            border-radius: 8px;
            font-size: 0.8rem;
            color: var(--text-secondary);
        }
        
        .category-indicators {
            display: grid;
            gap: 1rem;
        }
        
        .nyse-indicator-item {
            padding: 1rem;
            border-radius: 12px;
            border-left: 4px solid;
            transition: all 0.3s ease;
        }
        
        .nyse-indicator-item.bullish {
            background: rgba(72, 187, 120, 0.1);
            border-left-color: var(--success);
        }
        
        .nyse-indicator-item.bearish {
            background: rgba(239, 68, 68, 0.1);
            border-left-color: var(--danger);
        }
        
        .nyse-indicator-item.neutral {
            background: rgba(251, 191, 36, 0.1);
            border-left-color: var(--warning);
        }
        
        .nyse-indicator-item:hover {
            transform: translateX(4px);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        }
        
        .nyse-indicator-item .indicator-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
        }
        
        .indicator-name {
            font-weight: 700;
            font-size: 1rem;
            color: var(--text-primary);
        }
        
        .indicator-symbol {
            font-size: 0.8rem;
            color: var(--text-secondary);
            background: rgba(255, 255, 255, 0.05);
            padding: 0.2rem 0.5rem;
            border-radius: 6px;
        }
        
        .nyse-indicator-item .indicator-value {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
        }
        
        .nyse-indicator-item .value {
            font-size: 1.4rem;
            font-weight: 700;
            color: var(--text-primary);
        }
        
        .nyse-indicator-item .change {
            font-size: 0.9rem;
            font-weight: 600;
        }
        
        .change.positive { color: var(--success); }
        .change.negative { color: var(--danger); }
        
        .nyse-indicator-item .indicator-signal {
            font-size: 0.85rem;
            font-weight: 500;
            color: var(--text-secondary);
            text-align: center;
            background: rgba(255, 255, 255, 0.05);
            padding: 0.4rem;
            border-radius: 8px;
        }
        
        /* === SECCIÓN ORIGINAL === */
        .indices-analysis { padding: 2.5rem; margin-bottom: 2rem; }
        
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
        
        .indices-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
            gap: 2rem;
        }
        
        .index-detailed-card-with-chart {
            background: var(--glass-bg);
            backdrop-filter: blur(16px);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            padding: 1.5rem;
            transition: all 0.4s ease;
            overflow: hidden;
        }
        
        .index-detailed-card-with-chart:hover {
            transform: translateY(-8px);
            background: var(--glass-bg-hover);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
        }
        
        .index-detailed-card-with-chart.bullish { border-left: 4px solid var(--success); }
        .index-detailed-card-with-chart.bearish { border-left: 4px solid var(--danger); }
        .index-detailed-card-with-chart.neutral { border-left: 4px solid var(--warning); }
        
        .index-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--glass-border);
        }
        
        .index-symbol {
            font-size: 1.4rem;
            font-weight: 800;
            color: var(--glass-primary);
        }
        
        .index-name {
            font-size: 0.9rem;
            color: var(--text-secondary);
            margin-top: 0.25rem;
        }
        
        .price {
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--text-primary);
        }
        
        .change-20d {
            font-size: 1.1rem;
            font-weight: 600;
            margin-left: 0.5rem;
        }
        
        .positive { color: var(--success); }
        .negative { color: var(--danger); }
        
        /* GRÁFICOS FINVIZ (ORIGINAL) */
        .chart-section {
            margin-bottom: 1.5rem;
            position: relative;
        }
        
        .chart-wrapper {
            position: relative;
            border-radius: 12px;
            overflow: hidden;
            background: rgba(0, 0, 0, 0.3);
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .chart-wrapper:hover {
            transform: scale(1.02);
            box-shadow: 0 8px 25px rgba(99, 102, 241, 0.3);
        }
        
        .finviz-chart {
            width: 100%;
            height: auto;
            max-height: 200px;
            object-fit: cover;
            display: block;
            transition: all 0.3s ease;
        }
        
        .chart-overlay {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.6);
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0;
            transition: all 0.3s ease;
        }
        
        .chart-wrapper:hover .chart-overlay {
            opacity: 1;
        }
        
        .chart-expand {
            color: white;
            font-weight: 600;
            font-size: 0.9rem;
            background: rgba(99, 102, 241, 0.8);
            padding: 0.5rem 1rem;
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .chart-fallback {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 200px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            border: 2px dashed var(--glass-border);
        }
        
        .fallback-content {
            text-align: center;
            color: var(--text-secondary);
        }
        
        .fallback-icon {
            font-size: 2rem;
            display: block;
            margin-bottom: 0.5rem;
        }
        
        .fallback-text {
            display: block;
            margin-bottom: 0.75rem;
            font-size: 0.9rem;
        }
        
        .fallback-link {
            color: var(--glass-accent);
            text-decoration: none;
            font-size: 0.8rem;
            font-weight: 600;
            padding: 0.25rem 0.5rem;
            border: 1px solid var(--glass-accent);
            border-radius: 6px;
            transition: all 0.3s ease;
        }
        
        .fallback-link:hover {
            background: var(--glass-accent);
            color: white;
        }
        
        /* MODAL PARA GRÁFICOS (ORIGINAL) */
        .chart-modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.9);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            backdrop-filter: blur(10px);
        }
        
        .modal-backdrop {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            cursor: pointer;
        }
        
        .modal-content {
            position: relative;
            background: var(--glass-bg);
            backdrop-filter: blur(20px);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            padding: 0;
            max-width: 90vw;
            max-height: 90vh;
            overflow: hidden;
            box-shadow: var(--glass-shadow);
        }
        
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1.5rem;
            border-bottom: 1px solid var(--glass-border);
            background: rgba(255, 255, 255, 0.05);
        }
        
        .modal-header h3 {
            color: var(--text-primary);
            font-size: 1.25rem;
            font-weight: 600;
        }
        
        .modal-close {
            background: none;
            border: none;
            color: var(--text-primary);
            font-size: 2rem;
            cursor: pointer;
            padding: 0.25rem;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s ease;
        }
        
        .modal-close:hover {
            background: rgba(255, 255, 255, 0.1);
            color: var(--danger);
        }
        
        .modal-body {
            padding: 1.5rem;
            text-align: center;
        }
        
        .modal-body img {
            max-width: 100%;
            max-height: 70vh;
            border-radius: 12px;
            margin-bottom: 1rem;
        }
        
        .modal-actions {
            margin-top: 1rem;
        }
        
        .btn-finviz {
            display: inline-block;
            color: white;
            background: linear-gradient(135deg, var(--glass-primary), var(--glass-secondary));
            text-decoration: none;
            padding: 0.75rem 1.5rem;
            border-radius: 12px;
            font-weight: 600;
            transition: all 0.3s ease;
            border: 1px solid var(--glass-border);
        }
        
        .btn-finviz:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(99, 102, 241, 0.4);
        }
        
        .signals-section { margin-bottom: 1.5rem; }
        
        .signal-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
            padding: 0.5rem;
            background: rgba(255, 255, 255, 0.02);
            border-radius: 8px;
        }
        
        .signal-row.overall {
            background: rgba(99, 102, 241, 0.1);
            border: 1px solid rgba(99, 102, 241, 0.3);
            font-weight: 600;
        }
        
        .signal-label {
            font-size: 0.9rem;
            color: var(--text-secondary);
        }
        
        .signal-value {
            font-size: 0.9rem;
            font-weight: 500;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.5rem;
        }
        
        .metric-item {
            display: flex;
            justify-content: space-between;
            padding: 0.5rem;
            background: rgba(255, 255, 255, 0.02);
            border-radius: 6px;
            font-size: 0.85rem;
        }
        
        .metric-label { color: var(--text-secondary); }
        .metric-value { font-weight: 600; }
        
        .performers-section { padding: 2.5rem; margin-bottom: 2rem; }
        
        .performers-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
        }
        
        .performers-column {
            background: rgba(255, 255, 255, 0.02);
            border-radius: 16px;
            padding: 1.5rem;
            border: 1px solid var(--glass-border);
        }
        
        .performers-title {
            color: var(--glass-primary);
            margin-bottom: 1rem;
            text-align: center;
        }
        
        .performer-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem;
            margin-bottom: 0.5rem;
            border-radius: 12px;
            font-weight: 600;
        }
        
        .performer-item.best {
            background: rgba(72, 187, 120, 0.1);
            border: 1px solid rgba(72, 187, 120, 0.3);
        }
        
        .performer-item.worst {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
        }
        
        .charts-section { padding: 2.5rem; margin-bottom: 2rem; }
        
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 2rem;
        }
        
        .chart-container {
            background: rgba(255, 255, 255, 0.02);
            border-radius: 16px;
            padding: 1.5rem;
            border: 1px solid var(--glass-border);
        }
        
        .chart-title {
            color: var(--glass-primary);
            font-weight: 600;
            margin-bottom: 1rem;
            text-align: center;
        }
        
        canvas {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            height: 250px !important;
        }
        
        .floating-element { animation: float 6s ease-in-out infinite; }
        
        @keyframes float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-10px); }
        }
        
        .fade-in-up {
            opacity: 0;
            transform: translateY(30px);
            animation: fadeInUp 0.8s ease-out forwards;
        }
        
        @keyframes fadeInUp {
            to { opacity: 1; transform: translateY(0); }
        }
        
        .footer-liquid {
            text-align: center;
            margin-top: 4rem;
            padding: 2rem 0;
            border-top: 1px solid var(--glass-border);
            color: var(--text-secondary);
        }
        
        .footer-liquid a {
            color: var(--glass-accent);
            text-decoration: none;
            transition: all 0.3s ease;
        }
        
        @media (max-width: 768px) {
            .glass-container { padding: 1rem; }
            .indices-grid { grid-template-columns: 1fr; }
            .charts-grid { grid-template-columns: 1fr; }
            .performers-grid { grid-template-columns: 1fr; }
            .metrics-grid { grid-template-columns: 1fr; }
            .nyse-indicators-grid { grid-template-columns: 1fr; }
            
            .nyse-summary-header {
                flex-direction: column;
                text-align: center;
            }
            
            .nyse-signals {
                justify-content: center;
                gap: 1rem;
            }
            
            .category-header {
                flex-direction: column;
                text-align: center;
                gap: 0.5rem;
            }
            
            .modal-content {
                max-width: 95vw;
                max-height: 95vh;
            }
            
            .modal-body img {
                max-height: 60vh;
            }
        }
        """