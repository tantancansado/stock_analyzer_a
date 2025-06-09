#!/bin/bash
# Script para integrar el sistema histórico con el cron existente

echo "🔗 INTEGRANDO SISTEMA HISTÓRICO CON CRON"
echo "========================================"

# Variables
PROJECT_DIR="/Users/alejandroordonezvillar/Desktop/stockAnalyzer/stock_analyzer_a"
PYTHON_PATH="/usr/bin/python3"
HISTORICO_SCRIPT="sistema_reportes_historicos.py"
CRON_SCRIPT="run_insider_analysis_working.sh"

cd "$PROJECT_DIR"

echo "📁 Directorio: $PROJECT_DIR"
echo "🐍 Python: $PYTHON_PATH"

# Verificar que el script histórico está disponible
if [[ ! -f "$HISTORICO_SCRIPT" ]]; then
    echo "❌ $HISTORICO_SCRIPT no encontrado"
    echo "   Cópialo primero al directorio del proyecto"
    exit 1
fi

# Hacer ejecutable el script histórico
chmod +x "$HISTORICO_SCRIPT"
echo "✅ $HISTORICO_SCRIPT configurado como ejecutable"

# PASO 1: Modificar el script de análisis diario para incluir archivado
echo ""
echo "📝 PASO 1: Modificando script de análisis diario..."

# Crear backup del script actual
cp "$CRON_SCRIPT" "${CRON_SCRIPT}.backup.$(date +%Y%m%d_%H%M%S)"
echo "💾 Backup creado: ${CRON_SCRIPT}.backup.$(date +%Y%m%d_%H%M%S)"

# Verificar si ya tiene integración histórica
if grep -q "sistema_reportes_historicos" "$CRON_SCRIPT"; then
    echo "⚠️ El script ya tiene integración histórica"
    read -p "¿Quieres reemplazarla? (y/N): " replace
    if [[ ! $replace =~ ^[Yy]$ ]]; then
        echo "ℹ️ Manteniendo configuración actual"
    else
        # Eliminar líneas existentes del histórico
        sed -i '' '/sistema_reportes_historicos/d' "$CRON_SCRIPT"
        echo "🔄 Configuración histórica anterior eliminada"
    fi
fi

# Agregar archivado automático antes del exit
# Buscar la línea "log \"🏁 Análisis automático finalizado\"" y agregar antes
if grep -q "🏁 Análisis automático finalizado" "$CRON_SCRIPT"; then
    # Crear archivo temporal con la modificación
    awk '
    /log "🏁 Análisis automático finalizado"/ {
        print ""
        print "# Archivar reportes del día"
        print "log \"📦 Archivando reportes del día...\""
        print "\"$PYTHON_PATH\" \"$PROJECT_DIR/sistema_reportes_historicos.py\" --archivar >> \"$LOG_FILE\" 2>&1"
        print "if [[ $? -eq 0 ]]; then"
        print "    log \"✅ Reportes archivados correctamente\""
        print "else"
        print "    log \"⚠️ Error archivando reportes\""
        print "fi"
        print ""
    }
    { print }
    ' "$CRON_SCRIPT" > "${CRON_SCRIPT}.tmp"
    
    mv "${CRON_SCRIPT}.tmp" "$CRON_SCRIPT"
    chmod +x "$CRON_SCRIPT"
    echo "✅ Archivado diario integrado en $CRON_SCRIPT"
else
    echo "⚠️ No se encontró la línea de finalización esperada"
    echo "   Agregando al final del script..."
    
    # Agregar antes del último exit
    sed -i '' '/^exit \$exit_code$/i\
\
# Archivar reportes del día\
log "📦 Archivando reportes del día..."\
"$PYTHON_PATH" "$PROJECT_DIR/sistema_reportes_historicos.py" --archivar >> "$LOG_FILE" 2>&1\
if [[ $? -eq 0 ]]; then\
    log "✅ Reportes archivados correctamente"\
else\
    log "⚠️ Error archivando reportes"\
fi\
' "$CRON_SCRIPT"
    
    echo "✅ Archivado diario agregado al final del script"
fi

# PASO 2: Configurar cron semanal para resúmenes
echo ""
echo "📅 PASO 2: Configurando cron semanal para resúmenes..."

# Hacer backup del crontab actual
CRON_BACKUP="crontab_backup_historico_$(date +%Y%m%d_%H%M%S).txt"
crontab -l > "$CRON_BACKUP" 2>/dev/null || echo "# No hay crontab previo" > "$CRON_BACKUP"
echo "💾 Backup de crontab: $CRON_BACKUP"

# Crear nuevo crontab temporal
crontab -l 2>/dev/null > /tmp/new_crontab_historico.txt

# Verificar si ya existe entrada para resúmenes semanales
if grep -q "sistema_reportes_historicos.*resumen-semanal" /tmp/new_crontab_historico.txt; then
    echo "⚠️ Ya existe configuración de resúmenes semanales"
    read -p "¿Quieres reemplazarla? (y/N): " replace_weekly
    if [[ $replace_weekly =~ ^[Yy]$ ]]; then
        # Eliminar línea existente
        grep -v "sistema_reportes_historicos.*resumen-semanal" /tmp/new_crontab_historico.txt > /tmp/new_crontab_temp.txt
        mv /tmp/new_crontab_temp.txt /tmp/new_crontab_historico.txt
        echo "🔄 Configuración semanal anterior eliminada"
    else
        echo "ℹ️ Manteniendo configuración semanal actual"
        SKIP_WEEKLY=true
    fi
fi

# Agregar nueva entrada semanal si no se saltó
if [[ "$SKIP_WEEKLY" != "true" ]]; then
    echo "" >> /tmp/new_crontab_historico.txt
    echo "# Resumen semanal de insider trading (domingos 10:00 PM)" >> /tmp/new_crontab_historico.txt
    echo "0 22 * * 0 cd $PROJECT_DIR && $PYTHON_PATH sistema_reportes_historicos.py --resumen-semanal >> logs/weekly_summary.log 2>&1" >> /tmp/new_crontab_historico.txt
    echo "✅ Resumen semanal agregado (domingos 10:00 PM)"
fi

# PASO 3: Configurar limpieza mensual
echo ""
echo "🧹 PASO 3: Configurando limpieza mensual..."

if grep -q "sistema_reportes_historicos.*limpiar" /tmp/new_crontab_historico.txt; then
    echo "⚠️ Ya existe configuración de limpieza mensual"
    read -p "¿Quieres reemplazarla? (y/N): " replace_cleanup
    if [[ $replace_cleanup =~ ^[Yy]$ ]]; then
        grep -v "sistema_reportes_historicos.*limpiar" /tmp/new_crontab_historico.txt > /tmp/new_crontab_temp.txt
        mv /tmp/new_crontab_temp.txt /tmp/new_crontab_historico.txt
        echo "🔄 Configuración de limpieza anterior eliminada"
    else
        echo "ℹ️ Manteniendo configuración de limpieza actual"
        SKIP_CLEANUP=true
    fi
fi

if [[ "$SKIP_CLEANUP" != "true" ]]; then
    echo "" >> /tmp/new_crontab_historico.txt
    echo "# Limpieza mensual de archivos históricos (primer domingo de mes 11:00 PM)" >> /tmp/new_crontab_historico.txt
    echo "0 23 1-7 * 0 cd $PROJECT_DIR && $PYTHON_PATH sistema_reportes_historicos.py --limpiar 45 >> logs/cleanup.log 2>&1" >> /tmp/new_crontab_historico.txt
    echo "✅ Limpieza mensual agregada (primer domingo de mes 11:00 PM)"
fi

# Instalar nuevo crontab
crontab /tmp/new_crontab_historico.txt

if [[ $? -eq 0 ]]; then
    echo "✅ Crontab actualizado exitosamente"
else
    echo "❌ Error actualizando crontab"
    echo "   Restaurando backup..."
    crontab "$CRON_BACKUP"
    exit 1
fi

# Limpiar archivos temporales
rm -f /tmp/new_crontab_historico.txt /tmp/new_crontab_temp.txt

# PASO 4: Crear script de monitoreo histórico
echo ""
echo "📊 PASO 4: Creando script de monitoreo histórico..."

MONITOR_HISTORICO="monitor_historico.sh"

cat > "$MONITOR_HISTORICO" << 'EOF'
#!/bin/bash
# Script para monitorear el sistema histórico

PROJECT_DIR="PROJECT_DIR_PLACEHOLDER"
PYTHON_PATH="PYTHON_PATH_PLACEHOLDER"

echo "📊 MONITOR DEL SISTEMA HISTÓRICO"
echo "================================"

cd "$PROJECT_DIR"

# Mostrar estadísticas generales
echo "📈 ESTADÍSTICAS GENERALES:"
"$PYTHON_PATH" sistema_reportes_historicos.py --estadisticas

echo ""
echo "📅 CRON CONFIGURADO:"
crontab -l | grep -E "(sistema_reportes_historicos|run_insider_analysis)" | nl

echo ""
echo "📁 ESTRUCTURA DE ARCHIVOS:"
if [[ -d "reports/historical" ]]; then
    echo "✅ reports/historical/ existe"
    
    if [[ -d "reports/historical/daily" ]]; then
        daily_count=$(ls -1 reports/historical/daily/ 2>/dev/null | wc -l)
        echo "   📊 Días archivados: $daily_count"
        
        if [[ $daily_count -gt 0 ]]; then
            echo "   📅 Días más recientes:"
            ls -1t reports/historical/daily/ | head -5 | sed 's/^/      /'
        fi
    else
        echo "   ❌ reports/historical/daily/ no existe"
    fi
    
    if [[ -d "reports/historical/summaries" ]]; then
        summaries_count=$(ls -1 reports/historical/summaries/*.json 2>/dev/null | wc -l)
        echo "   📑 Resúmenes semanales: $summaries_count"
        
        if [[ $summaries_count -gt 0 ]]; then
            echo "   📊 Resúmenes más recientes:"
            ls -1t reports/historical/summaries/*.html 2>/dev/null | head -3 | sed 's/^/      /'
        fi
    else
        echo "   ❌ reports/historical/summaries/ no existe"
    fi
else
    echo "❌ reports/historical/ no existe"
fi

echo ""
echo "📄 LOGS RECIENTES:"
echo "• Análisis diario:"
latest_daily=$(ls -t logs/cron_analysis_*.log 2>/dev/null | head -1)
if [[ -n "$latest_daily" ]]; then
    echo "  $(basename "$latest_daily") ($(stat -f %Sm "$latest_daily" 2>/dev/null || stat -c %y "$latest_daily" 2>/dev/null))"
    echo "  Archivado: $(grep -c "✅ Reportes archivados" "$latest_daily" 2>/dev/null || echo "0") veces"
else
    echo "  ❌ Sin logs de análisis diario"
fi

echo "• Resúmenes semanales:"
if [[ -f "logs/weekly_summary.log" ]]; then
    echo "  weekly_summary.log ($(stat -f %Sm logs/weekly_summary.log 2>/dev/null || stat -c %y logs/weekly_summary.log 2>/dev/null))"
else
    echo "  ❌ Sin logs de resúmenes semanales"
fi

echo ""
echo "⚙️ COMANDOS ÚTILES:"
echo "• Ver estadísticas: $PYTHON_PATH sistema_reportes_historicos.py --estadisticas"
echo "• Archivar manual: $PYTHON_PATH sistema_reportes_historicos.py --archivar"
echo "• Resumen semanal: $PYTHON_PATH sistema_reportes_historicos.py --resumen-semanal"
echo "• Ver cron: crontab -l"
echo "• Logs diarios: tail -f logs/cron_analysis_*.log"
EOF

# Reemplazar placeholders
sed -i '' "s|PROJECT_DIR_PLACEHOLDER|$PROJECT_DIR|g" "$MONITOR_HISTORICO"
sed -i '' "s|PYTHON_PATH_PLACEHOLDER|$PYTHON_PATH|g" "$MONITOR_HISTORICO"
chmod +x "$MONITOR_HISTORICO"

echo "✅ Monitor histórico creado: $MONITOR_HISTORICO"

# PASO 5: Probar la integración
echo ""
echo "🧪 PASO 5: Probando la integración..."

read -p "¿Quieres ejecutar una prueba del archivado? (y/N): " test_archive
if [[ $test_archive =~ ^[Yy]$ ]]; then
    echo "🚀 Probando archivado..."
    "$PYTHON_PATH" "$HISTORICO_SCRIPT" --archivar
    
    if [[ $? -eq 0 ]]; then
        echo "✅ Archivado funcionando correctamente"
    else
        echo "❌ Error en el archivado"
    fi
fi

# Resumen final
echo ""
echo "🎉 INTEGRACIÓN COMPLETADA"
echo "========================"
echo "✅ Archivado diario integrado en: $CRON_SCRIPT"
echo "✅ Resumen semanal programado: Domingos 10:00 PM"
echo "✅ Limpieza mensual programada: Primer domingo de mes 11:00 PM"
echo "✅ Monitor histórico disponible: $MONITOR_HISTORICO"
echo ""
echo "📅 PROGRAMACIÓN FINAL:"
echo "• Análisis + Archivado: Lunes a Viernes 9:00 AM"
echo "• Resumen semanal: Domingos 10:00 PM"
echo "• Limpieza mensual: Primer domingo de mes 11:00 PM"
echo ""
echo "📊 MONITOREO:"
echo "• Estado histórico: ./$MONITOR_HISTORICO"
echo "• Análisis diario: ./monitor_cron.sh"
echo "• Estadísticas: $PYTHON_PATH $HISTORICO_SCRIPT --estadisticas"
echo ""
echo "📁 Los reportes se archivarán automáticamente en:"
echo "   reports/historical/daily/YYYY-MM-DD/"
echo ""
echo "🎯 El sistema ahora mantendrá un historial completo de todos los análisis"

# Mostrar crontab final
echo ""
echo "📋 CRONTAB FINAL:"
crontab -l | grep -v "^#" | nl