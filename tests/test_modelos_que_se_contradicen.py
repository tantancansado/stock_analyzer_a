"""
`upside_triangulated_pct` era, en un tercio de los casos, el número del analista.

La divergencia que ya existía solo miraba analista-CONTRA-modelos. El desacuerdo
de los modelos ENTRE ELLOS no lo miraba nadie, y es la mitad del universo:
medido el 16-sep-2026 sobre las 63 filas con DCF y P/E, la mediana de
|DCF − P/E| son 38,8 puntos de upside, y en el 32% uno dice BARATA y el otro CARA.

Ahí la «triangulación» es una ficción. Cuando el analista cae entre los dos
modelos —que es justo lo que pasa cuando se contradicen— la mediana de tres ES
el analista: ocurría en 14 de esas 20 filas.

    EQIX   DCF +54,3%   P/E −55,1%   «triangulado» 22,5 = el analista clavado
    AXP    DCF +50,0%   P/E −44,7%   ídem
    NUE    DCF −50,6%   P/E +47,6%   ídem

El corte no es un umbral inventado: es el signo. No existe un valor verdadero
entre «un 50% barata» y «un 45% cara» — son dos respuestas a la misma pregunta,
no dos medidas del mismo número. El código ya aplicaba exactamente ese
razonamiento al caso de CERO modelos válidos ("dejarlo en NaN en vez de devolver
el upside del analista disfrazado de mediana de tres fuentes"); dos modelos que
se contradicen son, para esto, lo mismo.
"""
import numpy as np
import pandas as pd
import pytest

from upside_triangulation import DISPERSION_ALTA_PTS, add_upside_triangulation


def _df(filas):
    return pd.DataFrame(filas)


def test_si_discrepan_en_el_signo_no_hay_triangulacion():
    r = add_upside_triangulation(_df([{
        'ticker': 'EQIX', 'analyst_upside_pct': 22.5,
        'target_price_dcf_upside_pct': 54.3, 'target_price_pe_upside_pct': -55.1,
    }]))
    assert r.loc[0, 'modelos_acuerdo'] == 'CONTRADICEN'
    assert pd.isna(r.loc[0, 'upside_triangulated_pct']), \
        'la mediana de dos respuestas contrarias no estima nada'


def test_aunque_no_haya_triangulacion_el_aviso_sigue_saliendo():
    """Escrito al revés el 16-sep («si los modelos no tienen opinión conjunta,
    no hay divergencia que medir») y corregido el 17.

    Con el criterio viejo, un pick cuyos modelos se contradecían perdía DOS
    cosas: el número consolidado Y el aviso de que el analista dice algo
    distinto que tus propios modelos. Doble silencio sobre el mismo problema,
    y en 24 de los 43 picks publicados ese día.

    No poder promediar dos respuestas contrarias no significa no tener nada que
    decir. AXP: el analista dice +15,9% y uno de tus modelos dice -44,7%. Eso
    es exactamente lo que hay que avisar, y se mide contra el MÁS PRUDENTE de
    los dos.
    """
    r = add_upside_triangulation(_df([{
        'ticker': 'AXP', 'analyst_upside_pct': 15.9,
        'target_price_dcf_upside_pct': 50.0, 'target_price_pe_upside_pct': -44.7,
    }]))
    assert pd.isna(r.loc[0, 'upside_triangulated_pct']), 'la triangulación sí se anula'
    assert r.loc[0, 'upside_divergence'] == 'ALTA', 'pero el aviso no'
    assert r.loc[0, 'upside_divergence_pts'] == pytest.approx(60.6, abs=0.1)


def test_coherentes_exige_magnitud_no_solo_signo():
    """«COHERENTES» con 44,7 puntos de diferencia es una etiqueta que miente.

    NYT el 17-sep: DCF -8,3% y P/E -53,0%. Los dos negativos, así que el
    criterio del signo los daba por coincidentes. Con el umbral en 45 se
    libraba por tres décimas.
    """
    r = add_upside_triangulation(_df([{
        'ticker': 'NYT', 'analyst_upside_pct': 12.0,
        'target_price_dcf_upside_pct': -8.3, 'target_price_pe_upside_pct': -53.0,
    }]))
    assert r.loc[0, 'modelos_acuerdo'] == 'DISPERSOS'


def test_si_coinciden_la_triangulacion_se_mantiene():
    r = add_upside_triangulation(_df([{
        'ticker': 'AAA', 'analyst_upside_pct': 15.0,
        'target_price_dcf_upside_pct': 18.0, 'target_price_pe_upside_pct': 12.0,
    }]))
    assert r.loc[0, 'modelos_acuerdo'] == 'COHERENTES'
    assert r.loc[0, 'upside_triangulated_pct'] == 15.0


def test_mismo_signo_pero_muy_separados_es_un_aviso_no_una_anulacion():
    """Es un aviso al usuario, no un filtro: la mediana sigue estimando algo
    cuando los dos apuntan al mismo lado. El umbral bajó de 45 a 20 puntos el
    17-sep — ver `test_coherentes_exige_magnitud_no_solo_signo`."""
    r = add_upside_triangulation(_df([{
        'ticker': 'BBB', 'analyst_upside_pct': 20.0,
        'target_price_dcf_upside_pct': 5.0,
        'target_price_pe_upside_pct': 5.0 + DISPERSION_ALTA_PTS + 10,
    }]))
    assert r.loc[0, 'modelos_acuerdo'] == 'DISPERSOS'
    assert not pd.isna(r.loc[0, 'upside_triangulated_pct'])


def test_se_publica_cuanto_se_separan():
    r = add_upside_triangulation(_df([{
        'ticker': 'CCC', 'analyst_upside_pct': 10.0,
        'target_price_dcf_upside_pct': 30.0, 'target_price_pe_upside_pct': -10.0,
    }]))
    assert r.loc[0, 'modelos_dispersion_pts'] == 40.0


def test_sobre_el_universo_real_los_que_pierden_la_triangulacion_la_tenian_falsa():
    from pathlib import Path
    import pytest
    f = Path(__file__).parent.parent / 'docs' / 'value_opportunities.csv'
    if not f.exists():
        pytest.skip('sin CSV VALUE')
    d = pd.read_csv(f)
    if d.empty or 'target_price_dcf_upside_pct' not in d.columns:
        pytest.skip('sin modelos propios en el CSV')
    r = add_upside_triangulation(d.drop(columns=[c for c in (
        'upside_divergence', 'upside_triangulated_pct', 'upside_divergence_pts') if c in d.columns]).copy())
    an = pd.to_numeric(d['analyst_upside_pct'], errors='coerce')
    antes = pd.to_numeric(d.get('upside_triangulated_pct'), errors='coerce')
    pierden = antes.notna() & r['upside_triangulated_pct'].isna()
    if not pierden.any():
        pytest.skip('hoy no hay modelos que se contradigan')
    era_el_analista = ((antes - an).abs() < 0.05) & pierden
    assert era_el_analista.sum() >= pierden.sum() * 0.5, \
        'si se anula una triangulación, la mayoría de las veces debe ser porque era el analista disfrazado'
