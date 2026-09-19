"""El gate de coherencia tumbaba el pipeline por datos de hace cinco días.

`coherence_check` es un gate duro a propósito: si la app se contradice
consigo misma, no se publica. Pero el 18-sep-2026 lo que encontraba eran
NUEVE incoherencias de identidad de TIKR que ya estaban arregladas:

    guardia de bolsa en tikr_scraper.py    17-sep 11:51
    docs/tikr_earnings_data.json           13-sep 11:50
    TIKR corre                             domingos 05:23 UTC

O sea, cuatro días de datos anteriores al arreglo y hasta el domingo no hay
forma de regenerarlos. Mientras tanto el paso salía con código 1 y se llevaba
por delante el Daily Briefing, el archivado, el informe de estado y el commit
de los datos: 155 tickers buenos sin publicar por 9 que ya no fallaban.

Lo fácil habría sido poner `continue-on-error` al paso. Eso es tapar, y
además hay un test que lo prohíbe con su motivo escrito. Lo que estaba mal no
era el gate sino la CLASIFICACIÓN: el mecanismo ⏳ ya existía para los
desfases entre artefactos de distinta cadencia, y esto es exactamente eso.
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FUENTE = (RAIZ / 'coherence_check.py').read_text()


def test_compara_la_fecha_del_volcado_con_la_del_resolvedor():
    """Sin git. La primera versión preguntaba a `git log` por las dos fechas
    y funcionaba en local, pero en CI no: actions/checkout clona en
    superficie (fetch-depth 1 por defecto) y `git log` de un fichero devuelve
    vacío. El indulto no se aplicaba y el pipeline volvió a caerse igual —lo
    vimos en la ejecución 35405660133, con las nueve incoherencias contando
    otra vez como reales.

    Las dos fechas se saben sin git: el volcado trae su propio
    `generated_at` y la del arreglo está escrita aquí.
    """
    assert 'RESOLVEDOR_TIKR_ARREGLADO' in FUENTE
    assert "get('generated_at')" in FUENTE
    assert 'tikr_desfasado' in FUENTE
    # Se comprueba el CÓDIGO, no la prosa: el comentario de arriba menciona
    # `git log` justo para explicar por qué ya no se usa, y una búsqueda de
    # texto plano lo cazaría.
    import ast
    arbol = ast.parse(FUENTE)
    llamadas_git = [
        n for n in ast.walk(arbol)
        if isinstance(n, ast.Call)
        and any(isinstance(a, ast.List)
                and any(isinstance(e, ast.Constant) and e.value == 'git' for e in a.elts)
                for a in n.args)
    ]
    assert not llamadas_git, 'en CI el historial está truncado: git no sirve aquí'


def test_la_fecha_del_arreglo_cita_su_commit():
    """Una constante a mano sin la referencia es un número que nadie sabe si
    sigue valiendo."""
    assert 'aed71672f' in FUENTE


def test_solo_se_indultan_los_hallazgos_que_señalan_a_tikr():
    """Si la contradicción es entre dos CSV del pipeline diario, ahí no hay
    desfase que valga: los dos se regeneran cada mañana."""
    assert "'tikr' in str(f).lower()" in FUENTE


def test_el_indulto_lleva_el_motivo():
    assert 'TIKR corre los domingos' in FUENTE


def test_se_marcan_con_el_simbolo_que_el_contador_ya_entiende():
    """⏳ es el prefijo que `run()` usa para no sumarlos al total."""
    i = FUENTE.index('tikr_desfasado and')
    assert "f'⏳ {f}" in FUENTE[i:i + 400]


def test_el_gate_sigue_siendo_duro():
    """Lo contrario sería tapar. Hay otro test que lo vigila desde el
    workflow; este lo fija desde el lado del script."""
    assert 'return 1' in FUENTE, 'sigue saliendo con error cuando hay contradicciones reales'
    wf = (RAIZ / '.github/workflows/daily-analysis.yml').read_text()
    m = re.search(r'- name: Coherence Check[^\n]*\n((?:\s+[^\n]*\n)*?)\s+run:', wf)
    assert m and 'continue-on-error' not in m.group(1)


def test_sin_fecha_legible_no_se_indulta_nada():
    """Si no se puede saber cuándo se generó, el hallazgo cuenta como real:
    ante la duda, el gate aprieta."""
    assert 'tikr_desfasado = False' in FUENTE
    i = FUENTE.index('except Exception:', FUENTE.index('tikr_desfasado = False'))
    assert 'tikr_desfasado = False' in FUENTE[i:i + 120]


class TestElHelperDeDesfase:
    """La comparación necesita la HORA, no solo el día.

    La primera versión comparaba fechas, y con TIKR colaba porque el volcado
    era del 13 y el arreglo del 17. Con los commodities no: el CSV se generó
    a las 00:18 y la categoría PRECIO_EXIGENTE se commiteó a las 10:01 del
    MISMO día, así que `d < arreglado` daba False y el indulto no se aplicaba
    — el pipeline seguía cayéndose.
    """

    def test_el_mismo_dia_pero_antes_cuenta_como_desfasado(self):
        import coherence_check as cc
        assert cc._artefacto_anterior_al_arreglo(
            '2026-09-19T00:18:02+00:00', cc.CATEGORIA_COMMODITY_CARO) is True

    def test_despues_del_arreglo_no_se_indulta(self):
        import coherence_check as cc
        assert cc._artefacto_anterior_al_arreglo(
            '2026-09-19T23:00:00+00:00', cc.CATEGORIA_COMMODITY_CARO) is False

    def test_sin_fecha_no_se_indulta(self):
        """Ante la duda, el gate aprieta."""
        import coherence_check as cc
        assert cc._artefacto_anterior_al_arreglo(None, cc.CATEGORIA_COMMODITY_CARO) is False
        assert cc._artefacto_anterior_al_arreglo('vete a saber',
                                                 cc.CATEGORIA_COMMODITY_CARO) is False

    def test_una_fecha_sin_zona_se_toma_como_utc(self):
        import coherence_check as cc
        assert cc._artefacto_anterior_al_arreglo(
            '2026-09-19T00:18:02', cc.CATEGORIA_COMMODITY_CARO) is True

    def test_las_dos_constantes_llevan_hora(self):
        """Un `date` a secas vuelve a perder el caso del mismo día."""
        import coherence_check as cc
        for c in (cc.RESOLVEDOR_TIKR_ARREGLADO, cc.CATEGORIA_COMMODITY_CARO):
            assert hasattr(c, 'hour'), 'tiene que ser datetime, no date'
            assert c.tzinfo is not None, 'sin zona, la comparación es ambigua'
