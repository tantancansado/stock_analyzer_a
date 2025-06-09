#!/bin/bash
# Script para integrar AMBOS sistemas históricos: local + GitHub Pages

echo "🌐 INTEGRANDO HISTÓRICO COMPLETO: LOCAL + GITHUB PAGES"
echo "====================================================="

# Variables
PROJECT_DIR="/Users/alejandroordonezvillar/Desktop/stockAnalyzer/stock_analyzer_a"
PYTHON_PATH="/usr/bin/python3"
HISTORICO_LOCAL="sistema_reportes_historicos.py"
HISTORICO_GITHUB="github_pages_historico.py"
CRON_SCRIPT="run_insider_analysis_working.sh"

cd "$PROJECT_DIR"

echo "📁 Directorio: $PROJECT_DIR"
echo "🐍 Python: $PYTHON_PATH"

# Verificar que ambos scripts históricos están disponibles
scripts_necesarios=("$HISTORICO_LOCAL" "$HISTORICO_GITHUB")
for script in "${scripts_necesarios[@]}"; do
    if [[ ! -f "$script" ]]; then
        echo "❌ $script no encontrado"
        echo "   Cópialo primero al directorio del proyecto"
        exit 1
    fi
    chmod +x "$script"
    echo "✅ $script configurado"
done

# PASO 1: Modificar script de análisis diario para incluir AMBOS históricos
echo ""
echo "📝 PASO 1: Modificando script para histórico dual..."

# Crear backup del script actual
cp "$CRON_SCRIPT" "${CRON_SCRIPT}.backup.historico.$(date +%Y%m%d_%H%M%S)"
echo "💾 Backup creado: ${CRON_SCRIPT}.backup.historico.$(date +%Y%m%d_%H%M%S)"

# Eliminar integraciones históricas previas si existen
sed -i '' '/sistema_reportes_historicos\|github_pages_historico/d' "$CRON_SCRIPT"
echo "🔄 Integraciones históricas previas eliminadas"

# Agregar AMBOS históricos antes del exit final
# Buscar la línea "log \"🏁 Análisis automático finalizado\"" y agregar antes
if grep -q "🏁 Análisis automático finalizado" "$CRON_SCRIPT"; then
    # Crear archivo temporal con la modificación
    awk '
    /log "🏁 Análisis automático finalizado"/ {
        print ""
        print "# === HISTÓRICO DUAL: LOCAL + GITHUB PAGES ==="
        print "log \"📦 Archivando reportes localmente...\""
        print "\"$PYTHON_PATH\" \"$PROJECT_DIR/sistema_reportes_historicos.py\" --archivar >> \"$LOG_FILE\" 2>&1"
        print "local_archive_status=$?"
        print ""
        print "log \"🌐 Organizando histórico en GitHub Pages...\""
        print "\"$PYTHON_PATH\" \"$PROJECT_DIR/github_pages_historico.py\" --completo >> \"$LOG_FILE\" 2>&1"
        print "github_archive_status=$?"
        print ""
        print "# Reportar estado de archivado"
        print "if [[ $local_archive_status -eq 0 ]]; then"
        print "    log \"✅ Archivo local: OK\""
        print "else"
        print "    log \"⚠️ Archivo local: ERROR\""
        print "fi"
        print ""
        print "if [[ $github_archive_status -eq 0 ]]; then"
        print "    log \"✅ Archivo GitHub Pages: OK\""
        print "else"
        print "    log \"⚠️ Archivo GitHub Pages: ERROR\""
        print "fi"
        print ""
        print "log \"📊 Histórico dual completado (Local: $local_archive_status, GitHub: $github_archive_status)\""
        print ""
    }
    { print }
    ' "$CRON_SCRIPT" > "${CRON_SCRIPT}.tmp"
    
    mv "${CRON_SCRIPT}.tmp" "$CRON_SCRIPT"
    chmod +x "$CRON_SCRIPT"
    echo "✅ Histórico dual integrado en $CRON_SCRIPT"
else
    echo "⚠️ No se encontró la línea de finalización esperada"
    echo "   Agregando al final del script..."
    
    # Agregar antes del último exit
    sed -i '' '/^exit \$exit_code$/i\
\
# === HISTÓRICO DUAL: LOCAL + GITHUB PAGES ===\
log "📦 Archivando reportes localmente..."\
"$PYTHON_PATH" "$PROJECT_DIR/sistema_reportes_historicos.py" --archivar >> "$LOG_FILE" 2>&1\
local_archive_status=$?\
\
log "🌐 Organizando histórico en GitHub Pages..."\
"$PYTHON_PATH" "$PROJECT_DIR/github_pages_historico.py" --completo >> "$LOG_FILE" 2>&1\
github_archive_status=$?\
\
# Reportar estado de archivado\
if [[ $local_archive_status -eq 0 ]]; then\
    log "✅ Archivo local: OK"\
else\
    log "⚠️ Archivo local: ERROR"\
fi\
\
if [[ $