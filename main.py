#!/usr/bin/env python3
"""
Script principal para ejecutar todo el análisis de insider trading
Coordina: análisis de oportunidades + gráficos + HTML + Telegram + HISTORIAL
VERSIÓN MEJORADA CON SISTEMA DE HISTORIAL COMPLETO
"""

import os
import sys
from datetime import datetime

def get_telegram_chat_id():
    """
    Obtiene el chat_id de Telegram desde config.py
    """
    try:
        from config import TELEGRAM_CHAT_ID
        return TELEGRAM_CHAT_ID
    except ImportError:
        try:
            import config
            return getattr(config, 'TELEGRAM_CHAT_ID', None)
        except:
            return None

def main():
    """
    Ejecuta el análisis completo de insider trading CON HISTORIAL
    """
    print("🚀 ANÁLISIS COMPLETO DE INSIDER TRADING CON HISTORIAL")
    print("=" * 60)
    print(f"📅 Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Verificar que existen los archivos necesarios
        csv_path = "reports/insiders_daily.csv"
        if not os.path.exists(csv_path):
            print(f"❌ Error: No se encontró {csv_path}")
            print("   Asegúrate de tener el CSV de insiders en la ubicación correcta")
            return False
        
        # Verificar configuración de Telegram
        chat_id = get_telegram_chat_id()
        if chat_id:
            print(f"✅ Telegram configurado: {chat_id}")
        else:
            print("⚠️ Telegram no configurado (chat_id no encontrado)")
        
        # Crear directorios necesarios
        os.makedirs("reports/graphs", exist_ok=True)
        
        # NUEVO: Verificar si sistema de historial está disponible
        historial_disponible = False
        try:
            from github_pages_historial import GitHubPagesHistoricalUploader
            historial_disponible = True
            print("✅ Sistema de historial disponible")
        except ImportError:
            print("⚠️ Sistema de historial no disponible - usando método tradicional")
        
        # EJECUTAR ANÁLISIS INTEGRADO CON O SIN HISTORIAL
        if historial_disponible:
            print("🎯 Ejecutando análisis integrado CON HISTORIAL...")
            
            from insiders.insider_tracker import generar_reporte_completo_integrado_con_historial
            result = generar_reporte_completo_integrado_con_historial()
        else:
            print("🎯 Ejecutando análisis integrado tradicional...")
            
            from insiders.insider_tracker import generar_reporte_completo_integrado
            result = generar_reporte_completo_integrado()
        
        if result:
            print(f"✅ Análisis integrado completado")
            
            # Mostrar resultados
            if result.get('csv_opportunities'):
                print(f"📄 CSV Oportunidades: {result['csv_opportunities']}")
            if result.get('html_opportunities'):
                print(f"🌐 HTML Oportunidades: {result['html_opportunities']}")
            if result.get('html_charts'):
                print(f"📊 HTML Gráficos: {result['html_charts']}")
            if result.get('bundle'):
                print(f"📦 Bundle completo: {result['bundle']}")
            
            # NUEVO: Mostrar información de historial si está disponible
            if result.get('github_pages'):
                print(f"\n🌐 ENLACES HISTÓRICOS:")
                print(f"📊 Reporte actual: {result['github_pages']['file_url']}")
                print(f"🏠 Historial completo: {result['github_pages']['index_url']}")
                print(f"🔍 Análisis cruzado: cross_analysis.html")
                print(f"📈 Tendencias: trends.html")
                
            if result.get('cross_analysis'):
                print(f"🔍 Análisis cruzado: {result['cross_analysis']}")
                
            # Variables para el resumen final
            csv_opportunities = result.get('csv_opportunities')
            html_opportunities = result.get('html_opportunities')
            html_charts = result.get('html_charts')
            bundle_path = result.get('bundle')
            github_pages = result.get('github_pages')
            
        else:
            print("⚠️ El análisis integrado no se completó correctamente")
            csv_opportunities = None
            html_opportunities = None
            html_charts = None
            bundle_path = None
            github_pages = None
        
        print("\n" + "=" * 60)
        print("🎉 ¡ANÁLISIS COMPLETADO!")
        print("=" * 60)
        
        if csv_opportunities:
            print(f"📄 Reporte de oportunidades: {csv_opportunities}")
        if html_opportunities:
            print(f"🌐 HTML oportunidades: {html_opportunities}")
        if html_charts:
            print(f"📊 HTML gráficos: {html_charts}")
        if bundle_path:
            print(f"📦 Bundle completo: {bundle_path}")
        if github_pages:
            print(f"🌐 GitHub Pages: {github_pages.get('file_url', 'N/A')}")
            
        print(f"📅 Finalizado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Error de importación: {e}")
        print("   Verifica que todos los módulos estén disponibles")
        return False
    
    except Exception as e:
        print(f"❌ Error durante la ejecución: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_individual_ticker():
    """
    Función para probar con un ticker individual
    """
    ticker = input("🎯 Introduce un ticker para probar (ej: AAPL): ").strip().upper()
    
    if not ticker:
        print("❌ Ticker no válido")
        return
    
    # Obtener chat_id
    chat_id = get_telegram_chat_id()
    
    try:
        from run_daily import run_daily
        
        print(f"📊 Generando gráficos para {ticker}...")
        daily_path, weekly_path = run_daily(ticker)
        
        if daily_path and weekly_path:
            print(f"✅ Gráficos generados:")
            print(f"   📈 Diario: {daily_path}")
            print(f"   📊 Semanal: {weekly_path}")
            
            # Enviar por Telegram si está disponible
            if chat_id:
                try:
                    from alerts.telegram_utils import send_message, send_image_telegram
                    send_message(chat_id, f"🎯 Gráficos generados para {ticker}")
                    send_image_telegram(chat_id, daily_path, f"📈 {ticker} - Diario")
                    send_image_telegram(chat_id, weekly_path, f"📊 {ticker} - Semanal")
                    print("✅ Enviado por Telegram")
                except Exception as e:
                    print(f"⚠️ Error enviando por Telegram: {e}")
            else:
                print("⚠️ Telegram no configurado")
        else:
            print("❌ No se pudieron generar los gráficos")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def solo_analisis_oportunidades():
    """
    Solo ejecuta el análisis de oportunidades de insider trading
    """
    try:
        from insiders.insider_tracker import scrape_openinsider, generar_reporte_html_oportunidades, enviar_reporte_telegram
        
        print("🎯 Ejecutando solo análisis de oportunidades...")
        csv_path = scrape_openinsider()
        
        if csv_path:
            html_path = generar_reporte_html_oportunidades(csv_path)
            if html_path:
                enviar_reporte_telegram(csv_path, html_path)
                print(f"✅ Completado: {csv_path}")
                print(f"✅ HTML: {html_path}")
            else:
                print("❌ Error generando HTML")
        else:
            print("❌ Error en análisis de oportunidades")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def analisis_cruzado_manual():
    """
    Genera análisis cruzado manual de los últimos reportes
    """
    try:
        from github_pages_historial import GitHubPagesHistoricalUploader
        
        uploader = GitHubPagesHistoricalUploader()
        
        days = input("🔍 ¿Cuántos días atrás analizar? (default: 30): ").strip()
        try:
            days = int(days) if days else 30
        except:
            days = 30
        
        print(f"📊 Generando análisis cruzado de últimos {days} días...")
        cross_analysis_file = uploader.generate_cross_analysis_report(days)
        
        if cross_analysis_file:
            print(f"✅ Análisis cruzado generado: {cross_analysis_file}")
            print(f"🌐 Abre el archivo en tu navegador para ver patrones")
            print(f"💡 El análisis mostrará:")
            print(f"   • Tickers con actividad recurrente")
            print(f"   • Frecuencia de aparición de cada empresa")
            print(f"   • Evaluación de consistencia de señales")
            print(f"   • Clasificación bullish/bearish/neutral")
        else:
            print("❌ Error generando análisis cruzado")
            
    except ImportError:
        print("❌ Sistema de historial no disponible")
        print("   Necesitas crear el archivo github_pages_historial.py")
    except Exception as e:
        print(f"❌ Error: {e}")

def ver_historial_github():
    """
    Muestra información sobre el historial en GitHub Pages
    """
    try:
        from github_pages_historial import GitHubPagesHistoricalUploader
        
        uploader = GitHubPagesHistoricalUploader()
        manifest = uploader.load_manifest()
        
        print(f"\n📊 HISTORIAL DE REPORTES")
        print(f"=" * 40)
        print(f"📈 Total reportes: {manifest.get('total_reports', 0)}")
        print(f"📅 Última actualización: {manifest.get('last_updated', 'N/A')[:19] if manifest.get('last_updated') else 'N/A'}")
        print(f"🌐 URL local: {uploader.index_file}")
        
        if manifest.get('reports'):
            print(f"\n🔥 ÚLTIMOS 5 REPORTES:")
            recent_reports = sorted(manifest['reports'], key=lambda x: x['timestamp'], reverse=True)[:5]
            
            for i, report in enumerate(recent_reports, 1):
                timestamp = report['timestamp'][:16]  # YYYY-MM-DD HH:MM
                stats = report.get('statistics', {})
                opportunities = stats.get('total_opportunities', 0)
                avg_score = stats.get('avg_score', 0)
                print(f"{i}. {timestamp} - {opportunities} oportunidades (Score: {avg_score:.1f})")
        
        print(f"\n💡 Para ver historial completo:")
        print(f"1. Abrir {uploader.index_file} en navegador")
        print(f"2. Ver análisis cruzado en cross_analysis.html")
        print(f"3. Revisar tendencias en trends.html")
        
        # Mostrar estadísticas de análisis cruzado si está disponible
        try:
            ticker_activity = uploader.get_cross_analysis_data(30)
            if ticker_activity:
                significant_tickers = {
                    ticker: data for ticker, data in ticker_activity.items()
                    if data['appearances'] >= 2
                }
                
                print(f"\n🔍 ANÁLISIS CRUZADO (últimos 30 días):")
                print(f"📊 Tickers con actividad recurrente: {len(significant_tickers)}")
                
                if significant_tickers:
                    print(f"🏆 TOP 3 MÁS ACTIVOS:")
                    sorted_tickers = sorted(
                        significant_tickers.items(),
                        key=lambda x: x[1]['appearances'] * x[1]['avg_score'],
                        reverse=True
                    )[:3]
                    
                    for i, (ticker, data) in enumerate(sorted_tickers, 1):
                        print(f"{i}. {ticker} - {data['appearances']} apariciones, Score: {data['avg_score']:.1f}")
        except:
            print("⚠️ Análisis cruzado no disponible")
        
    except ImportError:
        print("❌ Sistema de historial no disponible")
        print("   Necesitas crear el archivo github_pages_historial.py")
    except Exception as e:
        print(f"❌ Error: {e}")

def migrar_reportes_antiguos():
    """
    Migra reportes existentes al sistema de historial
    """
    try:
        from github_pages_historial import GitHubPagesHistoricalUploader, migrar_reportes_existentes
        
        print("🔄 Migrando reportes antiguos al sistema de historial...")
        
        uploader = GitHubPagesHistoricalUploader()
        migrated_count = migrar_reportes_existentes("reports", uploader)
        
        if migrated_count > 0:
            print(f"✅ {migrated_count} reportes migrados exitosamente")
            print(f"🌐 Revisa {uploader.index_file} para ver el historial")
            print(f"🔍 Ejecuta opción 8 para generar análisis cruzado")
        else:
            print("⚠️ No se encontraron reportes para migrar")
            print("   Verifica que existan archivos .html en la carpeta 'reports'")
            
    except ImportError:
        print("❌ Sistema de historial no disponible")
        print("   Necesitas crear el archivo github_pages_historial.py")
    except Exception as e:
        print(f"❌ Error en migración: {e}")

def solo_graficos():
    """
    Solo genera gráficos sin reporte
    """
    try:
        from run_daily import procesar_insiders_csv_y_generar_graficos
        graficos = procesar_insiders_csv_y_generar_graficos()
        print(f"✅ {len(graficos)} gráficos generados en reports/graphs/")
    except Exception as e:
        print(f"❌ Error: {e}")

def solo_html():
    """
    Solo genera el reporte HTML MODERNIZADO
    """
    try:
        # CAMBIAR: de crear_html_con_finviz a crear_html_moderno_finviz
        from alerts.plot_utils import crear_html_moderno_finviz, crear_bundle_completo
        html_path = crear_html_moderno_finviz()
        bundle_path = crear_bundle_completo()
        print(f"✅ HTML moderno: {html_path}")
        print(f"✅ Bundle: {bundle_path}")
    except ImportError:
        # Fallback a la función antigua
        try:
            from alerts.plot_utils import crear_html_con_finviz, crear_bundle_completo
            html_path = crear_html_con_finviz()
            bundle_path = crear_bundle_completo()
            print(f"✅ HTML: {html_path}")
            print(f"✅ Bundle: {bundle_path}")
        except Exception as e:
            print(f"❌ Error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

def verificar_telegram():
    """
    Verifica la configuración de Telegram
    """
    chat_id = get_telegram_chat_id()
    
    if not chat_id:
        print("❌ TELEGRAM_CHAT_ID no encontrado en config.py")
        print("   Verifica que config.py contenga: TELEGRAM_CHAT_ID = 'tu_chat_id'")
        return
    
    try:
        from alerts.telegram_utils import send_message
        send_message(chat_id, "✅ Test de configuración Telegram - Funcionando correctamente")
        print("✅ Telegram configurado correctamente")
        print(f"📱 Chat ID: {chat_id}")
    except ImportError:
        print("❌ Módulo telegram_utils no encontrado")
        print("   Verifica que esté en alerts/telegram_utils.py")
    except Exception as e:
        print(f"❌ Error en Telegram: {e}")
        print("   Verifica tu token y configuración")

def mostrar_configuracion():
    """
    Muestra la configuración actual del sistema
    """
    print("\n🔧 CONFIGURACIÓN ACTUAL")
    print("=" * 40)
    
    # Verificar archivos necesarios
    csv_path = "reports/insiders_daily.csv"
    print(f"📄 CSV de insiders: {'✅' if os.path.exists(csv_path) else '❌'} {csv_path}")
    
    # Verificar directorios
    dirs_to_check = ["reports", "reports/graphs", "alerts", "insiders"]
    for dir_path in dirs_to_check:
        print(f"📁 Directorio {dir_path}: {'✅' if os.path.exists(dir_path) else '❌'}")
    
    # Verificar módulos principales
    modules_to_check = [
        ("config.py", "config"),
        ("run_daily.py", "run_daily"),
        ("alerts/plot_utils.py", "alerts.plot_utils"),
        ("alerts/telegram_utils.py", "alerts.telegram_utils"),
        ("insiders/insider_tracker.py", "insiders.insider_tracker")
    ]
    
    print("\n📦 MÓDULOS PRINCIPALES:")
    for file_name, module_name in modules_to_check:
        try:
            __import__(module_name)
            print(f"✅ {file_name}")
        except ImportError:
            print(f"❌ {file_name}")
    
    # NUEVO: Verificar sistema de historial
    print("\n🌐 SISTEMA DE HISTORIAL:")
    try:
        from github_pages_historial import GitHubPagesHistoricalUploader
        print("✅ Sistema de historial disponible")
        
        # Verificar si ya hay historial
        uploader = GitHubPagesHistoricalUploader()
        if os.path.exists(uploader.manifest_file):
            manifest = uploader.load_manifest()
            total_reports = manifest.get('total_reports', 0)
            print(f"📊 Reportes en historial: {total_reports}")
        else:
            print("📊 Historial: No inicializado")
    except ImportError:
        print("❌ Sistema de historial no disponible")
        print("   Para habilitarlo: crear github_pages_historial.py")
    
    # Verificar configuración de Telegram
    print("\n📱 TELEGRAM:")
    chat_id = get_telegram_chat_id()
    if chat_id:
        print(f"✅ Chat ID configurado: {chat_id}")
    else:
        print("❌ Chat ID no configurado")
    
    # Verificar API keys
    print("\n🔑 API KEYS:")
    try:
        from run_daily import ALPHA_VANTAGE_API_KEY
        if ALPHA_VANTAGE_API_KEY and ALPHA_VANTAGE_API_KEY != "TU_API_KEY_AQUI":
            print(f"✅ Alpha Vantage: {ALPHA_VANTAGE_API_KEY[:8]}...")
        else:
            print("⚠️ Alpha Vantage no configurado")
    except:
        print("❌ Alpha Vantage no disponible")

def configurar_sistema_historial():
    """
    Configura el sistema de historial por primera vez
    """
    try:
        from github_pages_historial import GitHubPagesHistoricalUploader, migrar_reportes_existentes
        
        print("🔧 CONFIGURANDO SISTEMA DE HISTORIAL")
        print("=" * 50)
        
        # 1. Crear estructura de directorios
        print("📁 Creando estructura de directorios...")
        uploader = GitHubPagesHistoricalUploader()
        print("✅ Directorios creados")
        
        # 2. Migrar reportes existentes
        print("\n🔄 Migrando reportes existentes...")
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
        print(f"1. Ejecutar análisis con opción 1 (análisis completo)")
        print(f"2. Revisar historial abriendo index.html en navegador")
        print(f"3. Ver análisis cruzado para identificar patrones")
        
    except ImportError:
        print("❌ Sistema de historial no disponible")
        print("   Necesitas crear el archivo github_pages_historial.py")
    except Exception as e:
        print(f"❌ Error en configuración: {e}")

def show_menu():
    """
    Muestra el menú principal con opciones de historial
    """
    print("\n" + "=" * 60)
    print("📊 MENÚ PRINCIPAL - INSIDER TRADING CON HISTORIAL")
    print("=" * 60)
    
    # Verificar si el sistema de historial está disponible
    historial_disponible = False
    try:
        from github_pages_historial import GitHubPagesHistoricalUploader
        historial_disponible = True
    except ImportError:
        pass
    
    print("1. 🚀 Ejecutar análisis completo" + (" CON HISTORIAL" if historial_disponible else " (tradicional)"))
    print("2. 🎯 Solo análisis de oportunidades")
    print("3. 🎯 Probar ticker individual")
    print("4. 📊 Solo generar gráficos")
    print("5. 📄 Solo generar reporte HTML")
    print("6. 📱 Verificar configuración Telegram")
    print("7. 🔧 Mostrar configuración actual")
    
    if historial_disponible:
        print("8. 🔍 Generar análisis cruzado manual")
        print("9. 🌐 Ver historial en GitHub Pages")
        print("10. 🔄 Migrar reportes antiguos al historial")
        print("11. ⚙️ Configurar sistema de historial")
    else:
        print("8. ⚙️ Configurar sistema de historial")
        print("   (Requiere crear github_pages_historial.py)")
    
    print("0. ❌ Salir")
    print("=" * 60)
    
    if historial_disponible:
        print("✅ Sistema de historial ACTIVO - Análisis cruzado disponible")
    else:
        print("⚠️ Sistema de historial NO disponible - Modo tradicional")
    
    print("=" * 60)
    
    return input("Selecciona una opción: ").strip()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        # Modo automático
        main()
    else:
        # Modo interactivo
        while True:
            opcion = show_menu()
            
            # Verificar disponibilidad del sistema de historial para opciones avanzadas
            historial_disponible = False
            try:
                from github_pages_historial import GitHubPagesHistoricalUploader
                historial_disponible = True
            except ImportError:
                pass
            
            if opcion == "1":
                main()
            elif opcion == "2":
                solo_analisis_oportunidades()
            elif opcion == "3":
                test_individual_ticker()
            elif opcion == "4":
                solo_graficos()
            elif opcion == "5":
                solo_html()
            elif opcion == "6":
                verificar_telegram()
            elif opcion == "7":
                mostrar_configuracion()
            elif opcion == "8":
                if historial_disponible:
                    analisis_cruzado_manual()
                else:
                    configurar_sistema_historial()
            elif opcion == "9" and historial_disponible:
                ver_historial_github()
            elif opcion == "10" and historial_disponible:
                migrar_reportes_antiguos()
            elif opcion == "11" and historial_disponible:
                configurar_sistema_historial()
            elif opcion == "0":
                print("👋 ¡Hasta luego!")
                break
            else:
                print("❌ Opción no válida")
            
            input("\nPresiona Enter para continuar...")