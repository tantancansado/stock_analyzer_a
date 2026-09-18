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



def per_mediano_historico(stock) -> float | None:
    """PER mediano de los últimos años de la PROPIA empresa.

    El modelo de «P/E justo» usaba PEG = 1, o sea PER justo = crecimiento en
    porcentaje. Para una empresa de calidad que crece poco eso da disparates:

        MCD   cotiza a 20,2 · su PER mediano de 4 años es 24,7 · PEG=1 dice 10
        V     cotiza a 31,5 · mediano 32,8                     · PEG=1 dice 14
        ADSK  cotiza a 28,6 · mediano 58,8                     · PEG=1 dice 16

    Con ese ancla, la mitad del universo salía «un 50% cara» (77 de 148 con
    |upside| > 60% el 18-sep-2026). Un PER de 10 para McDonald's no es una
    valoración, es el modelo diciendo que no sabe.

    La mediana del múltiplo propio es el ancla estándar para esto: la empresa
    vuelve a lo que el mercado le ha pagado históricamente. No sirve cuando no
    hay histórico o el beneficio fue negativo; ahí se devuelve None y el que
    llama decide.
    """
    try:
        fin, hist = stock.income_stmt, stock.history(period='5y')
    except Exception:
        return None
    if fin is None or getattr(fin, 'empty', True) or hist is None or hist.empty:
        return None
    if 'Net Income' not in fin.index or 'Diluted Average Shares' not in fin.index:
        return None
    try:
        ni = fin.loc['Net Income'].dropna()
        sh = fin.loc['Diluted Average Shares'].dropna()
        idx = hist.index
        if getattr(idx, 'tz', None) is not None:
            idx = idx.tz_localize(None)
        cierres = hist['Close']
        cierres.index = idx
        pers = []
        for fecha in ni.index:
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
                pers.append(float(px.iloc[-1]) / bpa)
        if len(pers) < 3:
            return None
        import statistics
        return float(statistics.median(pers))
    except Exception:
        return None


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

    # Múltiplo propio, para anclar el «P/E justo» a lo que el mercado le ha
    # pagado a ESTA empresa y no a un PEG = 1 que no distingue calidad.
    per_hist = per_mediano_historico(stock)
    if per_hist is not None:
        out['perMedianoHistorico'] = per_hist
        filled.append(f'perMedianoHistorico({per_hist:.1f})')

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

    shares = info.get('sharesOutstanding')
    price  = info.get('currentPrice') or info.get('regularMarketPrice')
    mcap   = info.get('marketCap')

    if shares and price and mcap:
        try:
            ratio = (float(shares) * float(price)) / float(mcap)
            if abs(ratio - 1.0) > SHARES_PRICE_TOLERANCE:
                per_share_ok = False
                issues.append(
                    f'acciones × precio no cuadra con la capitalización '
                    f'(ratio {ratio:.4f}): el dato por acción y el precio no '
                    f'están en la misma unidad — típico de ADR. Los ratios por '
                    f'acción (EPS, FCF/acción, DCF) no son utilizables'
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
        'issues': issues,
    }
