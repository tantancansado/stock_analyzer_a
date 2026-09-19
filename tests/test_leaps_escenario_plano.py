"""Se publicaba lo que ganas si acierta, no lo que pierdes si no pasa nada.

La ficha de un LEAPS enseñaba el escenario bueno (si la acción llega al
objetivo del analista) y, desde el 18-sep-2026, el prudente (si llega al
objetivo más bajo de los modelos propios). Faltaba el tercero, que es el más
probable de todos: que la acción siga donde está.

Un LEAPS que no se mueve pierde TODO su valor temporal. Medido sobre los once
publicados el 18-sep:

    MA   -46,3%   AXP  -27,1%   AMZN -27,1%   FHN  -30,3%
    GOOG -25,8%   MSFT -22,6%   ICE  -20,0%   BAC  -12,0%

De MA se publicaba «ventaja neta +13,49%» sin decir que quedarse quieta
cuesta casi la mitad del contrato. Comprar la acción, en ese mismo escenario,
cuesta cero. Es la cara b del apalancamiento, y era la única que no se veía.
"""
from pathlib import Path

from conftest import bloque_de_codigo

RAIZ = Path(__file__).resolve().parent.parent
FUENTE = (RAIZ / 'leaps_analyzer.py').read_text()


def _retorno_plano(spot, strike, prima):
    """Lo que vale el contrato al vencimiento si el precio no cambia."""
    coste = prima * 100
    return (max(spot - strike, 0.0) * 100 - coste) / coste * 100


class TestElCalculo:
    def test_pierde_todo_el_valor_temporal(self):
        # GOOG el 18-sep: spot 345,93 · strike 260 · prima 115,83
        assert _retorno_plano(345.93, 260.0, 115.83) == __import__('pytest').approx(-25.8, abs=0.1)

    def test_cuanto_mas_cerca_del_dinero_mas_se_pierde(self):
        """MA tenía el strike a 500 con el spot en 565: casi todo extrínseco."""
        profundo = _retorno_plano(100.0, 60.0, 42.0)
        cercano = _retorno_plano(100.0, 95.0, 12.0)
        assert cercano < profundo

    def test_una_call_sin_valor_temporal_no_pierde_nada(self):
        assert _retorno_plano(100.0, 60.0, 40.0) == 0.0


class TestSePublica:
    BLOQUE = bloque_de_codigo(FUENTE, 'Lo que pasa si NO pasa nada',
                              'El mismo contrato contra el objetivo')

    def test_el_escenario_esta_en_el_analizador(self):
        assert "profit_at_target['si_no_se_mueve']" in self.BLOQUE

    def test_dice_que_la_accion_no_pierde_nada(self):
        assert "'stock_return_pct': 0.0" in self.BLOQUE

    def test_explica_por_qué(self):
        assert 'valor temporal' in self.BLOQUE

    def test_la_ficha_lo_enseña(self):
        tsx = (RAIZ / 'frontend/src/pages/Leaps.tsx').read_text()
        assert 'si_no_se_mueve' in tsx
        assert 'Si la acción se queda donde está' in tsx

    def test_el_tipo_lo_declara(self):
        cli = (RAIZ / 'frontend/src/api/client.ts').read_text()
        assert 'si_no_se_mueve' in cli
        assert 'escenario_prudente' in cli, 'el otro escenario tampoco estaba en el tipo'


def test_los_tres_escenarios_estan(self=None):
    """Bueno, prudente y plano. Publicar solo el primero es enseñar una cara
    de una apuesta apalancada."""
    for clave in ('target_price', 'escenario_prudente', 'si_no_se_mueve'):
        assert clave in FUENTE, f'falta el escenario {clave}'
