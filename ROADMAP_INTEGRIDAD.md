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

## Pendiente — por prioridad

### 0. `leaps_analyzer.py` — dos bugs encontrados el 5-ago comparando contratos
Al comparar los 7 LEAPS publicados para responder "¿es SAP el mejor contrato?":

  a. `week52_high` para UNH publicado en $433,02 (→ pct_from_52w_high -6,1%).
     Verificado contra yfinance en vivo: el máximo real de 365 días es $461,62
     (16-jul-2026) → dislocación real -11,7%, casi el doble de lo publicado.
     `t.history(period='1y')` en la línea 433 — revisar si el corte de fecha
     está mal alineado o si hay caché stale entre el fetch y el cierre real.

  b. Más interesante: el campo `ai_narrative` de esa misma ficha trae un
     "data_check" que la propia IA generó AUTOCORRIGIÉNDOSE — y su corrección
     está mal. Dice que el YTD +23,5% "no cuadra" y debería ser -19%,
     comparando contra el cierre de 2024 en vez del de 2025 (el YTD de 2026 se
     mide desde dic-2025). Verificado: el YTD real es +25,1%, así que el
     +23,5% publicado era CORRECTO y la "corrección" de la IA era la que
     estaba mal. También trata la exclusión de un máximo de nov-2024 (~$600)
     como un error, cuando excluirlo de una ventana de 52 semanas es lo
     correcto. Es la misma advertencia de todo el día — no fiarse de un
     veredicto de IA sin verificar — aplicada al propio verificador.

  Antes de tocar nada: auditar qué modelo/prompt genera `ai_narrative` en
  `leaps_analyzer.py`, por qué no usa las fuentes de `claude_research.py`
  (sin fuentes reales detrás, como aquí, no debería emitir un "data_check"
  con esa confianza) y si el `opportunity_score` pondera lo suficiente la
  liquidez del contrato — SAP puntúa 92,2 (el más alto) pese a tener la peor
  liquidez de los 7 (volumen 1, OI 66) y el segundo peor breakeven.

### 1. `enrich_why_cheap.py` solo procesa la lista US
El análisis de "por qué está barata" (deterioro vs ciclo vs sentimiento, con
fuentes reales de Claude) nunca toca `european_value_opportunities.csv`. WKL y
SAP no tienen `why_cheap` poblado por este motivo — hoy se hizo a mano en la
conversación. Extender `enrich_why_cheap.py` a un bucle sobre ambos CSV, igual
que se hizo con `technical_filter.py` hoy. Mismo patrón, ya probado.

### 2. Dos motores de veredicto de entrada sin fusionar
`entry_readiness` (en `technical_filter.py`) y `entry_verdict_agent.py` deciden
lo mismo con criterios parcialmente distintos. Hoy ya no se contradicen porque
el segundo consulta al primero, pero sobra un motor. Mientras convivan, un
cambio en uno puede reabrir la grieta que `coherence_check` detectó hoy.
Decidir cuál es la fuente de verdad y que el otro se retire o se convierta en
una capa fina sobre el primero.

### 3. Buscador de tickers (pendiente de auditar)
El usuario pidió revisar si extrae datos bien y si usa la IA con criterio. Sin
empezar todavía — necesita sesión propia: primero medir qué devuelve hoy contra
fuentes reales, después decidir la mejora, después implementar con tests. No
hacerlo de pasada.

### 4. RS 6 meses en Europa usa SPY como benchmark
`technical_filter.py` calcula `relative_strength_6m` siempre contra SPY, para
tickers europeos incluidos. Puede ser una decisión deliberada (todo se
compara en la misma vara), pero no está documentada como tal. Verificar si es
intencional; si no, el benchmark correcto para AEX/DAX/CAC sería un índice
europeo (Euro Stoxx 50, como ya usa `detect_european_market_regime`).

### 5b. `enrich_commodity_narrative.py` — extender el guard de coherencia
Nuevo hoy, sin cobertura todavía en `coherence_check.py`. Candidato: un
commodity con `value_rating: CARO` no debería salir con
`ai_narrative_veredicto: OPORTUNIDAD_ESTRUCTURAL` — la misma clase de
contradicción que se cazó hoy entre `entry_verdicts` y `entry_readiness`.

### 5. Auditar el resto de scanners "hermanos" del europeo
`european_value_scanner.py` tenía lógica de scoring duplicada y desincronizada
de la de US. Candidatos a la misma auditoría (bandas propias, corte de calidad
distinto, sin triangulación, sin `data_integrity`/`ai_pick_verifier`):
  - `global_value_opportunities` (BR/KR/JP/HK) — ¿mismo generador o propio?
  - `momentum_opportunities` — ¿aplica las mismas bandas donde corresponda?
  - `micro_cap_*` (si se revive) y `bond_scanner`/`commodity_scanner`
Metodología: para cada uno, comprobar (a) si importa `value_bands`, (b) si pasa
por `data_integrity.filter_dataframe`, (c) si su corte de calidad coincide con
el declarado en su propio código o está huérfano de un cambio anterior.

### 6. `coherence_check.py` — comprobaciones que faltan
El guard de hoy cubre 6 cruces. Candidatos para ampliarlo:
  - `signal_postmortem.json` contra `portfolio_tracker/summary.json` (¿el win
    rate que reporta el postmortem coincide con el del tracker?)
  - LEAPS (`leaps_opportunities.json`) contra VALUE: si un ticker está en LEAPS
    con `situation: CAIDA_CIRCUNSTANCIAL` pero en VALUE con `why_cheap:
    DETERIORO`, es una contradicción entre dos IAs que merece salir.
  - Precio: `leaps_opportunities.json` usó `spot: 193.57` para SAP mientras
    `european_value_opportunities.csv` tenía `current_price: 167.38` el mismo
    día — timestamps de fetch distintos, dentro de lo esperable, pero vale la
    pena poner un umbral de alerta (>5% de diferencia en el mismo día = sospechoso).

### 7. Consumidores del frontend sin test de coherencia
Se probó `ValueUS`/`ValueEU`. Sin auditar todavía: `Momentum.tsx`, `LeapsView`,
`BounceTrader` (ya tiene guard en `bounce_alerts.py`, pero no en el frontend),
`Cerebro`, `Portfolio`. Mismo método que hoy: no asumir que el filtro filtra —
escribir el test que lo demuestre con un caso real que debería quedar fuera.

## Principio para lo que sigue

Cuando se añada una pieza nueva que reutilice lógica de otra (score, bandas,
timing, valoración): **importar la fuente única, nunca reimplementar.** Si eso
obliga a extraer una función a un módulo propio (como hoy con
`upside_triangulation.py`) para no arrastrar dependencias pesadas, extraerla —
es más barato que dos copias divergiendo en silencio durante meses.
