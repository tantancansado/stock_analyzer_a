"""
Identidades que TIENEN que cumplirse. Si no, hay un bug arriba.

Todos los fallos de datos encontrados el 16-sep-2026 tienen la misma forma:
**dos números correctos por separado que juntos mienten.** Ni uno dio error.

    el R:R de un rebote        contra un objetivo distinto del publicado
    la zona de entrada         por encima del precio al que cotiza
    `fcf_per_share`            en libras contra un precio en peniques
    `priceclose` de TIKR       que era el tipo de cambio, no un precio
    `avg_move_pct`             que era la sorpresa de BPA, no el movimiento
    `upside_triangulated_pct`  que era el número del analista
    250 millones de acciones   por defecto, para 54 empresas distintas

Una identidad es una relación que se cumple por definición: el upside ES
(objetivo − precio) / precio. No es una heurística ni un umbral calibrado — o
cuadra o hay un bug. Es la comprobación más barata que existe y la única que no
necesita saber nada del negocio.
"""
import pandas as pd

import identidades as idn


def _df(**kw):
    n = len(next(iter(kw.values())))
    base = {'ticker': [f'T{i}' for i in range(n)]}
    return pd.DataFrame({**base, **kw})


def test_lo_que_cuadra_no_genera_ruido():
    """Un aviso que salta todos los días deja de leerse, y entonces tampoco
    avisa cuando sí importa."""
    d = _df(current_price=[100.0, 50.0],
            target_price_analyst=[120.0, 55.0],
            analyst_upside_pct=[20.0, 10.0])
    assert idn.revisar(d, 'x.csv') == []


def test_caza_un_upside_que_no_sale_de_su_objetivo():
    d = _df(current_price=[100.0], target_price_analyst=[120.0], analyst_upside_pct=[45.0])
    r = idn.revisar(d, 'x.csv')
    assert len(r) == 1 and 'upside analista' in r[0].identidad and r[0].grave


def test_caza_el_factor_100_de_los_peniques():
    """SGE.L: precio 1007 peniques, FCF por acción 0,70 libras. Cada número
    correcto en su unidad; el par daba 0,07% contra un 7,00% publicado."""
    d = _df(current_price=[1007.0], fcf_per_share=[0.70], fcf_yield_pct=[7.0])
    r = idn.revisar(d, 'eu.csv')
    assert any('FCF yield' in i.identidad and i.grave for i in r)


def test_caza_el_recuento_de_acciones_de_una_sola_clase():
    """BRK-B: `sharesOutstanding` es solo la clase B y `marketCap` son las dos.
    Dividir un agregado de toda la empresa entre una clase infla el valor por
    acción un 52%."""
    d = _df(current_price=[520.35], fcf_per_share=[51.12], fcf_yield_pct=[6.46])
    r = idn.revisar(d, 'us.csv')
    assert any('FCF yield' in i.identidad and i.grave for i in r)
    # Y con el recuento implícito (mcap/precio) cuadra:
    ok = _df(current_price=[520.35], fcf_per_share=[33.61], fcf_yield_pct=[6.46])
    assert not any('FCF yield' in i.identidad for i in idn.revisar(ok, 'us.csv'))


def test_un_desfase_pequeño_no_es_grave():
    """Entre capturar el precio y calcular un derivado pasan segundos. Eso se
    informa aparte, no como incoherencia."""
    d = _df(current_price=[100.0], target_price_analyst=[120.0], analyst_upside_pct=[23.0])
    r = idn.revisar(d, 'x.csv')
    assert r and not r[0].grave


class TestFichaOperativa:
    """La forma exacta del fallo de los rebotes: `risk_reward` calculado contra
    un objetivo que no era el publicado. Cero de doce fichas cuadraban."""

    def test_caza_el_rr_que_no_sale_de_sus_numeros(self):
        # PGHN.SW tal cual se publicó: R:R 3,34 con una ficha que da 13,41.
        d = _df(current_price=[625.0], entry_price=[625.0], stop_loss=[601.72],
                exit_price=[937.18], risk_reward_ratio=[3.34])
        r = idn.revisar_operacion(d, 'eu.csv')
        assert any('R:R' in i.identidad and i.grave for i in r)

    def test_prefiere_la_columna_que_describe_la_ficha(self):
        """`rr_operativo` se calcula CON esta entrada, este stop y esta salida.
        `risk_reward_ratio` es `analyst_upside_pct / 8` y describe otra cosa."""
        d = _df(current_price=[625.0], entry_price=[625.0], stop_loss=[601.72],
                exit_price=[937.18], rr_operativo=[13.41], risk_reward_ratio=[3.34])
        assert not any('R:R' in i.identidad for i in idn.revisar_operacion(d, 'eu.csv'))

    def test_caza_un_stop_por_encima_de_la_entrada(self):
        d = _df(current_price=[100.0], entry_price=[100.0], stop_loss=[105.0], exit_price=[120.0])
        r = idn.revisar_operacion(d, 'x.csv')
        assert any('stop por encima' in i.identidad and i.grave for i in r)

    def test_caza_una_salida_por_debajo_de_la_entrada(self):
        d = _df(current_price=[177.27], entry_price=[177.27], stop_loss=[170.0], exit_price=[156.76])
        r = idn.revisar_operacion(d, 'x.csv')
        assert any('salida por debajo' in i.identidad and i.grave for i in r)


def test_el_pipeline_lo_ejecuta():
    """Un guardián que nadie llama no guarda nada."""
    from pathlib import Path
    src = (Path(__file__).parent.parent / 'coherence_check.py').read_text()
    assert 'identidades_rotas' in src
    assert 'import identidades' in src
