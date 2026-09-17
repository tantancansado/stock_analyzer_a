"""«Me interesa a 127, avísame si llega.»

Las alertas que había eran genéricas —objetivo del analista alcanzado, stop del
8%, recuperación— y ninguna responde a la pregunta que uno se hace de verdad
después de estudiar un valor. La decisión vivía en una conversación y se perdía.

17-sep-2026, YUM: esperar a 127 porque ahí coinciden el soporte de 126,49
(aguantó 3 de 4 veces, sin visitar en 20 meses) y la valoración con crecimiento
del 6% (124 $). Dos cosas independientes en el mismo sitio.
"""
import json

import pytest

import niveles_vigilados as nv


@pytest.fixture(autouse=True)
def _aislado(tmp_path, monkeypatch):
    monkeypatch.setattr(nv, 'CONFIG', tmp_path / 'niveles_vigilados.json')


def _poner(**kw):
    nv.anadir(kw.pop('ticker', 'YUM'), kw.pop('nivel', 127.0),
              motivo=kw.pop('motivo', 'soporte + valoración'),
              accion=kw.pop('accion', 'cargar más'), **kw)


class TestCuandoAvisa:
    def test_no_avisa_si_esta_lejos(self):
        _poner()
        assert nv.revisar({'YUM': 136.65}) == []

    def test_avisa_ANTES_de_tocar(self):
        """Si esperas a que lo cruce, el aviso llega cuando ya hay que decidir
        con prisa."""
        _poner()
        a = nv.revisar({'YUM': 128.5})
        assert a and a[0]['estado'] == 'CERCA'

    def test_avisa_al_tocar(self):
        _poner()
        a = nv.revisar({'YUM': 126.9})
        assert a and a[0]['estado'] == 'TOCADO'

    def test_hacia_arriba_tambien(self):
        """Un nivel puede vigilarse para vender, no solo para comprar."""
        nv.anadir('MCO', 520.0, motivo='precio objetivo por valoración',
                  accion='vender', direccion='arriba')
        assert nv.revisar({'MCO': 525.0})[0]['estado'] == 'TOCADO'
        assert nv.revisar({'MCO': 400.0}) == []


class TestLoQueSeGuarda:
    def test_el_motivo_viaja_con_el_nivel(self):
        """Un nivel sin su razón es un número que dentro de tres meses nadie
        sabe de dónde salió: o se ignora, o se obedece sin saber por qué."""
        _poner(motivo='soporte de 126,49 y valoración a crecimiento 6%')
        a = nv.revisar({'YUM': 126.5})[0]
        assert 'soporte' in a['motivo'] and '126,49' in a['motivo']
        assert a['decidido_el']
        assert 'motivo' in nv.frase(a) or '126,49' in nv.frase(a)

    def test_la_frase_pone_el_motivo_delante_del_numero(self):
        _poner()
        f = nv.frase(nv.revisar({'YUM': 126.5})[0])
        assert 'YUM' in f and '127' in f and 'soporte' in f

    def test_un_ticker_puede_tener_varios_niveles(self):
        _poner(nivel=127.0)
        _poner(nivel=118.0, motivo='segundo soporte')
        assert len(json.loads(nv.CONFIG.read_text())['niveles']) == 2

    def test_reañadir_el_mismo_nivel_lo_actualiza_no_lo_duplica(self):
        _poner(nivel=127.0, motivo='primero')
        _poner(nivel=127.0, motivo='corregido')
        n = json.loads(nv.CONFIG.read_text())['niveles']
        assert len(n) == 1 and n[0]['motivo'] == 'corregido'


def test_fichero_ilegible_no_se_sobrescribe():
    """«No pude leerlo» no es «no había nada»: si se pisa, se pierden los
    niveles que el usuario decidió."""
    nv.CONFIG.write_text('{roto')
    assert nv._cargar() is None
    assert nv.revisar({'YUM': 100.0}) == []
    with pytest.raises(RuntimeError):
        nv.anadir('YUM', 127.0, motivo='x')
