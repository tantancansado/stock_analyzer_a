# Pendiente

Lista viva. Se marca al cerrar y se borra la línea cuando ya no aporta nada.
Lo de arriba es lo que está en curso; lo de abajo, lo que espera a tener datos.

## En curso

- [x] ~~**El health del pipeline miente.**~~ Arreglado el 17-sep con contrato de
      CONTENIDO: cada módulo declara una columna que tiene que venir poblada, y
      es siempre la que escribe un paso POSTERIOR al que genera el fichero, para
      que cubra la cadena y no el primer eslabón. Estado nuevo `incompleto`
      (fichero de hoy, contenido a medias) distinto de `stale` y de `empty`.
      Sobre los datos de hoy pasa de decir 20/20 a **16/20**.
- [x] ~~**El hover del Centro de mando.**~~ `.liquid-glass:hover` levantaba el
      elemento 2px y le pintaba un borde interior casi blanco (74% arriba). No
      se usa en nada pulsable —los siete sitios son modales, banners y tarjetas
      líder— así que el movimiento prometía una acción que no existe. Fuera, en
      los dos temas.
- [x] ~~**Tablas: barrido por patrón.**~~ Cuatro causas distintas, las cuatro
      con test que impide la reincidencia: pista de barra invisible (22 barras),
      `overflow-x-auto` crudo rompiendo el thead sticky, `overflow-hidden` en
      ThesisBody (lo mismo), y 6 tablas visibles en móvil sin `.table-x-wrap`.
      Las otras 13 sin envoltorio están dentro de un `hidden sm:block`: en móvil
      no se pintan, así que no necesitan nada.

## Optimización de cadencia (en curso)

- [x] ~~**Owner Earnings se revalidaba a diario sin que su entrada cambiara.**~~
      13,5 min/día + tokens de Groq, 6 de cada 7 días sobre un fichero byte a
      byte idéntico (TIKR se refresca los domingos, el batch cambia los lunes).
      Arreglado con huella de la entrada: se revalida cuando cambian las cuentas,
      ese mismo día, no por calendario.
- [x] ~~**TIKR solo traía las cuentas del 62% de los tickers cada semana.**~~
      Arreglado el 17-sep: una petición vacía ya no borra lo de la semana
      anterior. Con una sola semana de arrastre la cobertura pasa del 53% al
      89%, y crece hacia el 99% (la unión de 10 semanas). Y el paso de
      verificación ahora mira el CONTENIDO, no solo `total` y `errors` — que es
      lo que permitió que esto durara cuatro meses.
- [ ] `fundamental_scorer`: 8,2 min/día y sus campos cambian el 1-5% de los días
      (lo que cambia el 90% —precio, upside— es lo barato). Mismo tratamiento
      pendiente de decidir.

- [x] **`earnings_options` produce 0 snapshots** — FALSA ALARMA mía (17-sep).
      Este módulo solo mira la CARTERA, y esos seis (AZO, CTAS, PAYX, COST, FDS,
      MKC) no son posiciones; de las 7 que lo son, las earnings más próximas
      están a 26 días. El cero era correcto, lo que faltaba era el motivo: ahora
      el artefacto publica `motivo_vacio` y separa «no toca» de «no pude mirar».
      De paso salió un fallo real: `_load_positions()` devolvía `[]` también
      cuando no podía leer la cartera, y entonces se pisaba el último snapshot
      bueno con uno vacío.

- [ ] **Confirmar mañana que vuelven los once.** El verificador IA sacó de la
      lista a BR, SPGI, AXP, MSFT, MA, KO, INTU, DSGX, BRO, COST y VEEV — 11 de
      25 fichas, el 17-sep— por un vacío que pusimos a propósito la tarde
      anterior y que la ficha no explicaba. Arreglado; sin clave local no se
      puede probar contra el modelo real, así que se comprueba en la ejecución
      de mañana.

- [x] ~~**Un valor que desaparece no dejaba rastro.**~~ Para saber por qué
      faltaba BR hubo que bajarse el log de CI y leerlo a mano. Ahora los dos
      guards apuntan a quién echan y por qué (`picks_excluidos.json`), el aviso
      de desaparecidos lo dice, y el watchdog avisa por Telegram si se cae un
      pick con score ≥60 o si tres o más se caen por el MISMO motivo — que es la
      señal de que falla la ficha y no los valores. Ensayado con los datos del
      17-sep: habría avisado de BR e INTU y de los once por el mismo motivo.

## Esperando a que corra el pipeline

- [ ] `fcf_per_share` en peniques y clases de acción — arreglado en
      `fundamental_scorer`, se limpia cuando corra.
- [ ] R:R de los rebotes — arreglado en `mean_reversion_detector`, igual.
- [ ] Comprobar que `coherence_check` baja a 0 incoherencias.

## El patrón que hay que barrer en TODAS las fuentes

Los dos fallos que más daño hacen son el mismo visto desde dos sitios, y ya han
aparecido en TIKR, en el health del pipeline y en el veto de rebotes:

- [x] ~~**Escribir encima con las manos vacías.**~~ Barrido el 17-sep. De los
      65 ficheros que dan positivo en la forma, solo 2 eran peligrosos de verdad
      (el resto son helpers que devuelven un valor suelto): `political_scanner`
      (314 señales) y `conviction_filter` (110 tesis cacheadas). Los dos
      arreglados con la misma regla que TIKR: distinguir «no hay nada» de «no he
      podido leer», y no sobrescribir en el segundo caso.
- [ ] **Verificar el recuento en vez del contenido.** «137 tickers, 0 errores»
      daba luz verde mientras a 5 de cada 13 les faltaban las cuentas, cuatro
      meses. Y «20/20 módulos OK» el día que fallaron nueve pasos. Arreglados
      los dos; hay que mirar si algún otro paso verifica solo el tamaño.
- [x] ~~**Un registro completo pero de OTRA empresa.**~~ Cruzando las fuentes
      del mismo ticker salieron CUATRO de 137, y tres son fondos, no empresas:
      `AI.PA`→C3.ai, `BRK-B`→Direxion Daily BRKB Bull 2X ETF, `EXPN.L`→Horizon
      Expansion Leaders ETF, `MMC`→MM Conferences S.A. (Polonia). Chequeo nuevo
      (`identidad_ticker.py`) en `coherence_check`: divisa contra la bolsa del
      sufijo, nombre contra nombre y precio contra precio. Y ARREGLADO el
      resolvedor —nunca excluir, siempre arreglar—: buscaba con el sufijo
      puesto, comparaba mal el símbolo, y al fallar se quedaba con el primer
      resultado de una búsqueda difusa. Ahora exige símbolo Y bolsa, y sin
      candidato válido devuelve None en vez de otra empresa.
- [ ] `valuation_model` de TIKR viene vacío en 125 de 137 tickers **las dos
      semanas**: no es intermitente, ese endpoint no funciona. Nadie lo usa
      todavía, pero está ahí.

## Riesgo conocido, sin arreglar

- [ ] **`core-scoring` y su timeout de 90 min.** Medido bien el 17-sep: el JOB
      tarda 54-56 min (los 117 de antes eran del workflow entero, varios jobs).
      Con el universo curado completo pasa de 130 a 163 tickers, ~70 min
      estimados. Margen de 20 min. **Comprobar el tiempo real mañana**; si se
      acerca a 90, subir el techo antes de que se corte — cuando se corta, se
      corta en silencio y la app publica lo que hubiera.
- [ ] **`learner_config.json`**: fósil de abril (157 días) que nadie escribe ni
      lee, y publica "reglas de alta convicción" con n=9 y dos que exigen upside
      ≥30% — la banda que hoy es HARD REJECT. Decisión del usuario: borrarlo o no.

## Decidido, esperando datos

- [ ] **Mediados de octubre**: llegan los primeros 30d de `MEAN_REVERSION`, que
      es su horizonte real. Hasta entonces no se puede juzgar si funciona.
- [ ] **Separar «bajo MA200 que sube» de «bajo MA200 que baja»** en el timing:
      hoy los dos son ESPERAR porque no hay muestra para distinguirlos
      (`entry_readiness` solo se captura desde el 10-ago, n=21).
- [ ] Batch API para el gate, `thesis_generator` y `cerebro` (~2,4 $/mes menos).
- [ ] Repo público o privado — aplazado por el usuario.
