"""Un año de relleno de TIKR no puede llegar a la valoración."""
from tikr_scraper import es_anio_de_relleno, limpiar_forward

RELLENO = {'revenue': 1.1, 'ebitda': 1.1, 'ebit': 1.1, 'net_income_norm': 1.1,
           'eps_norm': 1.11, 'eps_gaap': 1.11, 'n_analysts': 1.11}
BUENO = {'revenue': 22099.0, 'ebitda': 11189.0, 'ebit': 8843.0, 'net_income_norm': 6181.5,
         'eps_norm': 11.09, 'eps_gaap': 10.99, 'n_analysts': 2.0}


def test_el_caso_real_del_25_oct():
    assert es_anio_de_relleno(RELLENO)
    assert not es_anio_de_relleno(BUENO)


def test_analistas_con_decimales_delata_el_relleno():
    assert es_anio_de_relleno({**BUENO, 'n_analysts': 2.5})


def test_limpiar_quita_solo_el_ano_roto():
    f, q = limpiar_forward({'2029': BUENO, '2030': RELLENO})
    assert list(f) == ['2029'] and q == ['2030']


def test_la_valoracion_no_ve_el_relleno(monkeypatch, tmp_path):
    import json
    import owner_earnings as oe
    p = tmp_path / 't.json'
    p.write_text(json.dumps({'data': {'X': {'analyst_estimates': {'forward': {'2029': BUENO, '2030': RELLENO}}}}}))
    monkeypatch.setattr(oe, 'TIKR_PATH', p)
    monkeypatch.setattr(oe, '_cache', {})
    assert list(oe._load_tikr()['X']['analyst_estimates']['forward']) == ['2029']


def test_ingresos_que_se_hunden_entre_anos_tambien_es_relleno():
    f, q = limpiar_forward({'2029': BUENO, '2030': {'revenue': 1.1, 'ebit': 1.1}})
    assert q == ['2030']


def test_se_importa_sin_pycognito():
    """owner_earnings usa limpiar_forward en el pipeline diario, que no instala
    pycognito (solo lo instala el workflow de TIKR). Con el import arriba del
    módulo, la primera llamada a _load_tikr reventaba."""
    import subprocess, sys
    codigo = ("import sys; sys.modules['pycognito'] = None; "
              "sys.modules['pycognito.aws_srp'] = None; "
              "import owner_earnings; owner_earnings._load_tikr()")
    r = subprocess.run([sys.executable, '-c', codigo], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-500:]
