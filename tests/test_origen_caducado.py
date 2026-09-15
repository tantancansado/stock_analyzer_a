"""Un origen caducado no produce precios de hoy.

`add_entry_exit_to_opportunities.py` leía por defecto `super_scores_ultimate.csv`
— un fósil que nadie escribe desde feb-2026 — le pedía precios FRESCOS a
yfinance y escribía el CSV del que `ticker_api` sirve entrada, stop y objetivo.

El resultado se commiteaba cada día con precios de hoy y fundamentales de hace
siete meses, así que parecía vivo justo porque el precio SÍ se actualizaba.
Para AVGO servía «BUY NOW, entrada 344,72, objetivo 479,44, R:R 14,59»
calculado sobre febrero.

Es el peor tipo de fallo: nada falla, el script hace su trabajo con esmero, y
la salida es indistinguible de una buena.
"""
import pandas as pd
import pytest

import add_entry_exit_to_opportunities as m


class TestAntiguedadDelDato:
    """Se mira la fecha del DATO, no la del fichero: el fichero se reescribía
    a diario, que es precisamente lo que disimulaba el problema."""

    def test_lee_data_as_of_date(self):
        df = pd.DataFrame({'ticker': ['A'], 'data_as_of_date': ['2026-02-19']})
        d = m._antiguedad_del_dato(df)
        assert d is not None and d > 180

    def test_un_dato_de_hoy_da_cero(self):
        hoy = pd.Timestamp.now().strftime('%Y-%m-%d')
        df = pd.DataFrame({'ticker': ['A'], 'data_as_of_date': [hoy]})
        assert m._antiguedad_del_dato(df) == 0

    def test_cae_a_otras_columnas_de_fecha(self):
        df = pd.DataFrame({'ticker': ['A'], 'score_timestamp': ['2026-02-19 17:04:04']})
        assert m._antiguedad_del_dato(df) > 180

    def test_sin_columna_de_fecha_devuelve_None(self):
        """No se puede afirmar que esté caducado si no lo declara: se deja pasar
        en vez de bloquear un origen legítimo que no lleve la columna."""
        assert m._antiguedad_del_dato(pd.DataFrame({'ticker': ['A']})) is None

    def test_fechas_ilegibles_no_revientan(self):
        df = pd.DataFrame({'ticker': ['A'], 'data_as_of_date': ['no es una fecha']})
        assert m._antiguedad_del_dato(df) is None


class TestRechazo:
    def _csv(self, tmp_path, fecha, n=2):
        f = tmp_path / 'origen.csv'
        pd.DataFrame({'ticker': ['AAA', 'BBB'][:n], 'vcp_score': [70, 60][:n],
                      'data_as_of_date': [fecha] * n}).to_csv(f, index=False)
        return f

    def test_un_origen_caducado_no_escribe_nada(self, tmp_path):
        entrada = self._csv(tmp_path, '2026-02-19')
        salida = tmp_path / 'salida.csv'
        m.add_entry_exit_prices(str(entrada), str(salida))
        assert not salida.exists(), \
            'mejor sin escalera de precios que con una calculada sobre datos muertos'

    def test_el_corte_son_MAX_ANTIGUEDAD_DIAS(self, tmp_path, monkeypatch):
        """Justo en el límite pasa; un día más, no. Y el límite es una
        constante con nombre, no un número suelto en medio del código."""
        assert isinstance(m.MAX_ANTIGUEDAD_DIAS, int)
        limite = pd.Timestamp.now() - pd.Timedelta(days=m.MAX_ANTIGUEDAD_DIAS)
        pasado = pd.Timestamp.now() - pd.Timedelta(days=m.MAX_ANTIGUEDAD_DIAS + 1)
        df_ok = pd.DataFrame({'ticker': ['A'], 'data_as_of_date': [limite.strftime('%Y-%m-%d')]})
        df_no = pd.DataFrame({'ticker': ['A'], 'data_as_of_date': [pasado.strftime('%Y-%m-%d')]})
        assert m._antiguedad_del_dato(df_ok) <= m.MAX_ANTIGUEDAD_DIAS
        assert m._antiguedad_del_dato(df_no) > m.MAX_ANTIGUEDAD_DIAS


class TestFuentePorDefecto:
    def test_ya_no_apunta_al_fosil(self):
        import inspect
        src = inspect.getsource(m.add_entry_exit_prices)
        assert "input_file = 'docs/momentum_opportunities.csv'" in src
        assert "input_file = 'docs/super_scores_ultimate.csv'" not in src

    def test_el_fosil_sigue_estando_caducado(self):
        """Si algún día alguien lo revive, este test avisa de que ya no es un
        fósil y hay que revisar esta decisión."""
        from pathlib import Path
        f = Path(__file__).parent.parent / 'docs' / 'super_scores_ultimate.csv'
        if not f.exists():
            pytest.skip('el fósil ya no existe')
        d = m._antiguedad_del_dato(pd.read_csv(f))
        assert d is None or d > m.MAX_ANTIGUEDAD_DIAS, \
            'super_scores_ultimate.csv vuelve a tener datos frescos: revisar la fuente por defecto'
