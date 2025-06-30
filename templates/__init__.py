"""
Templates para el Sistema Trading Unificado
Módulo de plantillas HTML/CSS separadas de la lógica de negocio
Incluye diseño Liquid Glass para GitHub Pages
"""

from .html_generator import HTMLGenerator, generate_html_report
from .github_pages_templates import GitHubPagesTemplates, generate_liquid_page

__all__ = [
    'HTMLGenerator', 
    'generate_html_report',
    'GitHubPagesTemplates',
    'generate_liquid_page'
]
__version__ = '2.0.0'