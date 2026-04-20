# 🌟 SISTEMA 5D - DOCUMENTACIÓN COMPLETA

## Resumen Ejecutivo

El **Super Analyzer 5D** es un sistema avanzado de análisis de acciones que combina 5 dimensiones independientes para identificar las mejores oportunidades de inversión.

## Las 5 Dimensiones

### 1️⃣ **VCP Patterns (30%)**
- **Qué es:** Volatility Contraction Pattern - patrón técnico de Mark Minervini
- **Scoring:** 0-100 basado en calidad del patrón
- **Fuente:** vcp_scanner.py + análisis técnico
- **Key Metrics:**
  - Contracciones progresivas
  - Base depth (profundidad de la base)
  - Stage analysis
  - Price action near breakout

### 2️⃣ **Recurring Insiders (25%)**
- **Qué es:** Compras recurrentes de insiders (directores, ejecutivos)
- **Scoring:** 0-100 basado en confianza
- **Fuente:** insider_tracker.py
- **Key Metrics:**
  - Frecuencia de compras
  - Número de insiders diferentes
  - Volumen total comprado
  - Timing de las compras

### 3️⃣ **Sector Enhancement (20%)** ⭐ NUEVO
- **Qué es:** Análisis dinámico del estado sectorial usando DJ Sectorial (140 índices)
- **Scoring:** 0-100 basado en:
  - **Ranking sectorial (50%):** Posición del sector (1-140)
  - **RSI sectorial (30%):** Momentum técnico del sector
  - **Estado del sector (20%):** 🔴 FUERTE / 🟡 CERCA / 🟢 OPORTUNIDAD
- **Tier Boost:** +0 a +10 puntos adicionales al score total
  - Top 10 sectores + improving momentum: +10
  - Top 25 sectores + stable: +7
  - Top 50 sectores: +3
- **Momentum Detection:**
  - **improving:** Sector ganando fuerza (RSI 50-70 o <30 oversold bounce)
  - **declining:** Sector perdiendo fuerza (RSI >70 overbought)
  - **stable:** Sector neutral (RSI 30-50)
- **Fuente:** sector_enhancement.py + dj_sectorial_analysis.csv

### 4️⃣ **Institutional Buying (25%)**
- **Qué es:** Actividad de compra de ballenas institucionales
- **Scoring:** 0-100 basado en:
  - Número de ballenas con posiciones
  - Valor total de holdings
  - Cambios recientes en posiciones
- **Fuente:** institutional_tracker.py + whale data
- **Top Whales:** BlackRock, Vanguard, State Street, etc.

### 5️⃣ **Fundamental Analysis + Price Targets** ⭐ NUEVO
- **Qué es:** Análisis fundamental completo con precio objetivo calculado
- **Componentes:**

#### Price Target Calculation:
- **DCF (40%):** Discounted Cash Flow simplificado
  - Proyección FCF a 5 años
  - Terminal value con perpetuity growth 3%
  - Discount rate 10% (WACC estimado)
- **P/E Multiple (30%):** Múltiplo de ganancias
  - Forward earnings proyectadas
  - P/E sectorial aplicado
- **Analyst Consensus (30%):** Consenso de analistas
  - Target mean de yfinance
  - Ponderado por número de analistas

#### Fundamental Score (0-100):
Evaluación multi-dimensional:
- **Valoración (20 pts):** PEG ratio óptimo
- **FCF Yield (20 pts):** Free Cash Flow Yield
- **Salud Financiera (20 pts):** Debt/Equity, Current Ratio
- **Rentabilidad (20 pts):** ROE (Return on Equity)
- **Crecimiento (20 pts):** Revenue Growth

#### Métricas Incluidas:
- P/E Ratio, PEG Ratio
- Price to Book, Price to Sales
- FCF, Operating Cash Flow
- Debt to Equity, Current Ratio
- ROE, ROA, Profit Margin
- Revenue Growth, Earnings Growth

## Score Total 4D (Base)

```
Super Score 4D = (VCP × 0.30) + (Insiders × 0.25) + (Sector × 0.20) + (Institutional × 0.25)
```

## Score Final 5D (Con Boost)

```
Super Score 5D = Super Score 4D + Tier Boost (0-10)
```

## Clasificación de Oportunidades

| Score | Tier | Descripción |
|-------|------|-------------|
| ≥85 | ⭐⭐⭐⭐ LEGENDARY | Confirmación cuádruple - Oportunidad HISTÓRICA |
| 75-84 | ⭐⭐⭐ ÉPICA | Triple/Cuádruple confirmación - Altísima probabilidad |
| 65-74 | ⭐⭐ EXCELENTE | Doble confirmación sólida |
| 55-64 | ⭐ BUENA | Señales positivas |
| <55 | 🔵 MODERADA | Seguimiento recomendado |

## Output CSV (27 Columnas)

### Core (4):
- ticker
- super_score_5d
- tier
- description

### 4 Dimensiones Base (4):
- vcp_score
- insiders_score
- sector_score
- institutional_score

### Sector Enhancement (4):
- sector_name
- sector_momentum
- tier_boost
- dj_ticker

### Price Targets (6):
- current_price
- price_target
- upside_percent
- analyst_target
- analyst_upside
- num_analysts

### Fundamental Analysis (6):
- fundamental_score
- pe_ratio
- peg_ratio
- fcf_yield
- roe
- revenue_growth

### Institutional Details (2):
- num_whales
- top_whales

## Dashboard Visualización

### Hero Section:
- **Total 5D Opportunities**
- **Legendary Count**
- **Avg Score**

### Top 10 Table (8 columnas):
1. # (ranking)
2. Ticker
3. 5D Score (coloreado por tier)
4. Tier (con emojis)
5. **Sector** (badge con momentum)
   - 🟢 Verde: improving
   - 🔴 Rojo: declining
   - 🔵 Azul: stable
6. **Target / Upside** (precio objetivo + %)
   - Verde: >20% upside
   - Azul: >0% upside
   - Rojo: <0% downside
7. Indicators (🐋 whales count)
8. Earnings (⚠️ próximos earnings)

## Flujo de Ejecución

### Análisis Completo:
```bash
python3 run_super_analyzer_4d.py
```

Proceso:
1. Carga datos VCP (vcp_scan_*.csv)
2. Carga recurring insiders (recurring_insiders.csv)
3. **Carga DJ Sectorial (140 sectores)**
4. Carga institutional data (whale_scan_*.json)
5. Para cada ticker:
   - Calcula VCP score
   - Calcula insider score
   - **Calcula sector score dinámico**
   - **Detecta sector momentum**
   - **Calcula tier boost**
   - Calcula institutional score
   - **Obtiene datos fundamentales (yfinance)**
   - **Calcula price target combinado (DCF+P/E+Analistas)**
   - **Calcula fundamental score**
   - Suma weighted score 4D
   - Aplica tier boost → Score 5D final
6. Ordena por score 5D
7. Genera CSV con 27 columnas
8. Genera reporte visual

### Integración en Pipeline Diario:
```bash
python3 run_all_scanners.py
```

Fases:
- FASE 1-7: VCP, Insiders, Sectorial, Institutional, 4D merge
- FASE 8: Earnings Calendar enrichment
- FASE 9: Backtest Snapshot creation
- FASE 10: Telegram alerts

## Mejoras vs Sistema 4D Anterior

| Aspecto | Antes (4D) | Ahora (5D) |
|---------|-----------|-----------|
| **Sector Score** | Hardcoded = 50 | Dinámico 0-100 basado en DJ |
| **Sector Info** | Solo score | Score + momentum + boost + nombre |
| **Tier Boost** | No existe | +0 a +10 por sector fuerte |
| **Price Targets** | ❌ No | ✅ Combinado (DCF+P/E+Analistas) |
| **Fundamental Analysis** | ❌ No | ✅ Completo (FCF, ROE, P/E, PEG) |
| **CSV Columns** | 9 | 27 |
| **Dashboard Columns** | 6 | 8 |
| **Upside Calculation** | ❌ No | ✅ Target vs Current |
| **Sector Badges** | ❌ No | ✅ Coloreados por momentum |
| **Fundamental Score** | ❌ No | ✅ 0-100 multi-dimensional |

## Ejemplo de Output

### Ticker: AAPL

**4D Scores:**
- VCP: 85/100
- Insiders: 70/100
- Sector: 77.96/100 (Technology) ⬆️ improving
- Institutional: 90/100

**Base Score 4D:** 80.49
**Tier Boost:** +3 (sector fuerte)
**Score 5D Final:** 83.49 ⭐⭐⭐ ÉPICA

**Price Targets:**
- Current: $278.12
- Target: $265.85
- Upside: -4.4% ⚠️

**Fundamentals:**
- Fundamental Score: 45/100
- P/E: 28.5
- PEG: 2.1
- FCF Yield: 3.2%
- ROE: 147%

**Institutional:**
- Whales: 15
- Top: BlackRock, Vanguard, State Street

## Archivos del Sistema

### Core:
- `super_analyzer_4d.py` - Motor principal 5D
- `run_super_analyzer_4d.py` - Script de ejecución completo
- `run_all_scanners.py` - Pipeline automático diario

### Módulos Nuevos:
- `sector_enhancement.py` - Sector scoring + tier boost
- `fundamental_analyzer.py` - Price targets + fundamental analysis

### Módulos Existentes:
- `vcp_scanner.py` - Detección de patrones VCP
- `insider_tracker.py` - Compras de insiders recurrentes
- `institutional_tracker.py` - Actividad de ballenas
- `earnings_calendar.py` - Próximos earnings

### Output:
- `docs/super_opportunities_5d_complete.csv` - CSV completo 27 columnas
- `docs/super_opportunities_5d_complete_with_earnings.csv` - Con earnings
- `docs/index.html` - Dashboard principal
- `docs/backtest_dashboard.html` - Sistema de backtesting

## Testing

### Test Rápido:
```bash
python3 -c "
from super_analyzer_4d import SuperAnalyzer4D
analyzer = SuperAnalyzer4D()
print('✅ Sistema 5D operativo')
"
```

### Test Individual de Módulos:
```bash
# Sector Enhancement
python3 sector_enhancement.py

# Fundamental Analyzer
python3 fundamental_analyzer.py
```

## Próximas Mejoras Potenciales

1. **Machine Learning Score:** Añadir predicción ML como 6ta dimensión
2. **Sentiment Analysis:** Integrar análisis de noticias y redes sociales
3. **Options Flow:** Incluir unusual options activity
4. **Short Interest:** Añadir datos de short interest y squeeze potential
5. **Sector Rotation:** Predicción de rotación sectorial
6. **Risk Score:** Calcular risk/reward ratio automático

## Notas Importantes

- Los datos fundamentales se obtienen en tiempo real de yfinance (puede ser lento)
- El DCF es simplificado (no considera net debt en equity value)
- Los pesos de las dimensiones pueden ajustarse según performance
- El tier boost es acumulativo (puede llevar scores >100)
- No todos los tickers tendrán datos fundamentales completos

---

**Versión:** 5.0
**Última actualización:** 2026-02-08
**Autor:** Stock Analyzer Team + Claude Sonnet 4.5
