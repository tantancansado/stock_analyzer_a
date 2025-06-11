#!/bin/bash
# Script de limpieza para stock_analyzer_a

echo "🧹 LIMPIEZA DEL REPOSITORIO"
echo "=========================="

# Confirmar antes de proceder
read -p "¿Estás seguro de que quieres limpiar archivos obsoletos? (s/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    echo "Cancelado."
    exit 1
fi

echo -e "\n📁 Creando backup por seguridad..."
BACKUP_DIR="backup_limpieza_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Lista de archivos a eliminar
FILES_TO_DELETE=(
    # Backups de docs
    "docs_backup_20250611_103621"
    
    # GitHub Pages antiguos
    "github_pages/"
    "github-pages-reports/"
    "github_pages_config.py"
    "github_pages_historico.py"
    "github_pages_uploader.py"
    
    # Scripts de análisis antiguos
    "run_insider_analysis_working.sh.backup.20250605_173049"
    "run_insider_analysis_working.sh.backup.historico.20250605_173545"
    "run_insider_analysis_working.sh.save"
    
    # Crontab backups
    "crontab_backup_20250605_171250.txt"
    "crontab_backup_20250605_171445.txt"
    "crontab_backup_20250605_171504.txt"
    "crontab_backup_20250605_171628.txt"
    "crontab_backup_20250605_171644.txt"
    "crontab_backup_historico_20250605_173049.txt"
    
    # Archivos temporales
    "__pycache__/"
    ".DS_Store"
    "*.pyc"
    "*.swp"
    "*.swo"
    
    # Otros obsoletos
    "README_backup.md"
    "parche_github"
)

# Mover archivos al backup antes de eliminar
echo -e "\n🔄 Moviendo archivos al backup..."
for file in "${FILES_TO_DELETE[@]}"; do
    if [ -e "$file" ]; then
        echo "  - Moviendo: $file"
        mv "$file" "$BACKUP_DIR/" 2>/dev/null || true
    fi
done

# Limpiar archivos Python compilados
echo -e "\n🐍 Limpiando archivos Python compilados..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

# Mostrar estructura actual
echo -e "\n📊 ESTRUCTURA ACTUAL DEL PROYECTO:"
echo "================================="
tree -L 2 -I '__pycache__|*.pyc|.git|.DS_Store' || ls -la

# Verificar integridad del sistema
echo -e "\n🔍 VERIFICANDO SISTEMA:"
echo "======================"

# Verificar archivos críticos
CRITICAL_FILES=(
    "insider_trading_unified.py"
    "github_pages_historial.py"
    "config.py"
    "main.py"
    "docs/index.html"
)

all_good=true
for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ $file - FALTA!"
        all_good=false
    fi
done

if [ "$all_good" = true ]; then
    echo -e "\n✅ Sistema verificado correctamente"
    echo "💡 Backup guardado en: $BACKUP_DIR"
    echo "   Puedes eliminarlo cuando confirmes que todo funciona:"
    echo "   rm -rf $BACKUP_DIR"
else
    echo -e "\n⚠️  Faltan archivos críticos"
    echo "   Restaura desde el backup si es necesario"
fi

# Estadísticas finales
echo -e "\n📈 ESTADÍSTICAS:"
echo "==============="
echo "Archivos en /docs: $(find docs -type f | wc -l)"
echo "Reportes en /reports: $(find reports -name "*.html" -o -name "*.csv" | wc -l)"
echo "Tamaño total: $(du -sh . | cut -f1)"
echo ""
echo "🎉 Limpieza completada!"