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


def test_una_peticion_vacia_no_borra_las_cuentas_anteriores():
    f = _fuente_run()
    assert "if not financials_history.get('metrics'):" in f
    assert "previo.get('metrics')" in f
    assert 'conservado_de' in f, 'hay que marcar que el dato viene de antes'


def test_lo_fresco_manda_sobre_lo_conservado():
    """Si la petición trae datos, se usan: así entran las reexpresiones."""
    f = _fuente_run()
    i_fetch = f.index('financials_history = fetch_tf_financials')
    i_fallback = f.index("if not financials_history.get('metrics'):")
    assert i_fetch < i_fallback, 'el fallback solo actúa DESPUÉS de intentar la petición'


def test_las_estimaciones_conservadas_llevan_su_fecha():
    """Las estimaciones sí se revisan, a diferencia de un año cerrado. Se
    conservan igual —sin ellas `owner_earnings` proyecta el FCF a ojo— pero
    tienen que llevar de cuándo son."""
    f = _fuente_run()
    assert "previo_est.get('forward')" in f
    assert "analyst_estimates['conservado_de']" in f


class TestVerificacionDelWorkflow:
    """El paso «Verify output» miraba `total` (137 ✅) y `errors` (0 ✅) y daba
    el visto bueno. Durante cuatro meses la cobertura osciló entre el 47% y el
    81% sin que nadie lo supiera: el scraper 'funcionaba'."""

    def _script(self) -> str:
        yml = (RAIZ / '.github' / 'workflows' / 'tikr-enrichment.yml').read_text()
        i = yml.index('con_fin = sum')
        ini = yml.rindex('python3 -c "', 0, i)
        fin = yml.index('\n          "\n', i)
        return textwrap.dedent(yml[yml.index('\n', ini) + 1:fin]).replace('\\"', '"')

    def test_compila_y_no_rompe_la_cadena_del_shell(self):
        yml = (RAIZ / '.github' / 'workflows' / 'tikr-enrichment.yml').read_text()
        i = yml.index('con_fin = sum')
        ini = yml.rindex('python3 -c "', 0, i)
        fin = yml.index('\n          "\n', i)
        compile(self._script(), 'verify', 'exec')
        crudo = yml[yml.index('\n', ini) + 1:fin]
        crudas = [l.strip() for l in crudo.split('\n') if re.search(r'(?<!\\)"', l)]
        assert not crudas, f'comillas dobles sin escapar: {crudas[:2]}'

    def test_mide_el_contenido_no_solo_el_recuento(self):
        s = self._script()
        assert "financials_history', {}).get('metrics')" in s
        assert 'sys.exit(1)' in s, 'y falla si la cobertura se hunde'
