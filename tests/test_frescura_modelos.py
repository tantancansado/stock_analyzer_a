"""El dato es de hoy, pero lo calculó el modelo de ayer.

El 18-sep-2026 pasó tres veces en la misma mañana:

    ancla del P/E arreglada 12:36  ·  value_opportunities.csv de las 08:06
    filtro de rebotes puesto 08:08 ·  bounce_setups_broad.json de las 06:01
    DCF de bancos bloqueado        ·  BAC publicado con un DCF de 28,43

No es el pipeline parado —de eso ya avisa `StaleDataBanner`—. El pipeline
corrió bien y con el código que había entonces. El problema es que después
cambió el modelo y nadie compara las dos fechas, así que un número calculado
con la versión anterior se lee exactamente igual que uno nuevo: MSFT salía
«un 45% cara» cuando con el ancla arreglada sale un 27% barata.
"""
from datetime import datetime, timedelta, timezone

import frescura_modelos as fm


def _iso(dias: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=dias)).strftime(
        '%Y-%m-%dT%H:%M:%SZ')


class TestLaComparacionDeFechas:
    def test_un_modulo_tocado_despues_marca_desfase(self, monkeypatch):
        monkeypatch.setattr(fm, 'MODELOS', {
            'x': {'fichero': 'f.json', 'etiqueta': 'x', 'modulos': ['m.py']}})
        monkeypatch.setattr(fm, '_generado_el', lambda _: _iso(2))
        monkeypatch.setattr(fm, '_ultimo_commit', lambda _: _iso(1))
        r = fm.revisar()
        assert r['modelos']['x']['desfasado'] is True
        assert r['hay_desfase'] is True
        assert r['modelos']['x']['modulos_mas_nuevos'][0]['modulo'] == 'm.py'

    def test_un_modulo_anterior_al_dato_no_marca_nada(self, monkeypatch):
        monkeypatch.setattr(fm, 'MODELOS', {
            'x': {'fichero': 'f.json', 'etiqueta': 'x', 'modulos': ['m.py']}})
        monkeypatch.setattr(fm, '_generado_el', lambda _: _iso(1))
        monkeypatch.setattr(fm, '_ultimo_commit', lambda _: _iso(2))
        r = fm.revisar()
        assert r['modelos']['x']['desfasado'] is False
        assert r['hay_desfase'] is False

    def test_sin_fecha_del_dato_es_no_lo_se_y_no_esta_al_dia(self, monkeypatch):
        """None ≠ False. «No lo sé» no puede publicarse como «está al día»."""
        monkeypatch.setattr(fm, 'MODELOS', {
            'x': {'fichero': 'f.json', 'etiqueta': 'x', 'modulos': ['m.py']}})
        monkeypatch.setattr(fm, '_generado_el', lambda _: None)
        monkeypatch.setattr(fm, '_ultimo_commit', lambda _: _iso(1))
        r = fm.revisar()
        assert r['modelos']['x']['desfasado'] is None
        assert r['hay_desfase'] is False, 'un «no lo sé» no dispara el aviso'

    def test_sin_commits_del_modulo_tampoco_se_concluye(self, monkeypatch):
        monkeypatch.setattr(fm, 'MODELOS', {
            'x': {'fichero': 'f.json', 'etiqueta': 'x', 'modulos': ['m.py']}})
        monkeypatch.setattr(fm, '_generado_el', lambda _: _iso(1))
        monkeypatch.setattr(fm, '_ultimo_commit', lambda _: None)
        r = fm.revisar()
        assert r['modelos']['x']['desfasado'] is None


class TestLaConfiguracion:
    def test_los_modulos_declarados_existen(self):
        """Un módulo renombrado dejaría de vigilarse sin avisar de nada."""
        from pathlib import Path
        raiz = Path(fm.__file__).resolve().parent
        for clave, cfg in fm.MODELOS.items():
            for m in cfg['modulos']:
                assert (raiz / m).exists(), f'{clave}: {m} no existe'

    def test_las_tres_secciones_que_el_usuario_mira_estan_vigiladas(self):
        """VALUE US, LEAPS y rebotes: «son las tres que realmente hago caso»."""
        for clave in ('value', 'leaps', 'rebotes'):
            assert clave in fm.MODELOS

    def test_el_scorer_esta_en_value_y_en_leaps(self):
        """Los dos leen de fundamental_scorer: un cambio ahí afecta a ambos."""
        assert 'fundamental_scorer.py' in fm.MODELOS['value']['modulos']
        assert 'fundamental_scorer.py' in fm.MODELOS['leaps']['modulos']

    def test_tasa_base_vigila_rebotes_y_reversion(self):
        """La esperanza de la operación sale de ahí para los dos."""
        assert 'tasa_base.py' in fm.MODELOS['rebotes']['modulos']
        assert 'tasa_base.py' in fm.MODELOS['reversion']['modulos']
