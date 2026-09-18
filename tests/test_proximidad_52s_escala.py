"""El mismo campo leído en tres escalas distintas, y dos estaban mal.

`proximity_to_52w_high` es `(precio / máximo52s - 1) * 100`. Sobre el
universo real va de -59,6 a -0,8, y NO PUEDE pasar de 0: el máximo de 52
semanas incluye el día de hoy. Tres consumidores, tres lecturas:

    portfolio_tracker   _prox >= -30      distancia negativa   correcto
    ai_quality_filter   proximity > 1.25  un múltiplo (1,25x)  imposible
    leaps_analyzer      prox >= 98        un % de 0 a 100      imposible

Los dos rotos llevaban desde siempre sin disparar una sola vez, y no se
notaba porque su trabajo es restar: un control que nunca salta se parece
mucho a un valor que está bien.

El de MOMENTUM buscaba sobreextensión, que no se mide contra el máximo de 52
semanas sino contra la media móvil — de ahí es de donde el precio se separa.
Ese dato no existía en el CSV y ahora lo calcula el scorer (`dist_ma50_pct`),
reaprovechando las medias que el trend template ya computaba.

Los cortes son los de antes traducidos, no unos nuevos: 1,25x → +25% sobre la
media; 98 → -2; 70-92 → -30 a -8.
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


class TestElCampoQueFaltaba:
    FUENTE = (RAIZ / 'fundamental_scorer.py').read_text()

    def test_el_scorer_publica_la_distancia_a_la_media(self):
        assert "'dist_ma50_pct': round((price / ma50 - 1) * 100, 1)" in self.FUENTE

    def test_aprovecha_la_media_que_ya_se_calculaba(self):
        """El trend template ya tenía ma50: no hace falta otra descarga."""
        i = self.FUENTE.index('ma50  = float(close.rolling(50).mean()')
        j = self.FUENTE.index("'dist_ma50_pct': round(")
        assert i < j, 'la media se calcula antes de usarla'

    def test_el_vacio_tambien_lleva_la_clave(self):
        """Si solo aparece en el camino bueno, la columna existe o no según
        qué tickers hayan pasado por ahí."""
        assert self.FUENTE.count("'dist_ma50_pct': None") >= 2

    def test_llega_al_csv(self):
        assert "'dist_ma50_pct'" in (RAIZ / 'super_score_integrator.py').read_text()


class TestElGateDeMomentum:
    FUENTE = (RAIZ / 'ai_quality_filter.py').read_text()

    def test_ya_no_compara_la_proximidad_contra_un_multiplo(self):
        assert 'proximity > 1.25' not in self.FUENTE
        assert 'proximity > 1.15' not in self.FUENTE

    def test_mide_la_sobreextension_contra_la_media(self):
        assert "extension = ticker_data.get('dist_ma50_pct')" in self.FUENTE
        assert 'extension > 25' in self.FUENTE

    def test_los_cortes_son_los_de_antes_traducidos(self):
        """1,25x → +25%, 1,15x → +15%, 1,05x → +5%, 0,85x → -15%."""
        for corte in ('> 25', '> 15', '5 < extension <= 15', '< -15'):
            assert corte in self.FUENTE, f'falta el corte {corte}'

    def test_el_campo_viaja_hasta_el_gate(self):
        assert self.FUENTE.count("'dist_ma50_pct'") >= 2, \
            'si no se pasa en el dict, el control vuelve a no saltar nunca'


class TestElTimingDeLeaps:
    FUENTE = (RAIZ / 'leaps_analyzer.py').read_text()

    def test_los_cortes_estan_en_la_escala_real(self):
        assert 'if prox >= -2:' in self.FUENTE
        assert 'elif -30 <= prox <= -8:' in self.FUENTE

    def test_no_quedan_los_cortes_imposibles(self):
        assert 'prox >= 98' not in self.FUENTE
        assert '70 <= prox <= 92' not in self.FUENTE

    def test_un_valor_positivo_se_ignora_por_imposible(self):
        """Delata que alguien ha vuelto a la escala 0-100. Tratarlo como «en
        el techo» —que es lo que haría `99 >= -2`— sería peor que ignorarlo."""
        assert 'and prox <= 0:' in self.FUENTE

    def test_se_deja_escrito_que_el_bonus_discrimina_poco(self):
        """103 de 164 lo cobran. Es un dato medido, no una opinión, y quien
        lo recalibre tiene que saberlo antes de tocar nada."""
        assert '103' in self.FUENTE


def test_el_consumidor_que_ya_estaba_bien_no_se_toca():
    tracker = (RAIZ / 'portfolio_tracker.py').read_text()
    assert '_prox >= _CAIDA_MAX_PCT' in tracker
    assert '_CAIDA_MAX_PCT = -30.0' in tracker
