

class TestLosCuatroQueResolvianAOtraEmpresa:
    """Cerrado el 18-sep-2026, ticker a ticker contra Algolia.

        AI.PA    daba C3.ai, Inc.                     -> L'Air Liquide (ENXTPA)
        EXPN.L   daba Horizon Expansion Leaders ETF   -> Experian plc (LSE)
        BRK-B    daba Direxion Daily BRKB Bull 2X ETF -> Berkshire (NYSE)
        MMC      daba MM Conferences S.A. (Polonia)   -> el ticker ya no existe

    Dos causas distintas, las dos con el guardia puesto y aun así pasando:

    1. `BOLSAS_US` se derivaba del mapa de RIC, que existe para construir
       identificadores y no para enumerar el mercado estadounidense. BATS no
       estaba, así que un ETF americano en BATS se daba por bolsa extranjera y
       colaba para un ticker `.L`.

    2. El símbolo de Berkshire en TIKR es `BRK.B` con punto, no `BRK/B`. Con
       la barra no había ningún resultado válido y se quedaba sin dato.
    """

    def _ns(self):
        """`tikr_scraper` necesita `pycognito`, que solo está en el runner: se
        ejecutan solo los bloques que interesan, como en test_identidad_ticker."""
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

    def test_bats_cuenta_como_bolsa_de_eeuu(self):
        assert 'BATS' in self._ns()['BOLSAS_US'], \
            'un ETF americano en BATS vuelve a colarse como bolsa extranjera'

    def test_un_ticker_con_sufijo_no_puede_resolver_a_eeuu(self):
        f = self._ns()['_bolsa_coherente']
        assert not f('EXPN.L', 'BATS')
        assert not f('AI.PA', 'NYSE')
        assert f('EXPN.L', 'LSE')

    def test_un_ticker_sin_sufijo_tiene_que_resolver_a_eeuu(self):
        f = self._ns()['_bolsa_coherente']
        assert f('MCO', 'NYSE')
        assert not f('MMC', 'WSE')      # la bolsa de Varsovia

    def test_el_simbolo_de_berkshire_lleva_punto(self):
        assert self._ns()['TIKR_TICKER_MAP']['BRK-B'] == 'BRK.B'

    def test_las_otc_tambien_son_eeuu(self):
        """Un ADR en OTC es estadounidense: si no cuenta, cualquier ticker con
        sufijo puede resolver a un ADR de otra empresa."""
        assert {'OTCPK', 'PINX'} <= self._ns()['BOLSAS_US']
