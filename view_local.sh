#!/bin/bash
# VIEW LOCAL - Servidor HTTP para ver páginas localmente
# Soluciona problemas de CORS al abrir HTMLs directamente

echo "🌐 Iniciando servidor HTTP local..."
echo "=================================="
echo ""
echo "📊 Páginas disponibles:"
echo "  • Super Opportunities:     http://localhost:8888/super_opportunities.html"
echo "  • Institutional Tracker:   http://localhost:8888/institutional_tracker.html"
echo "  • VCP Scanner:             http://localhost:8888/vcp_scanner_results.html"
echo ""
echo "🛑 Presiona Ctrl+C para detener el servidor"
echo ""

cd docs && python3 -m http.server 8888
