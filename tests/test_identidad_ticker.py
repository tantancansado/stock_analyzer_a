"""
Un registro completo, plausible, y de otra empresa.

Es el fallo más difícil de ver de todos los de este repo. Los demás dejan un
hueco —un `None`, una lista vacía, un cero— y se pueden buscar. Este deja el
dato lleno y bien formado: solo que es de otra compañía.

Cruzando las fuentes del MISMO ticker el 17-sep-2026 salieron cuatro:

    AI.PA    debería ser L'Air Liquide  →  TIKR traía C3.ai, Inc.
    BRK-B    Berkshire Hathaway         →  Direxion Daily BRKB Bull 2X ETF
    EXPN.L   Experian plc               →  Horizon Expansion Leaders ETF
    MMC      Marsh & McLennan           →  MM Conferences S.A. (Polonia, 8,90 PLN)

El resolvedor se queda con lo que se parece: `AI.PA` pierde el sufijo y encuentra
`AI`, `BRK-B` engancha un ETF apalancado que sigue a BRKB, `EXPN.L` otro ETF de
nombre parecido. Tres de los cuatro son fondos, no empresas — no tienen ROE ni
FCF que valga, pero el modelo los valoraba igual.
"""
import identidad_ticker as it


class TestDivisaSegunLaBolsa:
    """`.PA` cotiza en euros. Si vuelve en dólares, no es esa acción."""

    def test_los_sufijos_conocidos(self):
        assert it.divisa_esperada('AI.PA') == 'EUR'
        assert it.divisa_esperada('AUTO.L') == 'GBp'
        assert it.divisa_esperada('CSU.TO') == 'CAD'
        assert it.divisa_esperada('7741.T') == 'JPY'

    def test_sin_sufijo_es_estadounidense(self):
        assert it.divisa_esperada('MCO') == 'USD'
        assert it.divisa_esperada('BRK-B') == 'USD'

    def test_un_sufijo_desconocido_no_se_inventa(self):
        assert it.divisa_esperada('XXX.ZZ') is None

    def test_peniques_y_libras_no_son_empresas_distintas(self):
        """Londres cotiza en peniques; algunas fuentes lo dan en libras. Es la
        misma acción en otra unidad, no otra empresa."""
        assert it.revisar('AUTO.L', [
            {'fuente': 'csv', 'nombre': 'Autotrader Group plc', 'precio': 499.60, 'divisa': 'GBp'},
            {'fuente': 'tikr', 'nombre': 'Autotrader Group plc', 'precio': 4.894, 'divisa': 'GBP'},
        ]) == []


class TestNombreDeLaEmpresa:

    def test_tolera_la_forma_juridica(self):
        assert it.mismo_nombre('Moody’s Corporation', "Moody's Corp")
        assert it.mismo_nombre('Berkshire Hathaway Inc.', 'Berkshire Hathaway')
        assert it.mismo_nombre("L'Air Liquide S.A.", 'Air Liquide')

    def test_pero_no_que_sea_otra_empresa(self):
        assert not it.mismo_nombre('Berkshire Hathaway Inc.',
                                   'Direxion Daily BRKB Bull 2X ETF')
        assert not it.mismo_nombre("L'Air Liquide S.A.", 'C3.ai, Inc.')
        assert not it.mismo_nombre('Experian plc', 'Horizon Expansion Leaders ETF')

    def test_sin_nombre_no_se_puede_desmentir(self):
        assert it.mismo_nombre('', 'lo que sea')


class TestLosCuatroCasosReales:

    def test_ai_pa_no_es_c3_ai(self):
        f = it.revisar('AI.PA', [
            {'fuente': 'csv', 'nombre': "L'Air Liquide S.A.", 'precio': 166.42, 'divisa': 'EUR'},
            {'fuente': 'tikr', 'nombre': 'C3.ai, Inc.', 'precio': 10.54, 'divisa': 'USD'}])
        assert len(f) >= 2, 'debería saltar por divisa Y por nombre'

    def test_brk_b_no_es_un_etf_apalancado(self):
        f = it.revisar('BRK-B', [
            {'fuente': 'csv', 'nombre': 'Berkshire Hathaway Inc.', 'precio': 519.80, 'divisa': 'USD'},
            {'fuente': 'tikr', 'nombre': 'Direxion Daily BRKB Bull 2X ETF', 'precio': 23.38, 'divisa': 'USD'}])
        assert f, 'la divisa coincide: solo lo delatan el nombre y el precio'

    def test_mmc_no_es_polaca(self):
        f = it.revisar('MMC', [
            {'fuente': 'tikr', 'nombre': 'MM Conferences S.A.', 'precio': 8.90, 'divisa': 'PLN'}])
        assert f and 'PLN' in f[0]


def test_lo_que_concuerda_no_genera_ruido():
    """Un chequeo que salta en todo se ignora. Sobre los 137 tickers reales
    salta en 4."""
    assert it.revisar('MCO', [
        {'fuente': 'csv', 'nombre': 'Moody’s Corporation', 'precio': 466.98, 'divisa': 'USD'},
        {'fuente': 'tikr', 'nombre': "Moody's Corp", 'precio': 467.10, 'divisa': 'USD'}]) == []


def test_el_mapa_de_divisas_no_se_separa_del_frontend():
    """`frontend/src/lib/moneda.ts` tiene el mismo mapa. Dos copias que derivan
    es el fallo que más veces ha aparecido aquí."""
    import re
    from pathlib import Path
    ts = (Path(__file__).resolve().parent.parent / 'frontend' / 'src' / 'lib' / 'moneda.ts').read_text()
    bloque = ts[ts.index('DIVISA_POR_SUFIJO'):ts.index('}', ts.index('DIVISA_POR_SUFIJO'))]
    del_ts = dict(re.findall(r"(\w+):\s*'([A-Za-z]+)'", bloque))
    for suf, div in del_ts.items():
        assert it.DIVISA_POR_SUFIJO.get(suf) == div, \
            f'{suf}: el frontend dice {div} y Python dice {it.DIVISA_POR_SUFIJO.get(suf)}'
    assert set(del_ts) == set(it.DIVISA_POR_SUFIJO), 'faltan sufijos en uno de los dos'


def test_el_pipeline_lo_ejecuta():
    from pathlib import Path
    src = (Path(__file__).resolve().parent.parent / 'coherence_check.py').read_text()
    assert 'identidad_de_los_tickers' in src
