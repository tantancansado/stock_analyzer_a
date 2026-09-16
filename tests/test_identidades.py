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


class TestObjetivoPorValoracion:
    """El «precio de salida» de la ficha no era una valoración.

    `_calculate_exit_price` lo componía así:

        40%  «un 10% por encima del máximo de 52 semanas»
        40%  «suponer que toda empresa merece un PER de 25»
        20%  `current_price * 1.30`  ← un placeholder fijo; el comentario del
                                        propio código decía "Placeholder"
        y un suelo de `max(exit, precio × 1.20)`, "asegurar al menos un 20%"

    Medido el 16-sep-2026 sobre las 34 filas del VALUE filtrado: quedaba POR
    ENCIMA del consenso de analistas en 33 de 34, desvío mediano +10,5%, hasta
    +35% en INTU. Y los objetivos de verdad —consenso, DCF, modelo P/E— estaban
    ya calculados en la fila de al lado, sin mirarse.

    El suelo del 20% era además lo contrario de lo que el usuario hace: vende a
    precio objetivo POR VALORACIÓN, nunca a un porcentaje fijo. Con ese suelo
    ningún pick podía tener un objetivo por debajo de +20% ni estando caro.
    """

    def _calc(self):
        from entry_exit_calculator import EntryExitCalculator
        return EntryExitCalculator()

    def test_el_objetivo_es_el_consenso_no_un_invento(self):
        c = self._calc()
        v = c._calculate_exit_price(100.0, None, {}, {'target_price_analyst': 118.0})
        assert v == 118.0

    def test_sin_consenso_no_hay_objetivo(self):
        """Antes devolvía `precio × 1.20` pasara lo que pasara."""
        c = self._calc()
        assert c._calculate_exit_price(100.0, None, {}, {}) is None
        assert c._calculate_exit_price(100.0, None, {}, {'target_price_analyst': 0}) is None

    def test_si_los_modelos_propios_desmienten_al_analista_no_hay_objetivo(self):
        """Misma política que `upside_divergence` en el integrator: si DCF y P/E
        contradicen al sell-side, su objetivo no es argumento."""
        c = self._calc()
        v = c._calculate_exit_price(100.0, None, {}, {
            'target_price_analyst': 118.0,     # +18%
            'target_price_dcf': 60.0,          # -40%
            'target_price_pe': 55.0,           # -45%
        })
        assert v is None

    def test_pero_si_coinciden_en_direccion_el_objetivo_se_mantiene(self):
        c = self._calc()
        v = c._calculate_exit_price(100.0, None, {}, {
            'target_price_analyst': 118.0, 'target_price_dcf': 130.0, 'target_price_pe': 112.0,
        })
        assert v == 118.0

    def test_no_se_promedian_respuestas_contrarias(self):
        """Promediar un +8% del consenso con un −59% de los modelos daba 224,90
        sobre un precio de 301 (VRSN). Eso no es una valoración: es la media de
        un sí y un no — el mismo error que `upside_triangulated_pct`."""
        import inspect

        import ast

        from entry_exit_calculator import EntryExitCalculator
        fuente = inspect.getsource(EntryExitCalculator._calculate_exit_price)
        # Fuera el docstring: ahí SÍ se nombra el placeholder, para explicar
        # por qué se quitó.
        import textwrap
        fn = ast.parse(textwrap.dedent(fuente)).body[0]
        if (fn.body and isinstance(fn.body[0], ast.Expr)
                and isinstance(fn.body[0].value, ast.Constant)):
            fn.body = fn.body[1:]
        codigo = ast.unparse(fn)
        assert 'current_price * 1.3' not in codigo, 'volvió el placeholder'
        fuente = codigo
        assert 'min_target' not in fuente, 'volvió el suelo del 20%'
        assert 'sector_avg_pe' not in fuente, 'volvió el «PER 25 para todos»'

    def test_sin_objetivo_tampoco_hay_rr(self):
        """Una operación sin objetivo no tiene riesgo/recompensa que medir."""
        import inspect

        from entry_exit_calculator import EntryExitCalculator
        fuente = inspect.getsource(EntryExitCalculator.calculate_entry_exit)
        assert 'risk_reward = (reward / risk) if (reward is not None' in fuente
