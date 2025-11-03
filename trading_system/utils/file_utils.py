"""
Utilidades para manejo de archivos
"""

import os
import shutil
import zipfile
from pathlib import Path
from typing import List, Optional

def setup_directories():
    """Crea los directorios necesarios del sistema"""
    directories = [
        "reports",
        "data",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

def create_bundle(files: List[str], output_path: str) -> bool:
    """Crea un ZIP con los archivos especificados"""
    try:
        with zipfile.ZipFile(output_path, 'w') as zipf:
            for file_path in files:
                if os.path.exists(file_path):
                    zipf.write(file_path, arcname=os.path.basename(file_path))
        return True
    except Exception as e:
        print(f"❌ Error creando bundle: {e}")
        return False

def cleanup_old_reports(directory: str, keep_count: int = 10):
    """Limpia reportes antiguos, manteniendo solo los más recientes"""
    try:
        reports_dir = Path(directory)
        if not reports_dir.exists():
            return
        
        files = sorted(reports_dir.glob("*.html"), key=lambda x: x.stat().st_mtime, reverse=True)
        
        for file_to_remove in files[keep_count:]:
            file_to_remove.unlink()
            csv_file = file_to_remove.with_suffix('.csv')
            if csv_file.exists():
                csv_file.unlink()
        
        print(f"✅ Limpieza completada. Mantenidos {min(len(files), keep_count)} reportes")
        
    except Exception as e:
        print(f"❌ Error en limpieza: {e}")

def find_file_in_paths(filename: str, search_paths: List[str]) -> Optional[str]:
    """Busca un archivo en múltiples rutas"""
    for path in search_paths:
        full_path = os.path.join(path, filename)
        if os.path.exists(full_path):
            return full_path
    return None
