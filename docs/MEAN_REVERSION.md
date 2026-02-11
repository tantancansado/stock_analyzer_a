# 🔄 Mean Reversion Detector

Sistema automatizado de detección de oportunidades de compra en dips de stocks de calidad.

## 🎯 Concepto

**Mean Reversion** es la estrategia de comprar stocks de alta calidad cuando caen significativamente por debajo de su valor promedio, anticipando que revertirán a la media. Complementa la estrategia VCP (breakouts) permitiendo entradas en dips controlados.

## 📊 Estrategias Implementadas

### 1. 📉 Oversold Bounce
Stocks sobrevendidos con fundamentos sólidos listos para recuperación.

**Criterios:**
- RSI < 30 (oversold)
- Caída > 20% desde máximo reciente
- Cerca de nivel de soporte técnico (dentro del 5%)
- Volumen incrementando en bounce (> 20% promedio)

**Scoring:**
- Oversold: 30 puntos
- Significant dip: 25 puntos
- Near support: 25 puntos
- Volume spike: 20 puntos
- **Total: 100 puntos**

**Ideal para:** Entradas en pánico del mercado o correcciones exageradas

### 2. 📊 Bull Flag Pullback
Retrocesos saludables en tendencias alcistas fuertes.

**Criterios:**
- Rally previo > 30%
- Pullback ordenado 10-15%
- Tendencia mayor alcista (SMA50 > SMA200)
- Volumen decreciente en pullback (< 80% del rally)

**Scoring:**
- Bullish trend: 25 puntos
- Strong rally: 30 puntos
- Healthy pullback: 30 puntos
- Volume decrease: 15 puntos
- **Total: 100 puntos**

**Ideal para:** Entradas en consolidaciones dentro de tendencias alcistas

## 🚀 Uso

### Ejecución Manual

```bash
# Ejecutar detector (escanea primeros 100 tickers de 5D)
python3 mean_reversion_detector.py

# Generar dashboard HTML
python3 mean_reversion_dashboard_generator.py
```

### Ejecución en Pipeline Completo

```bash
# El detector se ejecuta automáticamente en el pipeline completo
./run_full_pipeline.sh
```

El pipeline incluye:
1. Detección de oportunidades Mean Reversion
2. Generación del dashboard HTML
3. Envío de alertas a Telegram

## 📁 Archivos Generados

### CSV
```
docs/mean_reversion_opportunities.csv
```

Contiene todas las oportunidades detectadas con:
- ticker, company_name, strategy
- reversion_score, quality
- current_price, entry_zone, target, stop_loss
- risk_reward ratio
- Métricas técnicas (RSI, drawdown, support/resistance)

### JSON
```
docs/mean_reversion_opportunities.json
```

Formato estructurado para el dashboard:
```json
{
  "scan_date": "2026-02-11 12:27:59",
  "total_opportunities": 41,
  "strategies": {
    "oversold_bounce": 31,
    "bull_flag_pullback": 10
  },
  "opportunities": [...]
}
```

### Dashboard HTML
```
docs/mean_reversion_dashboard.html
```

Dashboard interactivo con:
- Stats overview (total, por estrategia)
- Explicaciones de estrategias
- Top 30 oportunidades en tabla
- Responsive design para móviles
- Navegación integrada con el sistema

## 📱 Alertas de Telegram

El sistema envía alertas automáticas a Telegram con:

**Contenido:**
- Total de oportunidades detectadas
- Breakdown por estrategia (Oversold vs Bull Flag)
- Top 5 oportunidades con:
  - Ticker + nombre de empresa
  - Estrategia y score
  - Precio actual → Target (upside %)
  - Risk/Reward ratio

**Trigger:** Se ejecuta automáticamente en el pipeline completo

**Manual:**
```bash
# Opción 1: Script interactivo
python3 telegram_legendary_alerts.py
# Seleccionar opción 5 (Mean Reversion alerts)

# Opción 2: Pipeline automatizado
python3 auto_telegram_alerts.py
```

## 🔧 Configuración

### Source de Tickers

Por defecto, carga tickers desde:
```
docs/super_opportunities_5d_complete.csv
```

Si no existe, usa watchlist por defecto de 16 stocks.

### Límite de Scan

Por defecto limitado a **100 tickers** para velocidad. Modificar en `mean_reversion_detector.py` línea 372:

```python
if len(tickers) > 100:
    tickers = tickers[:100]  # Cambiar este número
```

### Lookback Period

Por defecto **180 días** (6 meses) de historia. Modificar en `MeanReversionDetector.__init__()`:

```python
self.lookback_days = 180  # Cambiar aquí
```

## 📊 Métricas y Indicadores

### RSI (Relative Strength Index)
- Período: 14 días
- Oversold: < 30
- Usado en estrategia Oversold Bounce

### Support/Resistance Levels
- Window: 20 días
- Método: Rolling min/max con center=True
- Usado para calcular entry zones y targets

### Volume Analysis
- Promedio 20 días vs volumen actual
- Spike detection: > 1.2x promedio
- Decrease detection: < 0.8x promedio de rally

### Moving Averages
- SMA 50: Tendencia corto plazo
- SMA 200: Tendencia largo plazo
- Usado en estrategia Bull Flag

## 📈 Resultados Típicos

De un scan de 100 tickers:
- **Total oportunidades:** 30-50
- **Alta calidad (≥70):** 10-20
- **Excelentes (≥80):** 5-10

**Distribución por estrategia:**
- Oversold Bounce: 70-80%
- Bull Flag Pullback: 20-30%

## 🎯 Quality Tiers

| Score | Tier | Descripción |
|-------|------|-------------|
| ≥ 80 | ⭐⭐⭐ EXCELENTE | Muy alta probabilidad de reversión |
| ≥ 70 | ⭐⭐ MUY BUENA | Alta probabilidad, criterios sólidos |
| ≥ 60 | ⭐ BUENA | Probabilidad moderada, seguimiento |
| < 60 | MODERADA | No incluido en alertas automáticas |

## 💡 Casos de Uso

### 1. Compra en Pánico del Mercado
Usar **Oversold Bounce** durante correcciones generales del mercado:
- RSI extremadamente bajo (< 25)
- Drawdown > 25%
- Fundamentales sólidos intactos

### 2. Entradas en Tendencias Alcistas
Usar **Bull Flag Pullback** en stocks con momentum:
- Rally previo > 40%
- Pullback ordenado 12-15%
- SMA50 bien por encima de SMA200

### 3. Diversificación de Estrategias
Combinar con VCP Scanner:
- **VCP:** Entradas en breakouts
- **Mean Reversion:** Entradas en dips
- **Sector Rotation:** Timing sectorial
- **5D Analysis:** Validación multi-dimensional

## ⚠️ Riesgos y Consideraciones

### 1. Catching Falling Knives
- No todas las caídas revierten
- Verificar fundamentos antes de entrar
- Usar stop loss estrictos

### 2. Market Regime
- Mean reversion funciona mejor en mercados laterales/alcistas
- Cuidado en mercados bajistas sostenidos
- Verificar contexto macro

### 3. Position Sizing
- No sobredimensionar posiciones en dips
- Risk por trade: 1-2% del portfolio
- Usar posiciones más pequeñas que en breakouts

### 4. Timing
- No apresurarse en la entrada
- Esperar confirmación de bounce (volumen, RSI recuperando)
- Entry zone es una guía, no obligación

## 🔄 Integración con Sistema 5D

El Mean Reversion Detector se integra perfectamente con el Sistema 5D:

1. **Input:** Usa tickers de `super_opportunities_5d_complete.csv`
2. **Complemento:** Stocks 5D con dips son oportunidades premium
3. **Validación:** Combinar score 5D con score de reversión
4. **Timing:** Mean reversion puede anticipar breakouts VCP

### Workflow Sugerido
```
1. Scan VCP semanal
2. 5D Analysis (identifica mejores tickers)
3. Mean Reversion (encuentra dips en esos tickers)
4. Dashboard muestra ambas oportunidades
5. Telegram alerta sobre las mejores
```

## 📅 Frecuencia Recomendada

- **Scan completo:** Diario o cada 2 días
- **Review dashboard:** Diario
- **Telegram alerts:** Automático con pipeline
- **Actualización datos:** Con cada pipeline completo

## 🆘 Troubleshooting

### Error: "No hay datos 5D"
**Solución:** Ejecutar primero:
```bash
python3 run_super_analyzer_4d.py
```

### Warning: "Limitando scan a 100 tickers"
**Solución:** Cambiar límite en línea 372 de `mean_reversion_detector.py` o esperar (100 tickers toma ~10-15 min)

### Pocas oportunidades detectadas
**Posibles causas:**
- Mercado en rally fuerte (normal)
- Scores muy estrictos (ajustar thresholds en detector)
- Datos de precios incompletos (verificar yfinance)

## 📚 Referencias

### Libros
- "Mean Reversion Trading Systems" - Howard Bandy
- "Trade Like a Stock Market Wizard" - Mark Minervini (combinar con VCP)

### Papers
- "Does Mean Reversion Work in Stocks?" - Jegadeesh & Titman
- "Contrarian Investment, Extrapolation, and Risk" - Lakonishok et al.

### Indicadores Técnicos
- RSI: J. Welles Wilder (1978)
- Support/Resistance: Charles Dow (Price Action)
- Bull Flags: Thomas Bulkowski (Pattern Recognition)

## 🚀 Mejoras Futuras

- [ ] ML model para predecir probabilidad de reversión
- [ ] Análisis de volumen institucional en dips
- [ ] Correlación con VIX y market fear
- [ ] Backtesting automático de señales
- [ ] Alertas en tiempo real (intraday)
- [ ] Integración con opciones (protective puts)
- [ ] Sector-specific thresholds
- [ ] Earnings calendar integration (evitar reversals pre-earnings)

---

🤖 **Generated by Stock Analyzer System**
Mean Reversion Detector - Buy the Dip Strategy
