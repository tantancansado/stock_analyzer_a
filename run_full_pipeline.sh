#!/bin/bash
# FULL PIPELINE UPDATE - Ejecuta todo el sistema en orden
# Ejecutar después de actualizar VCP o cuando necesites refresh completo

echo ""
echo "🚀 FULL PIPELINE UPDATE"
echo "======================================================================"
echo "Esto ejecutará todos los análisis en el orden correcto:"
echo "  1. Sector Rotation"
echo "  2. 5D Super Analyzer"
echo "  3. Super Dashboard"
echo "  4. Backtest Engine"
echo "  5. Position Sizing"
echo "  6. Earnings Calendar"
echo "  7. Telegram Alerts"
echo "======================================================================"
echo ""

# 1. Sector Rotation (independiente de VCP)
echo "📊 [1/6] Sector Rotation Scan..."
echo "----------------------------------------------------------------------"
python3 sector_rotation_detector.py
if [ $? -ne 0 ]; then
    echo "❌ Error en sector rotation detector"
    exit 1
fi

echo ""
echo "📊 [1/6] Sector Rotation Dashboard..."
python3 sector_rotation_dashboard_generator.py
if [ $? -ne 0 ]; then
    echo "❌ Error en sector rotation dashboard"
    exit 1
fi

# 2. 5D Analysis (usa VCP + insider + institutional + quality + sector)
echo ""
echo "🎯 [2/6] 5D Super Analyzer..."
echo "----------------------------------------------------------------------"
python3 run_super_analyzer_4d.py
if [ $? -ne 0 ]; then
    echo "❌ Error en 5D analyzer"
    exit 1
fi

# 3. Super Dashboard (unifica todo)
echo ""
echo "📈 [3/6] Super Dashboard Generator..."
echo "----------------------------------------------------------------------"
python3 super_dashboard_generator.py
if [ $? -ne 0 ]; then
    echo "❌ Error en super dashboard"
    exit 1
fi

# 4. Backtest
echo ""
echo "📉 [4/6] Backtest Engine..."
echo "----------------------------------------------------------------------"
python3 backtest_engine.py
if [ $? -ne 0 ]; then
    echo "❌ Error en backtest engine"
    exit 1
fi

echo ""
echo "📉 [4/6] Backtest Dashboard..."
python3 backtest_dashboard_generator.py
if [ $? -ne 0 ]; then
    echo "❌ Error en backtest dashboard"
    exit 1
fi

# 5. Position Sizing
echo ""
echo "💰 [5/6] Position Sizing..."
echo "----------------------------------------------------------------------"
python3 position_sizer.py
if [ $? -ne 0 ]; then
    echo "❌ Error en position sizer"
    exit 1
fi

# 6. Earnings Calendar (opcional - tiene timezone issues conocidos)
echo ""
echo "📅 [6/8] Earnings Calendar..."
echo "----------------------------------------------------------------------"
python3 earnings_calendar.py || echo "⚠️  Earnings calendar warning (conocido - no crítico)"

# 7. Mean Reversion Detector (compra en dips)
echo ""
echo "🔄 [7/8] Mean Reversion Detector..."
echo "----------------------------------------------------------------------"
python3 mean_reversion_detector.py
if [ $? -ne 0 ]; then
    echo "⚠️  Error en mean reversion detector (no crítico - continúa)"
fi

echo ""
echo "🔄 [7/9] Mean Reversion Dashboard..."
python3 mean_reversion_dashboard_generator.py
if [ $? -ne 0 ]; then
    echo "⚠️  Error en mean reversion dashboard (no crítico - continúa)"
fi

echo ""
echo "🔄 [7/9] Mean Reversion Backtest..."
python3 mean_reversion_backtester.py
if [ $? -ne 0 ]; then
    echo "⚠️  Error en mean reversion backtest (no crítico - continúa)"
fi

echo ""
echo "🔄 [7/9] Mean Reversion Backtest Dashboard..."
python3 mean_reversion_backtest_dashboard_generator.py
if [ $? -ne 0 ]; then
    echo "⚠️  Error en mean reversion backtest dashboard (no crítico - continúa)"
fi

# 8. Options Flow Detector (whale activity)
echo ""
echo "🐋 [8/10] Options Flow Detector..."
echo "----------------------------------------------------------------------"
python3 options_flow_detector.py
if [ $? -ne 0 ]; then
    echo "⚠️  Error en options flow detector (no crítico - continúa)"
fi

echo ""
echo "🐋 [8/10] Options Flow Dashboard..."
python3 options_flow_dashboard_generator.py
if [ $? -ne 0 ]; then
    echo "⚠️  Error en options flow dashboard (no crítico - continúa)"
fi

# 9. ML Scoring (predictive analysis)
echo ""
echo "🤖 [9/11] ML Scoring System..."
echo "----------------------------------------------------------------------"
python3 ml_scoring.py
if [ $? -ne 0 ]; then
    echo "⚠️  Error en ML scoring (no crítico - continúa)"
fi

# 10. Telegram Alerts (envía notificaciones automáticas)
echo ""
echo "📱 [10/11] Telegram Alerts..."
echo "----------------------------------------------------------------------"
python3 auto_telegram_alerts.py
if [ $? -ne 0 ]; then
    echo "⚠️  Error en telegram alerts (no crítico - continúa)"
fi

echo ""
echo "======================================================================"
echo "✅ PIPELINE COMPLETO - Todo actualizado!"
echo "======================================================================"
echo ""
echo "📊 Dashboards generados:"
echo "  - docs/super_dashboard.html"
echo "  - docs/sector_rotation_dashboard.html"
echo "  - docs/backtest_dashboard.html"
echo "  - docs/mean_reversion_dashboard.html"
echo "  - docs/mean_reversion_backtest_dashboard.html"
echo "  - docs/options_flow_dashboard.html"
echo ""
echo "📁 Datos generados:"
echo "  - docs/super_opportunities_5d_complete.csv"
echo "  - docs/position_sizing.csv"
echo "  - docs/sector_rotation/latest_scan.json"
echo "  - docs/backtest/*.json"
echo "  - docs/mean_reversion_opportunities.csv"
echo "  - docs/options_flow.csv"
echo "  - docs/ml_scores.csv"
echo ""
echo "📱 Alertas enviadas a Telegram"
echo ""
