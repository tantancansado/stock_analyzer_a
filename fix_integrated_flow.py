#!/usr/bin/env python3
"""
Parche para el flujo integrado - evita sobreescribir GitHub Pages cuando hay errores
"""

import os
import sys
import subprocess
from datetime import datetime
import shutil

def backup_github_pages():
    """
    Hace backup de GitHub Pages antes de ejecutar el flujo completo
    """
    print("💾 Haciendo backup de GitHub Pages...")
    
    if os.path.exists("docs"):
        backup_dir = f"docs_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            shutil.copytree("docs", backup_dir)
            print(f"✅ Backup creado: {backup_dir}")
            return backup_dir
        except Exception as e:
            print(f"⚠️ Error haciendo backup: {e}")
            return None
    else:
        print("ℹ️ No hay docs/ para hacer backup")
        return None

def restore_github_pages(backup_dir):
    """
    Restaura GitHub Pages desde backup
    """
    if backup_dir and os.path.exists(backup_dir):
        try:
            if os.path.exists("docs"):
                shutil.rmtree("docs")
            shutil.copytree(backup_dir, "docs")
            print(f"✅ GitHub Pages restaurado desde: {backup_dir}")
            return True
        except Exception as e:
            print(f"❌ Error restaurando: {e}")
            return False
    return False

def ejecutar_flujo_con_proteccion():
    """
    Ejecuta el flujo completo con protección de GitHub Pages
    """
    print("🛡️ FLUJO INTEGRADO CON PROTECCIÓN")
    print("=" * 40)
    
    # Hacer backup
    backup_dir = backup_github_pages()
    
    try:
        # Buscar insider_tracker.py
        tracker_paths = [
            "insiders/insider_tracker.py",
            "insider_tracker.py"
        ]
        
        tracker_path = None
        for path in tracker_paths:
            if os.path.exists(path):
                tracker_path = path
                break
        
        if not tracker_path:
            print("❌ insider_tracker.py no encontrado")
            return False
        
        print(f"🚀 Ejecutando: python {tracker_path} --completo")
        
        # Ejecutar con timeout
        result = subprocess.run([
            sys.executable, tracker_path, "--completo"
        ], capture_output=True, text=True, timeout=1800)
        
        print(f"📋 Código de salida: {result.returncode}")
        
        if result.returncode == 0:
            print("✅ Flujo completado exitosamente")
            
            # Verificar que se generaron archivos
            archivos_esperados = [
                "reports/insiders_opportunities.csv",
                "reports/insiders_opportunities.html"
            ]
            
            archivos_ok = 0
            for archivo in archivos_esperados:
                if os.path.exists(archivo):
                    print(f"✅ {archivo}")
                    archivos_ok += 1
                else:
                    print(f"❌ {archivo}")
            
            if archivos_ok == len(archivos_esperados):
                print("🎉 Todos los archivos generados correctamente")
                
                # Subir a GitHub Pages si no se hizo automáticamente
                if os.path.exists("docs") and len(os.listdir("docs")) > 1:
                    print("✅ GitHub Pages parece estar actualizado")
                else:
                    print("🌐 Ejecutando subida manual a GitHub Pages...")
                    try:
                        subprocess.run([sys.executable, "fix_github_pages_integration.py"], timeout=300)
                    except Exception as e:
                        print(f"⚠️ Error en subida manual: {e}")
                
                return True
            else:
                print("⚠️ Algunos archivos no se generaron")
                return False
        else:
            print(f"❌ Flujo falló con código: {result.returncode}")
            print("📋 Error output:")
            if result.stderr:
                print(result.stderr[-1000:])  # Últimos 1000 caracteres
            
            # Restaurar backup si hay error
            if backup_dir:
                print("🔄 Restaurando GitHub Pages desde backup...")
                restore_github_pages(backup_dir)
            
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Timeout en flujo integrado (30 minutos)")
        
        # Restaurar backup
        if backup_dir:
            print("🔄 Restaurando GitHub Pages desde backup...")
            restore_github_pages(backup_dir)
        
        return False
    except Exception as e:
        print(f"❌ Error ejecutando flujo: {e}")
        
        # Restaurar backup
        if backup_dir:
            print("🔄 Restaurando GitHub Pages desde backup...")
            restore_github_pages(backup_dir)
        
        return False

def ejecutar_flujo_por_pasos():
    """
    Ejecuta el flujo paso a paso para identificar dónde falla
    """
    print("🔧 FLUJO PASO A PASO")
    print("=" * 25)
    
    pasos = [
        ("Scraper de OpenInsider", "openinsider_scraper.py", []),
        ("Análisis de oportunidades", "fix_csv_opportunities.py", []),
        ("Generación de gráficos", "run_daily.py", []),
        ("Subida a GitHub Pages", "fix_github_pages_integration.py", [])
    ]
    
    resultados = {}
    
    for nombre, script, args in pasos:
        print(f"\n📋 PASO: {nombre}")
        print("-" * 30)
        
        if not os.path.exists(script):
            print(f"❌ Script no encontrado: {script}")
            resultados[nombre] = False
            continue
        
        try:
            cmd = [sys.executable, script] + args
            print(f"🚀 Ejecutando: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                print(f"✅ {nombre}: ÉXITO")
                resultados[nombre] = True
            else:
                print(f"❌ {nombre}: FALLÓ (código {result.returncode})")
                if result.stderr:
                    print(f"Error: {result.stderr[-300:]}")
                resultados[nombre] = False
                
        except subprocess.TimeoutExpired:
            print(f"⏰ {nombre}: TIMEOUT")
            resultados[nombre] = False
        except Exception as e:
            print(f"❌ {nombre}: ERROR - {e}")
            resultados[nombre] = False
    
    # Resumen
    print(f"\n📊 RESUMEN DE PASOS:")
    print("=" * 25)
    exitos = 0
    for paso, resultado in resultados.items():
        estado = "✅" if resultado else "❌"
        print(f"{estado} {paso}")
        if resultado:
            exitos += 1
    
    print(f"\n🎯 ÉXITO: {exitos}/{len(pasos)} pasos")
    
    if exitos == len(pasos):
        print("🎉 ¡Todos los pasos funcionaron!")
        return True
    else:
        print("⚠️ Algunos pasos fallaron, revisar logs arriba")
        return False

def verificar_estado_archivos():
    """
    Verifica el estado actual de los archivos
    """
    print("📊 ESTADO ACTUAL DE ARCHIVOS")
    print("=" * 35)
    
    archivos_clave = [
        "reports/insiders_daily.csv",
        "reports/insiders_opportunities.csv", 
        "reports/insiders_opportunities.html",
        "reports/insider_analysis_complete.html",
        "reports/insider_analysis_bundle.html"
    ]
    
    for archivo in archivos_clave:
        if os.path.exists(archivo):
            size = os.path.getsize(archivo)
            mtime = datetime.fromtimestamp(os.path.getmtime(archivo))
            age_minutes = (datetime.now() - mtime).total_seconds() / 60
            print(f"✅ {archivo}")
            print(f"   💾 {size:,} bytes | ⏰ {age_minutes:.0f} min ago")
        else:
            print(f"❌ {archivo}")
    
    # Estado de GitHub Pages
    print(f"\n🌐 GITHUB PAGES:")
    if os.path.exists("docs"):
        html_files = [f for f in os.listdir("docs") if f.endswith('.html')]
        print(f"✅ docs/ existe con {len(html_files)} archivos HTML")
    else:
        print(f"❌ docs/ no existe")
    
    # Estado de gráficos
    print(f"\n📊 GRÁFICOS:")
    if os.path.exists("reports/graphs"):
        png_files = [f for f in os.listdir("reports/graphs") if f.endswith('.png')]
        print(f"✅ reports/graphs/ con {len(png_files)} gráficos")
    else:
        print(f"❌ reports/graphs/ no existe")

def main():
    """
    Función principal
    """
    if len(sys.argv) > 1:
        comando = sys.argv[1]
        
        if comando == "--por-pasos":
            ejecutar_flujo_por_pasos()
        elif comando == "--estado":
            verificar_estado_archivos()
        elif comando == "--protegido":
            ejecutar_flujo_con_proteccion()
        elif comando == "--help":
            print("""
🛡️ FIX DEL FLUJO INTEGRADO

Uso: python fix_integrated_flow.py [opción]

Opciones:
  (sin opción)    Ejecutar flujo con protección de GitHub Pages
  --por-pasos     Ejecutar paso a paso para debug
  --estado        Verificar estado actual de archivos
  --protegido     Ejecutar con backup de GitHub Pages
  --help          Mostrar esta ayuda

Ejemplos:
  python fix_integrated_flow.py --por-pasos
  python fix_integrated_flow.py --estado
            """)
        else:
            print(f"❌ Opción no reconocida: {comando}")
    else:
        # Por defecto: flujo protegido
        ejecutar_flujo_con_proteccion()

if __name__ == "__main__":
    main()