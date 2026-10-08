#!/usr/bin/env python3
"""LEAPS calcula su propio `timing_score` y puede contradecir al
`entry_readiness` de la ficha VALUE del mismo valor.

El 22-sep-2026 FHN salía con LEAPS recomendado (timing_score 68) mientras su
ficha decía ESPERAR — «ha perdido la MA200». Un LEAPS deep-ITM apalanca la
caída igual que la subida, así que dos motores en desacuerdo sobre el mismo
valor no es un detalle de presentación.

No se bloquea: el horizonte de un LEAPS es 2028 y el de `entry_readiness` es
corto, así que pueden discrepar con motivo. Lo que no puede es no decirse.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from coherence_check import leaps_vs_timing_de_la_accion as revisar


class TestElDesacuerdoSeDice:

    def test_el_caso_real_de_fhn(self):
        fallos = revisar([{
            'ticker': 'FHN', 'in_value_list': True, 'timing_score': 68.0,
            'entry_readiness': 'ESPERAR',
            'entry_readiness_reason': 'Ha perdido la MA200'}])
        assert len(fallos) == 1
        assert 'FHN' in fallos[0] and 'ESPERAR' in fallos[0]
        assert 'MA200' in fallos[0], 'el motivo del timing tiene que viajar'

    def test_vigilar_y_entrada_no_saltan(self):
        """Solo ESPERAR significa «sigue cayendo». VIGILAR es el radar."""
        for timing in ('VIGILAR', 'ENTRADA'):
            assert revisar([{'ticker': 'X', 'in_value_list': True,
                             'timing_score': 80, 'entry_readiness': timing}]) == []

    def test_fuera_de_la_lista_value_no_aplica(self):
        """Sin ficha VALUE no hay dos motores que comparar."""
        assert revisar([{'ticker': 'UNH', 'in_value_list': False,
                         'timing_score': 50, 'entry_readiness': 'ESPERAR'}]) == []

    def test_sin_el_dato_no_se_inventa(self):
        """Un LEAPS de antes de que el campo existiera no puede dar un aviso."""
        assert revisar([{'ticker': 'X', 'in_value_list': True, 'timing_score': 60}]) == []
        assert revisar([{'ticker': 'X', 'in_value_list': True,
                         'entry_readiness': None}]) == []

    def test_el_analizador_publica_el_campo(self):
        """Sin esto el cruce nunca tendría nada que mirar."""
        from pathlib import Path
        src = (Path(__file__).resolve().parents[1] / 'leaps_analyzer.py').read_text()
        assert "'entry_readiness': sig.get('entry_readiness')" in src
        assert "s['entry_readiness'] = " in src


class TestSoloFallaSiNoSeDice:
    """El 8-oct-2026 BAC y MCD pusieron el run en rojo aunque la tarjeta LEAPS
    ya enseña el estado de entrada: el desacuerdo estaba dicho."""

    FILA = {'ticker': 'BAC', 'in_value_list': True, 'timing_score': 44.0,
            'entry_readiness': 'ESPERAR', 'entry_readiness_reason': 'Ha perdido la MA200'}

    def test_dicho_en_pantalla_es_informacion_no_fallo(self, monkeypatch):
        import coherence_check as cc
        monkeypatch.setattr(cc, '_leaps_enseña_el_timing', lambda: True)
        res = cc.leaps_vs_timing_de_la_accion([self.FILA])
        assert len(res) == 1 and res[0].startswith('ℹ')

    def test_si_la_pantalla_no_lo_dice_es_fallo(self, monkeypatch):
        import coherence_check as cc
        monkeypatch.setattr(cc, '_leaps_enseña_el_timing', lambda: False)
        res = cc.leaps_vs_timing_de_la_accion([self.FILA])
        assert len(res) == 1 and not res[0].startswith('ℹ')

    def test_la_tarjeta_leaps_enseña_el_estado_de_entrada(self):
        import coherence_check as cc
        assert cc._leaps_enseña_el_timing()

    def test_el_run_no_se_pone_rojo_por_un_aviso_informativo(self, monkeypatch, tmp_path):
        import coherence_check as cc
        monkeypatch.setattr(cc, 'DOCS', tmp_path)
        monkeypatch.setattr(cc, '_leaps_enseña_el_timing', lambda: True)
        cc_fn = cc.leaps_vs_timing_de_la_accion([self.FILA])
        informativos = [p for p in cc_fn if str(p).startswith('ℹ')]
        reales = [p for p in cc_fn if not str(p).startswith(('⏳', 'ℹ'))]
        assert informativos and not reales
