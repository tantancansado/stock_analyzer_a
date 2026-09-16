"""
`risk_reward_ratio` no es un factor: es el upside con otro nombre.

`super_score_integrator` lo calcula como `analyst_upside_pct / 8.0` (el stop
estándar del 8%). Medido sobre 1479 señales reales, corr(R:R, upside) = +1.0000
EXACTO. No aporta ni un dato nuevo.

El problema no es que exista —media app lo enseña— sino que se usaba como si
fuera independiente, y eso rompía dos reglas a la vez:

1. Doble conteo. Un umbral sobre R:R es un umbral sobre el upside, así que
   sumarlo al score después del `upside_bonus` premia dos veces el mismo hecho.
   `portfolio_tracker` y `conviction_filter` ya quitaron sus copias; quedaban
   el integrador (+2/-3 al value_score), `portfolio_builder` y `cerebro`.

2. Banda inline, y al revés. La banda dorada es [10, 25) y desde 30 hay HARD
   REJECT. Pero "R:R ≥3" es "upside ≥24%" y "R:R ≥4" es "upside ≥32%", así que
   cada umbral escrito en unidades de R:R apuntaba a la franja pegada a la
   trampa — o dentro de ella:
     · portfolio_builder exigía R:R ≥3,0 en CRISIS: en el régimen más peligroso
       solo dejaba pasar upside 24-30%, y nada más.
     · cerebro daba 18 puntos por el mismo hecho contado dos veces ("R:R ≥2" y
       "Upside ≥20%") y ponía "R:R <2" como CARENCIA a un pick con upside 14%,
       reprochándole estar en la mejor banda.
     · la app pintaba de verde R:R ≥3 en cuatro pantallas y titulaba
       "riesgo asimétrico excepcional" a R:R ≥4.

CLAUDE.md ya lo dice: las bandas de upside viven en `value_bands.py` y NUNCA se
escriben inline. Una banda escrita en unidades de R:R es una banda inline con
disfraz — más difícil de ver, y por eso sobrevivió en cinco sitios.
"""
import ast
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _sin_comentarios(ruta: Path) -> list[tuple[int, str]]:
    return [(n, l.split('#')[0]) for n, l in enumerate(ruta.read_text().splitlines(), 1)]


def test_el_integrador_no_suma_el_rr_al_score():
    src = (RAIZ / 'super_score_integrator.py').read_text()
    assert "df['risk_reward_ratio'] = (df['_upside'] / stop_loss_pct)" in src, \
        'la columna se sigue publicando: media app la enseña'
    assert "df['value_score'] += df['rr_bonus']" not in src, \
        'sumaba +2 a la banda [10,24), que el upside_bonus ya premia con +5'


def test_portfolio_builder_no_filtra_por_rr():
    """Exigir R:R ≥3 en CRISIS es exigir upside ≥24%: el embudo se estrechaba
    hacia la franja pegada a la trampa justo cuando el mercado va peor."""
    import portfolio_builder as pb
    for regimen, params in pb.REGIME_PARAMS.items():
        assert 'require_rr' not in params, f'{regimen} sigue con un umbral de R:R'


def test_portfolio_builder_premia_la_banda_declarada():
    import inspect
    import portfolio_builder as pb
    fuente = inspect.getsource(pb._rank_score)
    assert 'UPSIDE_MIN' in fuente and 'UPSIDE_GOLDEN_MAX' in fuente, \
        'la banda tiene que venir de value_bands, no de un número suelto'
    assert 'max(0, rr - 1)' not in fuente, \
        'premiaba el R:R de forma monótona hasta su tope en upside 32%'


def test_cerebro_cuenta_el_upside_una_sola_vez():
    src = (RAIZ / 'cerebro.py').read_text()
    assert 'sig("R:R ≥2"' not in src, '"R:R ≥2" es "upside ≥16%": el mismo hecho dos veces'
    assert 'sig("Upside ≥20%"' not in src
    assert 'UPSIDE_GOLDEN_MAX' in src, 'la banda sale de value_bands'


def test_ninguna_pantalla_pinta_en_verde_un_rr_alto():
    """R:R ≥3 es upside ≥24%: la banda que peor rinde. Pintarla de verde le dice
    al usuario justo lo contrario de lo que dice la calibración."""
    verde = re.compile(r"risk_reward_ratio\s*>=\s*([34])[^\n]*emerald")
    culpables = []
    for f in (RAIZ / 'frontend' / 'src').rglob('*.tsx'):
        if 'test' in f.parts:
            continue
        for n, linea in enumerate(f.read_text().splitlines(), 1):
            if verde.search(linea):
                culpables.append(f'{f.relative_to(RAIZ)}:{n}')
    assert not culpables, 'pintan en verde la banda de trampa: ' + ', '.join(culpables)


def test_ninguna_pantalla_titula_el_upside_de_trampa_como_virtud():
    """«riesgo asimétrico excepcional» a R:R ≥4 es upside ≥32%, dentro del HARD
    REJECT (0% de acierto en 55 señales reales)."""
    fuente = (RAIZ / 'frontend' / 'src' / 'pages' / 'Cerebro.tsx').read_text()
    # Fuera los comentarios: ahí sí se nombran, para explicar por qué se quitaron.
    codigo = re.sub(r'//[^\n]*|/\*.*?\*/', '', fuente, flags=re.S)
    assert 'riesgo asimétrico excepcional' not in codigo
    assert 'upside validado por analistas' not in codigo
