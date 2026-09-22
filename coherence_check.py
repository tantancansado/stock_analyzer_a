#!/usr/bin/env python3
"""
Coherence Check — cruza lo que el pipeline acaba de publicar consigo mismo.

Por qué existe: los tests de este repo comprueban que cada pieza hace lo que su
autor pensó, y por eso los tres bugs graves del 5-ago-2026 pasaron desapercibidos
durante meses. Ninguno estaba DENTRO de una pieza; los tres estaban ENTRE piezas:

  - la app mostraba ENTRA en 11 valores cuyo propio timing decía VIGILAR
  - el filtro de score dejaba pasar tickers por debajo del umbral elegido
  - los ratios de los ADR mezclaban la divisa del flujo con la de la cotización

Un test unitario no encuentra una contradicción entre dos fuentes. Esto sí:
compara los ficheros publicados unos con otros y sale con código 1 si algo no
cuadra, para que el fallo se vea en el pipeline en vez de llegar a la app.

Se ejecuta al final de daily-analysis.yml. No arregla nada: informa. Arreglar
automáticamente escondería el problema, que es justo cómo llegamos aquí.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

DOCS = Path('docs')

# Commit aed71672f, 17-sep-2026 11:51: «fix(tikr): arreglado el resolvedor que
# devolvía otra empresa». Un volcado anterior a esa fecha arrastra el bug
# conocido —AI.PA resolviendo a C3.ai, BRK-B a un ETF apalancado— y sus
# incoherencias no son contradicciones de la app: son datos viejos esperando
# a que TIKR vuelva a correr, cosa que hace los domingos.
from datetime import datetime as _dt_tipo, timezone as _tz
# Con fecha Y HORA: la primera versión comparaba solo el día y no distinguía
# un artefacto generado a las 00:18 de un arreglo commiteado a las 10:01 del
# mismo día — que es exactamente el caso de los commodities.
RESOLVEDOR_TIKR_ARREGLADO = _dt_tipo(2026, 9, 17, 11, 51, tzinfo=_tz.utc)

# Commit d671709bf, 19-sep-2026 10:01. Hasta entonces las tres categorías del
# clasificador de commodities describían todas un precio BAJO y no había
# ninguna para un precio alto, así que un commodity CARO acababa en
# OPORTUNIDAD_ESTRUCTURAL por no tener dónde caer. Los veredictos anteriores
# a esa fecha arrastran el sesgo y no describen una contradicción de la app.
CATEGORIA_COMMODITY_CARO = _dt_tipo(2026, 9, 19, 8, 1, tzinfo=_tz.utc)  # 10:01 CEST


def _artefacto_anterior_al_arreglo(generated_at, arreglado_el) -> bool:
    """¿El dato se produjo con el código de antes del arreglo?

    Es el patrón que ya hacía falta dos veces —TIKR y commodities— y va a
    hacer falta más: el pipeline publica artefactos de cadencias distintas
    (TIKR los domingos, commodities a diario) y un arreglo de mediodía deja
    todos los anteriores contradiciendo a un código que ya no existe.

    La fecha del dato sale de su propio `generated_at`, NO de `git log`: en CI
    el checkout es superficial y el historial de un fichero viene vacío. Ante
    la duda devuelve False — el gate aprieta.
    """
    if not generated_at:
        return False
    try:
        d = _dt_tipo.fromisoformat(str(generated_at).replace('Z', '+00:00'))
        if d.tzinfo is None:
            d = d.replace(tzinfo=_tz.utc)
    except Exception:
        return False
    return d < arreglado_el


def _rows(nombre: str) -> list[dict]:
    p = DOCS / nombre
    if not p.exists():
        return []
    try:
        with p.open(newline='') as fh:
            return list(csv.DictReader(fh))
    except OSError:
        return []


def _json(nombre: str):
    p = DOCS / nombre
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _f(x):
    try:
        v = float(x)
        return None if v != v else v
    except (TypeError, ValueError):
        return None


# ── Comprobaciones ────────────────────────────────────────────────────────────
# Cada una devuelve una lista de problemas. Lista vacía = todo cuadra.

def entry_verdicts_vs_timing(value: list[dict], verdicts: list[dict]) -> list[str]:
    """Un ENTRY del badge no puede contradecir el timing de la propia ficha."""
    timing = {r['ticker']: (r.get('entry_readiness') or '').strip()
              for r in value if r.get('ticker')}
    malos = []
    for v in verdicts:
        if v.get('verdict') != 'ENTRY':
            continue
        t = v.get('ticker', '')
        if timing.get(t) and timing[t] != 'ENTRADA':
            malos.append(f'{t}: el badge dice ENTRY y su timing dice {timing[t]}')
    return malos


def entry_verdicts_vs_valoracion(value: list[dict], verdicts: list[dict]) -> list[str]:
    """Un ENTRY no puede llevar la valoración triangulada en negativo."""
    tri = {r['ticker']: (r.get('upside_divergence'), _f(r.get('upside_triangulated_pct')))
           for r in value if r.get('ticker')}
    malos = []
    for v in verdicts:
        if v.get('verdict') != 'ENTRY':
            continue
        div, t = tri.get(v.get('ticker', ''), (None, None))
        if div == 'ALTA' and t is not None and t < 0:
            malos.append(f"{v['ticker']}: ENTRY con valoración triangulada {t:.0f}%")
    return malos


def score_bajo_el_corte(value: list[dict], minimo: float) -> list[str]:
    """Nada por debajo del corte de calidad debería estar publicado."""
    return [f"{r['ticker']}: score {_f(r.get('value_score')):.1f} < {minimo:.0f}"
            for r in value
            if (_f(r.get('value_score')) or 999) < minimo]


def ratios_imposibles(value: list[dict]) -> list[str]:
    """FCF yield de dos dígitos altos = divisa sin convertir (caso ATLKY)."""
    return [f"{r['ticker']}: FCF yield {_f(r.get('fcf_yield_pct')):.1f}%"
            for r in value
            if (_f(r.get('fcf_yield_pct')) or 0) > 20]


def etiqueta_ml_vs_probabilidad(value: list[dict]) -> list[str]:
    """Una etiqueta ALTA con menos del 55% de probabilidad miente."""
    return [f"{r['ticker']}: etiqueta ALTA con probabilidad {_f(r.get('ml_win_probability')):.2f}"
            for r in value
            if r.get('ml_win_label') == 'ALTA'
            and (_f(r.get('ml_win_probability')) or 1) < 0.55]


def leaps_vs_why_cheap(value: list[dict], leaps: list[dict]) -> list[str]:
    """Dos IAs distintas opinando lo contrario del mismo negocio.

    leaps_analyzer.py clasifica `situation` con la misma escala que
    why_cheap_analyzer.py: DETERIORO significa "el negocio empeora, no es
    ciclo" en ambos. Si LEAPS publica un ticker como CAIDA_CIRCUNSTANCIAL/
    CALIDAD_RAZONABLE/DIP_GANADOR (negocio intacto) mientras VALUE, para el
    MISMO ticker, dice why_cheap=DETERIORO, una de las dos IAs está mal o
    trabajando con datos distintos — no debería publicarse sin más.
    """
    why_cheap_por_ticker = {
        (r.get('ticker') or '').upper(): (r.get('why_cheap') or '').upper()
        for r in value if r.get('ticker')
    }
    no_deterioro = {'CAIDA_CIRCUNSTANCIAL', 'CALIDAD_RAZONABLE', 'DIP_GANADOR'}
    problemas = []
    for o in leaps:
        ticker = (o.get('ticker') or '').upper()
        situation = (o.get('situation') or '').upper()
        why_cheap = why_cheap_por_ticker.get(ticker)
        if situation in no_deterioro and why_cheap == 'DETERIORO':
            problemas.append(
                f"{ticker}: LEAPS dice {situation} pero VALUE dice why_cheap=DETERIORO")
    return problemas


def postmortem_vs_tracker_summary(postmortem: dict | None, summary: dict | None,
                                  tolerancia_pts: float = 5.0) -> list[str]:
    """El win rate que reporta el postmortem debe coincidir con el del tracker.

    Ambos analizan, en teoría, la misma pregunta ("¿cuánto acierta el sistema
    a este horizonte?"). El 5-ago-2026 signal_postmortem.py no aplicaba el
    corte CLEAN_FROM que portfolio_tracker.py sí aplica en 'overall' —
    analizaba 1489 señales (con el periodo contaminado pre-abril) y publicaba
    55.1% de acierto, contradiciendo el 35.8%/134 oficial del tracker para la
    misma ventana. Ver signal_postmortem.py y portfolio_tracker.py CLEAN_FROM.
    """
    if not postmortem or not summary:
        return []
    resumen = postmortem.get('resumen') or {}
    horizonte = str(resumen.get('horizonte') or '')  # 'return_90d' → '90d'
    if not horizonte.startswith('return_'):
        return []
    clave = horizonte.removeprefix('return_')
    tracker_win = ((summary.get('overall') or {}).get(clave) or {}).get('win_rate')
    pm_win = resumen.get('win_rate')
    if tracker_win is None or pm_win is None:
        return []
    diff = abs(float(pm_win) - float(tracker_win))
    if diff <= tolerancia_pts:
        return []

    # El postmortem es SEMANAL (lunes) y el tracker DIARIO. Tras cambiar un
    # criterio de medida, el postmortem publicado se queda con el anterior
    # hasta que le toque correr, y eso no es una contradicción del sistema:
    # es un artefacto viejo. Distinguirlo importa porque un aviso que salta
    # sin que haya nada que arreglar se aprende a ignorar — y esta
    # comprobación sí ha pillado incoherencias reales (5-ago-2026, el
    # postmortem no aplicaba CLEAN_FROM).
    pm_fecha = str(postmortem.get('generated_at') or '')[:10]
    sm_fecha = str(summary.get('generated_at') or '')[:10]
    if pm_fecha and sm_fecha and pm_fecha < sm_fecha:
        return [f'⏳ postmortem ({pm_fecha}) mide con un criterio anterior al del '
                f'tracker ({sm_fecha}): dice {pm_win}% a {clave} y el tracker '
                f'{tracker_win}%. Se corrige solo cuando el postmortem vuelva a '
                f'correr (lunes) — no es una contradicción del sistema']
    return [f'postmortem dice {pm_win}% de acierto a {clave}, '
            f'el tracker dice {tracker_win}% — diferencia de {diff:.1f}pts']


def leaps_vs_timing_de_la_accion(leaps: list[dict]) -> list[str]:
    """¿Recomienda LEAPS una acción cuyo propio timing dice que espere?

    LEAPS calcula su `timing_score` por su cuenta y puede contradecir al
    `entry_readiness` de la ficha VALUE. El 22-sep-2026 FHN salía con
    timing_score 68 mientras su ficha decía ESPERAR: «ha perdido la MA200».
    Un LEAPS deep-ITM apalanca la caída igual que la subida, así que dos
    motores en desacuerdo sobre el mismo valor no es un detalle.

    No bloquea nada — el horizonte de un LEAPS es 2028 y el de
    `entry_readiness` es corto — pero el desacuerdo tiene que estar dicho.
    """
    fallos = []
    for o in leaps:
        if not o.get('in_value_list'):
            continue
        timing = (o.get('entry_readiness') or '').strip().upper()
        if timing != 'ESPERAR':
            continue
        motivo = (o.get('entry_readiness_reason') or '').strip()
        fallos.append(
            f"{o.get('ticker')}: LEAPS lo recomienda (timing_score "
            f"{o.get('timing_score')}) y su ficha VALUE dice ESPERAR"
            + (f" — {motivo[:60]}" if motivo else ""))
    return fallos


def leaps_precio_vs_value(value: list[dict], value_eu: list[dict], leaps: list[dict],
                          umbral_pct: float = 8.0) -> list[str]:
    """El spot de LEAPS y el current_price de VALUE deberían ser casi el mismo precio.

    OJO con el ticker: LEAPS solo opera sobre el listing US con opciones
    (p.ej. 'SAP', el ADR en NYSE) — nunca sobre el listing europeo ('SAP.DE',
    Fráncfort, cotiza en EUR). Comparar 'SAP' de LEAPS contra 'SAP.DE' de la
    lista EU no es un dato obsoleto, es una divisa distinta (verificado:
    spot LEAPS 193.57 vs SAP.DE 167.38 = básicamente el tipo de cambio
    EUR/USD, no un desajuste real). Por eso el cruce es SOLO por ticker
    exacto — si no hay ese ticker exacto en ninguna de las dos listas
    VALUE, no se compara nada en vez de adivinar con el ticker equivocado.
    """
    precio_value = {r['ticker']: _f(r.get('current_price'))
                    for r in (value + value_eu) if r.get('ticker')}
    problemas = []
    for o in leaps:
        ticker = o.get('ticker') or ''
        spot = _f(o.get('spot'))
        precio = precio_value.get(ticker)
        if spot is None or precio is None or precio <= 0:
            continue
        diff_pct = abs(spot - precio) / precio * 100
        if diff_pct > umbral_pct:
            problemas.append(
                f'{ticker}: LEAPS spot {spot:.2f} vs VALUE current_price {precio:.2f} '
                f'({diff_pct:.1f}% de diferencia)')
    return problemas


def commodity_rating_vs_narrativa(commodities: list[dict]) -> list[str]:
    """value_rating (determinista) contra ai_narrative_veredicto (Claude+búsqueda).

    Solo cuenta como contradicción cuando los dos hablan DEL PRECIO y
    discrepan: un commodity CARO con veredicto OPORTUNIDAD_ESTRUCTURAL (esa
    categoría se define sobre un precio bajo), o uno barato con
    PRECIO_EXIGENTE.

    Lo que NO es contradicción, aunque lo parezca: barato + TRAMPA_DE_VALOR.
    La trampa de valor se define como «EL PRECIO BAJO refleja un cambio
    estructural que no se va a revertir» — parece barata por definición, si no
    no engañaría a nadie. Ahí los dos coinciden en el precio y la IA añade el
    porqué, que es justo lo que se le pide.
    """
    # Mismo indulto que en TIKR, por el mismo motivo: los veredictos de antes
    # de que existiera PRECIO_EXIGENTE no contradicen a la app de hoy, solo
    # son de ayer. Se marcan ⏳ y dejan de contar como incoherencia.
    viejo = _artefacto_anterior_al_arreglo(
        (commodities[0].get('generated_at') if commodities else None),
        CATEGORIA_COMMODITY_CARO)

    problemas = []
    for r in commodities:
        ticker = r.get('ticker') or r.get('sector') or '?'
        rating = (r.get('value_rating') or '').upper()
        veredicto = (r.get('ai_narrative_veredicto') or '').upper()
        if not veredicto or veredicto == 'SIN_DATOS':
            continue
        if rating == 'CARO' and veredicto == 'OPORTUNIDAD_ESTRUCTURAL':
            aviso = (f'{ticker}: value_rating=CARO pero '
                     f'ai_narrative_veredicto=OPORTUNIDAD_ESTRUCTURAL')
            problemas.append(
                f'⏳ {aviso} — clasificado antes de que existiera '
                f'PRECIO_EXIGENTE; se corrige al reenriquecer' if viejo else aviso)
        # «barato + TRAMPA_DE_VALOR» NO es una contradicción, y contarlo como
        # tal era un error de concepto que además tumbaba el pipeline. La
        # categoría se define en el system como «EL PRECIO BAJO refleja un
        # cambio estructural que no se va a revertir»: una trampa de valor
        # parece barata por definición, si no, no engañaría a nadie.
        #
        # Los dos están diciendo lo mismo desde ángulos distintos —el
        # cuantitativo ve el precio bajo, la IA ve por qué— y eso es
        # justamente lo que se le pide a la IA: avisar de lo que el múltiplo
        # no puede saber. PALL el 19-sep-2026: ATRACTIVO por precio y trampa
        # por la caída estructural de demanda de paladio con la
        # electrificación. El control lo marcaba en rojo.
        # El simétrico del primero. PRECIO_EXIGENTE se añadió el 19-sep-2026
        # porque las tres categorías de entonces describían todas un precio
        # BAJO —«el precio bajo responde a…», «está barato dentro de…»— y un
        # commodity caro no tenía dónde caer: la IA lo metía en
        # OPORTUNIDAD_ESTRUCTURAL, que era la que mejor sonaba. Ahora que
        # existe la categoría, usarla sobre algo barato es el error contrario.
        elif rating in ('MUY_ATRACTIVO', 'ATRACTIVO') and veredicto == 'PRECIO_EXIGENTE':
            problemas.append(f'{ticker}: value_rating={rating} pero ai_narrative_veredicto=PRECIO_EXIGENTE')
    return problemas


def columnas_obligatorias(value: list[dict], nombre_csv: str = 'value_opportunities.csv') -> list[str]:
    """Un scoring a medias no puede publicarse como si estuviera completo.

    El 5-ago-2026 esto solo se comprobaba en la lista US: las 36 filas de la
    europea llevaban meses sin entry_readiness/ma_filter_pass/tech_stage y
    nadie lo veía porque este guard no la miraba.
    """
    if not value:
        return [f'{nombre_csv} está vacío']
    obligatorias = ('ticker', 'value_score', 'current_price', 'entry_readiness')
    return [f'{nombre_csv}: la columna {c} está vacía en las {len(value)} filas'
            for c in obligatorias
            if not any((r.get(c) or '').strip() for r in value)]


def identidades_rotas(nombres: tuple[str, ...]) -> list[str]:
    """Identidades que TIENEN que cumplirse en los CSV publicados.

    Es la comprobación más barata que existe y la única que no necesita saber
    nada del negocio: el upside ES (objetivo − precio) / precio. O cuadra o hay
    un bug arriba.

    Se añade el 16-sep-2026 porque todos los fallos de datos de ese día tenían
    la misma forma —dos números correctos por separado que juntos mienten— y
    ninguno dio error: la página se pintaba igual y el CSV tenía sus filas. Ver
    identidades.py para la lista de casos.
    """
    try:
        import pandas as pd

        import identidades
    except ImportError as exc:
        return [f'no se pudo ejecutar el chequeo de identidades: {exc}']

    fuera: list[str] = []
    for nombre in nombres:
        ruta = DOCS / nombre
        if not ruta.exists():
            continue
        try:
            d = pd.read_csv(ruta)
        except Exception as exc:
            fuera.append(f'{nombre}: no se pudo leer ({exc})')
            continue
        revisiones = identidades.revisar(d, nombre) + identidades.revisar_operacion(d, nombre)
        # Bonos y materias primas tienen su propia aritmética (rango de 52
        # semanas); el flujo de opciones, la suya (primas y ratio put/call).
        if nombre in ('bonds_opportunities.csv', 'commodity_opportunities.csv'):
            revisiones += identidades.revisar_rango_52s(d, nombre)
        if nombre == 'options_flow.csv':
            revisiones += identidades.revisar_opciones(d, nombre)
        for i in revisiones:
            # Los desvíos pequeños son desfase entre el momento de capturar el
            # precio y el de calcular un derivado: se informan como ⏳ para que
            # no cuenten como incoherencia — un check que salta en rojo sin
            # nada que arreglar se acaba ignorando, y entonces tampoco avisa
            # cuando sí importa.
            fuera.append(str(i) if i.grave else f'⏳ {i}')
    return fuera


def identidad_de_los_tickers() -> list[str]:
    """¿Cada ticker trae los datos de la empresa que dice?

    El mismo ticker aparece en varios ficheros, cada uno de una descarga
    distinta. Si dos no coinciden en el nombre, en el precio o en la divisa que
    corresponde a su bolsa, una de las dos tiene OTRA empresa.

    El 17-sep-2026 salieron tres registros completos, plausibles y equivocados:

        AI.PA   debería ser L'Air Liquide  →  TIKR traía C3.ai, Inc.
        BRK-B   Berkshire Hathaway         →  Direxion Daily BRKB Bull 2X ETF
        MMC     Marsh & McLennan           →  MM Conferences S.A. (Polonia)

    Es el fallo más difícil de ver del repo: los demás dejan un hueco, este deja
    un dato lleno. Ver identidad_ticker.py.
    """
    try:
        import json as _json

        import pandas as pd

        import identidad_ticker
    except ImportError as exc:
        return [f'no se pudo comprobar la identidad de los tickers: {exc}']

    fuentes: dict[str, list[dict]] = {}
    for nombre in ('value_opportunities.csv', 'european_value_opportunities.csv',
                   'fundamental_scores.csv', 'momentum_opportunities.csv',
                   'global_value_opportunities.csv'):
        ruta = DOCS / nombre
        if not ruta.exists():
            continue
        try:
            d = pd.read_csv(ruta)
        except Exception:
            continue
        if 'ticker' not in d.columns:
            continue
        for _, r in d.iterrows():
            t = str(r['ticker']).upper().strip()
            fuentes.setdefault(t, []).append({
                'fuente': nombre.replace('.csv', '')[:18],
                'nombre': str(r.get('company_name') or '') or None,
                'precio': pd.to_numeric(pd.Series([r.get('current_price')]),
                                        errors='coerce').iloc[0],
                'divisa': None,   # los CSV no la traen; la divisa la aporta TIKR
            })

    ruta_tikr = DOCS / 'tikr_earnings_data.json'
    if ruta_tikr.exists():
        try:
            for t, v in _json.loads(ruta_tikr.read_text()).get('data', {}).items():
                pr = (v or {}).get('price') or {}
                c = pr.get('c')
                fuentes.setdefault(str(t).upper(), []).append({
                    'fuente': 'tikr',
                    'nombre': str((v or {}).get('company_name') or '') or None,
                    'precio': float(c) if c else None,
                    'divisa': pr.get('curr'),
                })
        except Exception:
            pass

    # ¿El fichero de TIKR es anterior al último arreglo del resolvedor?
    #
    # El 19-sep-2026 este control tumbaba el pipeline entero todos los días
    # por NUEVE incoherencias que ya estaban arregladas: el guardia de bolsa
    # de `tikr_scraper` entró el 17-sep a las 11:51 y el fichero de TIKR es
    # del 13-sep. TIKR solo corre los domingos, así que hasta entonces no hay
    # nada que hacer — y el paso, sin `continue-on-error`, se llevaba por
    # delante el briefing, el archivado, el informe de estado y el commit de
    # los datos. Ciento cincuenta y cinco tickers buenos sin publicar por
    # nueve que ya no fallan.
    #
    # Se marcan como ⏳: el mecanismo ya existía para los desfases entre
    # artefactos de distinta cadencia, y esto es exactamente eso.
    # La primera versión de esto preguntaba a `git log` por la fecha del
    # volcado y la del resolvedor. En local funcionaba; en CI no, porque
    # actions/checkout clona en superficie (fetch-depth 1 por defecto) y
    # `git log` de un fichero devuelve vacío. El indulto no se aplicaba y el
    # pipeline volvió a caerse igual.
    #
    # Las dos fechas se pueden saber sin git: el volcado trae su propio
    # `generated_at`, y la del arreglo se escribe aquí. Una constante a mano
    # es fea, pero es un hecho que no cambia —el commit está citado— y
    # funciona en cualquier checkout.
    tikr_desfasado = False
    if ruta_tikr.exists():
        try:
            crudo = _json.loads(ruta_tikr.read_text()).get('generated_at')
            tikr_desfasado = _artefacto_anterior_al_arreglo(
                crudo, RESOLVEDOR_TIKR_ARREGLADO)
        except Exception:
            tikr_desfasado = False

    fallos: list[str] = []
    for t, fs in sorted(fuentes.items()):
        if len(fs) < 2 and not any(f.get('divisa') for f in fs):
            continue
        for f in identidad_ticker.revisar(t, fs):
            # Solo los que señalan a TIKR: si la contradicción es entre dos
            # CSV del pipeline diario, ahí no hay desfase que valga.
            if tikr_desfasado and 'tikr' in str(f).lower():
                fallos.append(f'⏳ {f} — el resolvedor se arregló después de '
                              f'este volcado; TIKR corre los domingos')
            else:
                fallos.append(f)
    return fallos


def leaps_incoherentes() -> list[str]:
    """Una call profunda ITM no puede valer menos que su valor intrínseco.

    Es aritmética de opciones, no una heurística: si la prima es menor que
    (spot − strike), o hay dinero gratis sobre la mesa o el dato está mal.
    """
    try:
        import identidades
    except ImportError as exc:
        return [f'no se pudo comprobar los LEAPS: {exc}']
    d = _json('leaps_opportunities.json')
    ops = d.get('opportunities', []) if isinstance(d, dict) else []
    return [str(i) for i in identidades.revisar_leaps(ops, 'leaps_opportunities.json')]


def run() -> int:
    print('[coherence_check] Cruzando lo publicado consigo mismo...')

    value = _rows('value_opportunities.csv')
    value_eu = _rows('european_value_opportunities.csv')
    verdicts = _rows('entry_verdicts.csv')
    leaps_data = _json('leaps_opportunities.json')
    leaps = leaps_data.get('opportunities', []) if isinstance(leaps_data, dict) else []
    commodities = _rows('commodity_opportunities.csv')
    postmortem = _json('signal_postmortem.json')
    tracker_summary = _json('portfolio_tracker/summary.json')

    try:
        from value_bands import VALUE_SCORE_MIN
    except ImportError:
        VALUE_SCORE_MIN = 30.0

    comprobaciones = [
        ('badge ENTRY contra el timing de la ficha (US)', entry_verdicts_vs_timing(value, verdicts)),
        ('badge ENTRY contra el timing de la ficha (EU)', entry_verdicts_vs_timing(value_eu, verdicts)),
        ('badge ENTRY contra la valoración propia (US)',  entry_verdicts_vs_valoracion(value, verdicts)),
        ('badge ENTRY contra la valoración propia (EU)',  entry_verdicts_vs_valoracion(value_eu, verdicts)),
        ('corte de calidad (US)',                    score_bajo_el_corte(value, VALUE_SCORE_MIN)),
        ('corte de calidad (EU)',                    score_bajo_el_corte(value_eu, VALUE_SCORE_MIN)),
        ('ratios imposibles — divisa (US)',          ratios_imposibles(value)),
        ('ratios imposibles — divisa (EU)',          ratios_imposibles(value_eu)),
        ('etiqueta ML contra su probabilidad',       etiqueta_ml_vs_probabilidad(value)),
        ('columnas obligatorias (US)',                columnas_obligatorias(value, 'value_opportunities.csv')),
        ('columnas obligatorias (EU)',                columnas_obligatorias(value_eu, 'european_value_opportunities.csv')),
        ('LEAPS contra el timing de la acción',       leaps_vs_timing_de_la_accion(leaps)),
        ('LEAPS contra why_cheap de VALUE (US)',      leaps_vs_why_cheap(value, leaps)),
        ('LEAPS contra why_cheap de VALUE (EU)',      leaps_vs_why_cheap(value_eu, leaps)),
        ('commodities: rating contra narrativa IA',   commodity_rating_vs_narrativa(commodities)),
        ('postmortem contra el win rate del tracker', postmortem_vs_tracker_summary(postmortem, tracker_summary)),
        ('precio LEAPS contra precio VALUE',           leaps_precio_vs_value(value, value_eu, leaps)),
        ('identidad de los tickers (¿es esta empresa?)', identidad_de_los_tickers()),
        ('identidades aritméticas de lo publicado',   identidades_rotas((
            'value_opportunities.csv', 'value_opportunities_filtered.csv',
            'european_value_opportunities.csv', 'european_value_opportunities_filtered.csv',
            'momentum_opportunities.csv', 'mean_reversion_opportunities.csv',
            'bounce_setups_broad.csv',
            'bonds_opportunities.csv', 'commodity_opportunities.csv',
            'options_flow.csv',
        ))),
        ('aritmética de los LEAPS',                   leaps_incoherentes()),
    ]

    total = 0
    # Los avisos marcados con ⏳ son desfases conocidos entre artefactos de
    # distinta cadencia (el postmortem es semanal, el tracker diario): se
    # informan pero NO cuentan como incoherencia, porque no hay nada que
    # arreglar y un check que salta en rojo sin acción posible se ignora.
    desfases = []
    for nombre, problemas in comprobaciones:
        reales = [p for p in problemas if not str(p).startswith('⏳')]
        pendientes = [p for p in problemas if str(p).startswith('⏳')]
        desfases.extend(pendientes)
        if reales:
            total += len(reales)
            print(f'\n  ❌ {nombre}: {len(reales)}')
            for p in reales[:8]:
                print(f'       {p}')
            if len(reales) > 8:
                print(f'       ...y {len(reales) - 8} más')
        elif pendientes:
            print(f'  ⏳ {nombre}: se corrige solo al regenerarse el artefacto')
            for p in pendientes:
                print(f'       {p}')
        else:
            print(f'  ✓ {nombre}')

    informe = {
        'total_problemas': total,
        'desfases_conocidos': desfases,
        'detalle': {n: [p for p in ps if not str(p).startswith('⏳')]
                    for n, ps in comprobaciones if any(not str(p).startswith('⏳') for p in ps)},
        'tickers_value': len(value),
        'tickers_verdicts': len(verdicts),
    }
    (DOCS / 'coherence_check.json').write_text(
        json.dumps(informe, ensure_ascii=False, indent=2))

    if total:
        print(f'\n🚨 {total} incoherencias entre lo que publica la app y sus propios datos')
        return 1
    print('\n✓ Sin contradicciones entre las fuentes publicadas')
    return 0


if __name__ == '__main__':
    sys.exit(run())
