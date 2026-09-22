#!/usr/bin/env python3
"""«Por qué está barata» es la pregunta central de esta app, y se estaba
perdiendo por dos sitios.

1. `apply_to_dataframe` asignaba la columna ENTERA con un map, así que todo
   ticker fuera del lote recibía ''. Su propio docstring dice «lo no analizado
   se queda» y el código lo borraba: con un solo lote no se notaba, pero al
   aplicar dos (los de caché y los nuevos) el segundo se llevaba el primero.

2. El filtro de candidatos (score >= 50 y caída >= 12%) decide en quién se
   GASTA presupuesto de Claude — bien — pero también decidía a quién se le
   ENSEÑA lo ya comprado. El 22-sep-2026 MKC tenía en caché «EVENTO —
   recortes múltiples de guidance 2025-2026» y salía en blanco, porque su
   score había bajado a 39,8. Justo el deterioro que hay que ver antes de
   comprar una caída del 31%.
"""
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from why_cheap_analyzer import apply_to_dataframe


def _df():
    return pd.DataFrame([
        {'ticker': 'AAA', 'why_cheap': 'EVENTO', 'why_cheap_resumen': 'ya estaba',
         'why_cheap_fuentes': 'url1'},
        {'ticker': 'BBB', 'why_cheap': '', 'why_cheap_resumen': '', 'why_cheap_fuentes': ''},
    ])


class TestAplicarUnLoteNoBorraElAnterior:

    def test_conserva_lo_que_ya_habia(self):
        df, _ = apply_to_dataframe(_df(), {
            'BBB': {'veredicto': 'SENTIMIENTO', 'resumen': 'nuevo', 'fuentes': []}})
        d = df.set_index('ticker')
        assert d.loc['AAA', 'why_cheap'] == 'EVENTO', 'el de fuera del lote se borraba'
        assert d.loc['AAA', 'why_cheap_resumen'] == 'ya estaba'
        assert d.loc['BBB', 'why_cheap'] == 'SENTIMIENTO'

    def test_dos_lotes_seguidos_suman(self):
        df, _ = apply_to_dataframe(_df(), {
            'BBB': {'veredicto': 'SENTIMIENTO', 'resumen': 'b', 'fuentes': []}})
        df, _ = apply_to_dataframe(df, {
            'AAA': {'veredicto': 'EVENTO', 'resumen': 'a', 'fuentes': []}})
        llenos = (df['why_cheap'].astype(str).str.strip() != '').sum()
        assert llenos == 2, 'el segundo lote se llevó por delante el primero'

    def test_un_veredicto_nuevo_sustituye_al_viejo(self):
        """Conservar no es congelar: si hay análisis nuevo, manda."""
        df, _ = apply_to_dataframe(_df(), {
            'AAA': {'veredicto': 'DETERIORO_REAL', 'resumen': 'peor', 'fuentes': []}})
        assert df.set_index('ticker').loc['AAA', 'why_cheap'] in ('DETERIORO_REAL',) \
            or 'AAA' not in set(df['ticker'])   # o lo saca por bloqueante


class TestLoYaPagadoSeEnsenaATodos:

    def test_reaplica_aunque_no_sea_candidato_hoy(self, tmp_path):
        import enrich_why_cheap as e
        frames = {'x': pd.DataFrame([
            {'ticker': 'MKC', 'why_cheap': '', 'value_score': 39.8},   # bajo el corte
            {'ticker': 'ZZZ', 'why_cheap': '', 'value_score': 70.0},
        ])}
        cache = {'MKC': {'veredicto': 'EVENTO', 'resumen': 'recortes de guidance',
                         'fuentes': ['u'], 'fecha': '2026-09-10'}}
        e._reaplicar_lo_ya_pagado(frames, cache)
        d = frames['x'].set_index('ticker')
        assert d.loc['MKC', 'why_cheap'] == 'EVENTO'
        assert 'guidance' in str(d.loc['MKC', 'why_cheap_resumen'])

    def test_sin_datos_no_tapa_la_columna(self):
        """Una entrada SIN_DATOS no es un motivo: no debe pisar lo que otro
        paso pudiera rellenar."""
        import enrich_why_cheap as e
        frames = {'x': pd.DataFrame([{'ticker': 'AAA', 'why_cheap': 'EVENTO',
                                      'why_cheap_resumen': 'bueno'}])}
        e._reaplicar_lo_ya_pagado(frames, {'AAA': {'veredicto': 'SIN_DATOS', 'resumen': ''}})
        assert frames['x'].set_index('ticker').loc['AAA', 'why_cheap'] == 'EVENTO'
