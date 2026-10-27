"""El repo es público: nada de la cartera real con cantidades puede ir a docs/."""
import json

import earnings_thesis_generator as etg
import leaps_monitor as lm


def test_el_estado_de_tus_leaps_no_va_a_docs():
    assert 'docs' not in str(lm.STATUS_OUT)


def test_el_registro_de_avisos_no_lleva_el_contrato_en_claro():
    h = lm._huella('UBER-65-2027-12-17')
    assert h.startswith('pos-') and 'UBER' not in h and '65' not in h


def test_las_tesis_publicas_van_sin_cantidades():
    out = etg._sin_datos_de_cartera({'theses': {'MCD': {'thesis_summary': 'x', 'shares': 10,
                                                        'avg_price': 280.0, 'unrealized_pct': 3.1}}})
    assert set(out['theses']['MCD']) == {'thesis_summary'}


def test_gitignore_cubre_los_ficheros_personales():
    from pathlib import Path
    gi = (Path(__file__).resolve().parents[1] / '.gitignore').read_text()
    for f in ('privado/', 'docs/leaps_positions_status.json', 'docs/portfolio_watch.json'):
        assert f in gi
