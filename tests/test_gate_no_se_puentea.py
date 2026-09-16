"""
El gate de Claude (`ai_quality_filter`) es fail-CLOSED: un pick VALUE solo se
publica si Claude lo ha verificado. Escribe `value_opportunities_filtered.csv`;
el `value_opportunities.csv` de al lado es el universo entero, sin verificar.

El 16-sep-2026 llegó a Telegram Nucor (NUE, score 35,2) presentada como
comprable. No es que el gate la rechazara: nunca llegó a evaluarla — no está en
`ai_verdicts_cache.json`. Llegó porque tres emisores leían el CSV sin filtrar y
rodeaban el gate por completo:

    daily_briefing.gather_facts()          → el mensaje diario
    telegram_legendary_alerts             → alertas de picks
    new_value_alerts (fallback)           → «value nuevo»

Un gate fail-closed con una puerta lateral abierta no es fail-closed. Y el fallo
era silencioso: el mensaje salía perfectamente formado, solo que con un pick que
nadie había verificado.
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Emisores hacia Telegram que presentan picks VALUE al usuario.
EMISORES = ['daily_briefing.py', 'telegram_legendary_alerts.py', 'new_value_alerts.py']

# `value_opportunities.csv` (o el europeo) SIN el sufijo `_filtered`.
SIN_FILTRAR = re.compile(r"""['"][^'"]*(?<!_filtered)value_opportunities\.csv['"]""")


def test_ningun_emisor_de_telegram_lee_el_csv_sin_filtrar():
    culpables = []
    for nombre in EMISORES:
        for n, linea in enumerate(( RAIZ / nombre).read_text().splitlines(), 1):
            código = linea.split('#')[0]          # los comentarios sí pueden nombrarlo
            if 'HISTORY' in código:
                # El histórico sin filtrar sí vale como BASE de comparación
                # («¿estaba ayer?»): es un superconjunto del filtrado, así que
                # solo puede silenciar un aviso, nunca inventarlo. Lo que se
                # prohíbe es leerlo como fuente de lo que se anuncia.
                continue
            if SIN_FILTRAR.search(código):
                culpables.append(f'{nombre}:{n}: {linea.strip()}')
    assert not culpables, (
        'Estos emisores leen el CSV VALUE sin filtrar y se saltan el gate de Claude:\n  '
        + '\n  '.join(culpables))


def test_sin_historico_no_se_anuncia_nada_como_nuevo():
    """«Nuevo» se define contra una base. Sin base, no se afirma.

    El código imprimía "sending full top list instead" y mandaba la lista
    entera como si acabara de aparecer. Los datos eran ciertos; la afirmación,
    no. El usuario prefiere 0 avisos antes que un aviso falso.
    """
    import ast
    fuente = (RAIZ / 'new_value_alerts.py').read_text()
    assert 'sending full top list' not in fuente
    árbol = ast.parse(fuente)
    fn = next(n for n in ast.walk(árbol)
              if isinstance(n, ast.FunctionDef) and n.name == 'run_new_value_alerts')
    guarda = next(n for n in ast.walk(fn)
                  if isinstance(n, ast.If) and ast.unparse(n.test) == 'not yesterday_tickers')
    assert any(isinstance(x, ast.Return) for x in guarda.body), \
        'sin histórico con el que comparar, run_new_value_alerts debe salir sin avisar'

