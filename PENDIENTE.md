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
- [ ] **El hover del Centro de mando se ve raro.** Reportado con captura.
- [ ] **Repaso de tablas tipo Apple.** No un parche por página: el usuario lleva
      semanas reportando "las tablas no se ven bien" y cada vez es una causa
      distinta. Hay que barrer por patrón. Ya salieron tres:
      pista de barra invisible (22 barras), `overflow-x-auto` crudo rompiendo el
      thead sticky, y 14 tablas sin `.table-x-wrap` (se cortan en móvil, sin
      scroll posible).

## Optimización de cadencia (en curso)

- [x] ~~**Owner Earnings se revalidaba a diario sin que su entrada cambiara.**~~
      13,5 min/día + tokens de Groq, 6 de cada 7 días sobre un fichero byte a
      byte idéntico (TIKR se refresca los domingos, el batch cambia los lunes).
      Arreglado con huella de la entrada: se revalida cuando cambian las cuentas,
      ese mismo día, no por calendario.
- [ ] **TIKR solo trae las cuentas del 62% de los tickers cada semana**, y son
      tickers distintos cada vez (oscila 47-81% desde mayo). Por eso el FCF de un
      año CERRADO aparece y desaparece el 41% de las semanas. La unión de 10
      semanas cubre el 99%: guardando lo ya descargado se pasa del 62% al 99%
      sin una petición más. Un año fiscal cerrado es un hecho, no una cotización.
- [ ] `fundamental_scorer`: 8,2 min/día y sus campos cambian el 1-5% de los días
      (lo que cambia el 90% —precio, upside— es lo barato). Mismo tratamiento
      pendiente de decidir.

## Esperando a que corra el pipeline

- [ ] `fcf_per_share` en peniques y clases de acción — arreglado en
      `fundamental_scorer`, se limpia cuando corra.
- [ ] R:R de los rebotes — arreglado en `mean_reversion_detector`, igual.
- [ ] Comprobar que `coherence_check` baja a 0 incoherencias.

## Riesgo conocido, sin arreglar

- [ ] **`core-scoring` roza su timeout de 90 min.** 54-117 min en las últimas
      ejecuciones, con dos canceladas y dos fallidas de las últimas ocho. Cuando
      se corta, se corta en silencio y la app publica lo que hubiera.
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
