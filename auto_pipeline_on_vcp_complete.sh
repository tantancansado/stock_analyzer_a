#!/bin/bash
# AUTO PIPELINE EXECUTOR
# Espera a que termine VCP y automáticamente ejecuta el pipeline completo

VCP_PID=21210
VCP_LOG="/tmp/vcp_scan_sp500_v2.log"

echo "🤖 AUTO-PIPELINE ACTIVADO"
echo "======================================================================"
echo "Esperando a que termine VCP Scanner (PID: $VCP_PID)..."
echo "Cuando termine, ejecutaré automáticamente el pipeline completo."
echo "======================================================================"
echo ""

# Esperar a que termine VCP
while kill -0 $VCP_PID 2>/dev/null; do
    sleep 30
    LAST_LINE=$(tail -1 $VCP_LOG 2>/dev/null | grep -o '\[[0-9]*/[0-9]*\]' || echo "")
    if [ ! -z "$LAST_LINE" ]; then
        echo "$(date '+%H:%M:%S') - VCP en progreso: $LAST_LINE"
    fi
done

echo ""
echo "======================================================================"
echo "✅ VCP SCAN COMPLETADO!"
echo "======================================================================"
echo ""

# Mostrar resumen VCP
echo "📊 RESUMEN VCP:"
tail -20 $VCP_LOG | grep -E "✅|COMPLETADO|patrones|Progreso"
echo ""

LATEST_SCAN=$(find docs/reports/vcp -name "vcp_scan_*" -type d 2>/dev/null | sort -r | head -1)
if [ -d "$LATEST_SCAN" ]; then
    echo "📁 Scan guardado en: $LATEST_SCAN"
    if [ -f "$LATEST_SCAN/data.csv" ]; then
        NUM_PATTERNS=$(tail -n +2 "$LATEST_SCAN/data.csv" 2>/dev/null | wc -l | tr -d ' ')
        echo "📈 Patrones VCP detectados: $NUM_PATTERNS"
    fi
fi

echo ""
echo "======================================================================"
echo "🚀 INICIANDO PIPELINE COMPLETO AUTOMÁTICAMENTE..."
echo "======================================================================"
echo ""

# Ejecutar pipeline completo
./run_full_pipeline.sh

# Verificar si fue exitoso
if [ $? -eq 0 ]; then
    echo ""
    echo "======================================================================"
    echo "✅ PIPELINE COMPLETO EJECUTADO EXITOSAMENTE!"
    echo "======================================================================"
    echo ""

    # Notificación del sistema
    if command -v osascript &> /dev/null; then
        osascript -e 'display notification "Pipeline completo ejecutado! Sistema actualizado." with title "Stock Analyzer ✅" sound name "Glass"'
    fi

    # Opcional: Auto-commit resultados
    echo "💾 Guardando resultados en Git..."
    git add docs/

    # Contar archivos modificados
    CHANGED=$(git diff --cached --stat | tail -1)

    if [ ! -z "$CHANGED" ]; then
        git commit -m "chore: Auto-update - Full pipeline post-VCP $(date +%Y-%m-%d)

🔄 Automated full system update after VCP scan completion

Changes:
- VCP patterns: $NUM_PATTERNS detected
- Sector rotation updated
- 5D analysis refreshed
- Backtest metrics recalculated
- Position sizing updated

$CHANGED

🤖 Auto-executed by auto_pipeline_on_vcp_complete.sh
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

        echo "📤 Pushing to GitHub..."
        git push

        if [ $? -eq 0 ]; then
            echo "✅ Resultados committed y pushed a GitHub!"
        else
            echo "⚠️  Push falló - revisa git status"
        fi
    else
        echo "ℹ️  No hay cambios para commitear"
    fi

    echo ""
    echo "======================================================================"
    echo "🎉 TODO COMPLETO - SISTEMA TOTALMENTE ACTUALIZADO!"
    echo "======================================================================"
    echo ""
    echo "📊 Dashboards disponibles:"
    echo "   - docs/super_dashboard.html"
    echo "   - docs/sector_rotation_dashboard.html"
    echo "   - docs/backtest_dashboard.html"
    echo ""

else
    echo ""
    echo "======================================================================"
    echo "❌ ERROR en pipeline - Revisa los logs arriba"
    echo "======================================================================"
    echo ""

    if command -v osascript &> /dev/null; then
        osascript -e 'display notification "Error en pipeline - Revisa terminal" with title "Stock Analyzer ❌" sound name "Basso"'
    fi
fi
