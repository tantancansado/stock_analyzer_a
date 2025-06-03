from github_pages_uploader import GitHubPagesUploader

uploader = GitHubPagesUploader()
uploader.update_index_with_new_report(
    'insider_report_20250603_113953.html',
    'Reporte Completo Insider Trading - 2025-06-03 11:39',
    'Análisis completo con gráficos interactivos de FinViz y 61 oportunidades detectadas'
)
print('✅ Reporte completo agregado al índice')
