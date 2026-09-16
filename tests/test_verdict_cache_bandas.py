"""
La caché de veredictos acertaba el 16%, no el 86% que decía su diseño.

El 86% contaba TICKERS que se repetían de un día a otro. Lo que decide es que se
repita la HUELLA, y casi nunca se repetía. Medido sobre los 32 días de
`docs/history` (1.488 pares ticker-día): **16%**.

El culpable, campo a campo:

    analyst_upside_pct   cambiaba de banda el 75% de los días
    pct_from_52w_high                       el 69%
    fcf_yield_pct                           el 39%
    current_price                           el 21%
    roe / margen / deuda                  el 0-1%   ← como estaba previsto

El fallo: aplicar una banda RELATIVA del 5% a magnitudes que ya son porcentajes.
Un 5% relativo sobre un precio de 267 son 13 puntos, que el precio casi nunca
cruza. Sobre un upside de 16,7 son 0,8 puntos, que los cruza cualquier día.
Cuanto más pequeño el número, más sensible la banda — al revés de lo que hace
falta.

Y no era solo dinero. La caché existe sobre todo para que el gate fail-closed no
vacíe la página cuando falla la API o se acaba el saldo: con un 16% de acierto,
el 84% de los picks no tenía veredicto al que caer. Por ahí se cayó MCO —score
83,1, el más alto de la lista— que había pasado el gate el día anterior.

Con bandas ABSOLUTAS para los porcentajes el acierto sube al 55%.
"""
import verdict_cache as vc


def _fila(**kw):
    base = dict(ticker='MCO', sector='Financial Services', roe=26.3, profit_margin=34.6,
                debt_to_equity=0.28, rev_growth=15.1, fcf_yield_pct=3.19,
                current_price=466.98, target_price_analyst=560.0,
                analyst_upside_pct=19.9, pct_from_52w_high=-27.1, analyst_count=21)
    return {**base, **kw}


def test_el_goteo_de_los_porcentajes_ya_no_invalida_la_huella():
    """Eran el 75% / 69% / 39% de las invalidaciones. Con el precio quieto para
    aislarlo: el precio tiene su propia banda relativa y cruzarla de vez en
    cuando es correcto (era el 21%, y ahí sí toca volver a mirar)."""
    hoy = vc.huella(_fila())
    manana = vc.huella(_fila(analyst_upside_pct=19.1, pct_from_52w_high=-26.4,
                             fcf_yield_pct=3.24, roe=27.1, profit_margin=34.9,
                             rev_growth=16.8))
    assert hoy == manana, 'un goteo diario normal no cambia lo que vería el auditor'


def test_un_cambio_de_verdad_si_la_invalida():
    """Publicar resultados sí mueve los fundamentales, y ahí toca volver a mirar."""
    hoy = vc.huella(_fila())
    tras_resultados = vc.huella(_fila(roe=41.0, profit_margin=44.0, rev_growth=31.0))
    assert hoy != tras_resultados


class TestBandasAbsolutas:
    """Los porcentajes se agrupan en sus propias unidades, no en relativo."""

    def test_un_roe_de_26_y_otro_de_27_son_el_mismo_caso(self):
        assert vc._banda_absoluta(26.3, 5.0) == vc._banda_absoluta(27.1, 5.0)

    def test_pero_uno_de_26_y_otro_de_41_no(self):
        assert vc._banda_absoluta(26.3, 5.0) != vc._banda_absoluta(41.0, 5.0)

    def test_los_cortes_del_upside_caen_en_las_fronteras_que_importan(self):
        """10, 25 y 30 son las fronteras de `value_bands`. Con paso 5, un pick
        no puede salir de la banda dorada sin invalidar su veredicto."""
        from value_bands import UPSIDE_GOLDEN_MAX, UPSIDE_HARD_REJECT, UPSIDE_MIN
        paso = vc._CAMPOS_EN_BANDAS_ABSOLUTAS['analyst_upside_pct']
        for frontera in (UPSIDE_MIN, UPSIDE_GOLDEN_MAX, UPSIDE_HARD_REJECT):
            assert frontera % paso == 0, f'{frontera} no cae en un corte de banda'
            assert vc._banda_absoluta(frontera - 0.1, paso) != vc._banda_absoluta(frontera, paso)


def test_sin_dato_no_se_agrupa_con_nada():
    assert vc._banda_absoluta(None, 5.0) is None
    assert vc._banda_absoluta(float('nan'), 5.0) is None


def test_los_precios_siguen_en_banda_relativa():
    """Un precio no tiene escala natural —hay acciones a 17 y a 2.800— así que
    ahí lo que importa es el movimiento proporcional, no los puntos.

    Se mide el ANCHO de la banda, de borde a borde. La distancia desde un valor
    cualquiera hasta el borde siguiente no sirve: depende de dónde caiga ese
    valor dentro de su banda, no de lo ancha que sea.
    """
    assert 'current_price' in vc._CAMPOS_EN_BANDAS
    assert 'current_price' not in vc._CAMPOS_EN_BANDAS_ABSOLUTAS

    def ancho_de_banda(v: float) -> float:
        b, x, paso = vc._banda(v), v, 1.00002
        while vc._banda(x) == b:            # hasta el borde de arriba
            x *= paso
        arriba, y = x, v
        while vc._banda(y) == b:            # y hasta el de abajo
            y /= paso
        return arriba / (y * paso) - 1

    anchos = [ancho_de_banda(v) for v in (17.0, 500.0, 2800.0)]
    assert max(anchos) - min(anchos) < 0.01, f'la banda no es proporcional: {anchos}'
    assert all(0.045 < a < 0.055 for a in anchos), f'deberían ser ~5%: {anchos}'


def test_el_gate_distingue_rechazado_de_no_evaluado():
    """«Rechazado porque el dato no cuadra» es el gate funcionando; «no se pudo
    mirar» es una avería. Los dos dejaban al pick fuera con la misma cara."""
    from pathlib import Path
    src = (Path(__file__).parent.parent / 'ai_quality_filter.py').read_text()
    assert 'no_evaluados' in src and 'rechazados' in src
    assert 'NO EVALUADOS' in src
