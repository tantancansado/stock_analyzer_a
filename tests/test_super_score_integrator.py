"""El reparto en estrategias del integrador. Antes este fichero probaba una copia
de la suma de ajustes de VALUE; la nota vive ahora en value_bands.nota_value y sus
pruebas en test_nota_value.py y test_value_score_hard_rejects.py."""
from unittest.mock import patch

import pytest

from super_score_integrator import SuperScoreIntegrator
from value_bands import NOTA_OBSERVAR, NOTA_PRIORIDAD


def _integrator():
    with patch.object(SuperScoreIntegrator, '__init__', lambda self: None):
        return SuperScoreIntegrator()


@pytest.mark.parametrize('nota,tier', [
    (NOTA_PRIORIDAD, 'PRIORIDAD'), (99.0, 'PRIORIDAD'), (NOTA_OBSERVAR, 'OBSERVAR'), (60.0, 'OBSERVAR'), (0.0, 'FUERA')])
def test_el_tier_es_el_grupo(nota, tier):
    assert _integrator()._get_tier_value(nota) == tier
