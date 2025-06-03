#!/bin/bash
# Script para corregir errores comunes PRESERVANDO el índice existente

cd /Users/alejandroordonezvillar/Desktop/stockAnalyzer/stock_analyzer_a

echo "🔧 Iniciando pre-correcciones inteligentes..."

# Asegurar que docs/ existe
mkdir -p docs

# NUEVO: Solo crear index.html si NO existe, para preservar reportes existentes
if [ ! -f docs/index.html ]; then
    echo "🔧 Creando docs/index.html inicial (no existe)..."
    python3 github_pages_uploader.py setup > /dev/null 2>&1
else
    echo "✅ docs/index.html existe, preservando reportes existentes"
fi

# Asegurar que reports/ existe
mkdir -p reports

# Verificar que .nojekyll existe
if [ ! -f docs/.nojekyll ]; then
    echo "🔧 Creando .nojekyll..."
    touch docs/.nojekyll
fi

# Copiar CSV a ubicaciones necesarias
if [ -f reports/insiders_daily.csv ] && [ ! -f insiders_daily.csv ]; then
    cp reports/insiders_daily.csv . 2>/dev/null || true
    echo "📋 CSV copiado para plot_utils"
fi

# Verificar permisos
chmod 644 docs/*.html 2>/dev/null || true

echo "✅ Pre-correcciones completadas - índice preservado"
