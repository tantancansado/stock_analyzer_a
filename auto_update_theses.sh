#!/bin/bash
# AUTO UPDATE THESES - Actualiza datos y regenera tesis automáticamente
# Uso: ./auto_update_theses.sh [num_tickers]

cd "$(dirname "$0")"

NUM_TICKERS=${1:-50}
LOG_FILE="logs/auto_update_$(date +%Y%m%d_%H%M%S).log"

mkdir -p logs

echo "========================================" | tee -a "$LOG_FILE"
echo "🔄 AUTO UPDATE THESES - $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# 1. Actualizar datos fundamentales y entry scores (top 100)
echo "" | tee -a "$LOG_FILE"
echo "📊 Paso 1: Actualizando datos 5D (sector + fundamentals + entry)..." | tee -a "$LOG_FILE"
python3 enrich_5d.py >> "$LOG_FILE" 2>&1
if [ $? -eq 0 ]; then
    echo "   ✅ Datos 5D actualizados" | tee -a "$LOG_FILE"
else
    echo "   ❌ Error actualizando datos 5D" | tee -a "$LOG_FILE"
    exit 1
fi

# 2. Regenerar tesis para top N
echo "" | tee -a "$LOG_FILE"
echo "📝 Paso 2: Regenerando tesis para top $NUM_TICKERS..." | tee -a "$LOG_FILE"
python3 thesis_generator.py "$NUM_TICKERS" >> "$LOG_FILE" 2>&1
if [ $? -eq 0 ]; then
    echo "   ✅ Tesis regeneradas" | tee -a "$LOG_FILE"
else
    echo "   ❌ Error regenerando tesis" | tee -a "$LOG_FILE"
    exit 1
fi

# 3. Verificar que el archivo JSON se generó correctamente
if [ -f "docs/theses.json" ]; then
    SIZE=$(du -h docs/theses.json | cut -f1)
    COUNT=$(grep -c "\"ticker\"" docs/theses.json)
    echo "" | tee -a "$LOG_FILE"
    echo "✅ Update completado:" | tee -a "$LOG_FILE"
    echo "   - Archivo: docs/theses.json ($SIZE)" | tee -a "$LOG_FILE"
    echo "   - Tesis generadas: $COUNT" | tee -a "$LOG_FILE"
    echo "   - Timestamp: $(date)" | tee -a "$LOG_FILE"
else
    echo "   ❌ Error: theses.json no encontrado" | tee -a "$LOG_FILE"
    exit 1
fi

echo "" | tee -a "$LOG_FILE"
echo "🎯 Proceso completado. Log guardado en: $LOG_FILE" | tee -a "$LOG_FILE"
