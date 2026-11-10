"""Banda canónica de analyst_upside_pct para señales VALUE — única fuente.

Calibrada con señales reales. Recalibrada el 17-sep-2026 sobre 152 señales
del periodo limpio con retorno a 90 días ya cerrado:

  [10, 25)  → 61% win / +2.78% media   (28 señales)
  [25, 30)  → 62% win / +3.73% media   (24 señales)   ← IGUAL que la dorada
  >= 30     → 28% win / -3.26% media  (100 señales)   ← la trampa, y es real

El corte de la zona dorada estaba en 25 por un «n pequeño, sin evidencia
clara» que ya no es cierto: con 24 señales cerradas, [25,30) rinde lo mismo
que [10,25). No es que sea mejor — es que no hay NINGUNA diferencia, así que
penalizarla no tenía respaldo. El usuario lo dijo antes que los datos: «si
está barata está barata, no sospechamos porque sí». Tenía razón.

Lo que sigue en pie, y con la muestra más grande de las tres, es el ≥30%.

Antes cada consumidor tenía su propia banda (integrator ≥30 reject,
portfolio_tracker 10-45, conviction_filter 10-55) y el mismo ticker podía
ser trampa en un módulo y pick en otro. Cualquier cambio de banda se hace
AQUÍ y en ningún otro sitio.
"""

# Por debajo: upside demasiado justo para compensar el riesgo de la posición
UPSIDE_MIN = 10.0

# Fin de la zona dorada [10, 30): el bonus de score premia esta banda. Estaba
# en 25 y se sube a 30 el 17-sep-2026 — ver la nota de arriba: [25,30) rinde
# igual que [10,25) sobre 24 señales cerradas, y el corte dejaba fuera del
# bonus a picks indistinguibles de los premiados.
UPSIDE_GOLDEN_MAX = 30.0

# Upside ALTO: a partir de aquí el objetivo del analista no basta por sí solo y
# necesita el respaldo de la valoración propia (DCF / P-E). NO es un descarte.
#
# Fue un hard-reject («value trap, 0% de acierto») hasta el 27-oct-2026. El
# usuario: «las valoraciones de los analistas están bien, pero nosotros también
# calculamos precio objetivo y sabemos hacerlo». Y la evidencia del rechazo era
# débil: las «100 señales con 28% de acierto» eran 14 empresas de software y
# datos, una sola (EXPN.L) con 24 (desglose del 18-sep-2026). Un upside alto se
# investiga con nuestros números; solo se castiga si nuestros modelos lo niegan.
UPSIDE_ALTO = 30.0


def tiene_respaldo_propio(triangulado, divergencia) -> bool:
    """¿Respalda la valoración propia un upside alto del analista?

    Sí si la triangulación (mediana de analista, DCF y P/E) deja al menos
    UPSIDE_MIN de recorrido y los modelos propios no contradicen de lleno al
    analista (divergencia ALTA). Sin modelos propios no hay respaldo: un dato
    que no tenemos no confirma nada.
    """
    try:
        t = float(triangulado)
    except (TypeError, ValueError):
        return False
    return t == t and t >= UPSIDE_MIN and str(divergencia or '').upper() != 'ALTA'


def respaldo_propio(df):
    """Versión por filas de `tiene_respaldo_propio` (Serie booleana)."""
    import pandas as pd
    tri = (pd.to_numeric(df['upside_triangulated_pct'], errors='coerce')
           if 'upside_triangulated_pct' in df.columns else pd.Series(float('nan'), index=df.index))
    div = (df['upside_divergence'].fillna('').astype(str).str.upper()
           if 'upside_divergence' in df.columns else pd.Series('', index=df.index))
    return tri.notna() & (tri >= UPSIDE_MIN) & (div != 'ALTA')

# ── Qué es una idea VALUE (5-nov-2026) ───────────────────────────────────
# El usuario: «la filosofía no es comprar empresas cercanas a máximos a no ser
# que sus datos sean increíbles, tipo Microsoft [...] normalmente buscamos
# acciones que estén baratas sin que empeore el negocio ni los números,
# circunstanciales». La lista puntuaba sobre todo calidad y el upside solo
# sumaba o restaba unos puntos, así que mezclaba esas ideas con buenas empresas
# a precio justo: el 5-nov, en 6 de las 11 publicadas nuestra valoración no
# veía recorrido (WST -7,6%, EFX -13%, NDAQ -3,2%, FCNCA -1,3%, PG y TT 0%).
#
# Dos condiciones, y las dos son de entrada, no de puntuación:
#   1. Barata según NUESTRA valoración: `respaldo_propio` (triangulado ≥
#      UPSIDE_MIN y sin divergencia ALTA). Sin modelos propios no hay respaldo.
#   2. Que el negocio no empeore: ventas que no caen frente al año anterior.
#
# La segunda fue primero «cerca de máximos solo si es excepcional» y se cambió
# el mismo día, al medirla. Reconstruida la lista VALUE US de cada día desde
# git (174 días, 457 empresas, feb-nov 2026), con su precio después y contra el
# universo del que elige la app, a 180 días:
#
#                                  feb-mar      abr+     (puntos vs universo)
#   barata, ventas CAEN             -10,5      -16,1    IC <0 en todos los cortes,
#                                                       también sin financieras
#   barata, ventas no caen           +5,3       +5,0
#   barata y cerca de máximos        +8,0       +2,6    no era el problema
#   la regla de máximos entera       +1,8       +1,3    no mejoraba a la de solo barata
#
# El umbral no está afinado: con ventas ≥0, ≥5 o ≥10 la ventaja es la misma
# (+5 en los dos periodos); el escalón está en caer. Es lo que decía el usuario
# —«baratas sin que empeore el negocio»— medido con el dato que lo dice, en vez
# de con la distancia al máximo, que mide el precio y no el negocio.
VENTAS_MINIMAS = 0.0
CUARTIL_ALTO = 0.75
# Crecer a doble dígito separa a la lista (ver la nota de abajo) y, en la venta
# (portfolio_price_alerts), con margen del cuartil alto también es ser
# excepcional (MSFT), no solo el ROE (MCO).
CRECIMIENTO_QUE_JUSTIFICA = 10.0

# ── La nota de la lista VALUE US (7-nov-2026) ────────────────────────────────
# La puerta de arriba decide quién entra; esto decide el orden. Sustituye a una
# suma de más de 25 ajustes cuyos máximos daban unos 200 sobre 100, que medida
# casi no miraba el precio (correlación 0,10 con nuestra valoración), repartía
# el 34 % del orden entre Cerebro y opciones sin predecir a 180 días, y dejaba
# fuera del corte de 30 a las que mejor lo hicieron.
#
# Medido contra el universo actual en dos periodos independientes, con el P/E de
# BPA normalizado de TIKR y las ventas del último año cerrado:
#
#                                  2020-25, 12 meses    2026, 90 y 180 días
#   ventas >=10% y PER < -1σ       +8,8 (SPY +5,5)      +6,4 y +13,1     PRIORIDAD
#   ventas >=10%, PER no tan bajo  -7,5 (SPY -11,8)     -4,1 y  (sin muestra)
#   ventas de 0 a 10%              -3,1 (SPY  -6,3)     +1,2 y  +1,1
#
# Solo la combinación tiene ventaja, y en los dos periodos. Crecer sin estar barata
# contra su propia historia salió peor que no crecer, así que no hay un grupo
# intermedio: el resto pasa la puerta y se queda en observación, diciendo qué le
# falta. La puerta sola no aporta (-0,4 y -0,2 en 2026 contra este universo; el «+5»
# de la nota de arriba era contra el universo más amplio y peor de entonces).
#
# Son 31 empresas y 2024 salió -17: es lo mejor medido, no una garantía. Y son
# empresas que siguen vivas hoy, lo que favorece a todo lo que ha caído.
PER_BAJO_SU_MEDIA = -1.0     # σ contra sus 10 años (bandas_per)
NOTA_PRIORIDAD = 80.0
NOTA_OBSERVAR = 40.0
PUNTOS_POR_BARATA = 20.0     # dentro de cada grupo; nunca alcanza al siguiente
PER_Z_TOPE = 3.0             # 3σ por debajo de su media ya es lo más barato
FCF_YIELD_TOPE = 8.0
# Avisos de PRIORIDAD: se dicen, no puntúan. Medido en 2026 dentro del grupo, lo que se
# frena más de 10 puntos rinde +4,1 a 90 días frente a +7,6 (los dos ganan al universo).
# Recortar consenso va en la misma dirección (-5 a 0: +3,0; sin recorte: +7,0), pero de
# recortes mayores aún no hay retorno medido. Es poco para vetar y demasiado para callarlo:
# en noviembre las «ventas del último año» son un ejercicio cerrado hace diez meses.
FRENAZO_PUNTOS = 10.0
RECORTE_CONSENSO = -5.0

# Rango en que el múltiplo histórico propio sirve de ancla para el «P/E justo». Por
# encima es burbuja y por debajo suele ser un beneficio raro: en los dos casos no
# hay objetivo por P/E. El techo lo confirmó el usuario el 29-oct-2026 («no quiero
# precios de burbuja»), sabiendo que deja fuera a NOW aun con datos limpios.
PER_ANCLA_MIN, PER_ANCLA_MAX = 8.0, 45.0
# Tope de sensatez del objetivo por P/E. No es una banda de inversión: es el
# punto a partir del cual el número dice más del dato que de la empresa.
UPSIDE_PE_ABSURDO = 150.0


def _detalle(raw) -> dict:
    import ast
    if isinstance(raw, dict):
        return raw
    try:
        d = ast.literal_eval(str(raw))
        return d if isinstance(d, dict) else {}
    except (ValueError, SyntaxError):
        return {}


def calidad_negocio(df):
    """Margen operativo y ROE (%) de cada fila, sacados de `health_details`."""
    import pandas as pd
    salud = df.get('health_details', pd.Series(index=df.index, dtype=object)).map(_detalle)
    return pd.DataFrame({
        'margen': pd.to_numeric(salud.map(lambda d: d.get('operating_margin_pct')), errors='coerce'),
        'roe': pd.to_numeric(salud.map(lambda d: d.get('roe_pct')), errors='coerce'),
    }, index=df.index)


def motivo_fuera_de_value(df):
    """Por qué cada fila NO es una idea VALUE ('' si lo es)."""
    import pandas as pd
    motivo = pd.Series('', index=df.index, dtype=object)
    tri = (pd.to_numeric(df['upside_triangulated_pct'], errors='coerce')
           if 'upside_triangulated_pct' in df.columns else pd.Series(float('nan'), index=df.index))
    sin_margen = ~respaldo_propio(df)
    motivo[sin_margen & tri.isna()] = 'sin valoración propia que la respalde'
    motivo[sin_margen & tri.notna()] = [
        f'nuestra valoración solo le ve {int(round(v)):+d}%' for v in tri[sin_margen & tri.notna()]]

    crece = (pd.to_numeric(df['rev_growth_yoy'], errors='coerce')
             if 'rev_growth_yoy' in df.columns else pd.Series(float('nan'), index=df.index))
    cae = (motivo == '') & (crece < VENTAS_MINIMAS)
    motivo[cae] = [f'ventas cayendo ({v:+.1f}%): el negocio empeora' for v in crece[cae]]
    # Sin el dato no se puede decir que el negocio no empeora, y eso es lo que
    # separa una barata de una trampa: no se presume.
    motivo[(motivo == '') & crece.isna()] = 'sin dato de ventas para ver si el negocio empeora'
    # Un trimestre no basta: HHH daba +330 % con el año en -16 % (ventas de suelo a
    # golpes). Con el año cayendo, -3,0 y -5,7 contra el universo a 90 y 180 días
    # en 2026. Solo se mira donde bandas_per lo aporta: Europa no lo tiene.
    if 'ventas_anual_pct' in df.columns:
        anual = pd.to_numeric(df['ventas_anual_pct'], errors='coerce')
        cae_anual = (motivo == '') & (anual < VENTAS_MINIMAS)
        motivo[cae_anual] = [f'ventas cayendo en el último año ({v:+.1f}%): el negocio empeora' for v in anual[cae_anual]]
    return motivo


def nota_value(df):
    """Grupo, lo barata que está, qué le falta y nota de cada fila.

    PRIORIDAD: ventas del último año >=10 % y PER a más de 1σ bajo su media, o que
    pueda doblar con el beneficio en su tendencia (`value_dobla`, ver `puede_doblar`).
    El resto de la puerta queda en OBSERVAR y `value_falta` dice por qué. Fuera de la
    puerta, nota 0. Lo que falta no se rellena: sin historia de PER o sin ventas
    anuales no se puede ser PRIORIDAD. El FCF no cuenta donde no es caja libre
    (bancos, aseguradoras, REIT) ni donde el validador de Owner Earnings no se fía.
    """
    import pandas as pd
    salida = df.copy()
    nan = pd.Series(float('nan'), index=df.index)
    anual = pd.to_numeric(df['ventas_anual_pct'], errors='coerce') if 'ventas_anual_pct' in df.columns else nan
    z = pd.to_numeric(df['per_z'], errors='coerce') if 'per_z' in df.columns else nan
    fcf = pd.to_numeric(df['fcf_yield_pct'], errors='coerce') if 'fcf_yield_pct' in df.columns else nan
    if 'fcf_es_caja_libre' in df.columns:
        fcf = fcf.where(df['fcf_es_caja_libre'].astype(str).str.strip().str.lower() != 'false')
    if 'oe_fcf_no_fiable' in df.columns:
        fcf = fcf.where(df['oe_fcf_no_fiable'].astype(str).str.strip().str.lower() != 'true')

    barata = pd.concat([(-z / PER_Z_TOPE).clip(0, 1), (fcf / FCF_YIELD_TOPE).clip(0, 1)], axis=1).mean(axis=1).fillna(0.0)
    dobla = puede_doblar(df)[0]
    prioridad = ((anual >= CRECIMIENTO_QUE_JUSTIFICA) & (z < PER_BAJO_SU_MEDIA)) | dobla
    base = pd.Series(NOTA_OBSERVAR, index=df.index)
    base[prioridad] = NOTA_PRIORIDAD

    trimestre = pd.to_numeric(df['rev_growth_yoy'], errors='coerce') if 'rev_growth_yoy' in df.columns else nan
    revision = pd.to_numeric(df['revision_13s_pct'], errors='coerce') if 'revision_13s_pct' in df.columns else nan

    def _avisos(a, q, r):
        partes = []
        if a == a and q == q and q < a - FRENAZO_PUNTOS:
            partes.append(f'se frena: último trimestre {q:+.0f} %')
        if r == r and r <= RECORTE_CONSENSO:
            partes.append(f'consenso de BPA {r:+.0f} % en 13 semanas')
        return ' · '.join(partes)

    def _falta(a, zeta):
        partes = []
        if a != a:
            partes.append('sin ventas anuales')
        elif a < CRECIMIENTO_QUE_JUSTIFICA:
            partes.append(f'ventas anuales {a:+.1f} %, le falta crecer al {CRECIMIENTO_QUE_JUSTIFICA:.0f} %'.replace('.', ','))
        if zeta != zeta:
            partes.append('sin historia de PER')
        elif zeta >= PER_BAJO_SU_MEDIA:
            partes.append(f'PER a {zeta:+.2f}σ, le falta bajar de {PER_BAJO_SU_MEDIA:+.0f}σ'.replace('.', ','))
        return ' · '.join(partes)

    dentro = motivo_fuera_de_value(df) == ''
    salida['value_grupo'] = pd.Series('OBSERVAR', index=df.index, dtype=object).where(~prioridad, 'PRIORIDAD').where(dentro, '')
    salida['value_barata'] = barata.round(3)
    salida['value_falta'] = [_falta(a, zeta) if d and not p else ''
                             for a, zeta, d, p in zip(anual, z, dentro, prioridad)]
    salida['value_avisos'] = [_avisos(a, q, r) if d and p else ''
                              for a, q, r, d, p in zip(anual, trimestre, revision, dentro, prioridad)]
    salida['recorrido_propio_pct'] = recorrido_propio(df).round(1)
    salida['value_dobla'] = dobla & dentro
    salida['value_score'] = (base + PUNTOS_POR_BARATA * barata).round(1).where(dentro, 0.0)
    return salida


# ── Las que pueden doblar (8-nov-2026) ───────────────────────────────────────
# El usuario: «hay veces que se ve claro que una empresa puede doblar [...] no
# deberíamos obviarlas, pero haciéndolo con cabeza». Medido reconstruyendo cada mes
# de 2020-26 nuestro P/E (bandas_per con la fecha de entonces) y el DCF, contra el
# universo actual, dentro de la puerta y con nuestros modelos viéndole +100 % o más:
#
#                                   2020-23, 12m    2024-26, 12m / 6m
#   beneficio >50 % sobre tendencia   -9,9 (9)       -28,5 (4) / -15,8 (4)
#   beneficio en su tendencia        +23,5 (6)       +21,6 (2) / +10,1 (8)
#
# Más recorrido no da más ganancia en general (10-30 %: -1,2; >=100 %: -4,9): lo que
# separa es si el beneficio es de pico. Con el BPA muy por encima de su tendencia, el
# PER parece bajo porque el beneficio está arriba (la trampa de las cíclicas que
# describe Lynch): pierden ALLY, COF, CVX, NUE, OXY, PGR y LPX, todas a +59 % o más;
# ganan META, UNH, IT, FDS, LEN o THC, todas a +37 % o menos. Ningún caso cae entre
# 37 y 59, así que el corte en 50 no está afinado: cualquiera en ese hueco separa igual.
#
# Las de pico estaban casi todas en PRIORIDAD (8 de 11): se vetan. Las sanas en
# OBSERVAR también ganan en los dos periodos (+9,7 a 12m en 2020-23; +11,6 a 6m en
# 2024-26, 7 empresas) frente al -2 del grupo: suben a PRIORIDAD. Es lo más fino de lo
# medido —pocas empresas y supervivientes, que favorece a lo que cayó—, así que en
# febrero el tracker por grupos tiene que confirmarlo. Sin tendencia del BPA no se
# presume que el beneficio sea sano (CHTR: -14).
RECORRIDO_DE_DOBLAR = 100.0
BENEFICIO_DE_PICO = 50.0     # % del BPA sobre su tendencia de seis años (bandas_per)


def recorrido_propio(df):
    """Lo que nuestros modelos (DCF y P/E) le ven a cada fila, en %. Sin el analista.

    Mediana de los dos que haya; NaN si se contradicen en el signo o si alguno delira
    (fuera de ±MODEL_UPSIDE_SANE_MAX, divisa rota), igual que la triangulación.
    """
    import numpy as np
    import pandas as pd
    from upside_triangulation import MODEL_UPSIDE_SANE_MAX
    nan = pd.Series(float('nan'), index=df.index)
    dcf = pd.to_numeric(df['target_price_dcf_upside_pct'], errors='coerce') if 'target_price_dcf_upside_pct' in df.columns else nan
    pe = pd.to_numeric(df['target_price_pe_upside_pct'], errors='coerce') if 'target_price_pe_upside_pct' in df.columns else nan
    roto = ((dcf.abs() > MODEL_UPSIDE_SANE_MAX) | (pe.abs() > MODEL_UPSIDE_SANE_MAX)).fillna(False)
    contradicen = dcf.notna() & pe.notna() & (np.sign(dcf) != np.sign(pe))
    return pd.concat([dcf, pe], axis=1).median(axis=1, skipna=True).where(~(roto | contradicen))


def puede_doblar(df):
    """(sana, de_pico): nuestros modelos le ven +100 % o más, con el beneficio en su
    tendencia o más de un 50 % por encima. Dos Series booleanas."""
    import pandas as pd
    tendencia = (pd.to_numeric(df['bpa_sobre_tendencia_pct'], errors='coerce')
                 if 'bpa_sobre_tendencia_pct' in df.columns else pd.Series(float('nan'), index=df.index))
    dobla = recorrido_propio(df) >= RECORRIDO_DE_DOBLAR
    return dobla & (tendencia <= BENEFICIO_DE_PICO), dobla & (tendencia > BENEFICIO_DE_PICO)


def vetos_value(df):
    """Descartes duros, sean del grupo que sean (Serie booleana).

    ROE negativo, analistas por debajo del precio (dentro de PRIORIDAD, en 2026:
    -6,0 a 90 días, con solo 8 observaciones, contra +6,4 del resto del grupo) y
    el beneficio de pico, tenga el recorrido que tenga.
    Cerebro vetó aquí hasta el 7-nov-2026 con su AVOID y dejó de hacerlo al medirlo:
    lo vetado rindió +8,6 a 90 días frente a -1,5 de lo neutro.

    El pico se vetaba solo en «puede doblar» (8-nov) y el 10-nov PGR salió en
    PRIORIDAD con el BPA un 98 % sobre su tendencia, porque nuestros modelos le veían
    +73 % y no +100 %. Medido con la misma reconstrucción mensual, a 12 meses contra el
    universo, 2020-23 y 2024-26:

        PRIORIDAD con el BPA >50 % sobre su tendencia   -10,2 (8 emp.)   -14,1 (6)
        PRIORIDAD con el BPA en su tendencia (<=20 %)   +17,6 (14)       +8,9 (11)
        OBSERVAR con el BPA >50 % sobre su tendencia     -2,6 (8)         -7,3 (2)
        toda la puerta con el BPA >50 %                   -6,9 (13)       -11,9 (6)

    Sin el pico, PRIORIDAD pasa de +0,7 a +8,9 en 2024-26. Sin tendencia no se veta:
    «no lo sé» no es pico.
    """
    import pandas as pd
    veto = pd.Series(False, index=df.index)
    if 'negative_roe' in df.columns:
        # Leído de un CSV es texto, y bool('False') es True: compararlo como texto.
        veto |= df['negative_roe'].astype(str).str.strip().str.lower() == 'true'
    if 'analyst_upside_pct' in df.columns:
        veto |= pd.to_numeric(df['analyst_upside_pct'], errors='coerce') < 0
    if 'bpa_sobre_tendencia_pct' in df.columns:
        veto |= pd.to_numeric(df['bpa_sobre_tendencia_pct'], errors='coerce') > BENEFICIO_DE_PICO
    return veto


# Red de seguridad, no un criterio: lo que pasa la puerta sale con 40 o más. Lo
# siguen usando Europa y global, que puntúan con su propia suma.
VALUE_SCORE_MIN = 30.0


def solo_politica_vigente(df, columna: str = 'analyst_upside_pct'):
    """Quita del histórico las señales que el sistema YA NO emitiría.

    Medir "desde el periodo limpio" no basta: en abril-2026 todavía se emitían
    señales con upside >= UPSIDE_ALTO sin ninguna comprobación propia. Desde el
    27-oct-2026 solo se aceptan si la valoración propia las respalda, y el
    histórico no guarda ese dato: se siguen apartando hasta que haya historial
    de la política nueva. Eran 59 de las 120 limpias y las peores con
    diferencia — 1,7% de acierto a 30d y -8,28% de media — así que mezclarlas
    describe una política MUERTA y hunde el resultado del sistema actual:

        a 30d   con ellas 21,0% / -4,68%   ·   sin ellas 48,8% / +0,51%
        a 90d   con ellas 33,7% / -2,68%   ·   sin ellas 66,7% / +3,46%

    Vive aquí, junto a las bandas, porque el fallo fue tenerlo duplicado: el
    tracker y signal_postmortem filtraban cada uno por su cuenta y solo por
    fecha, y publicaban cifras que se contradecían entre sí (35,6% contra 61,5%
    de acierto a 90d, detectado por coherence_check el 12-ago-2026).

    Al añadir un filtro duro nuevo al integrator, añadirlo TAMBIÉN aquí.

    Excepción: `motivo_fuera_de_value` (5-nov-2026) no se puede aplicar hacia
    atrás sobre el tracker, porque no guardaba ni el triangulado ni las ventas.
    Desde ese día los guarda (`upside_triangulated_pct`, `rev_growth_yoy`); hasta
    que haya historial, las señales anteriores al 5-nov mezclan las dos
    políticas. (La regla sí se midió hacia atrás, pero sobre los snapshots
    diarios de git, no sobre el tracker.)
    """
    import pandas as pd
    if df is None or len(df) == 0 or columna not in df.columns:
        return df
    up = pd.to_numeric(df[columna], errors='coerce')
    # NaN se conserva: "sin dato de upside" no es lo mismo que "upside alto",
    # y descartarlo sesgaría la muestra hacia las que sí tienen cobertura.
    # Con grupo guardado (desde 7-nov-2026) ya pasó la puerta: sí es política vigente.
    con_grupo = (df['value_grupo'].fillna('').astype(str) != '') if 'value_grupo' in df.columns else False
    return df[~(up >= UPSIDE_ALTO) | con_grupo]
