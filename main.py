#!/usr/bin/env python3
"""
Script principal para ejecutar todo el análisis de insider trading
Coordina: análisis de oportunidades + gráficos + HTML + Telegram
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
    Ejecuta el análisis completo de insider trading
    """
    print("🚀 ANÁLISIS COMPLETO DE INSIDER TRADING")
    print("=" * 50)
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
        
        # NUEVO: Ejecutar análisis integrado completo
        print("🎯 Ejecutando análisis integrado completo...")
        
        from insiders.insider_tracker import generar_reporte_completo_integrado
        
        # Ejecutar análisis integrado que incluye oportunidades + gráficos + telegram
        result = generar_reporte_completo_integrado()
        
        if result:
            print(f"✅ Análisis integrado completado")
            if result.get('csv_opportunities'):
                print(f"📄 CSV Oportunidades: {result['csv_opportunities']}")
            if result.get('html_opportunities'):
                print(f"🌐 HTML Oportunidades: {result['html_opportunities']}")
            if result.get('html_charts'):
                print(f"📊 HTML Gráficos: {result['html_charts']}")
            if result.get('bundle'):
                print(f"📦 Bundle completo: {result['bundle']}")
                
            # Variables para el resumen final
            csv_opportunities = result.get('csv_opportunities')
            html_opportunities = result.get('html_opportunities')
            html_charts = result.get('html_charts')
            bundle_path = result.get('bundle')
            
        else:
            print("⚠️ El análisis integrado no se completó correctamente")
            csv_opportunities = None
            html_opportunities = None
            html_charts = None
            bundle_path = None
        
        print("\n" + "=" * 50)
        print("🎉 ¡ANÁLISIS COMPLETADO!")
        print("=" * 50)
        if 'csv_opportunities' in locals() and csv_opportunities:
            print(f"📄 Reporte de oportunidades: {csv_opportunities}")
        if 'html_opportunities' in locals() and html_opportunities:
            print(f"🌐 HTML oportunidades: {html_opportunities}")
        if 'html_charts' in locals() and html_charts:
            print(f"📊 HTML gráficos: {html_charts}")
        if 'bundle_path' in locals() and bundle_path:
            print(f"📦 Bundle completo: {bundle_path}")
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

def show_menu():
    """
    Muestra el menú principal
    """
    print("\n" + "=" * 50)
    print("📊 MENÚ PRINCIPAL - INSIDER TRADING")
    print("=" * 50)
    print("1. 🚀 Ejecutar análisis completo (oportunidades + gráficos)")
    print("2. 🎯 Solo análisis de oportunidades")
    print("3. 🎯 Probar ticker individual")
    print("4. 📊 Solo generar gráficos")
    print("5. 📄 Solo generar reporte HTML")
    print("6. 📱 Verificar configuración Telegram")
    print("7. 🔧 Mostrar configuración actual")
    print("0. ❌ Salir")
    print("=" * 50)
    
    return input("Selecciona una opción: ").strip()

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
    
    # Verificar módulos
    modules_to_check = [
        ("config.py", "config"),
        ("run_daily.py", "run_daily"),
        ("alerts/plot_utils.py", "alerts.plot_utils"),
        ("alerts/telegram_utils.py", "alerts.telegram_utils"),
        ("insiders/insider_tracker.py", "insiders.insider_tracker")
    ]
    
    print("\n📦 MÓDULOS:")
    for file_name, module_name in modules_to_check:
        try:
            __import__(module_name)
            print(f"✅ {file_name}")
        except ImportError:
            print(f"❌ {file_name}")
    
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

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        # Modo automático
        main()
    else:
        # Modo interactivo
        while True:
            opcion = show_menu()
            
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
            elif opcion == "0":
                print("👋 ¡Hasta luego!")
                break
            else:
                print("❌ Opción no válida")
            
            input("\nPresiona Enter para continuar...")