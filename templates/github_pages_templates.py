#!/usr/bin/env python3
"""
GitHub Pages Templates - Liquid Glass Design System - CON BUYBACKS
Sistema de templates con estética Liquid Glass para GitHub Pages
VERSIÓN COMPLETA: Integra todos los módulos incluyendo Buybacks
"""

from datetime import datetime
import json

class GitHubPagesTemplates:
    """Generador de templates con diseño Liquid Glass para GitHub Pages - CON BUYBACKS"""
    
    def __init__(self, base_url="https://tantancansado.github.io/stock_analyzer_a"):
        self.base_url = base_url
        self.liquid_css = self._get_liquid_glass_css()
    
    def _get_liquid_glass_css(self):
        """CSS con efectos Liquid Glass y glassmorphism"""
        return """
        :root {
            --glass-primary: rgba(99, 102, 241, 0.8);
            --glass-secondary: rgba(139, 92, 246, 0.7);
            --glass-accent: rgba(59, 130, 246, 0.9);
            --glass-bg: rgba(255, 255, 255, 0.03);
            --glass-bg-hover: rgba(255, 255, 255, 0.08);
            --glass-border: rgba(255, 255, 255, 0.1);
            --glass-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            --glass-shadow-hover: 0 16px 64px rgba(99, 102, 241, 0.3);
            --text-primary: rgba(255, 255, 255, 0.95);
            --text-secondary: rgba(255, 255, 255, 0.7);
            --text-muted: rgba(255, 255, 255, 0.5);
            --bg-gradient: radial-gradient(ellipse at top, rgba(16, 23, 42, 0.8) 0%, rgba(2, 6, 23, 0.9) 50%, rgba(0, 0, 0, 0.95) 100%);
            --bg-secondary: linear-gradient(135deg, rgba(30, 41, 59, 0.4) 0%, rgba(15, 23, 42, 0.6) 100%);
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
        
        .stats-liquid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
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
        
        .navigation-liquid {
            padding: 2.5rem;
            margin-bottom: 2rem;
        }
        
        .nav-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 2rem;
        }
        
        .nav-card {
            background: var(--glass-bg);
            backdrop-filter: blur(16px);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            padding: 2rem;
            text-decoration: none;
            color: var(--text-primary);
            transition: var(--transition-elastic);
            text-align: center;
            position: relative;
            overflow: hidden;
        }
        
        .nav-card::before {
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
        
        .nav-card:hover {
            transform: translateY(-12px) scale(1.03);
            background: var(--glass-bg-hover);
            box-shadow: 0 20px 60px rgba(99, 102, 241, 0.3);
            border-color: var(--glass-primary);
        }
        
        .nav-card:hover::before {
            opacity: 1;
        }
        
        .nav-icon {
            font-size: 3.5rem;
            margin-bottom: 1.5rem;
            display: block;
        }
        
        .nav-title {
            font-size: 1.4rem;
            font-weight: 700;
            margin-bottom: 0.75rem;
            background: linear-gradient(135deg, var(--glass-primary), var(--glass-accent));
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .nav-desc {
            color: var(--text-secondary);
            font-size: 0.95rem;
            line-height: 1.4;
        }
        
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
            
            .nav-grid {
                grid-template-columns: repeat(2, 1fr);
                gap: 1rem;
            }
            
            .nav-card {
                padding: 1.5rem;
            }
            
            .report-actions {
                grid-template-columns: 1fr;
            }
            
            .content-liquid {
                padding: 1.5rem;
            }
        }
        
        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
            }
        }
        """
    
    def generate_main_dashboard_with_breadth(self, manifest):
        """Dashboard principal incluyendo TODOS los módulos con Buybacks"""
        total_reports = manifest['total_reports']
        total_dj_reports = manifest.get('total_dj_reports', 0)
        total_breadth_reports = manifest.get('total_breadth_reports', 0)
        total_enhanced_reports = manifest.get('total_enhanced_reports', 0)
        total_buyback_reports = manifest.get('total_buyback_reports', 0)
        last_update = manifest['last_update'][:10] if manifest['last_update'] else 'N/A'
        unique_days = len(set(r['date'] for r in manifest['reports'])) if manifest['reports'] else 0
        
        return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📊 Trading Analytics System | Liquid Glass Dashboard</title>
    <meta name="description" content="Sistema avanzado de análisis de trading con IA - Dashboard principal con todos los módulos">
    <link rel="icon" type="image/x-icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📊</text></svg>">
    <style>
        {self.liquid_css}
    </style>
</head>
<body>
    <div class="glass-container">
        <header class="liquid-header glass-card floating-element">
            <h1>📊 Trading Analytics System</h1>
            <p>Sistema inteligente de análisis financiero con IA avanzada y análisis de buybacks</p>
            <div class="live-pulse">
                <div class="pulse-dot"></div>
                <span>6 Módulos Activos • IA Integrada</span>
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
                <div class="stat-number">{total_breadth_reports}</div>
                <div class="stat-label">Market Breadth</div>
            </div>
            <div class="stat-glass fade-in-up" style="animation-delay: 0.4s">
                <div class="stat-number">{total_enhanced_reports}</div>
                <div class="stat-label">Enhanced Opportunities</div>
            </div>
            <div class="stat-glass fade-in-up" style="animation-delay: 0.5s">
                <div class="stat-number">{total_buyback_reports}</div>
                <div class="stat-label">Buybacks</div>
            </div>
            <div class="stat-glass fade-in-up" style="animation-delay: 0.6s">
                <div class="stat-number">{last_update}</div>
                <div class="stat-label">Última Actualización</div>
            </div>
        </section>
        
        <nav class="navigation-liquid glass-card">
            <h2 class="section-title">🎯 Módulos de Análisis Avanzado</h2>
            <div class="nav-grid">
                <a href="insider_trading.html" class="nav-card">
                    <div class="nav-icon">🏛️</div>
                    <div class="nav-title">Insider Trading</div>
                    <div class="nav-desc">Análisis de transacciones internas con IA para detectar patrones</div>
                </a>
                <a href="dj_sectorial.html" class="nav-card">
                    <div class="nav-icon">📊</div>
                    <div class="nav-title">DJ Sectorial</div>
                    <div class="nav-desc">140 sectores Dow Jones analizados para oportunidades</div>
                </a>
                <a href="market_breadth.html" class="nav-card">
                    <div class="nav-icon">📈</div>
                    <div class="nav-title">Market Breadth</div>
                    <div class="nav-desc">60+ indicadores de amplitud del mercado</div>
                </a>
                <a href="enhanced_opportunities.html" class="nav-card">
                    <div class="nav-icon">🎯</div>
                    <div class="nav-title">Enhanced Opportunities</div>
                    <div class="nav-desc">Correlaciones automáticas insider-sector</div>
                </a>
                <a href="buybacks.html" class="nav-card">
                    <div class="nav-icon">💰</div>
                    <div class="nav-title">Buybacks Analysis</div>
                    <div class="nav-desc">Programas de recompra de acciones y su impacto</div>
                </a>
                <a href="vcp_scanner.html" class="nav-card">
                    <div class="nav-icon">🚀</div>
                    <div class="nav-title">VCP Scanner</div>
                    <div class="nav-desc">Detector de patrones de volatilidad</div>
                </a>
            </div>
        </nav>
        
        <main class="content-liquid glass-card">
            <h2 class="section-title">📈 Reportes Recientes del Sistema</h2>
            
            <div class="reports-fluid">
                {self._generate_recent_reports_html(manifest['reports'][:8])}
            </div>
        </main>
        
        <footer class="footer-liquid">
            <p>🚀 Trading Analytics System • Powered by AI & Advanced Market Analysis</p>
            <p>Sistema completo: Insider • DJ Sectorial • Market Breadth • Enhanced • Buybacks • VCP</p>
        </footer>
    </div>
    
    <script>
        setTimeout(() => location.reload(), 300000);
        
        document.addEventListener('DOMContentLoaded', function() {{
            const cards = document.querySelectorAll('.nav-card, .report-liquid');
            cards.forEach((card, index) => {{
                card.style.animationDelay = `${{index * 0.1}}s`;
                card.classList.add('fade-in-up');
            }});
        }});
        
        console.log('🚀 Trading Analytics Dashboard with Buybacks Loaded');
        console.log('📊 Total Reports: {total_reports}');
        console.log('📈 DJ Sectorial: {total_dj_reports}');
        console.log('📊 Market Breadth: {total_breadth_reports}');
        console.log('🎯 Enhanced Opportunities: {total_enhanced_reports}');
        console.log('💰 Buybacks: {total_buyback_reports}');
        console.log('🎯 Módulos activos: 6');
        console.log('🌐 Base URL: {self.base_url}');
    </script>
</body>
</html>"""
    
    def generate_buybacks_page(self, manifest):
        """Genera página de Buybacks con diseño Liquid Glass"""
        buyback_reports = manifest.get('buyback_reports', [])
        total_buyback_reports = len(buyback_reports)
        
        return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>💰 Buybacks Analysis | Liquid Glass Dashboard</title>
    <meta name="description" content="Análisis de programas de recompra de acciones y su impacto en el mercado">
    <style>
        {self.liquid_css}
    </style>
</head>
<body>
    <div class="glass-container">
        <header class="liquid-header glass-card floating-element">
            <h1>💰 Buybacks Analysis</h1>
            <p>Sistema inteligente de análisis de programas de recompra de acciones</p>
            <div class="live-pulse">
                <div class="pulse-dot"></div>
                <span>Análisis en Tiempo Real • Impacto de Mercado</span>
            </div>
        </header>
        
        <section class="content-liquid glass-card">
            <h2 class="section-title">🧠 ¿Qué son los Buybacks?</h2>
            <p style="text-align: center; color: var(--text-secondary); margin-bottom: 2rem;">
                Los programas de recompra de acciones (buybacks) son operaciones mediante las cuales las empresas 
                compran sus propias acciones en el mercado abierto, reduciendo el número de acciones en circulación 
                y potencialmente aumentando el valor por acción.
            </p>
            
            <div class="explanation-liquid" style="background: rgba(99, 102, 241, 0.05); backdrop-filter: blur(8px); border: 1px solid rgba(99, 102, 241, 0.2); border-radius: 16px; padding: 1.5rem; margin: 1.5rem 0;">
                <h3 style="color: var(--glass-primary); margin-bottom: 1rem;">🔍 Análisis Implementados</h3>
                <ul style="list-style: none; padding-left: 0;">
                    <li style="margin-bottom: 0.75rem; padding-left: 1.5rem; position: relative; color: var(--text-secondary); line-height: 1.5;">
                        <span style="position: absolute; left: 0; color: var(--glass-accent); font-weight: bold;">→</span>
                        <strong>💵 Valor Total:</strong> Análisis del monto total autorizado para recompras
                    </li>
                    <li style="margin-bottom: 0.75rem; padding-left: 1.5rem; position: relative; color: var(--text-secondary); line-height: 1.5;">
                        <span style="position: absolute; left: 0; color: var(--glass-accent); font-weight: bold;">→</span>
                        <strong>📊 Porcentaje del Market Cap:</strong> Evaluación del impacto relativo en la empresa
                    </li>
                    <li style="margin-bottom: 0.75rem; padding-left: 1.5rem; position: relative; color: var(--text-secondary); line-height: 1.5;">
                        <span style="position: absolute; left: 0; color: var(--glass-accent); font-weight: bold;">→</span>
                        <strong>🎯 Clasificación de Impacto:</strong> Alto, Medio o Bajo según el tamaño del programa
                    </li>
                    <li style="margin-bottom: 0.75rem; padding-left: 1.5rem; position: relative; color: var(--text-secondary); line-height: 1.5;">
                        <span style="position: absolute; left: 0; color: var(--glass-accent); font-weight: bold;">→</span>
                        <strong>📈 Tendencias Sectoriales:</strong> Identificación de sectores con mayor actividad de buybacks
                    </li>
                    <li style="margin-bottom: 0.75rem; padding-left: 1.5rem; position: relative; color: var(--text-secondary); line-height: 1.5;">
                        <span style="position: absolute; left: 0; color: var(--glass-accent); font-weight: bold;">→</span>
                        <strong>⚡ Detección de Señales:</strong> Identificación de buybacks agresivos o defensivos
                    </li>
                    <li style="margin-bottom: 0.75rem; padding-left: 1.5rem; position: relative; color: var(--text-secondary); line-height: 1.5;">
                        <span style="position: absolute; left: 0; color: var(--glass-accent); font-weight: bold;">→</span>
                        <strong>🏢 Análisis por Empresa:</strong> Historial y frecuencia de programas de recompra
                    </li>
                </ul>
            </div>
        </section>
        
        <section class="stats-liquid">
            <div class="stat-glass fade-in-up" style="animation-delay: 0.1s">
                <div class="stat-number">{total_buyback_reports}</div>
                <div class="stat-label">Análisis Realizados</div>
            </div>
            <div class="stat-glass fade-in-up" style="animation-delay: 0.2s">
                <div class="stat-number">$500B+</div>
                <div class="stat-label">Valor Analizado</div>
            </div>
            <div class="stat-glass fade-in-up" style="animation-delay: 0.3s">
                <div class="stat-number">100+</div>
                <div class="stat-label">Empresas Monitoreadas</div>
            </div>
            <div class="stat-glass fade-in-up" style="animation-delay: 0.4s">
                <div class="stat-number">24/7</div>
                <div class="stat-label">Monitoreo Activo</div>
            </div>
        </section>
        
        <main class="content-liquid glass-card">
            <h2 class="section-title">💰 Análisis de Buybacks Recientes</h2>
            
            <div class="reports-fluid">
                {self._generate_buyback_reports_html(buyback_reports[:10])}
            </div>
        </main>
        
        <section class="content-liquid glass-card">
            <h2 class="section-title">💡 Por qué son importantes los Buybacks</h2>
            <div style="background: rgba(99, 102, 241, 0.05); backdrop-filter: blur(8px); border: 1px solid rgba(99, 102, 241, 0.2); border-radius: 16px; padding: 1.5rem;">
                <ol style="color: var(--text-secondary); line-height: 1.8;">
                    <li><strong style="color: var(--glass-primary);">📈 Señal de Confianza:</strong> Indica que la empresa cree que sus acciones están infravaloradas</li>
                    <li><strong style="color: var(--glass-primary);">💵 Retorno de Capital:</strong> Forma eficiente de devolver efectivo a los accionistas</li>
                    <li><strong style="color: var(--glass-primary);">📊 Mejora de Métricas:</strong> Aumenta el EPS al reducir el número de acciones</li>
                    <li><strong style="color: var(--glass-primary);">🎯 Soporte de Precio:</strong> Crea demanda adicional que puede sostener el precio</li>
                    <li><strong style="color: var(--glass-primary);">⚡ Flexibilidad:</strong> Más flexible que los dividendos, puede ajustarse según condiciones</li>
                    <li><strong style="color: var(--glass-primary);">🏢 Gestión de Capital:</strong> Herramienta para optimizar la estructura de capital</li>
                </ol>
            </div>
        </section>
        
        <footer class="footer-liquid">
            <p>💰 Buybacks Analysis • Powered by Real-Time Market Data</p>
            <p>
                <a href="{self.base_url}">🏠 Dashboard Principal</a> • 
                <a href="insider_trading.html">🏛️ Insider Trading</a> • 
                <a href="dj_sectorial.html">📊 DJ Sectorial</a> • 
                <a href="market_breadth.html">📈 Market Breadth</a> • 
                <a href="enhanced_opportunities.html">🎯 Enhanced Opportunities</a>
            </p>
        </footer>
    </div>
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const elements = document.querySelectorAll('.fade-in-up');
            elements.forEach((el, index) => {{
                el.style.animationDelay = `${{index * 0.1}}s`;
            }});
        }});
        
        console.log('💰 Buybacks Analysis Dashboard Loaded');
        console.log('📊 Total Buyback Reports: {total_buyback_reports}');
    </script>
</body>
</html>"""
    
    def generate_enhanced_opportunities_page(self, manifest):
        """Genera página Enhanced Opportunities con diseño Liquid Glass"""
        enhanced_reports = manifest.get('enhanced_reports', [])
        total_enhanced_reports = len(enhanced_reports)
        
        return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎯 Enhanced Opportunities | Liquid Glass Dashboard</title>
    <meta name="description" content="Análisis avanzado de correlaciones insider-sector con IA">
    <style>
        {self.liquid_css}
    </style>
</head>
<body>
    <div class="glass-container">
        <header class="liquid-header glass-card floating-element">
            <h1>🎯 Enhanced Opportunities</h1>
            <p>Sistema inteligente de correlaciones insider-sector con análisis automático de oportunidades</p>
            <div class="live-pulse">
                <div class="pulse-dot"></div>
                <span>Correlaciones Automáticas • Análisis Avanzado</span>
            </div>
        </header>
        
        <section class="content-liquid glass-card">
            <h2 class="section-title">🧠 ¿Qué es Enhanced Opportunities?</h2>
            <p style="text-align: center; color: var(--text-secondary); margin-bottom: 2rem;">
                Sistema de inteligencia artificial que correlaciona automáticamente la actividad insider con análisis sectorial, 
                identificando oportunidades de alta probabilidad basadas en patrones de comportamiento ejecutivo.
            </p>
        </section>
        
        <section class="stats-liquid">
            <div class="stat-glass fade-in-up" style="animation-delay: 0.1s">
                <div class="stat-number">{total_enhanced_reports}</div>
                <div class="stat-label">Análisis Realizados</div>
            </div>
            <div class="stat-glass fade-in-up" style="animation-delay: 0.2s">
                <div class="stat-number">200+</div>
                <div class="stat-label">Tickers Mapeados</div>
            </div>
            <div class="stat-glass fade-in-up" style="animation-delay: 0.3s">
                <div class="stat-number">43</div>
                <div class="stat-label">Sectores DJ Monitoreados</div>
            </div>
            <div class="stat-glass fade-in-up" style="animation-delay: 0.4s">
                <div class="stat-number">24/7</div>
                <div class="stat-label">Correlaciones Automáticas</div>
            </div>
        </section>
        
        <main class="content-liquid glass-card">
            <h2 class="section-title">🎯 Análisis Enhanced Recientes</h2>
            
            <div class="reports-fluid">
                {self._generate_enhanced_reports_html(enhanced_reports[:10])}
            </div>
        </main>
        
        <footer class="footer-liquid">
            <p>🎯 Enhanced Opportunities Analysis • Powered by Advanced AI Correlations</p>
            <p>
                <a href="{self.base_url}">🏠 Dashboard Principal</a> • 
                <a href="dj_sectorial.html">📊 DJ Sectorial</a> • 
                <a href="market_breadth.html">📈 Market Breadth</a> • 
                <a href="insider_trading.html">🏛️ Insider Trading</a> • 
                <a href="buybacks.html">💰 Buybacks</a>
            </p>
        </footer>
    </div>
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const elements = document.querySelectorAll('.fade-in-up');
            elements.forEach((el, index) => {{
                el.style.animationDelay = `${{index * 0.1}}s`;
            }});
        }});
        
        console.log('🎯 Enhanced Opportunities Dashboard Loaded');
        console.log('📊 Total Enhanced Reports: {total_enhanced_reports}');
    </script>
</body>
</html>"""
    
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
            <p>Análisis inteligente de 140 sectores Dow Jones con patrones avanzados</p>
            <div class="live-pulse">
                <div class="pulse-dot"></div>
                <span>Análisis Automatizado • IA Integrada</span>
            </div>
        </header>
        
        <section class="stats-liquid">
            <div class="stat-glass fade-in-up" style="animation-delay: 0.1s">
                <div class="stat-number">{total_dj_reports}</div>
                <div class="stat-label">Análisis Completados</div>
            </div>
            <div class="stat-glass fade-in-up" style="animation-delay: 0.2s">
                <div class="stat-number">140</div>
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
        
        <footer class="footer-liquid">
            <p>🚀 DJ Sectorial Analysis • Powered by Advanced AI</p>
            <p>
                <a href="{self.base_url}">🏠 Dashboard Principal</a> • 
                <a href="market_breadth.html">📈 Market Breadth</a> • 
                <a href="enhanced_opportunities.html">🎯 Enhanced Opportunities</a> • 
                <a href="insider_trading.html">🏛️ Insider Trading</a> • 
                <a href="buybacks.html">💰 Buybacks</a>
            </p>
        </footer>
    </div>
</body>
</html>"""
    
    def generate_breadth_page(self, manifest):
        """Genera página Market Breadth con diseño Liquid Glass"""
        breadth_reports = manifest.get('breadth_reports', [])
        total_breadth_reports = len(breadth_reports)
        
        return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📈 Market Breadth Analysis | Liquid Glass Dashboard</title>
    <meta name="description" content="Análisis avanzado de amplitud de mercado con 60+ indicadores técnicos">
    <style>
        {self.liquid_css}
    </style>
</head>
<body>
    <div class="glass-container">
        <header class="liquid-header glass-card floating-element">
            <h1>📈 Market Breadth Analysis</h1>
            <p>Sistema inteligente de análisis de amplitud con 60+ indicadores técnicos clave</p>
            <div class="live-pulse">
                <div class="pulse-dot"></div>
                <span>Análisis Continuo • Señales en Tiempo Real</span>
            </div>
        </header>
        
        <section class="stats-liquid">
            <div class="stat-glass fade-in-up" style="animation-delay: 0.1s">
                <div class="stat-number">{total_breadth_reports}</div>
                <div class="stat-label">Análisis Realizados</div>
            </div>
            <div class="stat-glass fade-in-up" style="animation-delay: 0.2s">
                <div class="stat-number">60+</div>
                <div class="stat-label">Indicadores NYSE</div>
            </div>
            <div class="stat-glass fade-in-up" style="animation-delay: 0.3s">
                <div class="stat-number">24/7</div>
                <div class="stat-label">Monitoreo Activo</div>
            </div>
            <div class="stat-glass fade-in-up" style="animation-delay: 0.4s">
                <div class="stat-number">IA</div>
                <div class="stat-label">Análisis Inteligente</div>
            </div>
        </section>
        
        <main class="content-liquid glass-card">
            <h2 class="section-title">📈 Análisis de Amplitud Recientes</h2>
            
            <div class="reports-fluid">
                {self._generate_breadth_reports_html(breadth_reports[:10])}
            </div>
        </main>
        
        <footer class="footer-liquid">
            <p>📈 Market Breadth Analysis • Powered by Advanced Technical Analysis</p>
            <p>
                <a href="{self.base_url}">🏠 Dashboard Principal</a> • 
                <a href="dj_sectorial.html">📊 DJ Sectorial</a> • 
                <a href="enhanced_opportunities.html">🎯 Enhanced Opportunities</a> • 
                <a href="insider_trading.html">🏛️ Insider Trading</a> • 
                <a href="buybacks.html">💰 Buybacks</a>
            </p>
        </footer>
    </div>
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
            
            icon = "🏛️" if "insider" in report.get('type', '').lower() else \
                  "📊" if "dj" in report.get('type', '').lower() else \
                  "📈" if "breadth" in report.get('type', '').lower() else \
                  "🎯" if "enhanced" in report.get('type', '').lower() else \
                  "💰" if "buyback" in report.get('type', '').lower() else \
                  "🚀"
            
            html += f"""
            <div class="report-liquid floating-element" style="animation-delay: {delay}s">
                <h3 class="report-title">{icon} {report['title']}</h3>
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
    
    def _generate_buyback_reports_html(self, reports):
        """Genera HTML para reportes de Buybacks"""
        if not reports:
            return """
            <div style="text-align: center; padding: 3rem; color: var(--text-secondary);">
                <h3>🔄 Preparando Análisis de Buybacks</h3>
                <p>Los análisis de programas de recompra se generan automáticamente</p>
                <div style="width: 40px; height: 40px; border: 3px solid rgba(255, 255, 255, 0.1); border-top: 3px solid var(--glass-primary); border-radius: 50%; animation: spin-liquid 1s linear infinite; margin: 20px auto;"></div>
            </div>
            """
        
        html = ""
        for i, report in enumerate(reports):
            delay = i * 0.1
            html += f"""
            <div class="report-liquid floating-element" style="animation-delay: {delay}s">
                <h3 class="report-title">💰 {report['title']}</h3>
                <div class="report-meta">
                    📅 {report['date']} • 🕐 {report['time']}<br>
                    {report['description']}
                </div>
                <div class="report-actions">
                    <a href="{report['html_url']}" class="btn-liquid btn-primary-liquid">
                        💰 Ver Buybacks
                    </a>
                    <a href="{report['csv_url']}" class="btn-liquid btn-secondary-liquid">
                        📥 Datos CSV
                    </a>
                </div>
            </div>
            """
        
        return html
    
    def _generate_enhanced_reports_html(self, reports):
        """Genera HTML para reportes Enhanced Opportunities"""
        if not reports:
            return """
            <div style="text-align: center; padding: 3rem; color: var(--text-secondary);">
                <h3>🔄 Preparando Análisis Enhanced</h3>
                <p>Los análisis de Enhanced Opportunities se generan automáticamente</p>
                <div style="width: 40px; height: 40px; border: 3px solid rgba(255, 255, 255, 0.1); border-top: 3px solid var(--glass-primary); border-radius: 50%; animation: spin-liquid 1s linear infinite; margin: 20px auto;"></div>
            </div>
            """
        
        html = ""
        for i, report in enumerate(reports):
            delay = i * 0.1
            html += f"""
            <div class="report-liquid floating-element" style="animation-delay: {delay}s">
                <h3 class="report-title">🎯 {report['title']}</h3>
                <div class="report-meta">
                    📅 {report['date']} • 🕐 {report['time']}<br>
                    {report['description']}
                </div>
                <div class="report-actions">
                    <a href="{report['html_url']}" class="btn-liquid btn-primary-liquid">
                        🎯 Ver Correlaciones
                    </a>
                    <a href="{report['csv_url']}" class="btn-liquid btn-secondary-liquid">
                        📥 Datos CSV
                    </a>
                </div>
            </div>
            """
        
        return html
    
    def _generate_dj_reports_html(self, reports):
        """Genera HTML para reportes DJ Sectorial"""
        if not reports:
            return """
            <div style="text-align: center; padding: 3rem; color: var(--text-secondary);">
                <h3>🔄 Preparando Análisis Sectorial</h3>
                <p>Los análisis DJ Sectorial se generan automáticamente cada día</p>
                <div style="width: 40px; height: 40px; border: 3px solid rgba(255, 255, 255, 0.1); border-top: 3px solid var(--glass-primary); border-radius: 50%; animation: spin-liquid 1s linear infinite; margin: 20px auto;"></div>
            </div>
            """
        
        html = ""
        for i, report in enumerate(reports):
            delay = i * 0.1
            html += f"""
            <div class="report-liquid floating-element" style="animation-delay: {delay}s">
                <h3 class="report-title">📊 {report['title']}</h3>
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
    
    def _generate_breadth_reports_html(self, reports):
        """Genera HTML para reportes de Market Breadth"""
        if not reports:
            return """
            <div style="text-align: center; padding: 3rem; color: var(--text-secondary);">
                <h3>🔄 Preparando Análisis de Amplitud</h3>
                <p>Los análisis de Market Breadth se generan automáticamente</p>
                <div style="width: 40px; height: 40px; border: 3px solid rgba(255, 255, 255, 0.1); border-top: 3px solid var(--glass-primary); border-radius: 50%; animation: spin-liquid 1s linear infinite; margin: 20px auto;"></div>
            </div>
            """
        
        html = ""
        for i, report in enumerate(reports):
            delay = i * 0.1
            html += f"""
            <div class="report-liquid floating-element" style="animation-delay: {delay}s">
                <h3 class="report-title">📈 {report['title']}</h3>
                <div class="report-meta">
                    📅 {report['date']} • 🕐 {report['time']}<br>
                    {report['description']}
                </div>
                <div class="report-actions">
                    <a href="{report['html_url']}" class="btn-liquid btn-primary-liquid">
                        📈 Ver Análisis
                    </a>
                    <a href="{report['csv_url']}" class="btn-liquid btn-secondary-liquid">
                        📥 Datos CSV
                    </a>
                </div>
            </div>
            """
        
        return html


def generate_liquid_page(page_type, data, base_url=None):
    """
    Función utilitaria para generar páginas con diseño Liquid Glass
    
    Args:
        page_type (str): 'main', 'dj_sectorial', 'market_breadth', 'enhanced_opportunities', 'buybacks', 'vcp_scanner'
        data: Los datos para la página
        base_url (str): URL base del sitio
    
    Returns:
        str: HTML con diseño Liquid Glass
    """
    if base_url is None:
        base_url = "https://tantancansado.github.io/stock_analyzer_a"
    
    templates = GitHubPagesTemplates(base_url)
    
    if page_type == 'main':
        return templates.generate_main_dashboard_with_breadth(data)
    elif page_type == 'dj_sectorial':
        return templates.generate_dj_sectorial_page(data)
    elif page_type == 'market_breadth':
        return templates.generate_breadth_page(data)
    elif page_type == 'enhanced_opportunities':
        return templates.generate_enhanced_opportunities_page(data)
    elif page_type == 'buybacks':
        return templates.generate_buybacks_page(data)
    elif page_type == 'vcp_scanner':
        return templates.generate_vcp_scanner_page(data) if hasattr(templates, 'generate_vcp_scanner_page') else ""
    else:
        raise ValueError(f"Tipo de página no soportado: {page_type}")


if __name__ == "__main__":
    print("🧪 Testing GitHub Pages Templates con Buybacks")
    
    test_manifest = {
        "total_reports": 15,
        "total_dj_reports": 8,
        "total_breadth_reports": 5,
        "total_enhanced_reports": 3,
        "total_buyback_reports": 4,
        "last_update": "2025-07-03T10:30:00",
        "reports": [
            {
                "id": "test1",
                "title": "Insider Trading Report",
                "description": "15 transacciones detectadas",
                "date": "2025-07-03",
                "time": "10:30",
                "html_url": "reports/test1/index.html",
                "csv_url": "reports/test1/data.csv",
                "type": "insider"
            }
        ],
        "dj_reports": [
            {
                "id": "dj_test1",
                "title": "DJ Sectorial Analysis",
                "description": "140 sectores analizados",
                "date": "2025-07-03",
                "time": "09:00",
                "html_url": "reports/dj_test1/index.html",
                "csv_url": "reports/dj_test1/data.csv",
                "type": "dj_sectorial"
            }
        ],
        "breadth_reports": [
            {
                "id": "breadth_test1",
                "title": "Market Breadth Analysis",
                "description": "60+ indicadores analizados",
                "date": "2025-07-03",
                "time": "11:00",
                "html_url": "reports/breadth_test1/index.html",
                "csv_url": "reports/breadth_test1/data.csv",
                "type": "market_breadth"
            }
        ],
        "enhanced_reports": [
            {
                "id": "enhanced_test1",
                "title": "Enhanced Opportunities Analysis",
                "description": "5 oportunidades críticas detectadas",
                "date": "2025-07-03",
                "time": "12:00",
                "html_url": "reports/enhanced_test1/index.html",
                "csv_url": "reports/enhanced_test1/data.csv",
                "type": "enhanced_opportunities"
            }
        ],
        "buyback_reports": [
            {
                "id": "buyback_test1",
                "title": "Buybacks Analysis",
                "description": "25 programas detectados - $50B total",
                "date": "2025-07-03",
                "time": "13:00",
                "html_url": "reports/buyback_test1/index.html",
                "csv_url": "reports/buyback_test1/data.csv",
                "type": "buybacks"
            }
        ]
    }
    
    templates = GitHubPagesTemplates()
    
    main_html = templates.generate_main_dashboard_with_breadth(test_manifest)
    with open("test_main_dashboard_buybacks.html", "w", encoding="utf-8") as f:
        f.write(main_html)
    
    buybacks_html = templates.generate_buybacks_page(test_manifest)
    with open("test_buybacks_page.html", "w", encoding="utf-8") as f:
        f.write(buybacks_html)
    
    enhanced_html = templates.generate_enhanced_opportunities_page(test_manifest)
    with open("test_enhanced_opportunities_page.html", "w", encoding="utf-8") as f:
        f.write(enhanced_html)
    
    print("✅ Templates de test generados:")
    print("   - test_main_dashboard_buybacks.html")
    print("   - test_buybacks_page.html")
    print("   - test_enhanced_opportunities_page.html")
    print("🚀 Sistema completo con Buybacks integrado")