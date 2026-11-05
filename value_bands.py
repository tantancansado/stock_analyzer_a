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
# Lo usa la venta (portfolio_price_alerts): crecer a doble dígito con margen
# del cuartil alto también es ser excepcional (MSFT), no solo el ROE (MCO).
CRECIMIENTO_QUE_JUSTIFICA = 10.0


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
    return motivo


# Score mínimo para seguir en la lista VALUE. Vive aquí por el mismo motivo que
# las bandas de upside: el integrator lo aplicaba al ordenar y
# apply_oe_ai_adjustment bajaba scores DESPUÉS sin re-filtrar, así que el CSV
# publicado del 31-jul-2026 llevaba 15 tickers por debajo del propio corte.
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
    return df[~(up >= UPSIDE_ALTO)]
