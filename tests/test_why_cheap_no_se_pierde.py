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


class TestUnaCaidaGrandeSeExplicaAunqueElScoreSeaBajo:
    """El score BAJA cuando la acción cae —lo penalizan varios factores a la
    vez—, así que exigir score >= 50 excluía justo a las que más necesitan
    explicación.

    Medido el 22-sep-2026: de 54 picks, 36 no se habían analizado nunca y a
    NINGUNO le iba a llegar el turno. Entre ellos BSX con un -58,6% desde
    máximos. Separar castigo de deterioro es para lo que existe el módulo: en
    una caída del 30% la pregunta no es si el score llega a 50, es si la
    empresa se ha roto.
    """

    def test_el_caso_de_bsx(self):
        from why_cheap_analyzer import es_candidato
        assert es_candidato(58.6, 37.3) is True

    def test_el_corte_de_score_sigue_valiendo_para_caidas_normales(self):
        """Una caída del 15% con score 30 no merece gastarse una búsqueda."""
        from why_cheap_analyzer import es_candidato
        assert es_candidato(15.0, 30.0) is False
        assert es_candidato(15.0, 55.0) is True

    def test_el_umbral_de_caida_grande(self):
        from why_cheap_analyzer import es_candidato, CAIDA_QUE_MERECE_EXPLICACION
        justo = CAIDA_QUE_MERECE_EXPLICACION
        assert es_candidato(justo, 10.0) is True
        assert es_candidato(justo - 0.1, 10.0) is False

    def test_los_dos_ficheros_usan_el_mismo_criterio(self):
        """Si el enriquecedor filtrara distinto que el analizador, la cola y
        lo que se analiza dejarían de coincidir."""
        from pathlib import Path
        src = (Path(__file__).resolve().parents[1] / 'enrich_why_cheap.py').read_text()
        assert 'es_candidato' in src, (
            'enrich_why_cheap tiene que reutilizar el criterio, no copiarlo')
