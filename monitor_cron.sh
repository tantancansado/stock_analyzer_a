#!/bin/bash
# Script para monitorear el cron del análisis

PROJECT_DIR="/Users/alejandroordonezvillar/Desktop/stockAnalyzer/stock_analyzer_a"
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
