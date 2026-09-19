"""Lo que acaba de aparecer en la lista no llegaba a ningún sitio.

El paso «New VALUE Picks Alert» del workflow está silenciado delegando en el
briefing —«silenciado → daily_briefing»—, y eso es correcto: un solo mensaje
al día en vez de cinco. Pero el briefing nunca recogió esa parte. Mandaba la
lista entera cada mañana sin decir cuál acaba de entrar, que es justo lo que
se le pedía a esa alerta. La funcionalidad se perdió en la consolidación.

El 19-sep-2026 habían entrado seis (ADSK, GGG, MKC, RMD, V, VRSN) y se había
caído uno (QSR), y nada de eso salía por ninguna parte.

La trampa al medirlo, que casi me cuela un aviso falso: comparar la lista de
hoy SIN filtrar por score contra una base YA filtrada da 46 «nuevos» donde
hay 6. Las dos listas tienen que cargarse con la misma vara.
"""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BRIEF = (RAIZ / 'daily_briefing.py').read_text()
ALERTS = (RAIZ / 'new_value_alerts.py').read_text()


class TestLaBase:
    def test_la_deteccion_es_reutilizable(self):
        assert 'def base_de_comparacion()' in ALERTS

    def test_sin_base_no_se_inventan_nuevos(self):
        """None ≠ lista vacía: sin con qué comparar, «nuevo» no significa nada."""
        from conftest import bloque_de_codigo
        b = bloque_de_codigo(ALERTS, 'def base_de_comparacion()')
        assert 'return None' in b

    def test_un_dia_roto_no_sirve_de_base(self):
        """Si ayer el pipeline no terminó, sus 7 picks convierten en «nuevos»
        a los que ya estaban."""
        from conftest import bloque_de_codigo
        b = bloque_de_codigo(ALERTS, 'def base_de_comparacion()')
        assert 'len(hoy) * 0.5' in b
        assert 'no terminó' in b

    def test_las_dos_listas_usan_el_mismo_filtro(self):
        """El error que casi se cuela: 7 filtrados contra 52 sin filtrar."""
        from conftest import bloque_de_codigo
        b = bloque_de_codigo(ALERTS, 'def base_de_comparacion()')
        assert b.count('_load_value_csv') >= 2, 'ambas por la misma función'
        assert 'misma vara' in b or 'MISMO filtro' in b


class TestElBriefing:
    def test_publica_los_nuevos_y_los_que_se_van(self):
        assert "'picks_nuevos'" in BRIEF
        assert "'picks_que_se_van'" in BRIEF

    def test_un_fallo_al_comparar_no_tumba_el_briefing(self):
        """El briefing es el mensaje del día: no puede caerse por un extra."""
        from conftest import bloque_de_codigo
        b = bloque_de_codigo(BRIEF, 'nuevos, se_van = [], []', 'return {')
        assert 'except Exception' in b
        assert 'nuevos, se_van = [], []' in b

    def test_el_prompt_lo_pide_y_dice_cuando_callarse(self):
        assert 'picks_nuevos' in BRIEF and 'picks_que_se_van' in BRIEF
        assert 'no menciones el tema' in BRIEF, \
            'sin movimiento no hay noticia; repetirlo cada día lo convierte en ruido'

    def test_distingue_sin_movimiento_de_sin_datos(self):
        assert 'no que nada se haya movido' in BRIEF
