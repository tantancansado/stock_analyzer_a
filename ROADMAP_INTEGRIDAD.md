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

## Pendiente — por prioridad

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
