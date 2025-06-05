#!/bin/bash
# Script para configurar el cron final con opción 1 (que sabemos que funciona)

echo "🔧 CONFIGURANDO CRON FINAL - VERSIÓN QUE FUNCIONA"
echo "=================================================="

# Variables
PROJECT_DIR="/Users/alejandroordonezvillar/Desktop/stockAnalyzer/stock_analyzer_a"
PYTHON_PATH="/usr/bin/python3"
LOG_DIR="$PROJECT_DIR/logs"

# Crear directorio de logs
mkdir -p "$LOG_DIR"

echo "📁 Proyecto: $PROJECT_DIR"
echo "🐍 Python: $PYTHON_PATH"
echo "📄 Logs: $LOG_DIR"

# Crear script de ejecución que funciona
SCRIPT_PATH="$PROJECT_DIR/run_insider_analysis_working.sh"

cat > "$SCRIPT_PATH" << 'EOF'
#!/bin/bash
# Script que funciona - usa la opción 1 del menú

PROJECT_DIR="PROJECT_DIR_PLACEHOLDER"
PYTHON_PATH="PYTHON_PATH_PLACEHOLDER"
LOG_DIR="$PROJECT_DIR/logs"

# Crear log con timestamp
LOG_FILE="$LOG_DIR/cron_analysis_$(date +%Y%m%d_%H%M%S).log"

# Función de logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "🚀 INICIANDO ANÁLISIS AUTOMÁTICO CON OPCIÓN 1"
log "=============================================="
log "📁 Directorio: $PROJECT_DIR"
log "🐍 Python: $PYTHON_PATH"
log "📄 Log: $LOG_FILE"

# Cambiar al directorio del proyecto
cd "$PROJECT_DIR" || {
    log "❌ Error: No se pudo acceder al directorio $PROJECT_DIR"
    exit 1
}

# Verificar que main.py existe
if [[ ! -f "main.py" ]]; then
    log "❌ Error: main.py no encontrado en $PROJECT_DIR"
    exit 1
fi

log "📊 Ejecutando análisis con opción 1..."

# Ejecutar main.py con opción 1 (que sabemos que funciona)
# Usar timeout de 30 minutos y simular entrada "1"
echo "1" | timeout 1800 "$PYTHON_PATH" main.py >> "$LOG_FILE" 2>&1
exit_code=$?

if [[ $exit_code -eq 0 ]]; then
    log "✅ Análisis completado exitosamente"
elif [[ $exit_code -eq 124 ]]; then
    log "⏰ Análisis cancelado por timeout (30 minutos)"
else
    log "❌ Análisis falló con código: $exit_code"
fi

# Mostrar estadísticas de archivos generados
log "📊 ARCHIVOS GENERADOS:"
if [[ -f "$PROJECT_DIR/reports/insiders_daily.csv" ]]; then
    size=$(wc -l < "$PROJECT_DIR/reports/insiders_daily.csv")
    log "   ✅ insiders_daily.csv: $size líneas"
else
    log "   ❌ insiders_daily.csv: No generado"
fi

if [[ -f "$PROJECT_DIR/reports/insiders_opportunities.csv" ]]; then
    size=$(wc -l < "$PROJECT_DIR/reports/insiders_opportunities.csv")
    log "   ✅ insiders_opportunities.csv: $size líneas"
else
    log "   ❌ insiders_opportunities.csv: No generado"
fi

# Verificar subida a GitHub Pages
if [[ -d "$PROJECT_DIR/docs" ]]; then
    html_count=$(find "$PROJECT_DIR/docs" -name "*.html" | wc -l)
    log "   ✅ GitHub Pages: $html_count archivos HTML"
else
    log "   ❌ GitHub Pages: Directorio docs no existe"
fi

# Limpiar logs antiguos (mantener solo 14 días)
find "$LOG_DIR" -name "cron_analysis_*.log" -mtime +14 -delete 2>/dev/null

log "🏁 Análisis automático finalizado"

exit $exit_code
EOF

# Reemplazar placeholders
sed -i '' "s|PROJECT_DIR_PLACEHOLDER|$PROJECT_DIR|g" "$SCRIPT_PATH"
sed -i '' "s|PYTHON_PATH_PLACEHOLDER|$PYTHON_PATH|g" "$SCRIPT_PATH"

# Hacer ejecutable
chmod +x "$SCRIPT_PATH"
echo "✅ Script creado: $SCRIPT_PATH"

# Función para configurar crontab
setup_new_cron() {
    echo ""
    echo "🕒 CONFIGURANDO NUEVO CRONTAB..."
    
    # Hacer backup del crontab actual
    BACKUP_FILE="$PROJECT_DIR/crontab_backup_$(date +%Y%m%d_%H%M%S).txt"
    crontab -l > "$BACKUP_FILE" 2>/dev/null || echo "# No hay crontab previo" > "$BACKUP_FILE"
    echo "💾 Backup guardado en: $BACKUP_FILE"
    
    # Eliminar entradas anteriores del proyecto
    crontab -l 2>/dev/null | grep -v "stock_analyzer_a" | grep -v "insider" | grep -v "openinsider" > /tmp/new_crontab.txt
    
    # Agregar nueva entrada - ejecutar de lunes a viernes a las 9:00 AM
    echo "0 9 * * 1-5 $SCRIPT_PATH >> $LOG_DIR/cron_summary.log 2>&1" >> /tmp/new_crontab.txt
    
    # Instalar nuevo crontab
    crontab /tmp/new_crontab.txt
    
    if [[ $? -eq 0 ]]; then
        echo "✅ Crontab configurado exitosamente"
        echo ""
        echo "📅 PROGRAMACIÓN CONFIGURADA:"
        echo "   ⏰ Hora: 9:00 AM"
        echo "   📅 Días: Lunes a Viernes"
        echo "   📄 Logs: $LOG_DIR/"
        echo ""
        echo "📋 Crontab actual:"
        crontab -l | grep -v "^#" | nl
    else
        echo "❌ Error configurando crontab"
        echo "   Restaurando backup..."
        crontab "$BACKUP_FILE"
        return 1
    fi
    
    # Limpiar archivo temporal
    rm -f /tmp/new_crontab.txt
}

# Función para probar el script
test_script() {
    echo ""
    echo "🧪 PROBANDO EL SCRIPT..."
    
    read -p "¿Quieres ejecutar una prueba del script? (y/N): " test_run
    if [[ $test_run =~ ^[Yy]$ ]]; then
        echo "🚀 Ejecutando prueba..."
        echo "📄 El output aparecerá en: $LOG_DIR/"
        
        # Ejecutar en background
        nohup "$SCRIPT_PATH" &
        PID=$!
        
        echo "✅ Prueba iniciada (PID: $PID)"
        echo "📊 Para monitorear: tail -f $LOG_DIR/cron_analysis_*.log"
        echo "🛑 Para detener: kill $PID"
        
        # Esperar un poco y mostrar el inicio del log
        sleep 3
        echo ""
        echo "📋 Primeras líneas del log:"
        tail -10 "$LOG_DIR"/cron_analysis_*.log 2>/dev/null | head -10
    else
        echo "ℹ️ Puedes probar manualmente con: $SCRIPT_PATH"
    fi
}

# Función para crear script de monitoreo
create_monitor_script() {
    MONITOR_SCRIPT="$PROJECT_DIR/monitor_cron.sh"
    
    cat > "$MONITOR_SCRIPT" << 'EOF'
#!/bin/bash
# Script para monitorear el cron del análisis

PROJECT_DIR="PROJECT_DIR_PLACEHOLDER"
LOG_DIR="$PROJECT_DIR/logs"

echo "📊 MONITOR DEL ANÁLISIS AUTOMÁTICO"
echo "=================================="

# Mostrar último log
latest_log=$(ls -t "$LOG_DIR"/cron_analysis_*.log 2>/dev/null | head -1)

if [[ -n "$latest_log" ]]; then
    echo "📄 Último log: $(basename "$latest_log")"
    echo "📅 Fecha: $(stat -f %Sm "$latest_log" 2>/dev/null || stat -c %y "$latest_log" 2>/dev/null)"
    echo "📏 Tamaño: $(du -h "$latest_log" | cut -f1)"
    echo ""
    
    echo "📋 Últimas 15 líneas:"
    tail -15 "$latest_log"
    
    echo ""
    echo "🔍 Resumen de estado:"
    if grep -q "✅ Análisis completado exitosamente" "$latest_log"; then
        echo "   ✅ Última ejecución: ÉXITO"
    elif grep -q "❌ Análisis falló" "$latest_log"; then
        echo "   ❌ Última ejecución: ERROR"
    elif grep -q "⏰ Análisis cancelado por timeout" "$latest_log"; then
        echo "   ⏰ Última ejecución: TIMEOUT"
    else
        echo "   ❓ Estado desconocido"
    fi
    
    # Contar archivos generados
    if [[ -f "$PROJECT_DIR/reports/insiders_daily.csv" ]]; then
        echo "   📊 CSV insiders: ✅"
    else
        echo "   📊 CSV insiders: ❌"
    fi
    
    if [[ -f "$PROJECT_DIR/reports/insiders_opportunities.csv" ]]; then
        echo "   🎯 CSV oportunidades: ✅"
    else
        echo "   🎯 CSV oportunidades: ❌"
    fi
    
    if [[ -d "$PROJECT_DIR/docs" ]] && [[ $(find "$PROJECT_DIR/docs" -name "*.html" | wc -l) -gt 1 ]]; then
        echo "   🌐 GitHub Pages: ✅"
    else
        echo "   🌐 GitHub Pages: ❌"
    fi
    
else
    echo "❌ No se encontraron logs de ejecución"
fi

# Mostrar configuración de cron
echo ""
echo "🕒 Configuración de cron:"
crontab -l | grep stock_analyzer_a || echo "❌ No hay tareas programadas"

# Mostrar próxima ejecución
echo ""
echo "⏰ Próxima ejecución programada:"
echo "   📅 Lunes a Viernes a las 9:00 AM"

echo ""
echo "⚙️ COMANDOS ÚTILES:"
echo "• Ver logs en tiempo real: tail -f $LOG_DIR/cron_analysis_*.log"
echo "• Ejecutar manualmente: $PROJECT_DIR/run_insider_analysis_working.sh"
echo "• Editar cron: crontab -e"
echo "• Ver cron actual: crontab -l"
EOF

    sed -i '' "s|PROJECT_DIR_PLACEHOLDER|$PROJECT_DIR|g" "$MONITOR_SCRIPT"
    chmod +x "$MONITOR_SCRIPT"
    echo "✅ Script de monitoreo creado: $MONITOR_SCRIPT"
}

# Ejecutar configuración
echo ""
setup_new_cron

if [[ $? -eq 0 ]]; then
    create_monitor_script
    test_script
    
    echo ""
    echo "🎉 CONFIGURACIÓN COMPLETADA"
    echo "=========================="
    echo "✅ Script de ejecución: $SCRIPT_PATH"
    echo "✅ Monitor: $PROJECT_DIR/monitor_cron.sh"
    echo "✅ Cron configurado para ejecutarse automáticamente"
    echo ""
    echo "📱 COMANDOS ÚTILES:"
    echo "• Monitorear: $PROJECT_DIR/monitor_cron.sh"
    echo "• Ejecutar manual: $SCRIPT_PATH"
    echo "• Ver logs: ls -la $LOG_DIR/"
    echo ""
    echo "🎯 El sistema ejecutará automáticamente:"
    echo "   📅 Lunes a Viernes a las 9:00 AM"
    echo "   📊 Scraper + Análisis + GitHub Pages + Telegram"
    echo "   📄 Logs detallados en $LOG_DIR/"
else
    echo "❌ Error en la configuración"
fi