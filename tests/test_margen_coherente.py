"""El mismo campo del prompt, dos márgenes distintos según por dónde entre.

`ai_quality_filter` construye el diccionario que ve el modelo por dos
caminos, y cada uno rellenaba `profit_margin` con una cosa:

    extract_fundamentals()   profit_margin_pct      margen NETO
    filter_micro_cap()       operating_margin_pct   margen OPERATIVO

Y el prompt lo enseñaba en los dos casos como «Margen neto». El operativo es
siempre el mayor —en MCD son 46,5% contra un 31% neto—, así que según por
dónde entrara el ticker el modelo juzgaba un margen inflado creyendo que era
el neto.

No es lo mismo que un dato que falta: aquí el número está, es correcto, y la
etiqueta miente sobre qué mide. El arreglo es preferir el neto y, cuando solo
haya operativo, decirlo en el propio prompt en vez de callarlo.
"""
import re
from pathlib import Path

FUENTE = (Path(__file__).resolve().parent.parent / 'ai_quality_filter.py').read_text()


def test_se_prefiere_el_margen_neto():
    assert "'profit_margin': _f('profit_margin_pct') if _f('profit_margin_pct') is not None" \
        in FUENTE
    assert "'profit_margin': _f('operating_margin_pct')," not in FUENTE, \
        'volvió a rellenarse con el operativo a secas'


def test_se_marca_cuando_lo_que_va_es_el_operativo():
    assert "'profit_margin_es_operativo'" in FUENTE


def test_el_prompt_dice_cual_esta_viendo():
    """Tres sitios lo enseñan; los tres tienen que decir de cuál hablan."""
    etiquetas = re.findall(r"Margin \(\{'operating' if", FUENTE)
    assert len(etiquetas) >= 2
    assert "Margen neto: {_nd(ticker_data.get('profit_margin')" not in FUENTE, \
        'la etiqueta fija «Margen neto» puede estar mintiendo'


def test_el_camino_bueno_sigue_usando_el_neto():
    """`extract_fundamentals` ya lo hacía bien: no se toca."""
    i = FUENTE.index('def extract_fundamentals')
    bloque = FUENTE[i:FUENTE.index('def _avisar_de_los_que_desaparecen')]
    assert "profit_margin = ed.get('profit_margin_pct')" in bloque


def test_el_umbral_que_lo_consume_sigue_igual():
    """Cambiar el dato y el corte a la vez deja sin saber qué produjo el
    cambio. El corte de margen negativo se queda donde estaba."""
    assert 'profit_margin < 0' in FUENTE
