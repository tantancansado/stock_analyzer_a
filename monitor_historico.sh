#!/bin/bash
# Script para monitorear el sistema histórico

PROJECT_DIR="/Users/alejandroordonezvillar/Desktop/stockAnalyzer/stock_analyzer_a"
PYTHON_PATH="/usr/bin/python3"

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
