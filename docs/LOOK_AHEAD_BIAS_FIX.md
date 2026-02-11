# 🔴 LOOK-AHEAD BIAS FIX - Implementation Guide

**Fecha:** 2026-02-11
**Status:** ✅ PHASE 1 COMPLETADO - Timestamp validation
**Próximo:** 🚧 PHASE 2 EN PROGRESO - Historical scoring

---

## 🎯 OBJETIVO

Eliminar el look-ahead bias que infla los resultados del backtest al usar scores de HOY para simular trades de AYER.

---

## 🚨 PROBLEMA IDENTIFICADO

### Antes del Fix:

```python
# PROBLEMA: Super Score Ultimate generado HOY (2026-02-11)
df = pd.read_csv('docs/super_scores_ultimate.csv')

# BACKTEST: Simular compra hace 6 meses (2025-08-15)
entry_date = "2025-08-15"

# ❌ LOOK-AHEAD BIAS: Usando score del FUTURO
# - VCP score usa precios de hoy
# - ML prediction usa datos de hoy
# - Fundamentals usan earnings reportados después de entry
```

### Resultado:

- ✅ 3M: 90.9% win rate (INFLADO por look-ahead bias)
- ⚠️ 6M: 56.4% win rate (Menos inflado)
- ❌ 1Y: 14.5% win rate (COLAPSO - realidad sin el bias)

---

## ✅ SOLUCIÓN IMPLEMENTADA

### PHASE 1: Timestamp Validation (COMPLETADO)

**1. Modificar Super Score Integrator**

`super_score_integrator.py`:

```python
def integrate_scores(self, reference_date: str = None) -> pd.DataFrame:
    # Store reference date
    self.reference_date = reference_date if reference_date else datetime.now().strftime('%Y-%m-%d')

    # ... existing code ...

def _calculate_super_score(self, df: pd.DataFrame) -> pd.DataFrame:
    # ... existing calculations ...

    # 🔴 FIX LOOK-AHEAD BIAS: Add timestamps
    df['score_timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    df['data_as_of_date'] = self.reference_date

    return df
```

**Columnas agregadas al CSV:**
- `score_timestamp`: Cuándo se generó el score
- `data_as_of_date`: Fecha de los datos usados (pricing, earnings, etc.)

**2. Agregar Validación en Backtest V2**

`backtest_engine_v2.py`:

```python
def _validate_timestamps(self, df: pd.DataFrame, lookback_days: int):
    """Valida que no haya look-ahead bias"""
    reference_date = datetime.now() - timedelta(days=lookback_days)

    # Check 1: ¿Existen timestamps?
    if 'score_timestamp' not in df.columns or 'data_as_of_date' not in df.columns:
        print("⚠️  WARNING: No timestamp columns - LOOK-AHEAD BIAS RISK")
        return

    # Check 2: ¿Data as of > entry date?
    df['data_as_of_date_parsed'] = pd.to_datetime(df['data_as_of_date'])
    future_data_count = len(df[df['data_as_of_date_parsed'] > reference_date])

    if future_data_count > 0:
        print(f"🚨 LOOK-AHEAD BIAS DETECTED!")
        print(f"🚨 {future_data_count} scores use data AFTER entry date")
        print(f"🚨 Backtest results are INVALID")
```

**3. Crear Historical Scorer**

`historical_scorer.py`:

```python
# Genera snapshots de scores en fechas pasadas
python3 historical_scorer.py --backtest  # 3M, 6M, 1Y
python3 historical_scorer.py --weekly --weeks 52  # 1 año semanal
python3 historical_scorer.py --dates 2025-11-13 2025-08-15
```

---

## 📊 RESULTADOS DESPUÉS DEL FIX

### Validación Automática:

```bash
$ python3 backtest_engine_v2.py

🔬 EJECUTANDO BACKTEST V2 (MEJORADO)
======================================================================

   🚨 LOOK-AHEAD BIAS DETECTED!
   🚨 135 scores use data AFTER entry date
   🚨 Entry date: 2025-11-13
   🚨 Data as of: 2026-02-11
   🚨 Backtest results are INVALID
```

✅ **El sistema ahora DETECTA el look-ahead bias automáticamente**

---

## ✅ PHASE 2: Historical Scoring (CASI COMPLETADO - 90%)

**Status:** Todos los scorers modificados exitosamente + pipeline automatizado. Pendiente: testing y generación de snapshots.

### 🎉 IMPLEMENTACIONES COMPLETADAS (2026-02-11):

**1. VCP Scanner** (`vcp_scanner_usa.py`) ✅
- Añadido parámetro `--as-of-date` en CLI
- Modificado `DataProvider.get_stock_data()` para aceptar `as_of_date`
- Cambiado de `period='1y'` a rango de fechas (start/end) en `ticker.history()`
- Propagado `as_of_date` por toda la cadena: DataProvider → CalibratedVCPScanner → VCPScannerEnhanced
- Commit: `db1edcc` - "feat: Add --as-of-date parameter to VCP Scanner"

**2. ML Scoring** (`ml_scoring.py`) ✅
- Añadido parámetro `--as-of-date` en CLI
- Modificado `MLScorer.__init__()` para aceptar `as_of_date`
- Actualizado `calculate_features()` para usar rango de fechas (6 meses hasta `as_of_date`)
- Añadido argparse para manejo de argumentos
- Commit: `0cdbb18` - "feat: Add --as-of-date parameter to ML Scoring"

**3. Fundamental Scorer** (`fundamental_scorer.py`) ✅
- Añadido parámetro `--as-of-date` en CLI
- Modificado `FundamentalScorer.__init__()` para almacenar `as_of_date_dt`
- Actualizado `_get_quarterly_earnings()` para filtrar earnings por fecha de reporte
- Actualizado `_get_financials()` para filtrar quarterly financials y balance sheet por fecha
- Actualizado `_get_price_history()` para usar rango de fechas en vez de period
- Commit: `06ee709` - "feat: Add --as-of-date parameter to Fundamental Scorer"

**4. Super Score Integrator** (`super_score_integrator.py`) ✅
- Añadido parámetro `--as-of-date` en CLI
- Modificado `SuperScoreIntegrator.__init__()` para aceptar `as_of_date`
- Actualizado `integrate_scores()` para usar `as_of_date` en `reference_date`
- Añadida documentación completa del workflow histórico en help text
- Commit: `9516926` - "feat: Add --as-of-date parameter to Super Score Integrator"

**5. Historical Scorer** (`historical_scorer.py`) ✅
- Reescrito `generate_snapshot()` para ejecutar pipeline completo vía subprocess
- Pipeline automatizado: VCP Scanner → ML Scoring → Fundamental Scoring → Super Score Integration
- Cada componente ejecutado con `--as-of-date` parameter para consistencia histórica
- Añadido flag `--run-vcp` (VCP opcional, tarda 15-20 min)
- Parámetro `skip_vcp` (default True) para acelerar generación de snapshots
- Actualizado CLI con confirmación para operaciones largas (52 snapshots semanales)
- Snapshots guardados en `docs/historical_scores/{date}_scores.csv`
- Commit: `228bb07` - "feat: Automate historical scoring pipeline in historical_scorer.py"

### Componentes a Modificar (Documentación Original):

**1. VCP Scanner** (`vcp_scanner_usa.py`):

```python
# AGREGAR: --as-of-date parameter
python3 vcp_scanner_usa.py --sp500 --as-of-date 2025-08-15

# Usar solo precios hasta 2025-08-15
data_end_date = args.as_of_date if args.as_of_date else datetime.now()
prices = yf.download(ticker, start=start_date, end=data_end_date)
```

**2. ML Predictor** (`ml_scoring.py`):

```python
# AGREGAR: Training cutoff date
def train_model(self, cutoff_date: str = None):
    """Train usando solo data <= cutoff_date"""
    if cutoff_date:
        self.data = self.data[self.data['date'] <= cutoff_date]

    # Train model...
```

**3. Fundamental Scorer** (`fundamental_scorer.py`):

```python
# AGREGAR: Earnings date filtering
def get_fundamentals(self, ticker: str, as_of_date: str = None):
    """Get fundamentals reportados ANTES de as_of_date"""
    earnings = self.get_earnings(ticker)

    if as_of_date:
        # Filtrar solo earnings reportados antes de as_of_date
        earnings = earnings[earnings['report_date'] <= as_of_date]

    return earnings
```

### Workflow Propuesto:

```bash
# 1. Generar scores históricos (ejemplo: 6M atrás)
AS_OF_DATE="2025-08-15"

python3 vcp_scanner_usa.py --sp500 --as-of-date $AS_OF_DATE
python3 ml_scoring.py --as-of-date $AS_OF_DATE
python3 fundamental_scorer.py --vcp --as-of-date $AS_OF_DATE
python3 super_score_integrator.py --reference-date $AS_OF_DATE

# 2. Output: docs/historical_scores/2025-08-15_scores.csv

# 3. Backtest con scores históricos
python3 backtest_engine_v2.py --historical-scores docs/historical_scores/2025-08-15_scores.csv --lookback-days 180
```

---

## ⏱️ TIMELINE ESTIMADO

| Fase | Tarea | Tiempo | Status |
|------|-------|--------|--------|
| **PHASE 1** | Timestamp validation | 1 día | ✅ COMPLETADO |
| **PHASE 2** | Modify VCP scanner | 2-3 días | ✅ COMPLETADO |
| | Modify ML predictor | 2-3 días | ✅ COMPLETADO |
| | Modify Fundamental scorer | 2-3 días | ✅ COMPLETADO |
| | Modify Super Score Integrator | 1 día | ✅ COMPLETADO |
| | Test historical integration | 1 día | 🚧 PENDING |
| **PHASE 3** | Generate 52 weekly snapshots | 2-4 horas | 🚧 PENDING |
| | Re-run backtest V2 with clean data | 1 hora | 🚧 PENDING |
| | Analyze results | 1 día | 🚧 PENDING |
| **TOTAL** | | **2 semanas** | **~60% COMPLETADO** ✅ |

---

## 🎯 EXPECTATIVAS POST-FIX

### Cambios Esperados en Resultados:

| Período | V1 (Con Bias) | V2 (Sin Bias Esperado) | Cambio |
|---------|---------------|------------------------|--------|
| **3M** | 90.9% WR | ~65-70% WR | -20 a -25 pts |
| **6M** | 56.4% WR | ~50-55% WR | -5 a -10 pts |
| **1Y** | 14.5% WR | ~40-50% WR | +25 a +35 pts |

**Rationale:**

1. **3M performance bajará** porque scores de hoy NO predicen bien trades de hace 3 meses
2. **6M bajará menos** (ya estaba degradado por bias parcial)
3. **1Y MEJORARÁ** porque usaremos scores reales de hace 1 año (no inflados)

### Métricas Objetivo (Post-Fix):

- ✅ Win Rate: 55-60% (consistente en todos los períodos)
- ✅ Sharpe Ratio: 0.4-0.6 (sin inflación artificial)
- ✅ Profit Factor: 2.0-2.5 (realista)
- ✅ Avg Return: 3-5% por trade (sostenible)

---

## 📖 USO ACTUAL

### ✅ Generar Scores Históricos SIN Look-Ahead Bias:

```bash
# 1. Definir fecha histórica
AS_OF_DATE="2025-08-15"

# 2. Ejecutar cada scorer con la misma fecha
python3 vcp_scanner_usa.py --sp500 --as-of-date $AS_OF_DATE
python3 ml_scoring.py --as-of-date $AS_OF_DATE
python3 fundamental_scorer.py --vcp --as-of-date $AS_OF_DATE

# 3. Integrar scores
python3 super_score_integrator.py --as-of-date $AS_OF_DATE

# Output:
# - docs/super_scores_ultimate.csv (con score_timestamp y data_as_of_date)
# - Todos los scores usan SOLO datos disponibles hasta AS_OF_DATE
```

### ✅ Generar Scores Actuales (modo normal):

```bash
# Sin --as-of-date usa datos de hoy
python3 vcp_scanner_usa.py --sp500
python3 ml_scoring.py
python3 fundamental_scorer.py --vcp
python3 super_score_integrator.py
```

### ✅ Validar Look-Ahead Bias en Backtest:

```bash
# Backtest V2 valida automáticamente los timestamps
python3 backtest_engine_v2.py

# Si hay bias, imprime:
# 🚨 LOOK-AHEAD BIAS DETECTED!
# 🚨 135 scores use data AFTER entry date
# 🚨 Backtest results are INVALID
```

### 🚧 Generar Snapshots Semanales (PENDING):

```bash
# TODO: Actualizar historical_scorer.py para usar --as-of-date
# Fechas clave (3M, 6M, 1Y)
python3 historical_scorer.py --backtest

# Snapshots semanales
python3 historical_scorer.py --weekly --weeks 52
```

---

## ✅ CHECKLIST DE IMPLEMENTACIÓN

### Phase 1: Timestamp Validation ✅ COMPLETADO

- [x] Modificar `super_score_integrator.py` para agregar timestamps
- [x] Modificar `backtest_engine_v2.py` para validar timestamps
- [x] Crear `historical_scorer.py` para snapshots
- [x] Re-generar scores con timestamps
- [x] Validar detección de look-ahead bias
- [x] Documentar fix en `LOOK_AHEAD_BIAS_FIX.md`

### Phase 2: Historical Scoring ✅ 90% COMPLETADO

- [x] Modificar `vcp_scanner_usa.py` para `--as-of-date` ✅
- [x] Modificar `ml_scoring.py` para cutoff date ✅
- [x] Modificar `fundamental_scorer.py` para earnings filtering ✅
- [x] Modificar `super_score_integrator.py` para timestamp consistency ✅
- [x] Actualizar `historical_scorer.py` para automation ✅
- [ ] Testear scoring histórico (sample date: 2025-08-15) 🚧
- [ ] Generar 52 snapshots semanales 🚧
- [ ] Validar calidad de snapshots 🚧

### Phase 3: Re-validation 🚧 PENDIENTE

- [ ] Re-ejecutar Backtest V2 con scores limpios
- [ ] Comparar V1 (con bias) vs V2 (sin bias)
- [ ] Re-optimizar thresholds si necesario
- [ ] Walk-forward validation
- [ ] Documentar resultados finales

---

## 📝 REFERENCIAS

- **Backtest V2 Results:** `docs/BACKTEST_V2_RESULTS.md`
- **Comprehensive Analysis:** `docs/BACKTEST_ANALYSIS.md`
- **Code Files:**
  - `super_score_integrator.py` (Timestamp generation)
  - `backtest_engine_v2.py` (Timestamp validation)
  - `historical_scorer.py` (Snapshot generation)

---

**Actualizado:** 2026-02-11
**Status:** Phase 1 COMPLETADO ✅ | Phase 2 90% COMPLETADO ✅🚧 | Phase 3 PENDIENTE
**Completado Hoy:**
- ✅ VCP Scanner con --as-of-date (Commit: db1edcc)
- ✅ ML Scoring con --as-of-date (Commit: 0cdbb18)
- ✅ Fundamental Scorer con --as-of-date (Commit: 06ee709)
- ✅ Super Score Integrator con --as-of-date (Commit: 9516926)
- ✅ Historical Scorer automation (Commit: 228bb07)

**Próximo Paso:** Testing con fecha ejemplo (2025-08-15) y generación de snapshots
