"""Un ENTRY que se apoya en una sola fuente sin decirlo.

`entry_verdict_agent` bloquea la entrada cuando los modelos propios se
contradicen (DCF barata, P/E cara) o se dispersan. La regla es correcta y
está bien razonada. Lo que no contemplaba es que NO HAYA modelos: entonces
`modelos_acuerdo` viene vacío, la cadena if/elif se cae en silencio y el
ticker pasa como si los dos coincidieran.

El 19-sep-2026 GOOG era el ÚNICO ENTRY de 81 veredictos, y lo era por esto.
No tenía ni DCF ni P/E porque sus clases A+B+C rompían el cuadre de acciones
y se omitían los dos modelos; su entrada se apoyaba solo en el consenso de
analistas y nada lo decía. Es el mismo patrón de todo el día: «no lo sé»
pasando por «no hay problema», esta vez en el veredicto que dice *entra hoy*.

No bloquea: la falta de un modelo no es una señal en contra, y bloquear por
un hueco dejaría fuera picks buenos. Pero consta en las razones, porque un
ENTRY respaldado por una fuente no es el mismo ENTRY que uno respaldado por
tres.
"""
from pathlib import Path

from conftest import bloque_de_codigo

FUENTE = (Path(__file__).resolve().parent.parent / 'entry_verdict_agent.py').read_text()
BLOQUE = bloque_de_codigo(FUENTE, "if acuerdo == 'CONTRADICEN':",
                          '# ── Technical warnings')


def test_el_hueco_tiene_su_propia_rama():
    assert 'elif not acuerdo:' in BLOQUE, \
        'sin modelos, la cadena if/elif se cae y el ticker pasa en silencio'


def test_no_bloquea_la_entrada():
    """Un hueco no es una señal en contra."""
    i = BLOQUE.index('elif not acuerdo:')
    rama = BLOQUE[i:]
    assert 'reasons.append' in rama
    assert 'blockers.append' not in rama, \
        'la falta de un modelo no puede vetar una entrada'


def test_dice_cuál_falta():
    assert 'DCF' in BLOQUE and 'P/E propio' in BLOQUE
    assert 'solo en el consenso de analistas' in BLOQUE


def test_las_reglas_que_ya_estaban_siguen_bloqueando():
    """Contradicción y dispersión sí son señales en contra, y no se tocan."""
    assert "if acuerdo == 'CONTRADICEN':" in BLOQUE
    assert 'tus modelos se contradicen' in BLOQUE
    assert "elif acuerdo == 'DISPERSOS'" in BLOQUE
    i = BLOQUE.index("if acuerdo == 'CONTRADICEN':")
    j = BLOQUE.index('elif not acuerdo:')
    assert BLOQUE[i:j].count('blockers.append') == 2, \
        'las dos reglas de desacuerdo siguen vetando'
