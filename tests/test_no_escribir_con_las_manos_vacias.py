"""
No distinguir «no hay nada» de «no he podido mirar».

Es el fallo que más veces ha aparecido en este repo, siempre con la misma forma:
una lectura o una petición falla, devuelve `{}` o `[]`, y ese vacío se escribe
encima de datos buenos. Nunca da error. El fichero queda ahí, más pequeño.

Ya apareció en:
  · TIKR — cada semana perdía las cuentas de un ~38% de los tickers, y la
    semana siguiente de otros. Cuatro meses.
  · `bounce_catalyst_flags` — el veto caducado se leía como vigente.
  · el health del pipeline — «20/20 OK» el día que fallaron nueve pasos.

Y aquí quedan los dos últimos que encontró el barrido por el resto de scrapers.
"""
import json

import pytest


class TestSenalesPoliticas:
    """314 señales acumuladas, y se reescribe el fichero ENTERO en cada guardado.

    Si la lectura fallaba —JSON a medias, error de disco— devolvía `[]` y se
    guardaban encima solo las de hoy.
    """

    def test_fichero_ausente_no_es_lo_mismo_que_ilegible(self, tmp_path, monkeypatch):
        import political_scanner as ps
        monkeypatch.setattr(ps, 'SIGNALS_PATH', tmp_path / 'no_existe.json')
        assert ps._load_signals() == [], 'aún no hay nada: lista vacía'

        malo = tmp_path / 'roto.json'
        malo.write_text('{esto no es json')
        monkeypatch.setattr(ps, 'SIGNALS_PATH', malo)
        assert ps._load_signals() is None, 'no se ha podido leer: None, no []'

    def test_si_no_se_puede_leer_no_se_sobrescribe(self, tmp_path, monkeypatch):
        import political_scanner as ps
        f = tmp_path / 'signals.json'
        f.write_text('{JSON roto')
        antes = f.read_text()
        monkeypatch.setattr(ps, 'SIGNALS_PATH', f)
        ps._save_signal({'id': 'nueva', 'x': 1})
        assert f.read_text() == antes, 'ha machacado el histórico que no supo leer'

    def test_con_el_fichero_bien_sigue_guardando(self, tmp_path, monkeypatch):
        import political_scanner as ps
        f = tmp_path / 'signals.json'
        f.write_text(json.dumps([{'id': 'vieja'}]))
        monkeypatch.setattr(ps, 'SIGNALS_PATH', f)
        ps._save_signal({'id': 'nueva'})
        ids = [s['id'] for s in json.loads(f.read_text())]
        assert 'nueva' in ids and 'vieja' in ids


class TestCacheDeTesis:
    """110 tesis cacheadas. Perderlas no es un problema de veracidad —se
    regeneran— pero sí de dinero: cada hueco es una llamada al modelo."""

    def test_fichero_ausente_no_es_lo_mismo_que_ilegible(self, tmp_path, monkeypatch):
        import conviction_filter as cf
        monkeypatch.setattr(cf, 'CACHE_TESIS', tmp_path / 'no_existe.json')
        assert cf._cache_tesis_leer() == {}

        malo = tmp_path / 'roto.json'
        malo.write_text('no soy json')
        monkeypatch.setattr(cf, 'CACHE_TESIS', malo)
        assert cf._cache_tesis_leer() is None

    def test_no_se_reescribe_lo_que_no_se_pudo_leer(self):
        import inspect

        import conviction_filter as cf
        f = inspect.getsource(cf.enriquecer_con_tesis)
        assert 'sobrescribir = cache is not None' in f
        assert 'if sobrescribir:' in f


def test_ningun_lector_de_esos_confunde_los_dos_casos():
    """La regla, escrita: si el fichero EXISTE y no se puede leer, el valor de
    vuelta tiene que ser distinto del de «todavía no hay fichero». Con el mismo
    valor para los dos, el que escribe no puede protegerse."""
    import conviction_filter as cf
    import political_scanner as ps
    for fn in (ps._load_signals, cf._cache_tesis_leer):
        anotacion = str(fn.__annotations__.get('return', ''))
        assert 'None' in anotacion, f'{fn.__name__} no distingue los dos casos'
