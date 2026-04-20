# Cerebro — Review de lógica detectado durante refactor

Notas surgidas al extraer helpers a `cerebro_lib/`. No se cambia comportamiento:
se documenta aquí para que el usuario decida prioridad.

## Issues encontrados

### 1. Código muerto con walrus-operator (`scan_value_traps`, línea ~947 original)
```python
ticker=ticker if (ticker := t) else t
```
`(ticker := t)` asigna `ticker = t` y evalúa `t`, por lo que toda la expresión
se reduce a `ticker=t`. **Arreglado en este refactor** al extraer `score_value_trap`.

### 2. `compute_convergence_score` — saturación rápida al tope (NO arreglado)
Fórmula actual: `len(strategies) × 20 + bonuses`, cap en 100.
- 4 estrategias ya da 80 → cualquier bonus → 100.
- 5 estrategias da 100 por sí solo; los bonuses no diferencian nada.
- `int()` trunca (`99.9 → 99`). Considerar `round()`.

**Decisión**: no se arregla. En la última ejecución real solo hay 2 convergencias
triple+, cero quadruple+. La saturación casi no dispara. Cambiar la fórmula
movería scores que los usuarios ya ven en UI — no merece la pena sin feedback.

### 3. Streak bonus es escalón de 0→10 en `streak_days >= 3`
Un ticker con streak=2 y streak=30 reciben bonus idéntico. Más natural sería
`min(15, streak * 2)` o similar (persistencia tiene valor creciente).

### 4. `value_score=0` silencioso en convergencia
`if "VALUE" in strategies and m.get("value_score")` trata `0` como falsy.
Consistente con CLAUDE.md (0 = hard-reject), pero el comportamiento no es
obvio. Si un día se normalizan los scores negativos a 0, sigue filtrando
correctamente — pero un lector del código puede no notarlo.

### 5. `generate_alerts` — EU insiders completamente ausentes (ARREGLADO)
`generate_alerts` solo cargaba `recurring_insiders.csv` (US), nunca
`eu_recurring_insiders.csv`. Resultado: 35+ tickers EU con insider buying
no disparaban alertas. Ahora se concatena ambos y se dedupe por ticker
(keep max purchase_count).

### 6. `scan_entry_signals` — `sector_df.nlargest(5, rcol)` con `try/except` vacío
Línea 585-589: si `sector_rotation.csv` tiene `rs_score` con NaN o tipo no
numérico, el `nlargest` puede fallar silenciosamente y `fav_sectors` queda
vacío sin aviso. Merecería un log en lugar del `pass` mudo.

### 7. 30+ scan functions todas leen `docs/*.csv` por su cuenta (ARREGLADO)
Cada función hacía su propio `load_csv(DOCS/"value_opportunities.csv")`:
`value_opportunities.csv` se leía 18 veces, EU 18 veces, `recurring_insiders` 7
veces, etc. Añadido cache por ejecución (`_CSV_CACHE` en cerebro.py): cada
ruta se lee una sola vez; los callers reciben `.copy()` para no pisarse.
`main()` limpia el cache al arrancar. Tests en `test_cerebro_csv_cache.py`.

### 8. `_parse_health` vs `sf` inconsistencia en manejo de strings
`sf("5.0") → 5.0`. `_parse_health({"x":"5.0"}) → {"x":"5.0"}` (string sin
convertir). Quien consuma `parse_health_details` tiene que aplicar `sf()`
después. Documentado en docstring, no es bug pero es tropiezo fácil.

### 9. Groq rate-limit sin backoff en bucle
`ai()` captura `Exception` y printea, pero en funciones que llaman `ai()`
10-20 veces (e.g. `scan_convergence` top 3, pero otras hacen más) no hay
pause entre llamadas. Si Groq empieza a 429, todas fallan. Valorar
añadir un counter + sleep o un pool compartido.

## Ya refactorizado (sin cambio de comportamiento)

Helpers → `cerebro_lib.io`:
- `load_csv`, `load_json`, `save_json`, `sf`, `parse_health_details`

Scorers → `cerebro_lib.scoring`:
- `compute_convergence_score`
- `score_value_trap` (+ fix de walrus-operator muerto)
- `score_smart_money`
- `score_insider_cluster`
- `score_dividend_safety`
- `classify_piotroski_trend` + `classify_piotroski_signal`

Performance:
- CSV cache de ejecución en `cerebro.py` — cada `docs/*.csv` se lee una vez
  (antes `value_opportunities.csv` se leía 18×).

Bug fixes:
- `generate_alerts` ahora incluye EU insiders (35+ alertas que se perdían).

## Cobertura de tests añadida

| Archivo | Tests |
|---------|-------|
| `tests/test_cerebro_helpers.py` | 25 |
| `tests/test_cerebro_scoring.py` | 11 |
| `tests/test_cerebro_scoring_extra.py` | 27 |
| `tests/test_cerebro_value_trap.py` | 19 |
| `tests/test_cerebro_csv_cache.py` | 5 |
| **Total cerebro nuevos** | **87** |

Antes: 21 tests totales en el repo. Después: 108. Todos verdes.
