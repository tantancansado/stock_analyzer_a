# 🔍 Advanced Professional Filters

## Overview

Sistema de filtros profesionales implementado para evitar falsos positivos y mejorar la calidad de oportunidades detectadas. Basado en metodologías de Mark Minervini (Trend Template) y William O'Neil (CAN SLIM).

## Fecha de Implementación
**2026-02-12**

---

## 🎯 Filtros Implementados

### 1. Market Regime Detector 📈
**Archivo:** `market_regime_detector.py`

**Propósito:** Detectar la tendencia general del mercado para evitar operar contra corriente.

**Basado en:** CAN SLIM - "3 de cada 4 stocks siguen la dirección del mercado"

**Analiza:**
- **SPY (S&P 500)** - Mercado general
- **QQQ (Nasdaq 100)** - Tecnología
- **VIX** - Volatilidad/miedo

**Criterios por índice (5 checks):**
1. Precio > 150 MA
2. Precio > 200 MA
3. 150 MA > 200 MA
4. 50 MA > 150 MA > 200 MA (alignment)
5. 200 MA trending up (slope > 0)

**Regímenes:**
- `CONFIRMED_UPTREND` → **TRADE** ✅ (ambos índices fuertes, VIX < 30)
- `UPTREND_PRESSURE` → **CAUTION** ⚠️ (algún índice débil o VIX elevado)
- `CORRECTION` → **AVOID** ❌ (ambos índices débiles o VIX > 30)

**Impacto en scores:**
- AVOID: -15 puntos a todos los stocks
- CAUTION: -5 puntos a todos los stocks
- TRADE: Sin penalización

**Output:** `docs/market_regime.json`

---

### 2. Moving Average Filter 📊
**Archivo:** `moving_average_filter.py`

**Propósito:** Aplicar Minervini Trend Template a stocks individuales.

**Basado en:** Mark Minervini - Trend Template / Stage Analysis

**Criterios (6 checks):**
1. ✅ Precio > 150 MA AND > 200 MA
2. ✅ 150 MA > 200 MA
3. ✅ 200 MA trending up (> 1 mes)
4. ✅ 50 MA > 150 MA > 200 MA (ideal alignment)
5. ✅ Precio >= 30% arriba del 52-week low
6. ✅ Precio dentro del 25% del 52-week high

**Criterios críticos:** 1, 2, 3 son OBLIGATORIOS para pasar

**Resultado:**
- `passes: true/false`
- `score: 0-100` (% de criterios cumplidos)
- `reason`: Explicación del resultado

**Impacto en super_score:**
- ❌ Falla MA filter: -20 puntos
- ✅ Pasa pero score < 80: -5 puntos

---

### 3. Accumulation/Distribution Filter 📈📉
**Archivo:** `accumulation_distribution_filter.py`

**Propósito:** Detectar acumulación institucional vs distribución.

**Basado en:** CAN SLIM - Institutional Sponsorship + Volume patterns

**Analiza (últimos 50 días):**
- Volumen en días alcistas vs días bajistas
- Volumen promedio en días up vs down
- Días con volumen alto + precio alcista (compra institucional)
- Volume surge reciente (últimos 5 días)

**Métricas:**
- `volume_ratio`: Volumen días up / volumen días down
- `up_volume_pct`: % del volumen total en días alcistas
- `institutional_buying`: bool (2+ días de alto volumen + precio up)

**Señales:**
- `STRONG_ACCUMULATION` 🟢 (ratio >= 2.0x, instituciones comprando)
- `ACCUMULATION` 🟡 (ratio >= 1.0x, compra moderada)
- `NEUTRAL` ⚪ (ratio 0.7-1.0x, sin patrón claro)
- `DISTRIBUTION` 🟠 (ratio 0.5-0.7x, venta moderada)
- `STRONG_DISTRIBUTION` 🔴 (ratio < 0.5x, venta agresiva)

**Impacto en super_score:**
- STRONG_DISTRIBUTION: -15 puntos
- DISTRIBUTION: -10 puntos
- A/D score < 50: -5 puntos

---

### 4. Float Filter 📊
**Archivo:** `float_filter.py`

**Propósito:** Identificar stocks con float bajo para mejor movimiento.

**Basado en:** CAN SLIM / Minervini - Preferencia por float bajo-medio

**Categorías:**
- `MICRO_FLOAT` 🔥 (<10M shares) - Muy volátil, score 85
- `LOW_FLOAT` 🟢 (10M-25M) - **IDEAL** para momentum, score 100
- `MEDIUM_FLOAT` 🟡 (25M-50M) - Bueno, score 90
- `HIGH_FLOAT` 🟠 (50M-200M) - Aceptable, score 60
- `MEGA_FLOAT` 🔴 (>200M) - Difícil mover, score 30

**Impacto en super_score:**
- MEGA_FLOAT: -3 puntos (penalización mínima - informacional)

**Nota:** Este filtro es principalmente informativo. Mega caps como NVDA no pasan pero siguen siendo válidos.

---

## 📊 Integración en Pipeline

### Orden de Ejecución

1. **Calcular Super Score Ultimate** (VCP 40% + ML 30% + Fund 30%)
2. **Aplicar Market Regime Detector** (penaliza todos si mercado en corrección)
3. **Aplicar MA Filter** (stock por stock)
4. **Aplicar A/D Filter** (stock por stock)
5. **Aplicar Float Filter** (stock por stock)
6. **Calcular penalizaciones totales**
7. **Ajustar super_score_ultimate** (score original - penalizaciones)
8. **Validar top 20 con web research** (OpportunityValidator)

### Columnas Añadidas al DataFrame

```python
# Market Regime
'market_regime'             # CONFIRMED_UPTREND | UPTREND_PRESSURE | CORRECTION
'market_recommendation'     # TRADE | CAUTION | AVOID

# MA Filter
'ma_filter_pass'           # True/False
'ma_filter_score'          # 0-100
'ma_filter_reason'         # Explicación

# A/D Filter
'ad_signal'                # STRONG_ACCUMULATION | ACCUMULATION | NEUTRAL | DISTRIBUTION | STRONG_DISTRIBUTION
'ad_score'                 # 0-100
'ad_reason'                # Explicación

# Float Filter
'float_category'           # MICRO_FLOAT | LOW_FLOAT | MEDIUM_FLOAT | HIGH_FLOAT | MEGA_FLOAT
'shares_outstanding_millions'  # Float en millones

# Summary
'filter_penalty'           # Total de puntos restados (0-50+)
'filters_passed'           # "X/3" (Market + MA + A/D)
'super_score_before_filters'  # Score original antes de filtros
```

---

## 🎨 Dashboard Actualizado

### Nuevas Columnas en Tabla Principal

| Columna | Descripción | Valores |
|---------|-------------|---------|
| **MA** | Moving Average Filter | ✅ Pass / ❌ Fail |
| **A/D** | Accumulation/Distribution | 🟢🟡⚪🟠🔴 |
| **Filt** | Filtros pasados | X/3 (Market + MA + A/D) |

### Leyenda Actualizada

Incluye explicación de:
- MA: Minervini Trend Template
- A/D: Instituciones comprando vs vendiendo
- Filt: Cuántos filtros profesionales pasa el stock

---

## 📈 Resultados Esperados

### Antes de Filtros (ejemplo)
- 139 stocks analizados
- Score promedio: ~60/100
- Top score: ~90/100

### Después de Filtros
- 139 stocks analizados
- **124 stocks penalizados** (89%)
- **Score promedio: 42.6/100** (↓ 17.4 puntos)
- **Top score: 72.2/100** (↓ ~18 puntos)
- **Penalización promedio: 18.6 puntos**

### Impacto en Validación
- **Antes:** Muchos stocks cerca de ATH pasaban
- **Después:** Solo stocks con pullback adecuado + fundamentales OK
- **Ejemplo:** De 20 top opportunities, solo 1 BUY vs 19 AVOID

---

## 🔧 Uso Standalone

### Market Regime Detector
```bash
python3 market_regime_detector.py
```

### MA Filter
```bash
# Single ticker
python3 moving_average_filter.py --ticker NVDA

# From file
python3 moving_average_filter.py --file docs/super_scores_ultimate.csv --column ticker
```

### A/D Filter
```bash
# Single ticker
python3 accumulation_distribution_filter.py --ticker NVDA

# From file
python3 accumulation_distribution_filter.py --file docs/super_scores_ultimate.csv
```

### Float Filter
```bash
# Single ticker
python3 float_filter.py --ticker SMCI

# From file
python3 float_filter.py --file docs/super_scores_ultimate.csv
```

---

## 📚 Referencias

### Mark Minervini
- **Libro:** "Trade Like a Stock Market Wizard"
- **Método:** Trend Template (8 criterios)
- **Stage Analysis:** Stage 2 (uptrend) es ideal para comprar

### William O'Neil (CAN SLIM)
- **Libro:** "How to Make Money in Stocks"
- **C:** Current Quarterly Earnings
- **A:** Annual Earnings Growth
- **N:** New Product/Service
- **S:** Supply & Demand (float)
- **L:** Leader or Laggard
- **I:** Institutional Sponsorship ← **A/D Filter**
- **M:** Market Direction ← **Market Regime Detector**

---

## ⚙️ Configuración

### Cache Directories
```
cache/market_regime/    # Market regime cache
cache/ma_filter/        # MA filter cache
cache/ad_filter/        # A/D filter cache
cache/float_filter/     # Float filter cache
```

### Outputs
```
docs/market_regime.json     # Market regime report
docs/validation_report.json # Web validation report
docs/super_scores_ultimate.csv  # Final scores with filters
```

### .gitignore
```gitignore
# Advanced filter caches
cache/market_regime/
cache/ma_filter/
cache/ad_filter/
cache/float_filter/
docs/market_regime.json
```

---

## ✅ Checklist de Implementación

- [x] Market Regime Detector creado y testeado
- [x] Moving Average Filter creado y testeado
- [x] Accumulation/Distribution Filter creado y testeado
- [x] Float Filter creado y testeado
- [x] Integración en super_score_integrator.py
- [x] Dashboard actualizado con nuevas columnas
- [x] Workflow de GitHub Actions actualizado
- [x] .gitignore actualizado con nuevos caches
- [x] Documentación completa

---

## 🎯 Próximos Pasos

1. ✅ Monitorear resultados diarios del pipeline
2. ✅ Ajustar penalizaciones si es necesario (actualmente -20 MA, -15 STRONG_DIST, -15 CORRECTION)
3. ✅ Considerar añadir filtro de RS Rating (Relative Strength vs market)
4. ✅ Considerar añadir filtro de Group Strength (sector performance)

---

**Implementado por:** Claude Sonnet 4.5
**Fecha:** 2026-02-12
**Versión:** 1.0
