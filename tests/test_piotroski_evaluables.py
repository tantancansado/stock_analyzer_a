"""Un dato que falta bajaba el Piotroski, y el Piotroski decide.

Los nueve criterios suman con la forma `if dato is not None and se_cumple`,
así que la ausencia de un dato no deja el criterio sin evaluar: lo cuenta
como incumplido. Un 5/9 por falta de datos se lee exactamente igual que un
5/9 real.

A un banco no se le pueden calcular nunca F6 (ratio corriente) ni F8 (margen
bruto): no reporta activo corriente ni margen bruto. Su techo real es 7 de 9,
y nadie lo decía.

Y no era decorativo: el número va al prompt del gate de Claude —el que decide
qué VALUE se publica— con la coletilla «low = weak fundamentals». Se le estaba
pidiendo que castigara una empresa por un dato que su sector no publica.

F7 era además el único criterio que daba el beneficio de la duda cuando
faltaba el dato (`if sh_y1 is None or sh_y2 is None or ...`), mientras los
otros ocho penalizaban. Ahora todos se comportan igual: si no se sabe, no
cuenta ni a favor ni en contra, y el denominador lo dice.

El score NO se toca, para no mover la calibración. Lo que se añade es el
denominador de verdad.
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FUENTE = (RAIZ / 'fundamental_scorer.py').read_text()
# Delimitado por marcas de código, no por un número de caracteres: un
# comentario que crezca desplazaría la ventana y el test fallaría por eso.
BLOQUE = FUENTE[FUENTE.index('score = 0\n            evaluables = 0'):
                FUENTE.index('def _calculate_magic_formula_metrics')]


class TestElDenominador:
    def test_se_cuentan_los_criterios_evaluables(self):
        assert "result['piotroski_evaluables'] = evaluables" in BLOQUE

    def test_cada_criterio_declara_si_se_puede_evaluar(self):
        """Nueve llamadas: una por criterio, cada una con su condición."""
        llamadas = [m for m in re.findall(r'^\s+_criterio\(', BLOQUE, re.M)]
        assert len(llamadas) == 9, f'nueve criterios, encontradas {len(llamadas)} llamadas'

    def test_el_helper_separa_poder_de_cumplir(self):
        """`se_puede` decide si cuenta en el denominador; `se_cumple`, en el
        numerador. Mezclarlos es el bug original."""
        assert 'def _criterio(se_puede: bool, se_cumple: bool)' in FUENTE
        assert re.search(r'if not se_puede:\s*\n\s*return', FUENTE)

    def test_f7_ya_no_regala_el_punto(self):
        """Era el único que sumaba cuando faltaba el dato."""
        assert 'if sh_y1 is None or sh_y2 is None or sh_y1 <= sh_y2 * 1.01: score += 1' \
            not in FUENTE


class TestLaEtiqueta:
    def test_sin_siete_criterios_no_se_etiqueta(self):
        """Un 5 sobre 6 no es un 5 sobre 9; llamar «NEUTRAL» a los dos es
        afirmar algo que no se sabe."""
        assert 'if evaluables >= 7:' in BLOQUE
        assert "result['piotroski_label'] = None" in BLOQUE

    def test_y_se_dice_por_qué(self):
        assert "result['piotroski_motivo']" in BLOQUE
        assert 'calculables' in BLOQUE


class TestLoQueVeElGate:
    """El gate de Claude es quien decide si el pick se publica."""

    GATE = (RAIZ / 'ai_quality_filter.py').read_text()

    def test_el_prompt_enseña_el_denominador_real(self):
        assert 'def _piotroski(td)' in self.GATE
        assert "{_piotroski(td)}" in self.GATE
        assert "_nd(td.get('piotroski_score'), '/9')" not in self.GATE, \
            'el formato viejo daba /9 siempre'

    def test_el_prompt_explica_que_un_denominador_menor_no_es_un_fallo(self):
        assert 'NO que falle' in self.GATE or 'no es calculable' in self.GATE

    def test_el_campo_viaja_hasta_el_gate(self):
        assert self.GATE.count("'piotroski_evaluables'") >= 2, \
            'si no se pasa en el dict, el helper lee siempre None'


class TestLlegaAlCsv:
    def test_el_integrador_propaga_los_campos_nuevos(self):
        integ = (RAIZ / 'super_score_integrator.py').read_text()
        for campo in ('piotroski_evaluables', 'piotroski_motivo'):
            assert f"'{campo}'" in integ
