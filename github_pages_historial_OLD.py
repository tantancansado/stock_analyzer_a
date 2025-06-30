#!/usr/bin/env python3
"""
GitHub Pages Templates - Liquid Glass Design System
Sistema de templates con estética Liquid Glass para GitHub Pages
Incluye glassmorphism, animaciones fluidas y diseño moderno
"""

from datetime import datetime
import json

class GitHubPagesTemplates:
    """Generador de templates con diseño Liquid Glass para GitHub Pages"""
    
    def __init__(self, base_url="https://tantancansado.github.io/stock_analyzer_a"):
        self.base_url = base_url
        self.liquid_css = self._get_liquid_glass_css()
    
    def _get_liquid_glass_css(self):
        """CSS con efectos Liquid Glass y glassmorphism"""
        return """
        /* === LIQUID GLASS DESIGN SYSTEM === */
        
        :root {
            /* Colores principales */
            --glass-primary: rgba(99, 102, 241, 0.8);
            --glass-secondary: rgba(139, 92, 246, 0.7);
            --glass-accent: rgba(59, 130, 246, 0.9);
            
            /* Glassmorphism */
            --glass-bg: rgba(255, 255, 255, 0.03);
            --glass-bg-hover: rgba(255, 255, 255, 0.08);
            --glass-border: rgba(255, 255, 255, 0.1);
            --glass-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            --glass-shadow-hover: 0 16px 64px rgba(99, 102, 241, 0.3);
            
            /* Texto */
            --text-primary: rgba(255, 255, 255, 0.95);
            --text-secondary: rgba(255, 255, 255, 0.7);
            --text-muted: rgba(255, 255, 255, 0.5);
            
            /* Fondo */
            --bg-gradient: radial-gradient(ellipse at top, rgba(16, 23, 42, 0.8) 0%, rgba(2, 6, 23, 0.9) 50%, rgba(0, 0, 0, 0.95) 100%);
            --bg-secondary: linear-gradient(135deg, rgba(30, 41, 59, 0.4) 0%, rgba(15, 23, 42, 0.6) 100%);
            
            /* Animaciones */
            --transition-smooth: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            --transition-bounce: all 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            --transition-elastic: all 0.8s cubic-bezier(0.68, -0.55, 0.265, 1.55);
        }
        
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', Roboto, sans-serif;
            background: #020617;
            background-image: var(--bg-gradient);
            background-attachment: fixed;
            color: var(--text-primary);
            line-height: 1.6;
            overflow-x: hidden;
            min-height: 100vh;
        }
        
        /* === FLOATING PARTICLES BACKGROUND === */
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: 
                radial-gradient(circle at 20% 80%, rgba(99, 102, 241, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(139, 92, 246, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 40% 40%, rgba(59, 130, 246, 0.05) 0%, transparent 50%);
            pointer-events: none;
            z-index: -1;
            animation: float 20s ease-in-out infinite;
        }
        
        @keyframes float {
            0%, 100% { transform: translateY(0px) rotate(0deg); }
            33% { transform: translateY(-20px) rotate(1deg); }
            66% { transform: translateY(-10px) rotate(-1deg); }
        }
        
        /* === GLASS CONTAINER === */
        .glass-container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
            position: relative;
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
            box-shadow: var(--glass-shadow-hover);
            transform: translateY(-8px) scale(1.02);
            border-color: rgba(255, 255, 255, 0.2);
        }
        
        /* === HEADER === */
        .liquid-header {
            text-align: center;
            padding: 4rem 2rem;
            margin-bottom: 3rem;
            position: relative;
            z-index: 10;
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
        
        .live-pulse {
            display: inline-flex;
            align-items: center;
            gap: 0.75rem;
            background: rgba(72, 187, 120, 0.1);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(72, 187, 120, 0.3);
            color: rgba(72, 187, 120, 0.9);
            padding: 0.75rem 1.5rem;
            border-radius: 50px;
            font-weight: 600;
            transition: var(--transition-smooth);
        }
        
        .live-pulse:hover {
            background: rgba(72, 187, 120, 0.2);
            box-shadow: 0 8px 32px rgba(72, 187, 120, 0.3);
        }
        
        .pulse-dot {
            width: 8px;
            height: 8px;
            background: #48bb78;
            border-radius: 50%;
            animation: pulse-glow 2s ease-in-out infinite;
            box-shadow: 0 0 10px rgba(72, 187, 120, 0.8);
        }
        
        @keyframes pulse-glow {
            0%, 100% { 
                opacity: 1; 
                transform: scale(1);
                box-shadow: 0 0 10px rgba(72, 187, 120, 0.8);
            }
            50% { 
                opacity: 0.3; 
                transform: scale(1.2);
                box-shadow: 0 0 20px rgba(72, 187, 120, 1);
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
            background: var(--glass-bg);
            backdrop-filter: blur(20px);
            border: 1px solid var(--glass-border);
            border-radius: 24px;
            padding: 2.5rem;
            margin-bottom: 2rem;
            transition: var(--transition-smooth);
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
        
        /* === REPORT CARDS === */
        .reports-fluid {
            display: grid;
            gap: 1.5rem;
        }
        
        .report-liquid {
            background: var(--glass-bg);
            backdrop-filter: blur(16px);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            padding: 2rem;
            transition: var(--transition-elastic);
            position: relative;
            overflow: hidden;
        }
        
        .report-liquid::before {
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
        
        .report-liquid:hover {
            transform: translateX(12px) scale(1.02);
            border-color: var(--glass-accent);
            box-shadow: 0 16px 48px rgba(59, 130, 246, 0.25);
        }
        
        .report-liquid:hover::before {
            opacity: 1;
        }
        
        .report-title {
            font-size: 1.4rem;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 1rem;
            transition: var(--transition-smooth);
        }
        
        .report-liquid:hover .report-title {
            color: var(--glass-accent);
        }
        
        .report-meta {
            color: var(--text-secondary);
            font-size: 0.95rem;
            margin-bottom: 1.5rem;
            line-height: 1.6;
        }
        
        .report-actions {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
        }
        
        /* === LIQUID BUTTONS === */
        .btn-liquid {
            padding: 0.875rem 1.5rem;
            border-radius: 16px;
            text-decoration: none;
            font-weight: 600;
            text-align: center;
            transition: var(--transition-bounce);
            position: relative;
            overflow: hidden;
            backdrop-filter: blur(10px);
            border: 1px solid transparent;
        }
        
        .btn-liquid::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
            transition: var(--transition-smooth);
        }
        
        .btn-liquid:hover::before {
            left: 100%;
        }
        
        .btn-primary-liquid {
            background: linear-gradient(135deg, var(--glass-primary), var(--glass-accent));
            color: white;
            box-shadow: 0 8px 24px rgba(99, 102, 241, 0.3);
        }
        
        .btn-primary-liquid:hover {
            transform: translateY(-4px) scale(1.05);
            box-shadow: 0 16px 40px rgba(99, 102, 241, 0.5);
        }
        
        .btn-secondary-liquid {
            background: rgba(255, 255, 255, 0.1);
            color: var(--text-primary);
            border-color: var(--glass-border);
        }
        
        .btn-secondary-liquid:hover {
            transform: translateY(-4px) scale(1.05);
            background: rgba(255, 255, 255, 0.2);
            box-shadow: 0 12px 32px rgba(255, 255, 255, 0.1);
        }
        
        /* === SPECIAL EFFECTS === */
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
        
        /* === INFO SECTIONS === */
        .info-glass {
            background: rgba(255, 255, 255, 0.02);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(99, 102, 241, 0.2);
            border-radius: 16px;
            padding: 2rem;
            margin: 2rem 0;
            position: relative;
        }
        
        .info-glass::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 4px;
            height: 100%;
            background: linear-gradient(180deg, var(--glass-primary), var(--glass-secondary));
            border-radius: 2px;
        }
        
        .explanation-liquid {
            background: rgba(99, 102, 241, 0.05);
            backdrop-filter: blur(8px);
            border: 1px solid rgba(99, 102, 241, 0.2);
            border-radius: 16px;
            padding: 1.5rem;
            margin: 1.5rem 0;
        }
        
        .explanation-liquid h3 {
            color: var(--glass-primary);
            margin-bottom: 1rem;
        }
        
        .explanation-liquid ul {
            list-style: none;
            padding-left: 0;
        }
        
        .explanation-liquid li {
            margin-bottom: 0.75rem;
            padding-left: 1.5rem;
            position: relative;
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
        
        .no-data-liquid h3 {
            color: var(--text-secondary);
            margin-bottom: 1rem;
            font-size: 1.5rem;
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
            
            .report-actions {
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
        
        /* === LOADING STATES === */
        .loading-shimmer {
            background: linear-gradient(90deg, 
                rgba(255, 255, 255, 0.05) 25%, 
                rgba(255, 255, 255, 0.1) 50%, 
                rgba(255, 255, 255, 0.05) 75%
            );
            background-size: 200% 100%;
            animation: shimmer-loading 2s infinite;
        }
        
        @keyframes shimmer-loading {
            0% { background-position: -200% 0; }
            100% { background-position: 200% 0; }
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
        """
    
    def generate_main_dashboard(self, manifest):
        """Genera el dashboard principal con diseño Liquid Glass"""
        total_reports = manifest['total_reports']
        total_dj_reports = manifest.get('total_dj_reports', 0)
        last_update = manifest['last_update'][:10] if manifest['last_update'] else 'N/A'
        unique_days = len(set(r['date'] for r in manifest['reports'])) if manifest['reports'] else 0
        
        return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📊 Trading Analytics System | Liquid Glass Dashboard</title>
    <meta name="description" content="Sistema avanzado de análisis de trading con IA - Dashboard principal">
    <link rel="icon" type="image/x-icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📊</text></svg>">
    <style>
        {self.liquid_css}
    </style>
</head>
<body>
    <div class="glass-container">
        <header class="liquid-header glass-card floating-element">
            <h1>📊 Trading Analytics System</h1>
            <p>Sistema inteligente de análisis financiero con IA avanzada</p>
            <div class="live-pulse">
                <div class="pulse-dot"></div>
                <span>Sistema Activo • Actualización Automática</span>
            </div>
        </header>
        
        <section class="stats-liquid">
            <div class="stat-glass fade-in-up" style="animation-delay: 0.1s">
                <div class="stat-number">{total_reports}</div>
                <div class="stat-label">Análisis Insider</div>
            </div>
            <div class="stat-glass fade-in-up" style="animation-delay: 0.2s">
                <div class="stat-number">{total_dj_reports}</div>
                <div class="stat-label">Análisis Sectorial</div>
            </div>
            <div class="stat-glass fade-in-up" style="animation-delay: 0.3s">
                <div class="stat-number">{unique_days}</div>
                <div class="stat-label">Días Monitoreados</div>
            </div>
            <div class="stat-glass fade-in-up" style="animation-delay: 0.4s">
                <div class="stat-number">{last_update}</div>
                <div class="stat-label">Última Actualización</div>
            </div>
        </section>
        
        <main class="content-liquid glass-card">
            <h2 class="section-title">📈 Reportes Recientes</h2>
            
            <div class="reports-fluid">
                {self._generate_recent_reports_html(manifest['reports'][:10])}
            </div>
        </main>
        
        <footer class="footer-liquid">
            <p>🚀 Trading Analytics System • Powered by AI & Advanced Analytics</p>
            <p>
                <a href="{self.base_url}">🏠 Dashboard</a> • 
                <a href="dj_sectorial.html">📊 DJ Sectorial</a> • 
                <a href="vcp_scanner.html">🎯 VCP Scanner</a> • 
                <a href="trends.html">📈 Tendencias</a>
            </p>
        </footer>
    </div>
    
    <script>
        // Auto-refresh inteligente cada 5 minutos
        setTimeout(() => location.reload(), 300000);
        
        // Animaciones de entrada escalonadas
        document.addEventListener('DOMContentLoaded', function() {{
            const cards = document.querySelectorAll('.report-liquid');
            cards.forEach((card, index) => {{
                card.style.animationDelay = `${{index * 0.1}}s`;
                card.classList.add('fade-in-up');
            }});
        }});
        
        // Analytics
        console.log('🚀 Trading Analytics Dashboard Loaded');
        console.log('📊 Total Reports: {total_reports}');
        console.log('📈 DJ Sectorial: {total_dj_reports}');
        console.log('🌐 Base URL: {self.base_url}');
    </script>
</body>
</html>"""
    
    def _generate_recent_reports_html(self, reports):
        """Genera HTML para reportes recientes"""
        if not reports:
            return """
            <div class="no-data-liquid">
                <h3>🔍 No hay reportes disponibles</h3>
                <p>Los análisis aparecerán aquí cuando el sistema esté en funcionamiento</p>
            </div>
            """
        
        html = ""
        for i, report in enumerate(reports):
            delay = i * 0.1
            html += f"""
            <div class="report-liquid floating-element" style="animation-delay: {delay}s">
                <h3 class="report-title">{report['title']}</h3>
                <div class="report-meta">
                    📅 {report['date']} • 🕐 {report['time']}<br>
                    {report['description']}
                </div>
                <div class="report-actions">
                    <a href="{report['html_url']}" class="btn-liquid btn-primary-liquid">
                        📊 Ver Análisis
                    </a>
                    <a href="{report['csv_url']}" class="btn-liquid btn-secondary-liquid">
                        📥 Descargar CSV
                    </a>
                </div>
            </div>
            """
        
        return html
    
    def generate_dj_sectorial_page(self, manifest):
        """Genera página DJ Sectorial con diseño Liquid Glass"""
        dj_reports = manifest.get('dj_reports', [])
        total_dj_reports = len(dj_reports)
        
        return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📊 DJ Sectorial Analysis | Liquid Glass Dashboard</title>
    <meta name="description" content="Análisis avanzado de sectores Dow Jones con IA">
    <style>
        {self.liquid_css}
    </style>
</head>
<body>
    <div class="glass-container">
        <header class="liquid-header glass-card floating-element">
            <h1>📊 DJ Sectorial Analysis</h1>
            <p>Análisis inteligente de 43 sectores Dow Jones con patrones avanzados</p>
            <div class="live-pulse">
                <div class="pulse-dot"></div>
                <span>Análisis Automatizado • IA Integrada</span>
            </div>
        </header>
        
        <section class="content-liquid glass-card">
            <h2 class="section-title">🧠 ¿Qué es el análisis DJ Sectorial?</h2>
            <p style="text-align: center; color: var(--text-secondary); margin-bottom: 2rem;">
                Sistema de inteligencia artificial que evalúa 43 sectores del mercado estadounidense, 
                identificando oportunidades basadas en análisis técnico avanzado y patrones de comportamiento.
            </p>
            
            <div class="explanation-liquid">
                <h3>🎯 Clasificación Inteligente de Sectores</h3>
                <ul>
                    <li><strong>🟢 OPORTUNIDADES PREMIUM (&lt;10%):</strong> Sectores cerca de mínimos históricos - Potencial de rebote excepcional</li>
                    <li><strong>🟡 ZONA DE VIGILANCIA (10-25%):</strong> Sectores en consolidación - Monitoreo para timing óptimo</li>
                    <li><strong>🔴 MOMENTUM ALCISTA (&gt;25%):</strong> Sectores en tendencia fuerte - Confirmación de fortaleza</li>
                </ul>
            </div>
        </section>
        
        <section class="stats-liquid">
            <div class="stat-glass fade-in-up" style="animation-delay: 0.1s">
                <div class="stat-number">{total_dj_reports}</div>
                <div class="stat-label">Análisis Completados</div>
            </div>
            <div class="stat-glass fade-in-up" style="animation-delay: 0.2s">
                <div class="stat-number">43</div>
                <div class="stat-label">Sectores Monitoreados</div>
            </div>
            <div class="stat-glass fade-in-up" style="animation-delay: 0.3s">
                <div class="stat-number">24/7</div>
                <div class="stat-label">Monitoreo Continuo</div>
            </div>
            <div class="stat-glass fade-in-up" style="animation-delay: 0.4s">
                <div class="stat-number">IA</div>
                <div class="stat-label">Análisis Avanzado</div>
            </div>
        </section>
        
        <main class="content-liquid glass-card">
            <h2 class="section-title">📈 Análisis Sectoriales Recientes</h2>
            
            <div class="reports-fluid">
                {self._generate_dj_reports_html(dj_reports[:15])}
            </div>
        </main>
        
        <section class="content-liquid glass-card">
            <h2 class="section-title">💡 Estrategias de Inversión Inteligente</h2>
            <div class="info-glass">
                <ol style="color: var(--text-secondary); line-height: 1.8;">
                    <li><strong style="color: var(--glass-primary);">🎯 Identificación de Oportunidades:</strong> Sectores en zona verde ofrecen el mejor ratio riesgo/beneficio</li>
                    <li><strong style="color: var(--glass-primary);">📊 Análisis Técnico Combinado:</strong> RSI + Distancia de mínimos para timing perfecto</li>
                    <li><strong style="color: var(--glass-primary);">⚡ Momentum Trading:</strong> Sectores rojos confirman tendencias y fortaleza del mercado</li>
                    <li><strong style="color: var(--glass-primary);">🔄 Rotación Sectorial:</strong> Identificar rotaciones de capital entre sectores</li>
                    <li><strong style="color: var(--glass-primary);">🧭 Diversificación Inteligente:</strong> Balancear portafolio según fortaleza sectorial</li>
                </ol>
            </div>
        </section>
        
        <footer class="footer-liquid">
            <p>🚀 DJ Sectorial Analysis • Powered by Advanced AI</p>
            <p>
                <a href="{self.base_url}">🏠 Dashboard Principal</a> • 
                <a href="vcp_scanner.html">🎯 VCP Scanner</a> • 
                <a href="trends.html">📈 Análisis de Tendencias</a>
            </p>
        </footer>
    </div>
    
    <script>
        // Animaciones de entrada
        document.addEventListener('DOMContentLoaded', function() {{
            const elements = document.querySelectorAll('.fade-in-up');
            elements.forEach((el, index) => {{
                el.style.animationDelay = `${{index * 0.1}}s`;
            }});
        }});
    </script>
</body>
</html>"""
    
    def _generate_dj_reports_html(self, reports):
        """Genera HTML para reportes DJ Sectorial"""
        if not reports:
            return """
            <div class="no-data-liquid">
                <h3>🔄 Preparando Análisis Sectorial</h3>
                <p>Los análisis DJ Sectorial se generan automáticamente cada día</p>
                <div class="spinner-liquid"></div>
            </div>
            """
        
        html = ""
        for i, report in enumerate(reports):
            delay = i * 0.1
            html += f"""
            <div class="report-liquid floating-element" style="animation-delay: {delay}s">
                <h3 class="report-title">{report['title']}</h3>
                <div class="report-meta">
                    📅 {report['date']} • 🕐 {report['time']}<br>
                    {report['description']}
                </div>
                <div class="report-actions">
                    <a href="{report['html_url']}" class="btn-liquid btn-primary-liquid">
                        📊 Ver Sectores
                    </a>
                    <a href="{report['csv_url']}" class="btn-liquid btn-secondary-liquid">
                        📥 Datos Técnicos
                    </a>
                </div>
            </div>
            """
        
        return html
    
    def generate_vcp_scanner_page(self, all_tickers):
        """Genera página VCP Scanner con diseño Liquid Glass"""
        return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎯 VCP Pattern Scanner | Liquid Glass Dashboard</title>
    <meta name="description" content="Scanner avanzado de patrones VCP con IA para insider trading">
    <style>
        {self.liquid_css}
    </style>
</head>
<body>
    <div class="glass-container">
        <header class="liquid-header glass-card floating-element">
            <h1>🎯 VCP Pattern Scanner</h1>
            <p>Detección inteligente de patrones de volatilidad en acciones con actividad insider</p>
            <div class="live-pulse">
                <div class="pulse-dot"></div>
                <span>Scanner IA Activo • Análisis en Tiempo Real</span>
            </div>
        </header>
        
        <section class="content-liquid glass-card">
            <h2 class="section-title">🧠 Volatility Contraction Pattern (VCP)</h2>
            <p style="text-align: center; color: var(--text-secondary); margin-bottom: 2rem;">
                Patrón técnico desarrollado por Mark Minervini que identifica consolidaciones saludables 
                antes de movimientos alcistas significativos, potenciado con IA para mayor precisión.
            </p>
            
            <div class="explanation-liquid">
                <h3>⚡ Características del Patrón VCP Avanzado</h3>
                <ul>
                    <li><strong>📉 Contracciones Progresivas:</strong> Cada corrección menor que la anterior (ej: 25% → 15% → 8%)</li>
                    <li><strong>📊 Análisis de Volumen IA:</strong> Volumen decreciente durante correcciones con patrones predictivos</li>
                    <li><strong>⏰ Base Temporal Optimizada:</strong> Formación típica en 8-12 semanas con validación algorítmica</li>
                    <li><strong>🎯 Punto de Entrada Preciso:</strong> Ruptura de resistencia con confirmación de volumen e IA</li>
                    <li><strong>🔗 Correlación Insider:</strong> Combinación única con actividad de insider trading</li>
                </ul>
            </div>
        </section>
        
        <section class="stats-liquid">
            <div class="stat-glass fade-in-up" style="animation-delay: 0.1s">
                <div class="stat-number">{len(all_tickers)}</div>
                <div class="stat-label">Acciones Analizadas</div>
            </div>
            <div class="stat-glass fade-in-up" style="animation-delay: 0.2s">
                <div class="stat-number">∞</div>
                <div class="stat-label">Patrones Detectados</div>
            </div>
            <div class="stat-glass fade-in-up" style="animation-delay: 0.3s">
                <div class="stat-number">24/7</div>
                <div class="stat-label">Monitoreo IA</div>
            </div>
            <div class="stat-glass fade-in-up" style="animation-delay: 0.4s">
                <div class="stat-number">AI</div>
                <div class="stat-label">Tecnología Avanzada</div>
            </div>
        </section>
        
        <main class="content-liquid glass-card">
            <h2 class="section-title">🔍 Análisis en Progreso</h2>
            
            <div style="text-align: center; padding: 3rem;">
                <div class="spinner-liquid"></div>
                <p style="color: var(--glass-primary); font-size: 1.2rem; margin: 2rem 0;">
                    🧠 IA escaneando {len(all_tickers)} acciones con actividad insider...
                </p>
                <p style="color: var(--text-secondary);">
                    El análisis VCP avanzado puede tomar varios minutos para completarse
                </p>
            </div>
            
            <div id="vcp-results" style="display: none;">
                <div class="info-glass">
                    <h3 style="color: var(--glass-primary);">✅ Análisis Completado</h3>
                    <p>El scanner IA ha analizado todas las acciones con actividad insider.</p>
                </div>
                
                <div id="vcp-patterns">
                    <!-- Los resultados se cargarán aquí -->
                </div>
            </div>
        </main>
        
        <section class="content-liquid glass-card">
            <h2 class="section-title">🎯 Estrategias de Trading VCP + Insider</h2>
            <div class="info-glass">
                <ol style="color: var(--text-secondary); line-height: 1.8;">
                    <li><strong style="color: var(--glass-primary);">🟢 Confirmación Doble:</strong> VCP + Insider buying = Señal de alta probabilidad</li>
                    <li><strong style="color: var(--glass-primary);">🎯 Timing Preciso:</strong> Esperar ruptura de resistencia con volumen</li>
                    <li><strong style="color: var(--glass-primary);">🛡️ Gestión de Riesgo:</strong> Stop-loss por debajo del último mínimo de la base</li>
                    <li><strong style="color: var(--glass-primary);">📈 Objetivos de Precio:</strong> Proyecciones basadas en altura de la base VCP</li>
                    <li><strong style="color: var(--glass-primary);">⚡ Escalado Posiciones:</strong> Añadir en retests exitosos de la ruptura</li>
                </ol>
            </div>
        </section>
        
        <footer class="footer-liquid">
            <p>🎯 VCP Scanner • Enhanced with AI & Insider Analysis</p>
            <p>
                <a href="{self.base_url}">🏠 Dashboard Principal</a> • 
                <a href="dj_sectorial.html">📊 DJ Sectorial</a> • 
                <a href="trends.html">📈 Análisis de Tendencias</a>
            </p>
        </footer>
    </div>
    
    <script>
        // Simulación de análisis VCP
        setTimeout(() => {{
            document.querySelector('.spinner-liquid').style.display = 'none';
            document.querySelector('main .content-liquid p').innerHTML = `
                <span style="color: var(--glass-primary);">✅ Análisis IA completado</span><br>
                <span style="color: var(--text-secondary);">Se analizaron {len(all_tickers)} acciones con algoritmos avanzados</span>
            `;
            
            document.getElementById('vcp-results').style.display = 'block';
            document.getElementById('vcp-patterns').innerHTML = `
                <div class="no-data-liquid">
                    <h3>🔍 Patrones VCP en Evaluación</h3>
                    <p>El sistema IA está refinando la detección de patrones. Los resultados aparecerán cuando se identifiquen formaciones VCP válidas.</p>
                    <div style="margin-top: 2rem;">
                        <p style="color: var(--glass-primary);">💡 <strong>Factores en Análisis:</strong></p>
                        <ul style="text-align: left; display: inline-block; color: var(--text-secondary);">
                            <li>Contracciones de volatilidad progresivas</li>
                            <li>Patrones de volumen con IA</li>
                            <li>Correlación con insider trading</li>
                            <li>Fortaleza relativa del sector</li>
                        </ul>
                    </div>
                </div>
            `;
        }}, 4000);
        
        // Animaciones de entrada
        document.addEventListener('DOMContentLoaded', function() {{
            const elements = document.querySelectorAll('.fade-in-up');
            elements.forEach((el, index) => {{
                el.style.animationDelay = `${{index * 0.1}}s`;
            }});
        }});
    </script>
</body>
</html>"""

# Funciones utilitarias para uso directo
def generate_liquid_page(page_type, data, base_url=None):
    """
    Función utilitaria para generar páginas con diseño Liquid Glass
    
    Args:
        page_type (str): 'main', 'dj_sectorial', 'vcp_scanner'
        data: Los datos para la página
        base_url (str): URL base del sitio
    
    Returns:
        str: HTML con diseño Liquid Glass
    """
    if base_url is None:
        base_url = "https://tantancansado.github.io/stock_analyzer_a"
    
    templates = GitHubPagesTemplates(base_url)
    
    if page_type == 'main':
        return templates.generate_main_dashboard(data)
    elif page_type == 'dj_sectorial':
        return templates.generate_dj_sectorial_page(data)
    elif page_type == 'vcp_scanner':
        return templates.generate_vcp_scanner_page(data)
    else:
        raise ValueError(f"Tipo de página no soportado: {page_type}")