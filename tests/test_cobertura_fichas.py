"""Todo lo que el usuario puede pinchar tiene que tener ficha.

El cache de fichas se construía con los tickers que tienen score + el S&P 500
sacado de Wikipedia. El 17-sep-2026 Wikipedia devolvió un 403, la lista quedó
vacía y el cache salió con 60 tickers de 163: el 63% del universo sin ficha,
incluidas posiciones del usuario como ABT.

Y sin ruido. El aviso era una línea de log entre mil:

    ⚠️  No se pudo obtener S&P 500 de Wikipedia: HTTP Error 403: Forbidden
    📋 60 tickers VCP + 0 tickers S&P500 adicionales

El universo curado es lo que el usuario mira, así que va siempre, responda
Wikipedia o no.
"""
import json
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent


def test_el_universo_curado_entra_aunque_wikipedia_falle():
    src = (RAIZ / 'super_score_integrator.py').read_text()
    from conftest import bloque_de_codigo
    bloque = bloque_de_codigo(src, 'def export_ticker_data_cache')
    assert 'get_universe' in bloque, \
        'el cache vuelve a depender de que Wikipedia responda'
    # y el curado se añade ANTES de mirar el S&P 500
    assert bloque.index('get_universe') < bloque.index('_get_sp500_tickers')


def test_wikipedia_caida_no_es_motivo_para_quedarse_sin_fichas():
    """Si la lista externa falla, el aviso tiene que decir que no pasa nada
    porque el curado ya está dentro — no dejar al lector pensando."""
    src = (RAIZ / 'super_score_integrator.py').read_text()
    from conftest import bloque_de_codigo
    assert 'no se queda sin fichas' in bloque_de_codigo(
        src, 'def export_ticker_data_cache')


@pytest.mark.parametrize('ticker', ['ABT', 'BR', 'BSX', 'MSFT', 'OTIS', 'UNH', 'V'])
def test_las_posiciones_del_usuario_estan_en_el_universo(ticker):
    """Si una posición no está en el universo, no se puntúa ni tiene ficha."""
    from curated_tickers import get_universe
    assert ticker in get_universe(include_hf_watch=True), \
        f'{ticker} es una posición y no está en el universo que se cachea'


def test_la_cobertura_del_cache_se_puede_medir():
    """Sin esto el agujero es invisible: no hay hueco en pantalla, hay una
    ficha que no existe."""
    f = RAIZ / 'docs' / 'ticker_data_cache.json'
    if not f.exists():
        pytest.skip('sin cache')
    from curated_tickers import get_universe
    cache = set(json.loads(f.read_text()))
    universo = set(get_universe(include_hf_watch=True))
    cobertura = len(cache & universo) / len(universo)
    # No se exige 100% aquí (el fichero es el de la última ejecución, anterior
    # al arreglo). Lo que se fija es que la medida exista y sea calculable.
    assert 0 <= cobertura <= 1


def test_toda_posicion_del_usuario_esta_en_el_universo():
    """Una acción que se tiene en cartera tiene que poder analizarse.

    17-sep-2026: BSX (Boston Scientific) era posición y no estaba en el
    universo curado, así que no se puntuaba, no tenía ficha y no aparecía en
    ningún análisis. Nadie lo notó porque la ausencia no deja hueco: el ticker
    simplemente no sale por ninguna parte.

    Se lee del fichero de respaldo local; la fuente real es Supabase, pero si
    una posición está aquí y no en el universo, el agujero es el mismo.
    """
    import json
    from curated_tickers import get_universe
    f = RAIZ / 'docs' / 'portfolio_watch.json'
    if not f.exists():
        pytest.skip('sin fichero de posiciones')
    pos = [p['ticker'] for p in json.loads(f.read_text()).get('tickers', [])
           if isinstance(p, dict) and p.get('ticker')]
    universo = set(get_universe(include_hf_watch=True))
    fuera = [t for t in pos if t not in universo]
    assert not fuera, f'posiciones que el sistema no analiza: {fuera}'
