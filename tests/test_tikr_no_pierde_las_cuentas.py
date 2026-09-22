"""
Las cuentas se tiraban y se volvían a pedir cada semana, y a un 38% le fallaba.

`fetch_tf_financials` devuelve {} ante cualquier fallo, y ese {} se escribía
encima de lo que ya había. Como el scraper corre los domingos y la ventana de
reuso son 7 días, el reuso no llegaba a activarse: cada semana se volvía a pedir
todo, a una parte le fallaba la petición, y esa parte perdía sus cuentas. La
semana siguiente le tocaba a otros.

Medido sobre 10 semanas del histórico de git:

    cobertura semanal   47% – 81%   (media 62%)
    UNIÓN de 10 semanas            99%

O sea: el dato SÍ se había descargado, solo que no se guardaba. Y de ahí venía
que el FCF de un año YA CERRADO apareciera y desapareciera el 41% de las
semanas, y que cuando estaba en las dos cambiara de valor el 30% de las veces.

Un año fiscal cerrado es un hecho, no una cotización. Si la petición de hoy trae
datos, mandan ellos (así se recogen las reexpresiones); si vuelve vacía, sigue
valiendo lo de antes.
"""
import re
import textwrap
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _fuente_run() -> str:
    """El cuerpo de `run()` leído como texto.

    `tikr_scraper` no se puede importar aquí: depende de `pycognito`, que solo
    está en el runner. Se lee el fichero, que para comprobar una invariante de
    código es suficiente y no arrastra la dependencia."""
    src = (RAIZ / 'tikr_scraper.py').read_text()
    i = src.index('def run(tickers: list')
    resto = src[i + 10:]
    fin = resto.index('\ndef ') if '\ndef ' in resto else len(resto)
    return src[i:i + 10 + fin]


def _regla():
    """`_conservar_lo_que_ya_habia`, extraída como texto.

    `tikr_scraper` no se puede importar aquí (depende de `pycognito`, que solo
    está en el runner), así que se ejecuta solo el bloque que interesa."""
    import textwrap
    src = (RAIZ / 'tikr_scraper.py').read_text()
    i = src.index('_NUNCA_SE_CONSERVAN = {')
    j = src.index('def run(tickers: list')
    ns: dict = {}
    exec(textwrap.dedent(src[i:j]), ns)
    return ns['_conservar_lo_que_ya_habia'], ns['_NUNCA_SE_CONSERVAN']


def test_un_bloque_vacio_se_rellena_con_el_de_la_semana_pasada():
    conservar, _ = _regla()
    previo = {'financials_history': {'metrics': {'shares_diluted': {'2024': 100}}},
              'fetched_at': '2026-09-10T00:00:00+00:00'}
    hoy = {'financials_history': {}, 'price': {'c': '270'}, 'fetched_at': 'ahora'}
    r = conservar(dict(hoy), previo)
    assert r['financials_history']['metrics'], 'se ha perdido lo que ya se tenía'
    assert r['conservado_de'] == '2026-09-10T00:00:00+00:00'
    assert 'financials_history' in r['conservado_bloques']


def test_lo_fresco_manda_sobre_lo_conservado():
    """Si la petición trae datos, se usan: así entran reexpresiones y revisiones."""
    conservar, _ = _regla()
    previo = {'financials_history': {'metrics': {'x': 1}}, 'fetched_at': 'antes'}
    hoy = {'financials_history': {'metrics': {'x': 999}}, 'fetched_at': 'ahora'}
    r = conservar(dict(hoy), previo)
    assert r['financials_history']['metrics']['x'] == 999
    assert 'conservado_bloques' not in r


def test_el_precio_nunca_se_conserva():
    """Arrastrar un precio viejo es el bug del «precio fósil» que ya apareció en
    el tracker: un número que parece de hoy y es de hace una semana."""
    conservar, nunca = _regla()
    for campo in ('price', 'ntm', 'multiples', 'fetched_at'):
        assert campo in nunca
    previo = {'price': {'c': '100'}, 'fetched_at': 'antes'}
    r = conservar({'price': {}, 'fetched_at': 'ahora'}, previo)
    assert r['price'] == {}, 'un precio que no se ha podido leer se queda vacío'


def test_sin_nada_previo_no_inventa():
    conservar, _ = _regla()
    r = conservar({'financials_history': {}, 'fetched_at': 'ahora'}, {})
    assert r['financials_history'] == {}
    assert 'conservado_de' not in r


def test_la_marca_dice_de_cuando_viene():
    """Un dato de la semana pasada sin avisar es otra forma de mentir."""
    conservar, _ = _regla()
    r = conservar({'headlines': [], 'fetched_at': 'ahora'},
                  {'headlines': ['x'], 'fetched_at': '2026-09-10T00:00:00+00:00'})
    assert r['conservado_de'] == '2026-09-10T00:00:00+00:00'


class TestVerificacionDelWorkflow:
    """El paso «Verify output» miraba `total` (137 ✅) y `errors` (0 ✅) y daba
    el visto bueno. Durante cuatro meses la cobertura osciló entre el 47% y el
    81% sin que nadie lo supiera: el scraper 'funcionaba'."""

    DELIMITADOR = "VERIFICA"

    def _script(self) -> str:
        yml = (RAIZ / '.github' / 'workflows' / 'tikr-enrichment.yml').read_text()
        i = yml.index('con_fin = sum')
        ini = yml.rindex(f"<<'{self.DELIMITADOR}'", 0, i)
        fin = yml.index(f'\n          {self.DELIMITADOR}\n', i)
        return textwrap.dedent(yml[yml.index('\n', ini) + 1:fin])

    def test_compila_y_no_rompe_la_cadena_del_shell(self):
        """Antes esto exigía escapar las comillas dobles, porque el bloque iba
        dentro de `python3 -c "..."`. Pero las comillas no eran lo único que
        bash interpretaba ahí dentro: el 20-sep-2026 el paso murió con
        «total: command not found» por los backticks de un comentario, que
        bash ejecuta como orden. Escapar caracteres uno a uno es perseguir la
        lista; el heredoc con el delimitador entre comillas simples no
        interpreta nada, y eso es lo que se comprueba aquí.
        """
        yml = (RAIZ / '.github' / 'workflows' / 'tikr-enrichment.yml').read_text()
        compile(self._script(), 'verify', 'exec')

        assert f"<<'{self.DELIMITADOR}'" in yml, (
            "el bloque tiene que ir en un heredoc con el delimitador entre "
            "comillas simples: sin ellas bash expande $, backticks y \\")
        assert 'python3 -c "' not in yml, (
            'volver a `python3 -c "…"` reabre la puerta a que bash interprete '
            'el contenido del script')

    def test_mide_el_contenido_no_solo_el_recuento(self):
        s = self._script()
        assert "financials_history', {}).get('metrics')" in s
        assert 'sys.exit(1)' in s, 'y falla si la cobertura se hunde'

    def test_caza_un_ticker_resuelto_a_otra_empresa(self):
        """«MMC» resolvía a «MM Conferences S.A.», polaca, a 8,90 PLN — en vez
        de Marsh & McLennan. Todos sus números serían de otra compañía, y nada
        lo delataría: el registro está completo y es plausible. Un ticker US que
        cotiza en una divisa que no es el dólar es otra empresa."""
        s = self._script()
        assert 'impostores' in s
        assert "cur != 'USD'" in s


class TestLaMarcaDeConservadoViveEnLaRaiz:
    """`_conservar_lo_que_ya_habia` pone `conservado_de` en la raíz del
    registro. El contador del workflow la buscaba dentro de
    `financials_history`, así que imprimía «0 conservados» siempre — incluido
    el 20-sep-2026, con 30 registros arrastrados. El único indicador de que
    el arrastre funciona marcaba cero justo cuando empezó a funcionar.
    """

    def test_la_marca_va_en_la_raiz(self):
        from tikr_scraper import _conservar_lo_que_ya_habia
        r = _conservar_lo_que_ya_habia(
            {'ticker': 'X', 'financials_history': {}},
            {'financials_history': {'metrics': {'2025': 1}},
             'fetched_at': '2026-09-13T00:00:00+00:00'})
        assert r['conservado_de'] == '2026-09-13T00:00:00+00:00'
        assert 'conservado_de' not in r['financials_history'], \
            'la marca no se anida dentro del bloque conservado'

    def test_el_workflow_la_cuenta_donde_esta(self):
        yml = (RAIZ / '.github' / 'workflows' / 'tikr-enrichment.yml').read_text()
        linea = next(l for l in yml.split('\n')
                     if 'conservados = sum' in l)
        assert "(v or {}).get('conservado_de')" in linea, \
            f'el contador mira donde no esta: {linea.strip()}'
        assert "financials_history', {}).get('conservado_de')" not in linea
