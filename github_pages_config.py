GITHUB_PAGES_CONFIG = {
    # Configuración del repositorio para GitHub Pages
    'repo_path': 'github-pages-reports',
    'enable_cross_analysis': True,
    'cross_analysis_days': 30,
    'enable_trends_analysis': True,
    'enable_period_summaries': True,
    
    # Configuración de análisis
    'min_appearances_for_trend': 2,
    'high_confidence_threshold': 60,
    'medium_confidence_threshold': 30,
    
    # Configuración de archivos
    'keep_local_files': True,
    'compress_old_reports': False,
    'max_reports_in_memory': 100,
    
    # URLs base (si se usa GitHub Pages real)
    'github_pages_base_url': '',  # Ej: 'https://tuusuario.github.io/insider-trading/'
    'enable_real_github_pages': False,
    
    # Configuraciones de notificación
    'telegram_include_trends_link': True,
    'telegram_include_cross_analysis': True,
    'telegram_max_top_opportunities': 5
}
