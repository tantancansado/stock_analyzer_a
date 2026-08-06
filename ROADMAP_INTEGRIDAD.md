# Hoja de ruta — integridad de datos y coherencia

Iniciada 5-ago-2026, tras una tarde encontrando incoherencias entre lo que la
app muestra y lo que sus propios datos dicen. El patrón común en todo lo
encontrado: **los tests comprueban que cada pieza hace lo que su autor pensó,
no que el conjunto sea coherente.** Los bugs graves de hoy no vivían dentro de
ninguna pieza — vivían entre ellas, en las costuras, donde ningún test unitario
mira. `coherence_check.py` (hecho hoy) es el primer guard pensado para esas
costuras; el resto de esta hoja de ruta es extenderlo y arreglar lo que ya
encontró o probablemente esconde.

## Hecho hoy (5-ago-2026)

- [x] `currency_normalizer.py` — divisa de estados financieros vs cotización
- [x] `financial_cross_check.py` — cuadre contable (acciones × precio = mcap)
- [x] `data_integrity.py` — rangos imposibles, guard determinista
- [x] `ai_pick_verifier.py` + `why_cheap_analyzer.py` — verificación con Claude
- [x] Timeout y fail-open en todos los clientes de Anthropic
- [x] `entry_verdict_agent.py` — un ENTRY exige timing + valoración, no solo fundamentales
- [x] Filtro de score en ValueUS/ValueEU — los grados A/B se lo saltaban
- [x] `technical_filter.py` — procesa US y EU, antes solo US (hardcoded)
- [x] `european_value_scanner.py` — bandas de `value_bands`, no propias y desmentidas
- [x] `upside_triangulation.py` — extraída, ahora la usan US y EU
- [x] `coherence_check.py` — cruza lo publicado consigo mismo, corre en el pipeline
- [x] `commodity_scanner.py` — CYCLE_CONTEXT/SEASONALITY indexados por `commodity_type`
      hacían que gas natural describiera el mercado del petróleo (compartían "Energy"
      con WTI/Brent); separados por `sector` con fallback al tipo
- [x] `commodity_narrative_analyzer.py` + `enrich_commodity_narrative.py` — narrativa
      real por commodity con Claude+búsqueda, mismo patrón que `why_cheap_analyzer`,
      cita si es comprable en IBKR Ireland (dato ya existía en `eu_alternative`)
- [x] `global_market_scanner.py` — mismo bug de `currency_normalizer` que ATLKY/ASAZY
      pero nunca propagado aquí: `financialCurrency` ≠ `currency` en casi todo Hong
      Kong con subyacente chino (Tencent, Alibaba, CNOOC, PetroChina, HSBC, AIA,
      verificado en vivo). `fcf_yield` dividía `freeCashflow` sin convertir. Fix:
      `normalize_info()` antes de leer el campo; sin FX disponible se descarta
- [x] `short_scanner.py` — mismo patrón: BABA/JD/PDD/BIDU/LI (CNY) y STLA (EUR)
      cotizan en USD. BABA daba fcf_yield -14,1% sin convertir (real -2,1%),
      cruzando el umbral +10/+6 de `fund_score` en un scanner de posiciones EN
      CORTO — convicción corto inflada por divisa, no por el negocio. Mismo fix
- [x] `currency_normalizer.py` — BUG EN EL PROPIO MÓDULO: `PER_SHARE_FIELDS`
      (trailingEps, forwardEps, bookValue...) se multiplicaban por
      `fx_to_major` como si vinieran en `financialCurrency`. Verificado en 9
      tickers reales: yfinance SIEMPRE los da ya en la divisa de cotización;
      lo único real es el ×100 de subunidad (GBp), sin FX. El bug corrompía
      justo lo que debía arreglar (EXPN.L: ×79 en vez de ×100). Consumido por
      `fundamental_scorer.py` → `docs/fundamental_scores.csv`, pipeline
      completo. Añadido `epsCurrentYear`/`epsForward`/`epsTrailingTwelveMonths`
      (alias exactos que algunos consumidores leen primero) a la lista. Sin
      tests hasta ahora pese a ser el módulo fuente — añadidos
- [x] `earnings_thesis_generator.py` — genera tesis IA para POSICIONES REALES
      del usuario. Tickers GBp (AZN.L, ULVR.L...) mostraban al prompt "Precio
      actual: 12184 / EPS consenso: 8.52" — PE implícito ~1430x vs real ~14x.
      Dos causas: `epsForward` sin normalizar (ver arriba) y
      `tk.earnings_estimate` (consenso trimestral, llamada de yfinance aparte
      de `info`) sobreescribía el EPS ya normalizado con el crudo. También
      quitado el hardcode "M$" que mentía la divisa de `revenue_estimate`
      para cualquier ticker no-USD
- [x] `ticker_api.py` — mismo patrón en 4 sitios: `_build_search_live_snapshot`
      (buscador de tickers), `_build_earnings_expectation_snapshot` (earnings,
      3 llamadores), el endpoint de CARTERA REAL del usuario (`fcf_yield` por
      posición sin normalizar) y `/api/dividend-calendar`. De paso, añadidos
      `dividendRate`/`lastDividendValue`/`trailingAnnualDividendRate` a
      `PER_SHARE_FIELDS` (verificado: dividendRate ×100 da 1,98% vs 2,04%
      reportado por yfinance para AZN.L, faltaban en la lista)

Con esto quedan cerrados los 4 archivos detectados por el grep de mezcla
marketCap/currentPrice + campos de estados financieros sin `currency_normalizer`
(short_scanner, earnings_thesis_generator, ticker_api, global_market_scanner).

## Pendiente — por prioridad

### 0. ~~`leaps_analyzer.py` — dos bugs encontrados el 5-ago comparando contratos~~ — HECHO
Ambos arreglados en una sesión anterior (este archivo de roadmap no se había
actualizado): (a) `week52_high` daba -6,1% de máximos para UNH usando
`Close.max()`, cuando el `High.max()` real daba -11,7% (el precio tocó
$461,62 intradía el 16-jul-2026 y `Close.max()` nunca ve ese pico) — ahora
usa `High.max()`, comentario en la línea ~438. (b) `ai_narrative` traía un
"data_check" autogenerado donde Claude "corregía" un YTD +23,5% correcto a
-19% comparando contra el cierre de un año equivocado — el prompt ahora
prohíbe explícitamente ese fact-checking de memoria sin herramienta de
búsqueda, bloque "VERIFICACIÓN DE DATOS — LÍMITE ESTRICTO" en la línea ~748.

Sigue abierto, sin auditar: si `opportunity_score` pondera lo suficiente la
liquidez del contrato — el 5-ago SAP puntuaba 92,2 (el más alto de 7) pese a
tener la peor liquidez (volumen 1, OI 66) y el segundo peor breakeven.

### 1. ~~`enrich_why_cheap.py` solo procesa la lista US~~ — HECHO 5-ago-2026
`TARGET_CSVS` itera ambos universos, mismo patrón que `technical_filter.py`.
Presupuesto de tiempo y `MAX_TICKERS` compartidos entre ambos (no duplica
gasto de API), candidatos de US+EU compiten juntos por `value_score`.

### 2. ~~Dos motores de veredicto de entrada sin fusionar~~ — HECHO 5-ago-2026
No eran dos motores compitiendo por la misma pregunta: `entry_readiness`
(technical_filter.py) responde "¿el timing técnico es bueno hoy?" (badge
propio en las tablas VALUE) y `entry_verdict_agent.py` responde "¿debería
entrar ya, con todo lo que sé?" (fundamentales + `entry_readiness` como veto
+ valoración). Son dos preguntas distintas con dos badges distintos en el
frontend (ValueUS.tsx muestra ambos en la misma fila) — fusionarlas habría
sido quitar una señal real, no arreglar un bug.

Auditando la relación sí apareció un bug real: `entry_verdict_agent.py` tenía
un SEGUNDO chequeo de stage4, independiente de `entry_readiness`, leyendo
`row.get('weinstein_stage')` — columna que no existe en ningún CSV
publicado — cayendo a `row.get('stage')`, que trae valores de OTRO scorer
("Stage 2 Strong", nunca "stage4"). Nunca se disparó, para ningún ticker.
Mismo bug en el prompt de refinamiento IA: "MA pass" y "Stage" leían
columnas equivocadas, Groq recibía "MA pass: None" / "Stage: ?" siempre.
Quitado el código muerto en vez de arreglar la columna — `entry_readiness`
queda como única fuente de verdad para timing técnico, sin una segunda
reimplementación que pueda volver a divergir en silencio. Verificado con
los 9 tickers reales en stage4: siguen bloqueados correctamente vía el veto
de `entry_readiness`.

### 3. ~~Buscador de tickers~~ — AUDITADO 6-ago-2026 (prioridad baja, usuario)
Medido `/api/search` contra fuentes reales, dos bugs encontrados y arreglados:

  a. **Datos sucios reales**: `fundamental_scorer.py` priorizaba
     `info.get('shortName')` sobre `longName` para `company_name`. Verificado
     en vivo que `shortName` trae basura de formato de bolsa en casi todos
     los tickers europeos: `SAP.DE` → `'SAP SE                        I'`
     (un campo de ancho fijo del feed de Xetra sin sanear, visible tal cual
     en la app), `ULVR.L` → `'UNILEVER PLC ORD 3.5P'` en vez de `'Unilever
     PLC'`. Extraído `_company_name()`, aplicado también en `ticker_api.py`
     (cartera real) y `earnings_thesis_generator.py`. Parcheados los CSVs ya
     publicados (46/48 EU, 50/136 US corregidos) sin re-scorear nada.

  b. **Instrumentos sintéticos sin filtrar**: buscar "microsoft" devolvía
     `MSFTX-USD` (`quoteType=CRYPTOCURRENCY`, un token que sigue el precio
     pero no es la acción) como segundo resultado, justo debajo de MSFT —
     confuso y arriesgado en una app de VALUE investing. Filtrado a
     `quoteType` en `{EQUITY, ETF}` antes de recortar candidatos.

No se tocó: el ranking de empates entre resultados igual de relevantes (p.ej.
"appl" — typo de Apple — puede mostrar AppLovin antes que Apple) y algún caso
aislado de metadata de yfinance poco fiable (un certificado estructurado de
Nike listado como `quoteType=EQUITY`) — ninguno de los dos es un bug de datos
verificable, son matices de ranking/UX que no encajan en el mandato de
integridad de datos de esta sesión.

### 4. ~~RS 6 meses en Europa usa SPY como benchmark~~ — HECHO 5-ago-2026
No era deliberado: `portfolio_tracker.py` ya usaba VGK para el alpha de
EU_VALUE, `technical_filter.py` era la pieza inconsistente. Verificado en
vivo (SPY +13,5% vs VGK +9,9% a 6m, gap 3,6pp — cruza el umbral RS 6m < -25
que decide ENTRADA vs VIGILAR). Fix: `fetch_benchmark_6m_return(symbol)`
genérica, VGK para tickers de `european_value_opportunities.csv`, SPY para
el resto. `technical_signals.json` expone ambos retornos.

### 5b. ~~`enrich_commodity_narrative.py` — extender el guard de coherencia~~ — HECHO 5-ago-2026
`commodity_rating_vs_narrativa()` en `coherence_check.py`: CARO+OPORTUNIDAD_ESTRUCTURAL
o MUY_ATRACTIVO/ATRACTIVO+TRAMPA_DE_VALOR. 0 falsos positivos con datos reales.

### 6b. ~~LEAPS `situation` contra `why_cheap` de VALUE~~ — HECHO 5-ago-2026
Dos IAs contradiciéndose sobre el mismo negocio (LEAPS dice negocio intacto,
VALUE dice DETERIORO, o viceversa). 0 contradicciones activas hoy, guard
verificado sin falsos positivos con datos reales y tests.

### 5. ~~Auditar el resto de scanners "hermanos" del europeo~~ — CERRADO 5-ago-2026
  - `global_value_opportunities` (`global_market_scanner.py`, BR/KR/JP/HK):
    generador propio, no compartía `currency_normalizer` — arreglado arriba
    (fcf_yield sin convertir en HK con subyacente chino).
  - `momentum_opportunities`: comprobado, NO debe usar `value_bands` (el hard
    reject de upside ≥30% es un hallazgo del backtest de VALUE, no aplica a
    momentum). Scoring por VCP/proximidad a máximos/tendencia/institucional,
    sin analyst_upside_pct como input — arquitectura distinta, sin el mismo
    riesgo. Nada que arreglar.
  - `bond_scanner.py`/`commodity_scanner.py`: comprobado, no importan
    `value_bands` ni tienen bandas de upside propias — puntúan yield/liquidez/
    contexto de ciclo, no upside de analista. Sin el mismo riesgo.

### 6. ~~`coherence_check.py` — comprobaciones que faltan~~ — CERRADO 5-ago-2026
El guard cubre 16 cruces. ~~`signal_postmortem.json` contra
`portfolio_tracker/summary.json`~~ — HECHO 5-ago-2026, y encontró un bug real:
`signal_postmortem.py` no aplicaba el corte `CLEAN_FROM` de
`portfolio_tracker.py`, analizaba 1489 señales (con el periodo contaminado
pre-abril) y publicaba 55,1% de acierto contra el 35,8%/134 oficial. Arreglado
en el propio `signal_postmortem.py` (mismo `CLEAN_FROM`), verificado que ahora
da 134/35,8%/-1,84% — match exacto. El JSON publicado ahora mismo sigue con
el número viejo (corre semanalmente); se resolverá solo.

~~Precio: leaps_opportunities.json vs current_price VALUE~~ — HECHO 5-ago-2026,
y resultó ser una premisa equivocada: el gap SAP 193,57 vs SAP.DE 167,38 NO
era timestamps de fetch — SAP.DE cotiza en EUR, LEAPS opera sobre el ADR "SAP"
(NYSE, USD), son valores distintos. SAP SÍ está como entrada propia en
`value_opportunities.csv` (el ADR US) a 195,49 — 1% de diferencia, normal.
`leaps_precio_vs_value()` compara solo por ticker EXACTO contra ambas listas
VALUE; si no hay ese ticker exacto en ninguna, no compara nada en vez de
adivinar contra el listing equivocado en otra divisa. Umbral 8%, 0 falsos
positivos verificado con datos reales.

**Item 6 cerrado — los 3 candidatos hechos.**

### 7. ~~Consumidores del frontend sin test de coherencia~~ — AUDITADO 5-ago-2026
Se probó `ValueUS`/`ValueEU` (bug real, ya arreglado). Barrido hoy de
`Momentum.tsx`, `GlobalValue.tsx`, `BounceTrader.tsx`, `Leaps.tsx`,
`Cerebro.tsx`, `Portfolio.tsx`, `MyPortfolio.tsx`, `PersonalPortfolio.tsx`,
`DividendTraps.tsx`, `CatalystScreener.tsx`: ninguna tiene el patrón de bypass
del filtro de score (`highConviction || score < min`) — resultado negativo
verificado por grep dirigido, no una revisión superficial. El bug era
específico de ValueUS/ValueEU; la mayoría de estas páginas ni siquiera tienen
un filtro numérico de score que se pueda saltar.

~~Pendiente real: `BounceTrader` tenía guard de catalizador negativo en
`bounce_alerts.py` pero solo vivía en el paso de Telegram~~ — HECHO 5-ago-2026.
`bounce_alerts.py` persiste el veredicto en `bounce_catalyst_flags.json`
(expira a `DEDUP_DAYS`), `/api/bounce-catalyst-flags` lo expone,
`BounceTrader.tsx`/`BroadBounceView.tsx` excluyen esos tickers con aviso
visible. Un test atrapó un bug real de paso: cargaba `{'flags': {...}}`
entero en vez de `.get('flags', {})`, así que las flags viejas nunca
expiraban.

## Principio para lo que sigue

Cuando se añada una pieza nueva que reutilice lógica de otra (score, bandas,
timing, valoración): **importar la fuente única, nunca reimplementar.** Si eso
obliga a extraer una función a un módulo propio (como hoy con
`upside_triangulation.py`) para no arrastrar dependencias pesadas, extraerla —
es más barato que dos copias divergiendo en silencio durante meses.

## Estado: todos los items cerrados (6-ago-2026)

Los 10 items de esta hoja de ruta están hechos, auditados o cerrados por no
aplicar. Patrón que se repitió en casi todos: el bug no vivía dentro de un
módulo bien testeado, vivía en la costura entre dos módulos que dejaron de
estar de acuerdo sin que nada lo avisara — `coherence_check.py` es la
respuesta estructural a eso, y ahora cubre 16 cruces. Las 15 incoherencias
que reporta ahora mismo contra los datos publicados son todas obsoletas
(pipeline sin re-ejecutar desde los últimos fixes), documentadas caso por
caso arriba — se resuelven solas en la próxima corrida programada.

Si aparece un nuevo hallazgo de integridad, añadirlo aquí como item nuevo con
el mismo formato: qué se rompía, cómo se verificó contra datos reales, qué
arregla el fix, qué test lo cubre.
