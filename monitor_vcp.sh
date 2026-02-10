#!/bin/bash
# Monitor VCP Scanner - Notifica cuando termina

echo "🔍 Monitoreando VCP Scanner..."
echo "Presiona Ctrl+C para cancelar"
echo ""

VCP_PID=17708
LOG_FILE="/tmp/vcp_scan_sp500.log"

# Verificar si el proceso sigue corriendo
while kill -0 $VCP_PID 2>/dev/null; do
    # Mostrar última línea del log cada 30 segundos
    LAST_LINE=$(tail -1 $LOG_FILE 2>/dev/null)
    echo "$(date '+%H:%M:%S') - En progreso: $LAST_LINE"
    sleep 30
done

# VCP terminó!
echo ""
echo "======================================================================"
echo "✅ VCP SCAN COMPLETADO!"
echo "======================================================================"
echo ""

# Mostrar resumen del scan
echo "📊 Últimas 20 líneas del log:"
echo "----------------------------------------------------------------------"
tail -20 $LOG_FILE
echo ""

# Verificar si hay resultados
LATEST_SCAN=$(find docs/reports/vcp -name "vcp_scan_*" -type d 2>/dev/null | sort -r | head -1)
if [ -d "$LATEST_SCAN" ]; then
    echo "✅ Resultados encontrados: $LATEST_SCAN"
    if [ -f "$LATEST_SCAN/data.csv" ]; then
        NUM_PATTERNS=$(tail -n +2 "$LATEST_SCAN/data.csv" 2>/dev/null | wc -l | tr -d ' ')
        echo "📈 Patrones VCP detectados: $NUM_PATTERNS"
    fi
else
    echo "⚠️  No se encontraron resultados en docs/reports/vcp/"
fi

echo ""
echo "======================================================================"
echo "🚀 SIGUIENTE PASO: Ejecutar pipeline completo"
echo "======================================================================"
echo ""
echo "Ejecuta:"
echo "  ./run_full_pipeline.sh"
echo ""
echo "Esto actualizará todos los análisis con los datos frescos de VCP."
echo ""

# Notificación del sistema (si está disponible)
if command -v osascript &> /dev/null; then
    osascript -e 'display notification "VCP scan completado! Ejecuta ./run_full_pipeline.sh" with title "Stock Analyzer" sound name "Glass"'
fi
