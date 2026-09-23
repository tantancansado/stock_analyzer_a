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
import pytest

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


class TestLoQueSeCompraLlegaALaPagina:
    """El veredicto se pagaba y otro paso lo borraba tres pasos después.

    `enrich_why_cheap` corre en el paso 11 de core-scoring y
    `european_value_scanner.py` reescribe ENTERO
    `european_value_opportunities.csv` en el paso 14. Resultado medido el
    23-sep-2026: el CSV europeo publicado no tenía ni la columna `why_cheap`,
    mientras la caché guardaba veredictos europeos ya comprados —Claude con
    búsqueda web, la llamada más cara de la app— y volvía a comprarlos al
    caducar cada 14 días.
    """

    @staticmethod
    def _csvs_publicados():
        import csv
        raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for nombre in ('value_opportunities.csv', 'value_opportunities_filtered.csv',
                       'european_value_opportunities.csv',
                       'european_value_opportunities_filtered.csv'):
            ruta = os.path.join(raiz, 'docs', nombre)
            if os.path.exists(ruta):
                with open(ruta) as fh:
                    yield nombre, list(csv.DictReader(fh))

    def test_si_hay_veredicto_comprado_esta_en_el_csv(self):
        """Contra la caché publicada y los CSV publicados."""
        import json
        raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ruta_cache = os.path.join(raiz, 'docs', 'why_cheap_cache.json')
        if not os.path.exists(ruta_cache):
            pytest.skip('sin caché publicada')
        with open(ruta_cache) as fh:
            cache = json.load(fh)
        util = {t: e for t, e in cache.items()
                if (e.get('veredicto') or '').strip() not in ('', 'SIN_DATOS')}

        perdidos = []
        for nombre, filas in self._csvs_publicados():
            if not filas:
                continue
            if 'why_cheap' not in filas[0]:
                # Sin la columna, cualquier ticker con veredicto está perdido.
                con_veredicto = [r['ticker'] for r in filas if r.get('ticker', '').upper() in util]
                if con_veredicto:
                    perdidos.append(f'{nombre}: sin columna why_cheap y {len(con_veredicto)} '
                                    f'tickers con veredicto comprado')
                continue
            for r in filas:
                t = (r.get('ticker') or '').upper()
                if t in util and not (r.get('why_cheap') or '').strip():
                    perdidos.append(f'{nombre}:{t}')
        assert not perdidos, (
            'Veredictos comprados que no llegan al CSV que sirve la app '
            f'(alguien reescribe el fichero después de enriquecerlo): {perdidos[:12]}'
        )

    def test_el_workflow_reaplica_despues_de_quien_reescribe(self):
        """El paso gratuito tiene que ir DESPUÉS del escáner europeo."""
        yaml = pytest.importorskip('yaml')
        raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(raiz, '.github/workflows/daily-analysis.yml')) as fh:
            wf = yaml.safe_load(fh)
        pasos = wf['jobs']['core-scoring']['steps']
        def indice(fragmento):
            for i, s in enumerate(pasos):
                if fragmento in str(s.get('run', '')):
                    return i
            return None
        escaner = indice('european_value_scanner.py')
        reaplica = None
        for i, s in enumerate(pasos):
            if '--solo-cache' in str(s.get('run', '')):
                reaplica = i
        assert reaplica is not None, 'falta el paso que reaplica la caché sin gastar'
        assert escaner is None or reaplica > escaner, (
            'el escáner europeo reescribe el CSV después de reaplicar: los '
            'veredictos europeos se vuelven a perder'
        )
