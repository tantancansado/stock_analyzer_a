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
    assert "_commit('tikr_scraper.py')" in FUENTE
    assert 'tikr_desfasado' in FUENTE


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


def test_sin_git_no_se_indulta_nada():
    """Si no se puede saber la fecha, el hallazgo cuenta como real: ante la
    duda, el gate aprieta."""
    assert 'tikr_desfasado = False' in FUENTE
    i = FUENTE.index('except Exception:', FUENTE.index('tikr_desfasado = False'))
    assert 'tikr_desfasado = False' in FUENTE[i:i + 120]
