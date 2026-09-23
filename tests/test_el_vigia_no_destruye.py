#!/usr/bin/env python3
"""Una comprobación que encuentra un problema tiene que AVISAR, no destruir.

`coherence_check.py` devolvía 1 al encontrar una contradicción, y ese 1
tumbaba el paso del workflow. Detrás venían el archivo del día, el informe de
salud y el commit de todos los escáneres: la única consecuencia de detectar
una incoherencia era tirar el trabajo del día. Y el hallazgo tampoco salía,
porque `coherence_check.json` no lo leía nadie.

Lo mismo con dos pasos más que podían llevarse por delante todo el pipeline
por motivos que no lo justifican:

  · el latido que solo anuncia que el pipeline ha arrancado
  · el `git fetch` de los patrones VCP, que son técnicos y no entran en VALUE
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import data_freshness_watchdog as w

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestElHallazgoLlegaAlAviso:

    def test_una_contradiccion_sale_por_el_watchdog(self, tmp_path, monkeypatch):
        (tmp_path / 'coherence_check.json').write_text(json.dumps({
            'total_problemas': 2,
            'detalle': {'corte de calidad (US)': ['XYZ con score 12 por debajo del corte 30']},
        }))
        monkeypatch.setattr(w, 'DOCS', tmp_path)
        problemas = w._contradicciones_publicadas()
        assert len(problemas) == 1
        assert problemas[0]['critical'] is True
        assert 'corte de calidad' in problemas[0]['detail']

    def test_sin_contradicciones_no_avisa(self, tmp_path, monkeypatch):
        (tmp_path / 'coherence_check.json').write_text(json.dumps({'total_problemas': 0}))
        monkeypatch.setattr(w, 'DOCS', tmp_path)
        assert w._contradicciones_publicadas() == []

    def test_sin_informe_no_se_inventa_nada(self, tmp_path, monkeypatch):
        monkeypatch.setattr(w, 'DOCS', tmp_path)
        assert w._contradicciones_publicadas() == []


class TestNingunPasoAccesorioTumbaElPipeline:
    """Los pasos que pueden matar el job tienen que ser los que producen el
    dato, no los que lo anuncian ni los que lo comprueban."""

    ACCESORIOS = (
        'Pipeline Heartbeat (API push)',
        'Coherence Check — ¿se contradice la app consigo misma?',
    )

    @staticmethod
    def _pasos():
        yaml = pytest.importorskip('yaml')
        with open(os.path.join(RAIZ, '.github/workflows/daily-analysis.yml')) as fh:
            wf = yaml.safe_load(fh)
        for job, jd in wf['jobs'].items():
            for s in jd.get('steps', []):
                yield job, s

    def test_los_accesorios_no_tumban_el_job(self):
        duros = [f'{job}: {s.get("name")}' for job, s in self._pasos()
                 if s.get('name') in self.ACCESORIOS
                 and s.get('continue-on-error') not in (True, 'true')]
        assert not duros, (
            f'Estos pasos pueden llevarse por delante el resto del pipeline: {duros}')

    def test_el_sync_de_vcp_tolera_un_corte_de_red(self):
        for job, s in self._pasos():
            if s.get('name') == 'Sync VCP outputs from parallel job':
                run = s.get('run') or ''
                assert 'git fetch origin main ||' in run or s.get('continue-on-error'), (
                    'un fetch sin red tumba core-scoring con 23 pasos por detrás')
                return
        pytest.skip('el paso de sync de VCP ya no existe')
