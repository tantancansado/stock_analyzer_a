# 🎯 Stock Analyzer - On Demand Analysis

## Descripción

Sistema web para analizar **cualquier ticker** que te dé curiosidad, aplicando **TODO el pipeline completo**:

- ✅ VCP Pattern Analysis
- ✅ ML Momentum Scoring
- ✅ Fundamental Analysis
- ✅ Advanced Filters (MA, A/D, Float, Market Regime)
- ✅ Web Validation
- ✅ **Investment Thesis Generation**
- ✅ **BUY/HOLD/AVOID Recommendation**

## Cómo Usar

### 1. Arrancar el Backend

```bash
cd /Users/ale/Documents/stock_analyzer_a
python3 ticker_analyzer_api.py
```

**Output:**
```
🚀 TICKER ANALYZER API SERVER
📡 Server running at http://localhost:5001
🌐 Frontend: Open docs/ticker_analyzer.html
```

### 2. Abrir el Frontend

**Opción A - Desde el navegador:**
```
file:///Users/ale/Documents/stock_analyzer_a/docs/ticker_analyzer.html
```

**Opción B - Abrir desde terminal:**
```bash
open docs/ticker_analyzer.html
```

### 3. Analizar un Ticker

1. Introduce el ticker (ej: `NVDA`, `AAPL`, `TSLA`)
2. Click en **"Analyze Stock"**
3. Espera ~30 segundos (análisis completo)
4. ¡Recibe el reporte completo con tesis de inversión! 📊

## Qué Obtienes

### 📊 Score Final
- **0-100 puntos** con filtros profesionales aplicados
- Traffic light: 🟢 BUY / 🟡 HOLD / 🔴 AVOID

### 📝 Investment Thesis
- **Summary**: Resumen de la oportunidad
- **Strengths**: ✅ Factores positivos
- **Weaknesses**: ❌ Factores de riesgo
- **Entry Timing**: Cuándo entrar
- **Risk Level**: LOW / MEDIUM / HIGH

### 🔍 Component Analysis

**VCP Pattern (40%):**
- Volatility contraction
- Consolidation range
- Pattern detected: Yes/No

**ML Momentum (30%):**
- 20-day momentum
- MA 50 position
- Volume ratio

**Fundamentals (30%):**
- P/E ratio
- PEG ratio
- Market cap quality

### 🔍 Professional Filters

**Market Regime:**
- 🟢 CONFIRMED_UPTREND
- 🟡 UPTREND_PRESSURE
- 🔴 CORRECTION

**MA Filter (Minervini):**
- ✅ Pass: Cumple Trend Template
- ❌ Fail: No cumple criterios

**A/D Signal:**
- 🟢 STRONG_ACCUMULATION
- 🟡 ACCUMULATION
- ⚪ NEUTRAL
- 🟠 DISTRIBUTION
- 🔴 STRONG_DISTRIBUTION

**Float Category:**
- 🔥 MICRO_FLOAT (<10M)
- 🟢 LOW_FLOAT (10-25M)
- 🟡 MEDIUM_FLOAT (25-50M)
- 🟠 HIGH_FLOAT (50-200M)
- 🔴 MEGA_FLOAT (>200M)

**Web Validation:**
- ✅ BUY: Good entry point
- ⚠️ HOLD: Wait for better setup
- ❌ AVOID: Near ATH or valuation risk

### 📈 Stock Information
- Market Cap
- P/E Ratio
- 52-Week High/Low
- Beta
- Industry
- Sector

## API Endpoints

### Health Check
```bash
curl http://localhost:5001/api/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-12T12:00:00.000000"
}
```

### Analyze Ticker
```bash
curl http://localhost:5001/api/analyze/NVDA
```

**Response:** JSON completo con todo el análisis

## Ejemplo de Uso

### Desde Terminal (API directa)
```bash
# Analizar NVDA
curl -s "http://localhost:5001/api/analyze/NVDA" | python3 -m json.tool > nvda_analysis.json

# Ver solo el recommendation
curl -s "http://localhost:5001/api/analyze/AAPL" | jq '.recommendation'
```

### Desde Web (Frontend)
1. Abre `docs/ticker_analyzer.html`
2. Escribe `TSLA`
3. Click "Analyze Stock"
4. **¡Boom!** Reporte completo con tesis de inversión

## Casos de Uso

### ✅ Tickers que te dan curiosidad
```
"Vi a SMCI en las noticias, ¿es buena oportunidad?"
→ Analiza SMCI → Obtienes reporte completo
```

### ✅ Validar ideas de trading
```
"Creo que META está en buen setup"
→ Analiza META → Confirma/rechaza tu tesis
```

### ✅ Investigar nuevos sectores
```
"Quiero explorar semiconductores"
→ Analiza NVDA, AMD, TSM, AVGO → Compara resultados
```

### ✅ Verificar antes de comprar
```
"Estoy a punto de comprar AAPL"
→ Analiza AAPL → Ve si es buen momento de entry
```

## Estructura del Reporte

```
┌─────────────────────────────────────┐
│   AAPL - Apple Inc.                 │
│   Technology                         │
│   $180.50                           │
│                                     │
│   75.5/100                          │
│   🟡 HOLD (LOW confidence)          │
└─────────────────────────────────────┘

📝 Investment Thesis
────────────────────────────────────────
AAPL shows mixed signals. While there
are 2 positive factors, 1 concerns
suggest waiting for better entry...

✅ Strengths:
  • Market in confirmed uptrend
  • Reasonable valuation (P/E: 28.5)

❌ Weaknesses:
  • Too close to ATH (-2.5%) - poor entry

Entry Timing: Wait for pullback
Risk Level: MEDIUM

📊 Component Analysis
────────────────────────────────────────
VCP:        65/100  • Consolidating
ML:         70/100  • Strong momentum
Fundamental: 60/100  • P/E: 28.5

🔍 Professional Filters
────────────────────────────────────────
Market:     🟢 CONFIRMED_UPTREND
MA Filter:  ✅ Passes Minervini Template
A/D:        🟡 ACCUMULATION
Float:      🔴 MEGA_FLOAT
Validation: ⚠️ HOLD

📈 Stock Information
────────────────────────────────────────
Market Cap: $2.8T
P/E Ratio:  28.5
52W High:   $185.00
52W Low:    $125.30
Beta:       1.2
Industry:   Consumer Electronics
```

## Detener el Servidor

```bash
# Buscar PID
ps aux | grep ticker_analyzer_api

# Matar proceso
kill $(cat /tmp/flask_server.pid)

# O simplemente
pkill -f ticker_analyzer_api
```

## Troubleshooting

### Puerto 5001 ocupado
```bash
# Cambiar puerto en ticker_analyzer_api.py línea ~468
app.run(debug=True, host='0.0.0.0', port=5002)  # Cambiar a 5002

# Y en docs/ticker_analyzer.html línea ~482
const API_URL = 'http://localhost:5002';
```

### Flask no instalado
```bash
python3 -m pip install --break-system-packages flask flask-cors
```

### CORS errors en el navegador
- Asegúrate que Flask-CORS está instalado
- Verifica que el servidor está corriendo
- Revisa la consola del navegador (F12)

### Análisis tarda mucho
- Normal! El análisis completo toma 20-40 segundos
- Incluye: VCP, ML, Fundamental, 4 filtros, web validation
- Espera a que aparezca el reporte

## Archivos del Sistema

```
ticker_analyzer_api.py          # Backend Flask (Python)
docs/ticker_analyzer.html       # Frontend (HTML/CSS/JS)
docs/TICKER_ANALYZER_README.md  # Este archivo
```

## Features Futuras (Posibles)

- [ ] Guardar reportes en `docs/ticker_analysis/`
- [ ] Histórico de análisis
- [ ] Comparar múltiples tickers
- [ ] Alertas cuando un ticker mejora su score
- [ ] Export a PDF
- [ ] Gráficos de precio integrados
- [ ] Análisis de opciones
- [ ] Deploy del backend a la nube (Railway/Render)

## Tecnologías Usadas

**Backend:**
- Flask (Web server)
- Flask-CORS (CORS handling)
- yfinance (Stock data)
- pandas, numpy (Data processing)
- All our analysis modules (VCP, ML, Fundamental, Filters)

**Frontend:**
- HTML5
- CSS3 (Glassmorphism design)
- Vanilla JavaScript (No frameworks!)
- Fetch API (AJAX calls)

## Performance

**Análisis completo:**
- ~20-40 segundos por ticker
- Includes: Data fetch + VCP + ML + Fundamental + 4 Filters + Validation

**API latency:**
- Health check: <10ms
- Full analysis: 20-40s (data fetch dominates)

## Seguridad

⚠️ **IMPORTANTE:**
- Este servidor es para **uso local** solamente
- NO expongas el puerto 5001 a internet
- Si quieres deployment público, necesitas:
  - HTTPS
  - Rate limiting
  - API authentication
  - Input validation extra

## Licencia

Uso personal - Stock Analyzer System
© 2026

---

**¡Disfruta analizando stocks on demand! 🚀📊**

Para soporte, reporta issues en el repo o contacta al desarrollador.
