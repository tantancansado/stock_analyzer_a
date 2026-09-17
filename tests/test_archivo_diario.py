"""Lo que decide qué se publica tiene que quedar archivado.

El snapshot diario guardaba `value_opportunities.csv` (la lista CRUDA) pero no
la FILTRADA, que es la que sale en la app. Así que el efecto del gate de
Claude —la pieza fail-closed del sistema, la que decide qué pick llega al
usuario— no se podía auditar a posteriori: no había forma de saber a quién
echó ningún día pasado.

El 17-sep-2026, para averiguar por qué faltaba Broadridge, hubo que bajarse el
log de GitHub Actions. Con el filtrado archivado y `picks_excluidos.json`, eso
se responde con los ficheros del propio repo.
"""
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
YML = (RAIZ / '.github' / 'workflows' / 'daily-analysis.yml').read_text()


def _archivados() -> set[str]:
    i = YML.index('Archive daily CSV snapshot')
    bloque = YML[i:YML.index('\n      - name:', i + 10)]
    return set(re.findall(r'docs/([A-Za-z0-9_./-]+\.(?:csv|json))', bloque))


@pytest.mark.parametrize('fichero', [
    'value_opportunities.csv',              # la lista cruda
    'value_opportunities_filtered.csv',     # la que ve el usuario
    'leaps_opportunities.json',             # una de las tres que el usuario sigue
    'picks_excluidos.json',                 # a quién se echó y por qué
    'mean_reversion_opportunities.csv',
    'bounce_setups_broad.json',
])
def test_se_archiva_lo_que_decide(fichero):
    assert fichero in _archivados(), (
        f'{fichero} no se archiva: su histórico no se podrá auditar')


def test_la_lista_filtrada_y_la_cruda_se_archivan_juntas():
    """Con solo una de las dos no se puede medir qué hizo el gate."""
    a = _archivados()
    assert {'value_opportunities.csv', 'value_opportunities_filtered.csv'} <= a
