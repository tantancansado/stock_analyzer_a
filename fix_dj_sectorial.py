import re
import os
import sys
from datetime import datetime
import shutil

# --- CONFIGURACIÓN ---
# Ajusta el nombre del archivo si es diferente
MAIN_FILE = "sistema_principal.py" 
BACKUP_FILE = MAIN_FILE + ".bak"
# ---------------------

def safe_copy_restore(src, dest):
    """Copia un archivo de forma segura."""
    try:
        shutil.copyfile(src, dest)
        return True
    except Exception as e:
        print(f"❌ Error crítico al operar con archivos {src} -> {dest}: {e}")
        return False

def apply_fixes():
    """
    Función principal para aplicar las correcciones de URL estáticas.
    """
    print(f"🛠️ Iniciando reparación de rutas estáticas en {MAIN_FILE}...")
    
    # 1. Restaurar desde la copia de seguridad por si el intento anterior lo corrompió
    if os.path.exists(BACKUP_FILE):
        if not safe_copy_restore(BACKUP_FILE, MAIN_FILE):
            sys.exit(1)
        print(f"✅ Restaurado {MAIN_FILE} desde la copia de seguridad (.bak).")
    
    if not os.path.exists(MAIN_FILE):
        print(f"❌ Error: Archivo principal '{MAIN_FILE}' no encontrado.")
        sys.exit(1)

    try:
        with open(MAIN_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Error al leer el archivo: {e}")
        sys.exit(1)
        
    # Crear nueva copia de seguridad (por si acaso)
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_copy_restore(MAIN_FILE, f"{MAIN_FILE}.new_bak_{timestamp_str}")
    
    
    # ---------------------------------------------------------------------
    # PARCHE 1: Corregir la lógica de ID, Directorio y base_path en upload_report
    # ---------------------------------------------------------------------

    logic_start_match = re.search(r'(\s+)if report_type == "dj_sectorial":', content)
    logic_end_match = re.search(r'(\s+)# Actualizar lista de reportes', content)
    
    if logic_start_match and logic_end_match:
        start_index = logic_start_match.start()
        end_index = logic_end_match.start()
        
        # Obtenemos la indentación del inicio del bloque 'if'
        indent = logic_start_match.group(1)
        
        # Generamos el nuevo bloque de lógica con rutas estáticas (sin fecha) para DJ y Breadth
        # Usamos INDENTACIÓN para claridad, pero Python lo maneja como una sola cadena de reemplazo.
        new_logic = f"""{indent}if report_type == "dj_sectorial":
{indent}    report_id = "dj_sectorial"
{indent}    report_dir = self.reports_path / "dj_sectorial"
{indent}    base_path = "reports/dj_sectorial"
{indent}elif report_type == "market_breadth":
{indent}    report_id = "market_breadth"
{indent}    report_dir = self.reports_path / "market_breadth"
{indent}    base_path = "reports/market_breadth"
{indent}elif report_type == "enhanced_opportunities":
{indent}    report_id = f"enhanced_opportunities_{datetime.now().strftime('%Y%m%d_%H%M%S')}" # ID completo
{indent}    report_dir = self.reports_path / "enhanced_opportunities" / report_id
{indent}    base_path = f"reports/enhanced_opportunities/{{report_id}}"
{indent}else: # insider
{indent}    report_id = f"report_{datetime.now().strftime('%Y-%m-%d')}"
{indent}    report_dir = self.reports_path / "daily" / report_id
{indent}    base_path = f"reports/daily/{{report_id}}"
{indent}
{indent}report_dir.mkdir(exist_ok=True, parents=True)
{indent}
{indent}# Copiar archivos
{indent}shutil.copy2(html_file, report_dir / "index.html")
{indent}shutil.copy2(csv_file, report_dir / "data.csv")
{indent}
{indent}# Actualizar manifest
{indent}manifest = self.load_manifest()
{indent}
{indent}# Crear entrada del reporte
{indent}report_entry = {{
{indent}    "id": report_id,
{indent}    "title": title,
{indent}    "description": description,
{indent}    "timestamp": datetime.now().isoformat(),
{indent}    "date": datetime.now().strftime('%Y-%m-%d'),
{indent}    "time": datetime.now().strftime('%H:%M:%S'),
{indent}    "html_url": f"{{base_path}}/index.html",
{indent}    "csv_url": f"{{base_path}}/data.csv",
{indent}    "full_url": f"{{self.base_url}}/{{base_path}}/index.html",
{indent}    "type": report_type
{indent}}}"""
        
        # Aplicar el reemplazo
        content = content[:start_index] + new_logic + content[end_index:]
        print("✅ Parche 1: Lógica de rutas estáticas/dinámicas en GitHubPagesUploader.upload_report aplicada.")
    else:
        print("❌ Parche 1: No se pudo encontrar el bloque de lógica de rutas en GitHubPagesUploader. (Continuando con el Parche 2)")


    # ---------------------------------------------------------------------
    # PARCHE 2: Corregir los enlaces en el mensaje de Telegram
    # ---------------------------------------------------------------------
    
    # Patrón para la sección de URLs de GitHub Pages en send_ultra_enhanced_telegram_report
    pattern_telegram_links = re.compile(
        r'(\s+)# URLs de GitHub Pages' # Captura la indentación
        r'([\s\S]*?)' # Captura el bloque intermedio con la lógica rota
        r'(\s+)if github_links:' # Captura el final del bloque
    )
    
    # Nuevo bloque de código (usando las URLs correctas del diccionario results)
    replacement_telegram_links = r"""\1# URLs de GitHub Pages
\1github_links = ""
\1if results['github_insider']:
\1    github_links += f"\n🏛️ [Ver Insider Trading]({results['github_insider']['github_url']})"
\1if results['github_dj']:
\1    github_links += f"\n📊 [Ver DJ Sectorial]({results['github_dj']['github_url']})"
\1if results['github_breadth']:
\1    github_links += f"\n📈 [Ver Market Breadth COMPLETO]({results['github_breadth']['github_url']})"
\1if results['github_enhanced']:
\1    github_links += f"\n🎯 [Ver Enhanced Opportunities]({results['github_enhanced']['github_url']})"
\1\3"""
    
    content, count_telegram = pattern_telegram_links.subn(replacement_telegram_links, content)

    if count_telegram > 0:
        print("✅ Parche 2: URLs estáticas de Telegram corregidas (usando la URL completa generada).")
    else:
        print("⚠️ Parche 2: No se encontró la sección de enlaces de Telegram para corregir.")

    # --- GUARDAR ARCHIVO CORREGIDO ---
    try:
        with open(MAIN_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"\n🎉 ÉXITO: El archivo {MAIN_FILE} ha sido corregido y guardado.")
        print(f"   Ahora el DJ Sectorial y Market Breadth usan URLs estáticas.")
    except Exception as e:
        print(f"\n❌ Error crítico al guardar el archivo: {e}")


if __name__ == "__main__":
    apply_fixes()