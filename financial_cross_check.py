#!/usr/bin/env python3
"""
Financial Cross-Check — rellena huecos desde la fuente primaria y comprueba que
los datos cuadran entre sí antes de usarlos.

Dos funciones, en este orden:

1. derive_from_statements()
   `info` es un resumen y a veces le faltan campos que SÍ están en los estados
   financieros (`stock.cashflow`, `.financials`, `.balance_sheet`). ATLKY el
   3-ago-2026: `operatingCashflow` = None en info, y el estado de flujos tenía
   'Free Cash Flow' y 'Capital Expenditure' de 2023, 2024 y 2025. Antes de
   preguntarle a nadie, se mira donde el dato ya está.

2. check_coherence()
   Cuadres contables que deben cumplirse siempre. El más útil es también el más
   simple:

       sharesOutstanding × precio ≈ marketCap

   MCO da 1.0000 y ATLKY 0.6801. Ese 0.68 NO es el tipo de cambio (0.105): es el
   ratio del ADR — `sharesOutstanding` son las acciones ordinarias suecas y el
   precio es el del ADS, que representa otra fracción. Por eso convertir la
   divisa no bastaba: todo ratio POR ACCIÓN (EPS, FCF/acción y el DCF que sale
   de ahí) sigue mal. De ahí el DCF de +568.9% de ATLKY.

   Cuando el cuadre falla, los agregados (FCF yield, EBIT/EV, que usan marketCap)
   siguen siendo válidos; los por acción no. Se marcan y no se usan, en vez de
   publicar un DCF inventado por una discrepancia de unidades.
"""
from __future__ import annotations

from typing import Any

# Cuánto puede desviarse shares×price de marketCap y seguir siendo cuadre.
# Holgura para recompras y acciones emitidas entre el cierre y el dato.
SHARES_PRICE_TOLERANCE = 0.05

# A partir de esta diferencia con el estado de flujos, el `freeCashflow` de
# yfinance se descarta y manda el derivado. Mismo umbral que ya usaba el aviso
# de `check_coherence`, que detectaba el problema sin actuar.
TOLERANCIA_FCF = 0.25

# Filas de los estados financieros por campo de `info`
STATEMENT_ROWS = {
    'freeCashflow':      ('cashflow', 'Free Cash Flow'),
    'operatingCashflow': ('cashflow', 'Operating Cash Flow'),
    'capitalExpenditure': ('cashflow', 'Capital Expenditure'),
    'totalRevenue':      ('financials', 'Total Revenue'),
    'netIncomeToCommon': ('financials', 'Net Income'),
    'ebitda':            ('financials', 'EBITDA'),
    'totalDebt':         ('balance_sheet', 'Total Debt'),
    'totalCash':         ('balance_sheet', 'Cash And Cash Equivalents'),
}


def _latest(df, row_name: str):
    """Valor más reciente de una fila del estado financiero, o None."""
    if df is None or getattr(df, 'empty', True):
        return None
    try:
        if row_name not in df.index:
            return None
        series = df.loc[row_name].dropna()
        if series.empty:
            return None
        return float(series.iloc[0])
    except Exception:
        return None


def _ttm(df, row_name: str):
    """Suma de los cuatro últimos trimestres de una fila, o None.

    El valor «más reciente» de un estado TRIMESTRAL es un trimestre suelto, no
    un año. Para comparar contra `info` —que da magnitudes anuales— hay que
    sumar cuatro.
    """
    if df is None or getattr(df, 'empty', True):
        return None
    try:
        if row_name not in df.index:
            return None
        serie = df.loc[row_name].dropna().sort_index(ascending=False)
        if len(serie) < 4:
            return None
        return float(serie.iloc[:4].sum())
    except Exception:
        return None


def fcf_del_estado_de_flujos(stock):
    """FCF de los últimos doce meses: flujo operativo menos capex.

    `freeCashflow` de yfinance es un campo calculado por ellos y se desvía sin
    patrón. Medido el 17-sep-2026:

        YUM   declarado   833M   ·  operativo - capex  1.679M   (la MITAD)
        MCD   declarado 6.262M   ·  operativo - capex  7.761M   (-19%)

    Con 833M, el FCF yield de YUM salía 2,22% cuando el real es 4,48%, y el DCF
    partía de la mitad del flujo: por eso decía que estaba un 5,7% cara mientras
    el modelo de P/E decía +73,7%. Los dos modelos se contradecían porque los
    dos tenían el input roto, y el sistema respondía descartando los dos en vez
    de mirar cuál estaba mal.

    Por qué no bastaba `info`: `capitalExpenditure` viene None en ambas, así
    que el cuadre de abajo ni siquiera podía compararlos. Aquí se va al estado
    de flujos trimestral, que es donde el dato está de verdad.
    """
    try:
        qc = stock.quarterly_cashflow
    except Exception:
        return None, None
    ocf = _ttm(qc, 'Operating Cash Flow')
    capex = _ttm(qc, 'Capital Expenditure')
    if ocf is None or capex is None:
        return None, None
    fcf = ocf - abs(capex)

    # El capital circulante es un movimiento de BALANCE, no dinero que genere
    # el negocio, y puede revertir al año siguiente. Distorsiona en las dos
    # direcciones (datos del 17-sep-2026, último año fiscal):
    #
    #     CBOE   flujo 1.753M   circulante  +529M  (+30%)  -> lo INFLA
    #     V      flujo 23.059M  circulante -15.172M (-66%) -> lo DEPRIME
    #     ADP    flujo 5.441M   circulante  -1.106M (-20%)
    #
    # Con el de CBOE dentro, su FCF yield salía 6,04% cuando el real es 4,14%,
    # y parecía crecer al 27,6% cuando sus ingresos crecen al 6,0%.
    #
    # Se toma el MENOR entre el FCF con circulante y sin él. Es conservador en
    # los dos sentidos: a quien se lo infla se le quita, y a quien se lo
    # deprime no se le regala un flujo que no ha entrado en caja.
    wc = _ttm(qc, 'Change In Working Capital')
    if wc is not None:
        fcf = min(fcf, ocf - wc - abs(capex))

    return fcf, capex



def crecimiento_ingresos_3y(stock) -> float | None:
    """Crecimiento anual compuesto de ingresos a 3 años, del estado anual.

    `revenueGrowth` de yfinance es el crecimiento de UN trimestre contra el
    mismo del año anterior. Proyectar cinco años con eso da resultados
    absurdos en cuanto el trimestre es atípico:

        OXY   revenueGrowth +53,4%   ->  DCF 123 $ cotizando a 59 $  (+109%)
        CVX   revenueGrowth +51,4%   ->  DCF 386 $ cotizando a 211 $  (+84%)

    Los dos números son ciertos y salen de las cuentas; lo que no es cierto es
    que una petrolera crezca al 15% anual durante un lustro porque un trimestre
    rebotara con el crudo. Es el mismo error que cometí yo al describir a
    McDonald's con un solo trimestre.

    Tres años suaviza el ciclo sin llegar a describir otra empresa.
    """
    try:
        fin = stock.income_stmt
    except Exception:
        return None
    if fin is None or getattr(fin, 'empty', True) or 'Total Revenue' not in fin.index:
        return None
    try:
        r = fin.loc['Total Revenue'].dropna().sort_index(ascending=False)
        if len(r) < 4:
            return None
        ini, fin_ = float(r.iloc[3]), float(r.iloc[0])
        if ini <= 0 or fin_ <= 0:
            return None
        return (fin_ / ini) ** (1 / 3) - 1
    except Exception:
        return None



def crecimiento_bpa_3y(stock) -> float | None:
    """Crecimiento anual compuesto del BPA a 3 años, del estado anual.

    Existe por el mismo motivo que `crecimiento_ingresos_3y`, y para el mismo
    modelo: el DCF necesita una tasa que se pueda proyectar un lustro, y
    `earningsGrowth` de yfinance es UN trimestre contra el mismo del año
    anterior. Medido el 23-sep-2026 sobre 22 empresas del universo, en nueve
    de ellas el crecimiento que acababa usando el DCF salía de ese trimestre,
    y en cinco lo mandaba al suelo del -10%:

        WMT   ingresos 3a  +5,3%   ·  un trimestre de beneficio  -9,1%
        CP    ingresos 3a +19,6%   ·  un trimestre               -13,5%
        ETN   ingresos 3a  +9,8%   ·  un trimestre               -15,9%
        LEN   ingresos 3a  +0,5%   ·  un trimestre               -48,0%

    Con eso el DCF proyectaba a Walmart encogiendo un 9% anual cinco años y la
    valoraba en 31,64 $ cotizando a 110 $.

    Tomar el MENOR de ingresos y beneficio sigue siendo lo correcto —si el
    beneficio crece menos que las ventas, los márgenes se estrechan y eso hay
    que recogerlo—. Lo que no se puede es comparar tres años contra un
    trimestre y quedarse con el peor: no miden lo mismo.

    Usa el beneficio NETO por acción diluida, que es la misma base con la que
    `serie_per_historica` calcula los múltiplos.
    """
    try:
        fin = stock.income_stmt
    except Exception:
        return None
    if fin is None or getattr(fin, 'empty', True):
        return None
    if 'Net Income' not in fin.index or 'Diluted Average Shares' not in fin.index:
        return None
    try:
        ni = fin.loc['Net Income'].dropna()
        sh = fin.loc['Diluted Average Shares'].dropna()
        fechas = sorted(set(ni.index) & set(sh.index), reverse=True)
        if len(fechas) < 4:
            return None
        def _bpa(f):
            acciones = float(sh[f])
            return float(ni[f]) / acciones if acciones > 0 else None
        fin_, ini = _bpa(fechas[0]), _bpa(fechas[3])
        # Un BPA negativo en cualquiera de los dos extremos no da un CAGR: la
        # raíz cúbica de un cociente negativo no existe, y forzarla inventaría
        # una tasa. Sin dato es mejor que con uno falso.
        if ini is None or fin_ is None or ini <= 0 or fin_ <= 0:
            return None
        return (fin_ / ini) ** (1 / 3) - 1
    except Exception:
        return None


def serie_per_historica(stock) -> dict:
    """Los P/E anuales de la empresa, y cuáles NO cuentan para el ancla.

    Devuelve {'pers', 'mediana', 'n', 'dispersion', 'excluidos', 'fragil'}.

    Un año con el beneficio en un VALLE no dice a qué múltiplo cotiza la
    empresa: dice que ese año ganó poco. El P/E sale disparado por el
    denominador, no porque el mercado pagara más. SPGI en 2023 marcó 49,5x
    con un BPA de 8,23 hundido por la integración de IHS Markit, entre un
    10,20 antes y un 12,35 después; ese 49,5 empujaba su ancla de 33,5 a 35,6
    y el objetivo de 550 a 584.

    Medido sobre las 129 del universo con histórico: 13 tienen un año así y
    12 mueven el ancla más de un 5%. Los cambios son SIEMPRE a la baja —un
    valle solo puede inflar el múltiplo— así que esto quita objetivos
    optimistas, no los inventa. Los mayores: BN 59,8→36,9, TECK 12,9→9,0,
    NOW 123,2→91,8.

    Lo que NO se toca: la mediana sobre los años que quedan. El ancla no
    tiene sesgo de conjunto —sobre el universo publica un upside mediano de
    +5,4% con el 56% positivo— así que el método base funciona y solo hacía
    falta quitarle la basura.
    """
    vacio = {'pers': [], 'mediana': None, 'n': 0, 'dispersion': None,
             'excluidos': [], 'fragil': True}
    try:
        fin, hist = stock.income_stmt, stock.history(period='5y')
    except Exception:
        return vacio
    if fin is None or getattr(fin, 'empty', True) or hist is None or hist.empty:
        return vacio
    if 'Net Income' not in fin.index or 'Diluted Average Shares' not in fin.index:
        return vacio
    try:
        ni = fin.loc['Net Income'].dropna()
        sh = fin.loc['Diluted Average Shares'].dropna()
        idx = hist.index
        if getattr(idx, 'tz', None) is not None:
            idx = idx.tz_localize(None)
        cierres = hist['Close']
        cierres.index = idx

        puntos = []   # (fecha, bpa, per), del más viejo al más nuevo
        for fecha in sorted(ni.index):
            if fecha not in sh.index:
                continue
            acciones = float(sh[fecha])
            if acciones <= 0:
                continue
            bpa = float(ni[fecha]) / acciones
            if bpa <= 0:
                continue
            px = cierres[cierres.index <= fecha]
            if len(px):
                puntos.append((fecha, bpa, float(px.iloc[-1]) / bpa))
        if len(puntos) < 3:
            return vacio

        # Un valle: el beneficio cae respecto al año anterior y se recupera al
        # siguiente. Los extremos de la serie no se pueden juzgar así —les
        # falta un vecino— y se quedan.
        fuera = []
        for k in range(1, len(puntos) - 1):
            b_prev, b, b_next = puntos[k - 1][1], puntos[k][1], puntos[k + 1][1]
            if b < b_prev * 0.85 and b_next > b * 1.15:
                fuera.append(k)
        limpio = [p for k, p in enumerate(puntos) if k not in fuera]
        if len(limpio) < 3:      # sin material suficiente, mejor con todo
            limpio, fuera = puntos, []

        import statistics
        pers = [p for _, _, p in limpio]
        mediana = float(statistics.median(pers))
        dispersion = (max(pers) - min(pers)) / mediana if mediana else None
        return {
            'pers': [round(p, 1) for p in pers],
            'mediana': mediana,
            'n': len(pers),
            'dispersion': round(dispersion, 2) if dispersion is not None else None,
            'excluidos': [str(puntos[k][0])[:10] for k in fuera],
            # Con tres puntos o con los extremos separados por más del doble
            # de la mediana, el ancla la decide un año suelto.
            'fragil': len(pers) < 4 or (dispersion is not None and dispersion > 1.0),
        }
    except Exception:
        return vacio


def per_mediano_historico(stock) -> float | None:
    """PER mediano de la PROPIA empresa, sin los años de beneficio en valle.

    El modelo de «P/E justo» usaba PEG = 1, o sea PER justo = crecimiento en
    porcentaje. Para una empresa de calidad que crece poco eso da disparates:

        MCD   cotiza a 20,2 · su PER mediano de 4 años es 24,7 · PEG=1 dice 10
        V     cotiza a 31,5 · mediano 32,8                     · PEG=1 dice 14
        ADSK  cotiza a 28,6 · mediano 58,8                     · PEG=1 dice 16

    Con ese ancla, la mitad del universo salía «un 50% cara» (77 de 148 con
    |upside| > 60% el 18-sep-2026). Un PER de 10 para McDonald's no es una
    valoración, es el modelo diciendo que no sabe.

    La mediana del múltiplo propio es el ancla estándar para esto: la empresa
    vuelve a lo que el mercado le ha pagado históricamente. Ver
    `serie_per_historica` para qué años cuentan y por qué.
    """
    return serie_per_historica(stock).get('mediana')


# Tasa fiscal con la que se normaliza el BPA cuando la efectiva es anómala.
# No es un invento: es el orden de la tasa efectiva de una empresa grande de
# EE.UU. y coincide con la que estas mismas empresas pagan en los trimestres
# normales.
TASA_FISCAL_NORMAL = 0.245
# A partir de esta desviación de la tasa efectiva, el beneficio del periodo no
# es representativo y el BPA se normaliza.
DESVIO_FISCAL_ANOMALO = 0.12



def bpa_normalizado(stock) -> tuple[float | None, str | None]:
    """BPA de los últimos doce meses con una tasa fiscal normal.

    YUM, 18-sep-2026: un crédito fiscal de 320 M$ en un trimestre dejó la tasa
    efectiva de los últimos doce meses en -0,9%, y el BPA reportado en 7,82
    cuando el normalizado es 5,99. Sobre ese BPA inflado, el modelo de P/E
    daba un objetivo de 199 $ (+46,8%) cuando con el BPA real da 152 $
    (+12,4%).

    Es el mismo apunte que ya se detecta para el CRECIMIENTO —comparar el
    beneficio neto contra el operativo— pero aplicado al nivel, no a la
    variación. Se arreglaron por separado porque son dos usos distintos del
    mismo número contaminado.

    Devuelve (bpa, motivo) y (None, None) si no hace falta normalizar.
    """
    try:
        q = stock.quarterly_income_stmt
    except Exception:
        return None, None
    if q is None or getattr(q, 'empty', True):
        return None, None
    for fila in ('Pretax Income', 'Tax Provision', 'Diluted Average Shares'):
        if fila not in q.index:
            return None, None
    try:
        pre = q.loc['Pretax Income'].dropna().sort_index(ascending=False).iloc[:4]
        tax = q.loc['Tax Provision'].dropna().sort_index(ascending=False).iloc[:4]
        acc = q.loc['Diluted Average Shares'].dropna().sort_index(ascending=False).iloc[0]
        if len(pre) < 4 or len(tax) < 4 or not acc or float(acc) <= 0:
            return None, None
        pre_ttm, tax_ttm = float(pre.sum()), float(tax.sum())
        if pre_ttm <= 0:
            return None, None
        efectiva = tax_ttm / pre_ttm
        if abs(efectiva - TASA_FISCAL_NORMAL) <= DESVIO_FISCAL_ANOMALO:
            return None, None     # tasa normal: el BPA reportado vale
        bpa = pre_ttm * (1 - TASA_FISCAL_NORMAL) / float(acc)
        return bpa, (f'tasa fiscal efectiva {efectiva:.1%} — el beneficio del '
                     f'periodo no es representativo')
    except Exception:
        return None, None



def cambio_de_acciones_pct(stock) -> float | None:
    """Cuánto ha cambiado el NÚMERO de acciones en un año, en porcentaje.

    Negativo = la empresa ha reducido su capital. Es lo que le importa al
    accionista: su trozo de la empresa es mayor.

    No es lo mismo que el gasto en recompras, que es lo que se publicaba con
    este nombre (importe recomprado / capitalización). La diferencia es lo que
    se recompra solo para tapar la emisión a empleados, y es sistemática
    (18-sep-2026):

        BAC    publicaba -6,18%   ·  acciones reales -4,67%
        SPGI              -4,36%  ·                  -3,46%
        MCD               -1,32%  ·                  -0,91%

    Siempre exagera a favor. Un campo llamado «cambio de acciones» que mide
    otra cosa es peor que no tenerlo: nadie va a comprobarlo.
    """
    try:
        q = stock.quarterly_income_stmt
    except Exception:
        return None
    if q is None or getattr(q, 'empty', True) or 'Diluted Average Shares' not in q.index:
        return None
    try:
        sh = q.loc['Diluted Average Shares'].dropna().sort_index(ascending=False)
        if len(sh) < 5:
            return None
        hoy, hace_un_ano = float(sh.iloc[0]), float(sh.iloc[4])
        if hoy <= 0 or hace_un_ano <= 0:
            return None
        return (hoy / hace_un_ano - 1) * 100
    except Exception:
        return None


def peso_del_margen_de_intereses(stock) -> float | None:
    """Ingreso neto por intereses sobre ingresos totales. None si no se sabe.

    Separa a quien vive del diferencial de tipos de quien cobra comisiones,
    que es la distinción que la etiqueta de industria no hace. Ver la nota en
    `derive_from_statements`.
    """
    try:
        fin = stock.income_stmt
    except Exception:
        return None
    if fin is None or getattr(fin, 'empty', True):
        return None

    def _fila(*claves):
        for c in claves:
            if c in fin.index:
                v = fin.loc[c].dropna()
                if len(v):
                    return float(v.iloc[0])
        return None

    ingresos = _fila('Total Revenue')
    intereses = _fila('Net Interest Income', 'Total Interest Income', 'Interest Income')
    if not ingresos or ingresos <= 0 or intereses is None:
        return None
    return intereses / ingresos


def derive_from_statements(stock, info: dict, fields: list[str] | None = None) -> tuple[dict, list[str]]:
    """Rellena campos ausentes en `info` desde los estados financieros.

    Devuelve (info, campos rellenados). Fuente primaria y misma divisa que el
    resto de estados — sin IA y sin estimaciones.
    """
    wanted = fields or list(STATEMENT_ROWS)
    missing = [f for f in wanted if info.get(f) is None and f in STATEMENT_ROWS]
    if not missing:
        return info, []

    cache: dict[str, Any] = {}
    out, filled = dict(info), []
    for field in missing:
        stmt_name, row = STATEMENT_ROWS[field]
        if stmt_name not in cache:
            try:
                cache[stmt_name] = getattr(stock, stmt_name)
            except Exception:
                cache[stmt_name] = None
        val = _latest(cache[stmt_name], row)
        if val is not None:
            out[field] = val
            filled.append(field)

    # FCF: el del estado de flujos MANDA sobre el declarado, no solo lo
    # completa. Antes esto solo rellenaba el hueco cuando faltaba, y cuando
    # estaba presente pero mal —YUM: 833M contra 1.679M reales— se usaba el
    # malo y el desajuste se quedaba en un aviso por pantalla.
    derivado, capex_ttm = fcf_del_estado_de_flujos(stock)
    if capex_ttm is not None and out.get('capitalExpenditure') is None:
        out['capitalExpenditure'] = capex_ttm
        filled.append('capitalExpenditure(TTM)')
    if derivado is None:
        # Sin cuatro trimestres no hay TTM, pero puede haber anual: es lo que
        # había antes de mirar al trimestral, y quitarlo dejaba sin FCF a quien
        # solo publica cuentas anuales.
        ocf_a, capex_a = out.get('operatingCashflow'), out.get('capitalExpenditure')
        if out.get('freeCashflow') is None and ocf_a is not None and capex_a is not None:
            out['freeCashflow'] = float(ocf_a) - abs(float(capex_a))
            filled.append('freeCashflow(derivado OCF-capex)')

    if derivado is not None:
        # El derivado manda SIEMPRE, no solo cuando el desvío es escandaloso.
        # Con un umbral del 25% MCD se colaba por poco (19%: 6.262M declarados
        # contra 7.761M reales) y seguía valorándose con un flujo un quinto más
        # bajo del que genera. O el dato bueno es el del estado de flujos o no
        # lo es; no puede serlo solo a partir de cierta diferencia.
        declarado = out.get('freeCashflow')
        out['freeCashflow'] = derivado
        try:
            desvio = abs(float(declarado) - derivado) / abs(derivado) if declarado else None
        except (TypeError, ValueError, ZeroDivisionError):
            desvio = None
        if declarado is None:
            filled.append('freeCashflow(OCF-capex)')
        elif desvio is not None and desvio > TOLERANCIA_FCF:
            filled.append(f'freeCashflow(OCF-capex {derivado:,.0f} en vez del '
                          f'declarado {float(declarado):,.0f} — {desvio:.0%} de desvío)')
        elif desvio:
            filled.append(f'freeCashflow(OCF-capex, {desvio:.0%} sobre el declarado)')

    # Crecimiento de ingresos a 3 AÑOS: el `revenueGrowth` de yfinance es de un
    # trimestre, y proyectarlo cinco años dispara el DCF en cualquier negocio
    # cíclico. Se añade como campo aparte para que el que valore elija.
    g3 = crecimiento_ingresos_3y(stock)
    if g3 is not None:
        out['revenueGrowth3y'] = g3
        filled.append(f'revenueGrowth3y({g3:.1%})')

    # Lo mismo para el beneficio: sin esto, la única medida de beneficio que
    # tenía el DCF era de un trimestre, y comparar tres años contra un
    # trimestre y quedarse con el peor no es ser conservador.
    ge3 = crecimiento_bpa_3y(stock)
    if ge3 is not None:
        out['earningsGrowth3y'] = ge3
        filled.append(f'earningsGrowth3y({ge3:.1%})')

    # ¿Vive del diferencial de tipos? Es lo que separa a un prestamista de
    # una red de pagos, y la industria de yfinance no lo distingue: Visa,
    # Mastercard, Capital One, Ally y American Express comparten la etiqueta
    # «Credit Services». Los tres últimos prestan; los dos primeros cobran
    # una comisión por transacción y no asumen riesgo de crédito.
    #
    # El dato lo separa sin ambigüedad — ingreso neto por intereses sobre
    # ingresos totales, medido el 19-sep-2026:
    #
    #     V     -1%     MA    -2%          redes de pago
    #     AXP   35%     COF  110%          prestan
    #     JPM  106%     BAC  123%   ALLY 154%
    #
    # Un prestamista lo tiene positivo y grande; una red de pagos lo tiene
    # NEGATIVO, porque paga intereses por su deuda y no cobra por prestar.
    peso = peso_del_margen_de_intereses(stock)
    if peso is not None:
        out['netInterestIncomeShare'] = peso
        filled.append(f'netInterestIncomeShare({peso:.0%})')

    # Múltiplo propio, para anclar el «P/E justo» a lo que el mercado le ha
    # pagado a ESTA empresa y no a un PEG = 1 que no distingue calidad.
    _serie = serie_per_historica(stock)
    if _serie.get('mediana') is not None:
        # Los metadatos viajan con el ancla: un múltiplo sacado de tres años
        # o con los extremos muy separados lo decide un año suelto, y quien
        # lea el objetivo tiene que poder saberlo.
        out['perAnclaN'] = _serie['n']
        out['perAnclaDispersion'] = _serie['dispersion']
        out['perAnclaFragil'] = _serie['fragil']
        if _serie['excluidos']:
            out['perAnclaExcluidos'] = ','.join(_serie['excluidos'])
    per_hist = _serie.get('mediana')
    if per_hist is not None:
        out['perMedianoHistorico'] = per_hist
        filled.append(f'perMedianoHistorico({per_hist:.1f})')

    # BPA sin apuntes fiscales de un trimestre. Va DESPUÉS del múltiplo propio
    # porque los dos alimentan el mismo objetivo por P/E, y multiplicar un
    # múltiplo alto por un BPA inflado es equivocarse dos veces en el mismo
    # número.
    cambio_acc = cambio_de_acciones_pct(stock)
    if cambio_acc is not None:
        out['cambioAccionesPct'] = cambio_acc
        filled.append(f'cambioAccionesPct({cambio_acc:+.2f}%)')

    bpa, motivo = bpa_normalizado(stock)
    if bpa is not None:
        out['epsNormalizado'] = bpa
        out['epsNormalizadoMotivo'] = motivo
        filled.append(f'epsNormalizado({bpa:.2f}: {motivo})')

    if filled:
        print(f"   📄 Estados financieros aportan: {', '.join(filled)}")
    return out, filled


def check_coherence(info: dict, ticker: str = '') -> dict:
    """Cuadres contables. Devuelve qué se puede usar y qué no.

    {'per_share_reliable': bool, 'aggregate_reliable': bool, 'issues': [...],
     'shares_price_ratio': float|None}
    """
    issues: list[str] = []
    per_share_ok = True
    aggregate_ok = True
    ratio = None
    shares_efectivas = None

    shares = info.get('sharesOutstanding')
    price  = info.get('currentPrice') or info.get('regularMarketPrice')
    mcap   = info.get('marketCap')

    if shares and price and mcap:
        try:
            ratio = (float(shares) * float(price)) / float(mcap)
            if abs(ratio - 1.0) > SHARES_PRICE_TOLERANCE:
                # Dos causas distintas con el mismo síntoma, y solo una es
                # irrecuperable:
                #
                #   CLASES MÚLTIPLES — `sharesOutstanding` trae UNA clase y
                #   `marketCap` es de la empresa entera. GOOG 0,4519 (A+B+C),
                #   META 0,8656, MKC 0,9450 (con y sin voto). Aquí el dato por
                #   acción sí se puede calcular: las acciones de verdad son
                #   capitalización ÷ precio, y para GOOG eso da 12.230 M, que
                #   es su cifra real. Bloquearlo dejaba a tres de los mejores
                #   picks del universo sin DCF ni P/E — y sin decir por qué.
                #
                #   ADR — el precio es el del ADS y los estados van en otra
                #   divisa (ATLKY 0,6801, estados en SEK y cotización en USD).
                #   Ahí el número de acciones no es lo único que baila, así
                #   que sigue bloqueado.
                #
                # La divisa los separa: si los estados y la cotización están
                # en la misma, el desajuste es de clases y se puede corregir.
                fin_ccy = str(info.get('financialCurrency') or '').upper()
                cot_ccy = str(info.get('currency') or '').upper()
                # Las DOS tienen que estar y coincidir. Si falta alguna no se
                # puede descartar que sea un ADR, y dar por bueno el dato por
                # acción sin saberlo es equivocarse hacia el lado caro: un
                # DCF publicado sobre una unidad equivocada. Lo cazó el test
                # de ATLKY, que no declara divisas.
                misma_divisa = bool(fin_ccy and cot_ccy and fin_ccy == cot_ccy)
                efectivas = float(mcap) / float(price)
                if misma_divisa and efectivas > 0:
                    shares_efectivas = efectivas
                    issues.append(
                        f'acciones × precio no cuadra (ratio {ratio:.4f}) pero la '
                        f'divisa sí: son clases múltiples. Se usan '
                        f'{efectivas / 1e6:,.0f} M de acciones efectivas '
                        f'(capitalización ÷ precio) en vez de las '
                        f'{float(shares) / 1e6:,.0f} M declaradas'
                    )
                else:
                    per_share_ok = False
                    donde = (f'los estados van en {fin_ccy} mientras cotiza en '
                             f'{cot_ccy}' if (fin_ccy and cot_ccy)
                             else 'no consta en qué divisa van los estados')
                    issues.append(
                        f'acciones × precio no cuadra con la capitalización '
                        f'(ratio {ratio:.4f}) y {donde} — puede ser un ADR. Los '
                        f'ratios por acción (EPS, FCF/acción, DCF) no son '
                        f'utilizables'
                    )
        except (TypeError, ValueError, ZeroDivisionError):
            pass

    # FCF declarado contra el derivado del propio estado de flujos
    fcf, ocf, capex = info.get('freeCashflow'), info.get('operatingCashflow'), info.get('capitalExpenditure')
    if fcf and ocf and capex:
        try:
            derived = float(ocf) - abs(float(capex))
            if derived and abs(float(fcf) - derived) / abs(derived) > 0.25:
                issues.append(
                    f'FCF declarado ({float(fcf):,.0f}) se aparta del derivado '
                    f'de flujo operativo menos capex ({derived:,.0f})'
                )
        except (TypeError, ValueError, ZeroDivisionError):
            pass

    if issues and ticker:
        for i in issues:
            print(f'   🔍 {ticker}: {i}')

    return {
        'per_share_reliable': per_share_ok,
        'aggregate_reliable': aggregate_ok,
        'shares_price_ratio': round(ratio, 4) if ratio is not None else None,
        # Las que hay que usar para los ratios por acción cuando las
        # declaradas son de una sola clase. None = valen las declaradas.
        'shares_efectivas': shares_efectivas,
        'issues': issues,
    }
