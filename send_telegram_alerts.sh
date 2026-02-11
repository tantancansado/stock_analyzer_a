#!/bin/bash
# SEND TELEGRAM ALERTS
# Script para enviar alertas de Telegram manualmente o automáticamente

echo "🤖 TELEGRAM ALERTS - SISTEMA 5D"
echo "========================================================================"
echo ""

# Verificar que existe el CSV de oportunidades
CSV_FILE="docs/super_opportunities_5d_complete.csv"

if [ ! -f "$CSV_FILE" ]; then
    echo "⚠️  No existe $CSV_FILE"
    echo "   Ejecuta primero: python3 run_super_analyzer_4d.py"
    exit 1
fi

# Obtener stats del CSV
NUM_OPPS=$(tail -n +2 "$CSV_FILE" | wc -l | tr -d ' ')
echo "📊 Oportunidades 5D disponibles: $NUM_OPPS"
echo ""

# Ejecutar auto alerts
python3 auto_telegram_alerts.py

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================================================"
    echo "✅ ALERTAS ENVIADAS EXITOSAMENTE"
    echo "========================================================================"
else
    echo ""
    echo "========================================================================"
    echo "❌ ERROR AL ENVIAR ALERTAS"
    echo "========================================================================"
    exit 1
fi
