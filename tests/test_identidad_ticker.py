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


class TestElResolvedorDeTikr:
    """La causa de los cuatro registros equivocados, arreglada en el origen.

    Tres bugs encadenados en `algolia_resolve_ticker`:

      1. buscaba con el sufijo puesto («AI.PA»), y Algolia indexa «AI»;
      2. comparaba el símbolo del resultado contra el ticker CON sufijo, así
         que la comparación exacta no acertaba nunca;
      3. y al no acertar caía en `primary = hits[0]` — el primer resultado que
         devolviera la búsqueda difusa, coincidiera o no.

    De ahí salían C3.ai por Air Liquide y un ETF apalancado por Berkshire.

    El discriminador de verdad es la BOLSA, no el símbolo: «AI» es C3.ai en
    NYSE y Air Liquide en París. Con el símbolo solo no se pueden distinguir.
    """

    def _modulo(self):
        """`tikr_scraper` depende de `pycognito`, que solo está en el runner:
        se ejecutan solo los bloques que interesan."""
        import textwrap
        from pathlib import Path
        src = (Path(__file__).resolve().parent.parent / 'tikr_scraper.py').read_text()
        ns: dict = {}
        for ini, fin in (('EXCHANGE_RIC = {', '\n}\n'),
                         ('TIKR_TICKER_MAP = {', 'def build_ric_id'),
                         ('BOLSAS_US = (', '# Stealth timing')):
            i = src.index(ini)
            j = src.index(fin, i) + (3 if fin == '\n}\n' else 0)
            exec(textwrap.dedent(src[i:j]), ns)
        return ns

    def test_se_busca_sin_el_sufijo(self):
        f = self._modulo()['tikr_ticker']
        assert f('AI.PA') == 'AI'
        assert f('SAP.DE') == 'SAP'
        assert f('4684.T') == '4684'
        assert f('MCO') == 'MCO', 'sin sufijo se queda igual'

    def test_los_casos_especiales_siguen_mandando(self):
        # 'BRK.B' con PUNTO desde el 18-sep-2026: con la barra, Algolia no
        # devolvía ningún resultado que cuadrara y Berkshire se quedaba sin
        # datos de TIKR. Comprobado contra las cuatro variantes.
        assert self._modulo()['tikr_ticker']('BRK-B') == 'BRK.B'

    def test_un_ticker_nuevo_no_depende_del_mapa_a_mano(self):
        """El mapa cubre los 9 tickers con sufijo de hoy. El décimo que se
        añada no estaría, y antes se buscaba con el sufijo puesto."""
        ns = self._modulo()
        assert 'NUEVO.PA' not in ns['TIKR_TICKER_MAP']
        assert ns['tikr_ticker']('NUEVO.PA') == 'NUEVO'

    def test_un_ticker_con_sufijo_no_puede_resolver_a_una_bolsa_de_eeuu(self):
        coherente = self._modulo()['_bolsa_coherente']
        assert not coherente('AI.PA', 'NYSE'), 'C3.ai en NYSE no es Air Liquide'
        assert not coherente('EXPN.L', 'NasdaqGM'), 'un fondo US no es Experian'
        assert coherente('AI.PA', 'ENXTPA')
        assert coherente('AUTO.L', 'LSE')

    def test_y_uno_sin_sufijo_tiene_que_resolver_a_una(self):
        coherente = self._modulo()['_bolsa_coherente']
        assert not coherente('MMC', 'WSE'), 'MM Conferences (Varsovia) no es Marsh & McLennan'
        assert coherente('MCO', 'NYSE')

    def test_sin_poder_juzgar_no_se_desmiente(self):
        """Se valida por exclusión: las bolsas de EE.UU. las conoce el mapa, las
        de París o Ámsterdam no, y no se van a adivinar. Desmentir sin dato es
        tan malo como afirmar sin dato."""
        coherente = self._modulo()['_bolsa_coherente']
        assert coherente('XX.ZZ', 'BolsaQueNoConozco')
        assert coherente('XX.ZZ', '')

    def test_sin_candidato_valido_no_se_devuelve_el_primero(self):
        from pathlib import Path
        src = (Path(__file__).resolve().parent.parent / 'tikr_scraper.py').read_text()
        i = src.index('def algolia_resolve_ticker')
        cuerpo = src[i:src.index('\ndef ', i + 10)]
        codigo = '\n'.join(l.split('#')[0] for l in cuerpo.split('\n'))
        assert 'primary = hits[0]' not in codigo, \
            'volvió el fallback que devolvía cualquier resultado parecido'
        assert 'return None' in codigo


# ─── La puerta de atrás del resolvedor ────────────────────────────────────────

class TestFallbackNoInventaEmpresa:
    """El arreglo del 17-sep-2026 blindó el resolvedor de Algolia, y funciona.
    Pero dejó abierto el fallback `/trkdids`, que no comprueba símbolo, bolsa
    ni nombre: cuando Algolia rechazaba un ticker, el código preguntaba allí y
    se quedaba con lo primero que le dieran. Los datos del 20-sep publicaban
    BRK-B=Brooks Macdonald (GBP), DOL.TO=un ETF de WisdomTree y MMC=MM
    Conferences de Varsovia. Fichas completas, números plausibles, otra
    compañía.
    """

    def test_rechazo_de_algolia_no_cae_al_fallback(self, monkeypatch):
        import tikr_scraper as ts
        llamado = []
        monkeypatch.setattr(ts, "algolia_resolve_ticker",
                            lambda t: ts.SIN_COINCIDENCIA)
        monkeypatch.setattr(ts, "resolve_ticker_api",
                            lambda *a: llamado.append(a) or {"cid": "malo", "tid": "malo"})

        out = ts.resolve_ticker(None, "tok", "BRK-B", {})
        assert out is None, "un rechazo con motivo no se reintenta a ciegas"
        assert not llamado, "no debe preguntarse al endpoint que no valida nada"

    def test_fallo_tecnico_si_usa_el_fallback(self, monkeypatch):
        """Distinto caso: Algolia no pudo responder. Ahí el fallback es lo
        único que hay, y usarlo es correcto."""
        import tikr_scraper as ts
        monkeypatch.setattr(ts, "algolia_resolve_ticker", lambda t: None)
        monkeypatch.setattr(ts, "resolve_ticker_api",
                            lambda *a: {"cid": "1", "tid": "2"})
        monkeypatch.setattr(ts, "_fetch_oa_perm_id", lambda *a: None)
        monkeypatch.setattr(ts, "save_id_cache", lambda c: None)

        out = ts.resolve_ticker(None, "tok", "AAPL", {})
        assert out is not None and out["cid"] == "1"


class TestDivisaIncoherenteAntesDePublicar:
    """Red de seguridad al guardar: aunque algo se cuele, un registro cuya
    divisa contradice la bolsa del sufijo no llega al fichero."""

    CASOS_MALOS = [
        ("AI.PA",  "USD", "C3.ai, Inc."),
        ("BRK-B",  "GBP", "Brooks Macdonald Group plc"),
        ("DOL.TO", "USD", "WisdomTree Trust"),
    ]

    def test_descarta_los_tres_casos_reales(self):
        import tikr_scraper as ts
        for ticker, divisa, nombre in self.CASOS_MALOS:
            motivo = ts._divisa_incoherente(
                ticker, {"price": {"curr": divisa}, "company_name": nombre})
            assert motivo, f"{ticker} en {divisa} tendria que descartarse"
            assert divisa in motivo and nombre in motivo

    def test_deja_pasar_lo_correcto(self):
        import tikr_scraper as ts
        buenos = [("AI.PA", "EUR"), ("AAPL", "USD"), ("DOL.TO", "CAD"),
                  ("AZN.L", "GBp")]   # Londres cotiza en peniques
        for ticker, divisa in buenos:
            assert ts._divisa_incoherente(
                ticker, {"price": {"curr": divisa}}) is None, f"{ticker}/{divisa}"

    def test_dato_ausente_no_es_dato_equivocado(self):
        """Sin divisa, o con un sufijo que no conocemos, no hay nada que
        probar. Descartar ahí sería tirar empresas buenas por un hueco."""
        import tikr_scraper as ts
        assert ts._divisa_incoherente("AAPL", {"price": {}}) is None
        assert ts._divisa_incoherente("AAPL", {}) is None
        assert ts._divisa_incoherente("XYZ.ZZ", {"price": {"curr": "USD"}}) is None


class TestPrecioDistintoNoEsOtraEmpresa:
    """El 22-sep-2026 META tumbó el pipeline con «fundamental_scores=741,25 y
    tikr=665,75 (11% de diferencia)». Las dos fuentes decían «Meta Platforms,
    Inc.» y las dos en dólares: no era otra compañía, era que TIKR se refresca
    los domingos y el resto del pipeline a diario. A mitad de semana cualquier
    valor movido pasa del 10%. Un desfase se vigila con la frescura.
    """

    @staticmethod
    def _dos(nombre_a, precio_a, nombre_b, precio_b, divisa='USD'):
        return [{'fuente': 'fund', 'nombre': nombre_a, 'precio': precio_a, 'divisa': divisa},
                {'fuente': 'tikr', 'nombre': nombre_b, 'precio': precio_b, 'divisa': divisa}]

    def test_mismo_nombre_y_precio_movido_no_salta(self):
        from identidad_ticker import revisar
        fuentes = self._dos('Meta Platforms, Inc.', 741.25,
                            'Meta Platforms, Inc.', 665.75)
        assert revisar('META', fuentes) == []

    def test_mismo_nombre_pero_precio_disparatado_sigue_saltando(self):
        """Tolerar el desfase no es dejar de mirar: el doble de precio ya no
        se explica por unos días de diferencia."""
        from identidad_ticker import revisar
        fallos = revisar('X', self._dos('Apple Inc.', 100.0, 'Apple Inc.', 900.0))
        assert fallos and '800%' in fallos[0]

    def test_sin_nombre_el_precio_vuelve_a_ser_la_prueba(self):
        """Si no hay nombre con el que comparar, el precio es lo único que
        queda y el listón vuelve a estar bajo."""
        from identidad_ticker import revisar
        fuentes = [{'fuente': 'a', 'nombre': None, 'precio': 100.0, 'divisa': 'USD'},
                   {'fuente': 'b', 'nombre': None, 'precio': 130.0, 'divisa': 'USD'}]
        assert revisar('X', fuentes), 'un 30% sin nombre que lo respalde sí es sospechoso'

    def test_los_impostores_reales_se_siguen_cazando(self):
        from identidad_ticker import revisar
        assert revisar('AI.PA', [
            {'fuente': 'eu', 'nombre': "L'Air Liquide S.A.", 'precio': 165.24, 'divisa': 'EUR'},
            {'fuente': 'tikr', 'nombre': 'C3.ai, Inc.', 'precio': 10.54, 'divisa': 'USD'}])
        assert revisar('BRK-B', [
            {'fuente': 'f', 'nombre': 'Berkshire Hathaway Inc.', 'precio': 502.01, 'divisa': 'USD'},
            {'fuente': 'tikr', 'nombre': 'Brooks Macdonald Group plc', 'precio': 16.40, 'divisa': 'GBP'}])
