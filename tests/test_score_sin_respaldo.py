"""Un score de 53 que en realidad era «no tengo datos».

El fundamental score son cinco componentes ponderados. Cuando no hay estados
trimestrales, dos de ellos se quedan en su neutro: calidad de beneficios
(30%) y aceleración del crecimiento (25%). El 55% del número lo pone el
relleno, y el 53 que sale se lee como una empresa mediocre.

El 18-sep-2026 le pasaba a 16 de 164, todos ADR y valores no estadounidenses
(LRLCY, RELX, SBGSY, 4684.T…), con fundamental scores entre 44,8 y 62,8.

El propio código ya tenía escrito este razonamiento para el caso extremo —sin
cotización— y con el caso real documentado (MMC, 15 corridas seguidas con un
'⭐ AVERAGE' inventado; resultó ser un cambio de ticker a MRSH que nadie
detectó justamente porque la fila parecía normal). La frase es suya:

    «Se emite vacío (None → celda vacía en el CSV, NaN al leerlo), NO un 50
     centinela: un número que hay que saber interpretar es un número que
     alguien interpretará mal.»

Esto es lo mismo un paso antes: no hace falta que falle todo, basta con que
falle más de la mitad del peso.

Y de propina, un bug que esto destapó: el `print` del final formateaba el
score con `:.1f` sin contemplar el None, así que el TypeError caía al
`except` y el ticker acababa en `_get_empty_result` —score 0.0, tier
❌ ERROR— en vez del ❓ SIN DATOS que el bloque había decidido. La protección
estaba escrita, documentada, y no llegaba a publicarse nunca.
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FUENTE = (RAIZ / 'fundamental_scorer.py').read_text()


class TestElCorte:
    def test_el_umbral_es_la_mitad_del_peso(self):
        assert '_sin_respaldo = _peso_sin_respaldo > 0.5' in FUENTE

    def test_solo_cuentan_los_dos_que_dependen_de_los_trimestres(self):
        i = FUENTE.index('_peso_sin_respaldo = sum(')
        bloque = FUENTE[i:i + 500]
        assert "'earnings_quality'" in bloque
        assert "'growth_acceleration'" in bloque
        assert "'relative_strength'" not in bloque, \
            'la fuerza relativa depende del precio, no de los estados'

    def test_un_componente_sin_marca_se_da_por_bueno(self):
        """`con_datos` por defecto True: un componente que aún no declara su
        estado no puede tumbar el score de golpe."""
        assert "comp.get('con_datos', True)" in FUENTE

    def test_los_dos_componentes_declaran_si_tuvieron_datos(self):
        assert FUENTE.count("'con_datos':") == 2


class TestLoQueSePublica:
    def test_se_dice_por_qué_no_hay_score(self):
        assert "'sin_score_motivo': result_motivo," in FUENTE
        assert 'valores por defecto' in FUENTE

    def test_el_motivo_lleva_el_porcentaje(self):
        """«El 55% del score se apoyaría en valores por defecto» dice mucho
        más que «datos insuficientes»."""
        assert re.search(r"el \{_peso_sin_respaldo \* 100:\.0f\}% del score", FUENTE)

    def test_llega_al_csv(self):
        integ = (RAIZ / 'super_score_integrator.py').read_text()
        assert "'sin_score_motivo'" in integ


class TestElPrintQueRompiaLaProteccion:
    def test_no_formatea_un_none(self):
        assert 'if fundamental_score is None:' in FUENTE
        i = FUENTE.index('if fundamental_score is None:')
        bloque = FUENTE[i:i + 400]
        assert 'Sin score' in bloque
        assert 'Score: {fundamental_score:.1f}' in bloque, \
            'la rama con score sigue imprimiendo el número'

    def test_la_rama_de_error_tambien_dice_su_motivo(self):
        assert "'sin_score_motivo': 'error al puntuar el valor'" in FUENTE
