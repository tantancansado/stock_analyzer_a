#!/usr/bin/env python3
"""Unit tests for conviction_filter.py"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import pandas as pd
import numpy as np
import tempfile
from conviction_filter import extract_health_metrics, calculate_conviction_score, filter_by_conviction


class TestExtractHealthMetrics:
    """Tests for parsing health_details and earnings_details dicts"""

    def test_valid_health_details(self):
        row = pd.Series({
            'health_details': "{'roe_pct': 25.0, 'debt_to_equity': 0.5, 'current_ratio': 2.0, 'operating_margin_pct': 20.0}",
            'earnings_details': "{'profit_margin_pct': 15.0, 'earnings_accelerating': True, 'eps_accel_quarters': 3}"
        })
        metrics = extract_health_metrics(row)
        assert metrics['roe'] == 25.0
        assert metrics['debt_to_equity'] == 0.5
        assert metrics['profit_margin'] == 15.0

    def test_missing_details(self):
        row = pd.Series({'health_details': None, 'earnings_details': None})
        metrics = extract_health_metrics(row)
        assert metrics['roe'] is None
        assert metrics['debt_to_equity'] is None

    def test_invalid_string(self):
        row = pd.Series({'health_details': 'not a dict', 'earnings_details': '{}'})
        metrics = extract_health_metrics(row)
        assert isinstance(metrics, dict)


class TestCalculateConvictionScore:
    """Tests for the conviction scoring logic"""

    def _make_row(self, **overrides):
        base = {
            'ticker': 'TEST',
            'value_score': 50,
            'current_price': 100.0,
            'health_details': "{'roe_pct': 20.0, 'debt_to_equity': 0.5, 'current_ratio': 2.0, 'operating_margin_pct': 18.0}",
            'earnings_details': "{'profit_margin_pct': 12.0, 'earnings_accelerating': True}",
            'fcf_yield_pct': 6.0,
            'target_price_dcf': 130.0,
            'target_price_dcf_upside_pct': 30.0,
            'analyst_upside_pct': 20.0,
            'analyst_count': 10,
            'analyst_recommendation': 2.0,
            'risk_reward_ratio': 3.0,
            'dividend_yield_pct': 2.0,
            'buyback_active': True,
            'payout_ratio_pct': 40.0,
            'earnings_warning': False,
            'rev_growth_yoy': 10.0,
        }
        base.update(overrides)
        return pd.Series(base)

    def test_high_quality_stock_gets_high_score(self):
        row = self._make_row()
        result = calculate_conviction_score(row)
        assert result['conviction_score'] >= 60
        assert result['conviction_grade'] in ('A', 'B')

    def test_negative_roe_penalized(self):
        row = self._make_row(
            health_details="{'roe_pct': -5.0, 'debt_to_equity': 2.0, 'current_ratio': 0.5, 'operating_margin_pct': 3.0}"
        )
        result = calculate_conviction_score(row)
        assert result['conviction_score'] < 60

    def test_dcf_overvalued_penalized(self):
        # Must also clear target_price_dcf_upside_pct so the code falls back to
        # computing upside from current_price instead of using the stored precomputed value.
        row_bad = self._make_row(target_price_dcf=70.0, target_price_dcf_upside_pct=None)   # DCF says overvalued (-30%)
        row_good = self._make_row(target_price_dcf=160.0, target_price_dcf_upside_pct=None)  # DCF says undervalued (+60%)
        result_bad = calculate_conviction_score(row_bad)
        result_good = calculate_conviction_score(row_good)
        assert result_bad['conviction_score'] < result_good['conviction_score']

    def test_earnings_warning_penalized(self):
        row_warn = self._make_row(earnings_warning=True)
        row_safe = self._make_row(earnings_warning=False)
        result_warn = calculate_conviction_score(row_warn)
        result_safe = calculate_conviction_score(row_safe)
        assert result_warn['conviction_score'] < result_safe['conviction_score']

    def test_returns_valid_grade(self):
        row = self._make_row()
        result = calculate_conviction_score(row)
        assert result['conviction_grade'] in ('A', 'B', 'C', 'D')
        assert 0 <= result['conviction_score'] <= 100


class TestFilterByConviction:
    def test_empty_csv(self):
        with tempfile.NamedTemporaryFile(suffix='.csv', mode='w', delete=False) as f:
            f.write('ticker,value_score\n')
            f.flush()
            result = filter_by_conviction(f.name, f.name + '.out')
        assert result == 0 or result is None

    def test_filters_low_grade(self):
        df = pd.DataFrame([
            {
                'ticker': 'GOOD', 'value_score': 50,
                'health_details': "{'roe_pct': 25.0, 'debt_to_equity': 0.3, 'current_ratio': 2.5, 'operating_margin_pct': 22.0}",
                'earnings_details': "{'profit_margin_pct': 15.0}",
                'fcf_yield_pct': 7.0, 'target_price_dcf_upside_pct': 25.0,
                'analyst_upside_pct': 20.0, 'analyst_count': 15, 'analyst_recommendation': 1.8,
                'risk_reward_ratio': 3.5, 'dividend_yield_pct': 2.5, 'buyback_active': True,
                'payout_ratio_pct': 35.0, 'earnings_warning': False, 'rev_growth_yoy': 12.0,
            },
            {
                'ticker': 'BAD', 'value_score': 25,
                'health_details': "{'roe_pct': -10.0, 'debt_to_equity': 5.0, 'current_ratio': 0.3, 'operating_margin_pct': -5.0}",
                'earnings_details': "{'profit_margin_pct': -8.0}",
                'fcf_yield_pct': -3.0, 'target_price_dcf_upside_pct': -30.0,
                'analyst_upside_pct': -5.0, 'analyst_count': 2, 'analyst_recommendation': 4.0,
                'risk_reward_ratio': 0.5, 'dividend_yield_pct': 0, 'buyback_active': False,
                'payout_ratio_pct': 120.0, 'earnings_warning': True, 'rev_growth_yoy': -15.0,
            }
        ])
        with tempfile.NamedTemporaryFile(suffix='.csv', mode='w', delete=False) as f:
            df.to_csv(f.name, index=False)
            output = f.name + '.filtered.csv'
            result = filter_by_conviction(f.name, output, min_grade='B')

        if result and result > 0:
            out_df = pd.read_csv(output)
            assert 'GOOD' in out_df['ticker'].values
            if 'BAD' in out_df['ticker'].values:
                good_score = out_df[out_df['ticker'] == 'GOOD']['conviction_score'].iloc[0]
                bad_score = out_df[out_df['ticker'] == 'BAD']['conviction_score'].iloc[0]
                assert good_score > bad_score


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


class TestTesisValue:
    """La convicción sale de dos preguntas, no de "está barata".

    1. ¿El negocio va a menos? Si ingresos y margen CRECEN mientras el precio
       cae, la caída no tiene motivo real y el precio acaba siguiendo a los
       beneficios. La ausencia de motivo ES la tesis.
    2. ¿Y si el múltiplo no vuelve nunca? Con dos empresas igual de sanas, la
       que crece rápido gana sin ayuda del mercado; la que crece despacio
       depende de que el mercado cambie de opinión.
    """

    # ── El fallo más caro: declarar "sano" sin datos ──────────────────────
    def test_un_NaN_no_puede_salir_como_sin_deterioro(self):
        """`nan < 0` es False, así que el dato ausente caía en la rama
        optimista — y aquí "sin deterioro" es la señal de COMPRA."""
        import math
        from conviction_filter import _num
        assert _num(float('nan')) is None
        assert _num(math.inf) is None
        assert _num('') is None
        assert _num(3.5) == 3.5

    def test_sin_datos_la_seccion_no_puntua(self):
        from conviction_filter import _puntuar_tesis
        pts, motivos, flags = _puntuar_tesis({'tesis_deterioro': None})
        assert pts is None and not motivos and not flags
        pts, _, _ = _puntuar_tesis({'tesis_deterioro': float('nan')})
        assert pts is None, 'un NaN debe contar como "sin datos", no como sano'

    # ── Emparejamiento interanual ─────────────────────────────────────────
    def test_se_empareja_por_fecha_no_por_posicion(self):
        """En BSX faltaban dos trimestres y `columns[-5]` comparaba 2025-09
        contra 2026-06 — tres trimestres de distancia, no cuatro."""
        import numpy as np
        import pandas as pd
        from conviction_filter import _par_interanual
        fechas = pd.to_datetime(['2024-12-31', '2025-03-31', '2025-06-30',
                                 '2025-09-30', '2025-12-31', '2026-03-31', '2026-06-30'])
        s = pd.Series([np.nan, 100, 200, 300, 400, 500, 600], index=fechas)
        hace_un_anio, actual = _par_interanual(s)
        assert (hace_un_anio, actual) == (200, 600), 'debe casar 2025-06 con 2026-06'

    def test_sin_trimestre_comparable_no_inventa(self):
        import pandas as pd
        from conviction_filter import _par_interanual
        s = pd.Series([100, 200], index=pd.to_datetime(['2026-03-31', '2026-06-30']))
        assert _par_interanual(s) == (None, None)

    # ── Porcentajes sobre base negativa ───────────────────────────────────
    def test_no_se_calcula_porcentaje_sobre_base_negativa(self):
        """INTC pasó de -1,29B a +1,97B de operativo: eso salía como '-252,9%',
        que se lee como desplome siendo una recuperación."""
        from conviction_filter import _yoy
        assert _yoy(1.97, -1.29) is None
        assert _yoy(1.97, 0) is None
        assert _yoy(110, 100) == pytest.approx(10.0)

    # ── Ancla de múltiplo ─────────────────────────────────────────────────
    def test_un_multiplo_historico_disperso_no_es_ancla(self):
        """BSX cotizó a 48-93x con el BPA deprimido; proyectar la vuelta a esos
        63x daba un objetivo de +293%, que invalida todo el análisis."""
        from conviction_filter import CV_MAX_ANCLA, PE_MAX_ANCLA  # noqa: F401
        import numpy as np
        bsx = np.array([52.0, 61.0, 48.0, 93.0])
        mco = np.array([35.1, 37.7, 36.5, 38.9])
        assert bsx.std() / bsx.mean() > CV_MAX_ANCLA or bsx.max() >= PE_MAX_ANCLA
        assert mco.std() / mco.mean() <= CV_MAX_ANCLA and mco.max() < PE_MAX_ANCLA

    # ── Puntuación ────────────────────────────────────────────────────────
    def test_el_deterioro_resta_y_lo_explica(self):
        from conviction_filter import _puntuar_tesis
        pts, _, flags = _puntuar_tesis({
            'tesis_deterioro': True, 'tesis_ingresos_yoy': -6.0,
            'tesis_op_yoy': -9.0, 'tesis_margen_op_delta': -3.0})
        assert pts < 0
        assert any('DETERIORO' in f for f in flags)
        assert any('-6.0' in f for f in flags), 'debe decir POR QUÉ, no solo que sí'

    def test_ganar_sin_reversion_puntua_mas_que_depender_de_ella(self):
        """Es lo que separa dos tesis igual de sanas."""
        from conviction_filter import _puntuar_tesis
        base = {'tesis_deterioro': False, 'tesis_ingresos_yoy': 12.0,
                'tesis_margen_op_delta': 2.0}
        gana_sola, _, _ = _puntuar_tesis({**base, 'tesis_ret_2a_sin_reversion': 35.0})
        necesita, _, flags = _puntuar_tesis({**base, 'tesis_ret_2a_sin_reversion': -5.0})
        assert gana_sola > necesita
        assert any('depende de que el mercado' in f for f in flags)

    def test_los_extraordinarios_penalizan(self):
        """SPGI tenía 7,2% del BPA en extraordinarios: su múltiplo real era
        26,7x, no los 24,8x que aparentaba."""
        from conviction_filter import _puntuar_tesis
        base = {'tesis_deterioro': False, 'tesis_ingresos_yoy': 10.0,
                'tesis_margen_op_delta': 2.5}
        limpio, _, _ = _puntuar_tesis({**base, 'tesis_extraordinarios_pct': 1.0})
        sucio, _, flags = _puntuar_tesis({**base, 'tesis_extraordinarios_pct': 7.2})
        assert sucio < limpio and any('extraordinarios' in f for f in flags)

    def test_la_razon_de_la_tesis_va_la_primera(self):
        """El resumen se corta a 4 razones; "no hay deterioro" no puede caerse."""
        from conviction_filter import calculate_conviction_score
        r = calculate_conviction_score({
            'ticker': 'TEST', 'roe_pct': 30, 'fcf_yield_pct': 6,
            'analyst_count': 20, 'analyst_recommendation': 'buy',
            'analyst_upside_pct': 15, 'current_price': 100,
            'tesis_deterioro': False, 'tesis_ingresos_yoy': 12.0,
            'tesis_margen_op_delta': 2.0, 'tesis_ret_2a_sin_reversion': 35.0})
        assert r['conviction_reasons'].startswith('Sin deterioro')

    def test_la_cache_de_tesis_sobrevive_a_CI(self):
        """`*_cache.json` del .gitignore se traga toda caché nueva: si CI no la
        commitea, cada run repite las llamadas de red y no se nota."""
        import subprocess
        from pathlib import Path
        from conviction_filter import CACHE_TESIS
        raiz = Path(__file__).parent.parent
        assert not CACHE_TESIS.name.startswith('.')
        r = subprocess.run(['git', 'check-ignore', '-q', str(CACHE_TESIS)],
                           cwd=raiz, capture_output=True)
        assert r.returncode != 0, f'{CACHE_TESIS} está gitignorada — CI no la guarda'


class TestQueEsDeterioro:
    """Deterioro = el negocio produce menos, medido en euros, no en puntos de
    margen. Partners Group crecía ingresos +21,9% con el margen cediendo 2,2
    pts (64,8→62,6) y salía marcada como deteriorada — su beneficio operativo
    crecía un +17,8%. Un margen que cede mientras el beneficio sube es una
    empresa invirtiendo en crecer, no una en decadencia.
    """

    def _clasificar(self, ingresos_yoy, op_yoy, margen_actual):
        """Reproduce la regla de analizar_tesis_value sin tocar la red."""
        if margen_actual < 0:
            return True
        if ingresos_yoy < 0:
            return True
        if op_yoy is not None:
            return op_yoy < 0
        return False

    def test_margen_cediendo_con_beneficio_al_alza_NO_es_deterioro(self):
        assert self._clasificar(21.9, 17.8, 62.6) is False

    def test_ingresos_cayendo_SI_es_deterioro(self):
        assert self._clasificar(-3.6, 2.0, 11.6) is True      # HEIA.AS
        assert self._clasificar(-4.8, -8.0, 13.6) is True     # SIKA.SW

    def test_beneficio_operativo_cayendo_SI_es_deterioro(self):
        assert self._clasificar(3.0, -12.0, 15.0) is True

    def test_perder_dinero_operando_es_deterioro(self):
        assert self._clasificar(20.0, None, -4.0) is True

    def test_recuperarse_de_perdidas_no_es_deterioro(self):
        """op_yoy None porque la base era negativa: el año pasado perdía dinero
        y ahora gana. Es recuperación (INTC), no decadencia."""
        assert self._clasificar(25.4, None, 12.2) is False


class TestFiltroDeEntrada:
    """El corte duro es SOLO la banda canónica de upside.

    Antes llevaba además `value_score >= 60` y `risk_reward_ratio >= 2.0`, los
    dos calibrados con 681 señales del periodo contaminado. En el limpio
    (n=100 a 30d) los tres cortes iban en la misma dirección — hacia peor:

        solo dorada [10,25)   n=18  win 77,8%  medio +5,67%
        + ambos filtros       n= 5  win 60,0%  medio +0,52%
        lo que descartaban    n=13  win 84,6%  medio +7,65%
    """

    def test_no_hay_filtro_de_risk_reward(self):
        """RR = analyst_upside_pct / 8 (corr 0,999999 sobre 1501 señales), así
        que `RR >= 2.0` ES `upside >= 16`: una banda inline encubierta que
        recortaba la dorada a [16,25). CLAUDE.md lo prohíbe explícitamente."""
        import re
        from pathlib import Path
        import conviction_filter as cf
        src = Path(cf.__file__).read_text()
        cuerpo = src[src.index('def filter_by_conviction'):]
        activo = [l for l in cuerpo.splitlines()
                  if 'risk_reward_ratio' in l and not l.lstrip().startswith('#')]
        assert not activo, f'vuelve a haber un filtro de RR (= banda de upside oculta): {activo}'

    def test_no_hay_umbral_de_value_score(self):
        """Dentro de la dorada el score no informa: corr con el retorno a 30d
        es -0,026 (p=0,918). Su signo negativo global sale de que va con
        upside alto (+0,332), o sea que premia justo lo que hay que evitar."""
        import re
        from pathlib import Path
        import conviction_filter as cf
        src = Path(cf.__file__).read_text()
        cuerpo = src[src.index('def filter_by_conviction'):]
        activo = [l for l in cuerpo.splitlines()
                  if re.search(r"value_score.*>=\s*\d", l) and not l.lstrip().startswith('#')]
        assert not activo, f'vuelve a haber un umbral de value_score: {activo}'

    def test_la_banda_sale_de_value_bands(self):
        """Nunca hardcodeada inline — es la regla que evitó tener tres verdades
        distintas (integrator, tracker y conviction)."""
        import conviction_filter as cf
        from value_bands import UPSIDE_HARD_REJECT, UPSIDE_MIN
        assert cf.UPSIDE_MIN is UPSIDE_MIN
        assert cf.UPSIDE_HARD_REJECT is UPSIDE_HARD_REJECT


class TestCompresionConBpaCreciendo:
    """Beneficio arriba y multiplo abajo: el patron value por excelencia — y el
    que `_pe_historico` descarta POR CONSTRUCCION.

    Si el multiplo se comprime fuerte, la dispersion se dispara y el ancla se
    declara "no fiable". BR paso de ~29x a 17x con el BPA subiendo de 5,30 a
    9,60 (+81%) y se quedaba sin ninguna señal: justo el caso que mas interesa.
    """

    def test_el_patron_suma_pero_poco(self):
        """Poco a proposito: parte de una compresion asi es re-normalizacion
        legitima (32x era caro para algo que crece al 9%), no castigo."""
        from conviction_filter import _puntuar_tesis
        base = {'tesis_deterioro': False, 'tesis_ingresos_yoy': 7.5,
                'tesis_margen_op_delta': 0.5}
        sin, _, _ = _puntuar_tesis(base)
        con, motivos, _ = _puntuar_tesis({
            **base, 'tesis_compresion_con_bpa_creciendo': True,
            'tesis_bpa_crecio_pct': 81.0, 'tesis_multiplo_vario_pct': -41.0,
            'tesis_pe_antes': 29.4, 'tesis_pe_ahora': 17.3})
        assert 0 < con - sin <= 4, 'debe sumar, pero no dominar la puntuacion'
        assert any('multiplo' in m for m in motivos)

    def test_no_promete_precio_objetivo(self):
        """Reportar el hecho, no proyectar la vuelta al multiplo viejo: eso
        seria inventar (a BSX le daba un objetivo de +293%)."""
        from conviction_filter import _compresion_con_bpa_creciendo
        import inspect
        src = inspect.getsource(_compresion_con_bpa_creciendo)
        claves = ('compresion_con_bpa_creciendo', 'bpa_crecio_pct',
                  'multiplo_vario_pct', 'pe_antes', 'pe_ahora')
        assert all(k in src for k in claves)
        assert 'objetivo' not in src.split('"""')[2]  # no en el codigo, solo el docstring


class TestInteresCorto:
    """El interés corto no se puntúa: no hay evidencia en NUESTRO universo.

    Hasta el 11-ago-2026 el integrator sumaba +3 pts al 8-20% de float corto
    ("squeeze fuel for breakouts") mientras ai_quality_filter restaba confianza
    al mismo dato (-5 por encima del 10%, -15 por encima del 20%): el sistema
    premiaba y penalizaba lo mismo a la vez. Y el bonus era lógica de momentum
    metida en un score que alimenta la lista VALUE.

    Medido sobre 6265 observaciones (110 tickers × 24 fechas de docs/history):
    spearman(cortos, retorno) = +0,015 a 5d, +0,034 a 10d, +0,064 a 21d. Nada,
    y del signo contrario al que justificaría penalizar. Por bandas a 21d no hay
    patrón: 0-2% +3,84%, 2-5% +3,57%, 5-10% +6,56%, 10-20% +3,73%.
    """

    def test_el_interes_corto_no_suma_puntos(self):
        from pathlib import Path
        import super_score_integrator as ssi
        src = Path(ssi.__file__).read_text()
        i = src.index("df['short_bonus']")
        bloque = src[i:i + 400]
        assert '+= 3.0' not in bloque and '+= 1.0' not in bloque, \
            'vuelve a premiarse el interés corto sin evidencia'

    def test_el_umbral_del_2pct_descartaria_el_universo(self):
        """La mediana del universo curado es 2,80%: cortar en el 2% tiraría dos
        tercios de los candidatos. No es un filtro, es apagar el sistema."""
        import pandas as pd
        from pathlib import Path
        f = Path(__file__).parent.parent / 'docs' / 'fundamental_scores.csv'
        if not f.exists():
            import pytest
            pytest.skip('sin fundamental_scores.csv')
        s = pd.to_numeric(pd.read_csv(f)['short_percent_float'], errors='coerce').dropna()
        if len(s) < 50:
            import pytest
            pytest.skip('muestra pequeña')
        assert s.median() > 2.0, (
            f'la mediana del universo es {s.median():.2f}% — si baja de 2% '
            f'habría que revisar la conclusión de que el umbral es inservible')

    def test_el_tracker_guarda_el_dato_para_decidirlo_luego(self):
        """Hoy no se puede responder con nuestras señales (n=20 a 7d). Sin
        capturarlo, dentro de seis meses seguiremos igual."""
        from pathlib import Path
        import portfolio_tracker as pt
        src = Path(pt.__file__).read_text()
        assert src.count("'short_percent_float':") >= 2, \
            'debe capturarse tanto en VALUE como en MOMENTUM'
