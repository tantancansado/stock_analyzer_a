def setup_sistema_historial():
    """
    Script para configurar el sistema de historial
    """
    print("🔧 CONFIGURANDO SISTEMA DE HISTORIAL")
    print("=" * 50)
    
    # 1. Crear estructura de directorios
    print("📁 Creando estructura de directorios...")
    from github_pages_historial import GitHubPagesHistoricalUploader
    uploader = GitHubPagesHistoricalUploader()
    print("✅ Directorios creados")
    
    # 2. Migrar reportes existentes
    print("\n🔄 Migrando reportes existentes...")
    from github_pages_historial import migrar_reportes_existentes
    migrated = migrar_reportes_existentes("reports", uploader)
    print(f"✅ {migrated} reportes migrados")
    
    # 3. Generar páginas iniciales
    print("\n🌐 Generando páginas iniciales...")
    uploader.generate_main_index()
    uploader.generate_trends_analysis()
    uploader.generate_period_summaries()
    print("✅ Páginas generadas")
    
    # 4. Generar análisis cruzado si hay datos
    print("\n🔍 Generando análisis cruzado inicial...")
    try:
        cross_file = uploader.generate_cross_analysis_report(30)
        print(f"✅ Análisis cruzado: {cross_file}")
    except:
        print("⚠️ No hay suficientes datos para análisis cruzado")
    
    print(f"\n🎉 CONFIGURACIÓN COMPLETADA")
    print(f"📁 Directorio base: {uploader.repo_path}")
    print(f"🌐 Página principal: {uploader.index_file}")
    print(f"🔍 Análisis cruzado: cross_analysis.html")
    print(f"📈 Tendencias: trends.html")
    
    print(f"\n📋 PRÓXIMOS PASOS:")
    print(f"1. Ejecutar análisis con: python main.py (opción 1)")
    print(f"2. Revisar historial en navegador abriendo index.html")
    print(f"3. Configurar GitHub Pages real si es necesario")
    
if __name__ == "__main__":
    setup_sistema_historial()