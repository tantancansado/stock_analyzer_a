# VCP Scanner Output Directory

Este directorio contiene todos los scans VCP históricos y actuales.

## 📁 Estructura Estandarizada

```
docs/reports/vcp/
├── vcp_calibrated_results_YYYYMMDD_HHMMSS.csv  # Resultados CSV con timestamp
├── vcp_scanner_YYYYMMDD_HHMMSS.html            # Visualización HTML con timestamp
├── latest.csv → symlink al CSV más reciente
└── latest.html → symlink al HTML más reciente
```

## 🔄 Formato de Archivos

### CSV Columns:
- `ticker`: Símbolo del stock
- `precio`: Precio actual
- `vcp_score`: Score del patrón VCP (0-100)
- `calidad_patron`: EXCELENTE, BUENA, REGULAR
- `num_contracciones`: Número de contracciones detectadas
- `contracciones`: Secuencia de contracciones (%)
- `profundidad_base`: Profundidad total de la base
- `etapa_analisis`: Etapa de mercado (Stage 1, 2, 3, 4)
- `trend_score`: Score de tendencia (0-100)
- `volumen_score`: Score de volumen (0-100)
- `breakout_potential`: Potencial de breakout (LOW, MEDIUM, HIGH)
- `listo_comprar`: ¿Listo para comprar? (Yes/No)
- `sector`: Sector de la empresa
- `market_cap`: Capitalización de mercado
- `razon`: Razón detallada del patrón

## 🎯 Uso

Los archivos más recientes son accesibles via symlinks:
- `latest.csv` - Último scan en formato CSV
- `latest.html` - Última visualización HTML

El archivo `docs/vcp_scanner.html` (raíz) es una copia del HTML más reciente para fácil acceso desde el dashboard principal.

## 🔍 VCP History Analyzer

El sistema `vcp_history_analyzer.py` escanea este directorio para:
- Identificar "VCP Repeaters" (stocks que forman VCP múltiples veces)
- Calcular consistency scores
- Generar bonus en el sistema 5D

## 📊 Integración con 5D System

El `super_analyzer_4d.py` carga automáticamente el scan VCP más reciente desde este directorio para:
- Dimensión 1: VCP Pattern Quality
- Cross-referencia con Insiders, Sector, Institutional data
- Generación de super scores 5D

## 🗂️ Legacy Format

Archivos antiguos pueden existir en formato:
```
vcp_scan_YYYYMMDD_HHMMSS/
├── data.csv
└── index.html
```

Estos son detectados automáticamente para backward compatibility.
