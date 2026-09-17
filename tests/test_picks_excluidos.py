"""Por qué falta un valor de la lista publicada.

17-sep-2026: Broadridge desapareció de VALUE con el segundo mejor score del día
(87,8) y con ella otros diez. Para saber por qué hubo que bajarse el log de
GitHub Actions y leerlo a mano — el CSV publicado no dice nada de lo que NO
contiene, así que «lo echamos por un dato incoherente» y «nunca estuvo» se ven
igual. Y el usuario se enteró preguntando, que es justo lo que no debe pasar.
"""
import json

import picks_excluidos as pe


def _ruta(tmp_path):
    return tmp_path / 'picks_excluidos.json'


class TestRegistro:
    def test_guarda_ticker_paso_motivo_y_score(self, tmp_path):
        r = _ruta(tmp_path)
        pe.registrar('value_opportunities', [
            {'ticker': 'BR', 'paso': 'verificador_ia',
             'motivo': 'upside_triangulated_pct es NaN', 'score': 87.8},
        ], candidatas=60, publicadas=43, ruta=r)
        d = json.loads(r.read_text())['listas']['value_opportunities']
        assert d['candidatas'] == 60 and d['publicadas'] == 43
        assert d['excluidos'][0]['ticker'] == 'BR'

    def test_una_lista_no_borra_la_otra(self, tmp_path):
        """VALUE y MOMENTUM se publican en llamadas distintas."""
        r = _ruta(tmp_path)
        pe.registrar('value_opportunities', [{'ticker': 'BR'}], candidatas=60, publicadas=43, ruta=r)
        pe.registrar('momentum_opportunities', [{'ticker': 'X'}], candidatas=5, publicadas=2, ruta=r)
        listas = json.loads(r.read_text())['listas']
        assert set(listas) == {'value_opportunities', 'momentum_opportunities'}

    def test_sin_fichero_es_none_no_diccionario_vacio(self, tmp_path):
        """None es «no lo sé», no «no echamos a nadie»."""
        assert pe.leer(ruta=_ruta(tmp_path)) is None

    def test_fichero_ilegible_tambien_es_none(self, tmp_path):
        r = _ruta(tmp_path)
        r.write_text('{roto')
        assert pe.leer(ruta=r) is None

    def test_se_puede_preguntar_por_un_ticker(self, tmp_path):
        r = _ruta(tmp_path)
        pe.registrar('value_opportunities', [
            {'ticker': 'BR', 'paso': 'verificador_ia', 'motivo': 'x', 'score': 87.8}],
            candidatas=60, publicadas=43, ruta=r)
        assert pe.motivo_de('br', ruta=r)['paso'] == 'verificador_ia'
        assert pe.motivo_de('MCO', ruta=r) is None


class TestElWatchdogAvisa:
    """El aviso existía, pero solo en el log de CI. De ahí no sale solo."""

    def _con_registro(self, tmp_path, monkeypatch, excluidos):
        r = _ruta(tmp_path)
        pe.registrar('value_opportunities', excluidos,
                     candidatas=60, publicadas=43, ruta=r)
        monkeypatch.setattr(pe, 'RUTA', r)
        import data_freshness_watchdog as wd
        return wd._picks_de_calidad_fuera()

    def test_un_pick_de_score_alto_fuera_es_noticia(self, tmp_path, monkeypatch):
        probs = self._con_registro(tmp_path, monkeypatch, [
            {'ticker': 'BR', 'paso': 'verificador_ia', 'motivo': 'a', 'score': 87.8}])
        assert any(p['status'] == 'pick_bueno_fuera' for p in probs)
        assert 'BR' in next(p['detail'] for p in probs if p['status'] == 'pick_bueno_fuera')

    def test_uno_flojo_fuera_no_molesta(self, tmp_path, monkeypatch):
        """El usuario odia el ruido: echar a un valor mediocre es rutina."""
        probs = self._con_registro(tmp_path, monkeypatch, [
            {'ticker': 'ZZZ', 'paso': 'rangos_imposibles', 'motivo': 'a', 'score': 31.0}])
        assert not [p for p in probs if p['status'] == 'pick_bueno_fuera']

    def test_el_mismo_motivo_en_varios_delata_la_ficha(self, tmp_path, monkeypatch):
        """Once de veinticinco por lo mismo no habla de once empresas."""
        motivo = 'upside_triangulated_pct es NaN pero modelos_acuerdo indica CONTRADICEN'
        probs = self._con_registro(tmp_path, monkeypatch, [
            {'ticker': t, 'paso': 'verificador_ia', 'motivo': motivo, 'score': 40.0}
            for t in ('BR', 'SPGI', 'AXP', 'MA')])
        rep = [p for p in probs if p['status'] == 'mismo_motivo_en_varios']
        assert rep and '4 valores' in rep[0]['detail']

    def test_motivos_distintos_no_disparan_el_aviso(self, tmp_path, monkeypatch):
        probs = self._con_registro(tmp_path, monkeypatch, [
            {'ticker': 'A', 'paso': 'x', 'motivo': 'FCF yield fuera de rango', 'score': 40.0},
            {'ticker': 'B', 'paso': 'x', 'motivo': 'DCF fuera de rango', 'score': 40.0},
            {'ticker': 'C', 'paso': 'x', 'motivo': 'Falta analyst_upside_pct', 'score': 40.0}])
        assert not [p for p in probs if p['status'] == 'mismo_motivo_en_varios']

    def test_sin_registro_no_se_concluye_que_salio_todo(self, tmp_path, monkeypatch):
        monkeypatch.setattr(pe, 'RUTA', _ruta(tmp_path))
        import data_freshness_watchdog as wd
        assert wd._picks_de_calidad_fuera() == []


def test_el_watchdog_sabe_explicar_el_estado_incompleto():
    """Ese estado se creó el 17-sep en el health y aquí no se contempló: los
    tres módulos de VALUE salieron 'incompleto' ese mismo día y el aviso habría
    viajado con el detalle en blanco."""
    import data_freshness_watchdog as wd
    src = (wd.__file__)
    with open(src) as fh:
        assert "'incompleto'" in fh.read() or '"incompleto"' in open(src).read()
