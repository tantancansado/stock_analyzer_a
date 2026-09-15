"""La Batch API ahorra la mitad, pero solo sirve si NUNCA deja sin respuesta.

El pipeline es secuencial: el gate alimenta a entry_exit y a thesis_generator
en el mismo run. Un lote que tarde de más no puede traducirse en un CSV vacío,
porque eso sería cambiar dinero por fiabilidad. Así que lo que se prueba aquí
no es el camino feliz —ese es el fácil— sino los cinco que acaban en respaldo.
"""
import sys
import types
import pytest

import claude_lote
from claude_lote import Peticion, claude_lote as lote_fn


# ── Dobles ────────────────────────────────────────────────────────────────

class _Texto:
    type = 'text'
    def __init__(self, t): self.text = t

class _Uso:
    input_tokens = 1000
    output_tokens = 200
    cache_read_input_tokens = 0
    server_tool_use = None

class _Mensaje:
    def __init__(self, t):
        self.content = [_Texto(t)]
        self.usage = _Uso()

class _Resultado:
    def __init__(self, tipo, texto=None):
        self.type = tipo
        self.message = _Mensaje(texto) if texto is not None else None

class _Fila:
    def __init__(self, cid, tipo, texto=None):
        self.custom_id = cid
        self.result = _Resultado(tipo, texto)

class _Lote:
    def __init__(self, estado='ended'):
        self.id = 'lote_1'
        self.processing_status = estado


class _Batches:
    def __init__(self, filas, estado='ended'):
        self._filas, self._estado = filas, estado
        self.creados, self.cancelado = [], False
    def create(self, requests):
        self.creados.append(requests); return _Lote(self._estado)
    def retrieve(self, _id):
        return _Lote(self._estado)
    def results(self, _id):
        return iter(self._filas)
    def cancel(self, _id):
        self.cancelado = True


class _Cliente:
    def __init__(self, batches):
        self.messages = types.SimpleNamespace(batches=batches)


@pytest.fixture(autouse=True)
def _entorno(monkeypatch, tmp_path):
    """Presupuesto de sobra y contador aparte: los tests no tocan el real."""
    import claude_budget
    monkeypatch.setattr(claude_budget, 'ESTADO', tmp_path / 'budget.json')
    monkeypatch.setattr(claude_budget, 'TOPE_USD', 1000.0)
    # `claude_lote` importa groq_utils dentro de la función
    falso = types.ModuleType('groq_utils')
    falso._SIN_SAMPLING = ('sonnet-5',)
    falso._SIN_CONTROL_MUESTREO = ('haiku-4-5',)
    falso._get_anthropic_client = lambda: _entorno.cliente
    monkeypatch.setitem(sys.modules, 'groq_utils', falso)
    # sin esperas reales
    monkeypatch.setattr(claude_lote.time, 'sleep', lambda *_: None)


def _preparar(filas, estado='ended'):
    b = _Batches(filas, estado)
    _entorno.cliente = _Cliente(b)
    return b


PETS = [Peticion('AAPL', [{'role': 'user', 'content': 'a'}]),
        Peticion('MSFT', [{'role': 'user', 'content': 'b'}])]


# ── Camino normal ─────────────────────────────────────────────────────────

def test_devuelve_cada_respuesta_con_su_id():
    _preparar([_Fila('AAPL', 'succeeded', 'sí'), _Fila('MSFT', 'succeeded', 'no')])
    r = lote_fn(PETS, model='claude-sonnet-5')
    assert r == {'AAPL': 'sí', 'MSFT': 'no'}


def test_cobra_a_mitad_de_precio():
    import claude_budget
    _preparar([_Fila('AAPL', 'succeeded', 'sí')])
    lote_fn([PETS[0]], model='claude-sonnet-5')
    d = claude_budget._leer()
    esperado = claude_budget.coste_de(_Mensaje('x'), 'claude-sonnet-5',
                                      claude_budget.DESCUENTO_LOTE)
    assert d['gastado_usd'] == pytest.approx(esperado, rel=1e-6)
    assert d['llamadas_lote'] == 1
    assert d['ahorro_lote_usd'] > 0


# ── Los cinco caminos al respaldo ─────────────────────────────────────────

def test_respaldo_si_una_peticion_falla():
    _preparar([_Fila('AAPL', 'succeeded', 'sí'), _Fila('MSFT', 'errored')])
    r = lote_fn(PETS, model='claude-sonnet-5', respaldo=lambda p: f'sync:{p.id}')
    assert r == {'AAPL': 'sí', 'MSFT': 'sync:MSFT'}


def test_respaldo_si_el_lote_no_termina_a_tiempo():
    b = _preparar([], estado='in_progress')
    r = lote_fn(PETS, model='claude-sonnet-5', espera_max_s=0,
                respaldo=lambda p: f'sync:{p.id}')
    assert r == {'AAPL': 'sync:AAPL', 'MSFT': 'sync:MSFT'}
    assert b.cancelado, 'un lote que ya no se espera debe cancelarse'


def test_respaldo_si_no_se_puede_crear_el_lote():
    b = _preparar([])
    b.create = lambda requests: (_ for _ in ()).throw(RuntimeError('503'))
    r = lote_fn(PETS, model='claude-sonnet-5', respaldo=lambda p: f'sync:{p.id}')
    assert r == {'AAPL': 'sync:AAPL', 'MSFT': 'sync:MSFT'}


def test_respaldo_si_falta_una_fila_en_los_resultados():
    _preparar([_Fila('AAPL', 'succeeded', 'sí')])      # falta MSFT
    r = lote_fn(PETS, model='claude-sonnet-5', respaldo=lambda p: f'sync:{p.id}')
    assert r['MSFT'] == 'sync:MSFT'


def test_sin_respaldo_devuelve_None_pero_nunca_pierde_un_id():
    _preparar([_Fila('AAPL', 'succeeded', 'sí')])
    r = lote_fn(PETS, model='claude-sonnet-5')
    assert set(r) == {'AAPL', 'MSFT'} and r['MSFT'] is None


# ── Presupuesto ───────────────────────────────────────────────────────────

def test_sin_presupuesto_no_envia_nada_ni_cae_al_sincrono(monkeypatch):
    """Sin saldo el síncrono también devolvería None: caer ahí solo gastaría
    tiempo de CI para llegar al mismo sitio."""
    import claude_budget
    monkeypatch.setattr(claude_budget, 'TOPE_USD', 0.0)
    b = _preparar([_Fila('AAPL', 'succeeded', 'sí')])
    llamado = []
    r = lote_fn(PETS, model='claude-sonnet-5',
                respaldo=lambda p: llamado.append(p.id))
    assert r == {'AAPL': None, 'MSFT': None}
    assert not b.creados and not llamado


# ── Forma de la petición ──────────────────────────────────────────────────

def test_sonnet5_va_con_thinking_adaptive_y_sin_temperature():
    """Mismo armado que `claude_chat`: Sonnet 5 rechaza `temperature` con un
    400. Si el lote lo montara distinto sería una segunda forma de llamar,
    capaz de desincronizarse de la primera sin que nadie se entere."""
    b = _preparar([_Fila('AAPL', 'succeeded', 'sí')])
    lote_fn([Peticion('AAPL', [{'role': 'user', 'content': 'a'}], system='S', max_tokens=1200)],
            model='claude-sonnet-5')
    params = b.creados[0][0]['params']
    assert b.creados[0][0]['custom_id'] == 'AAPL'
    assert params['thinking'] == {'type': 'adaptive'}
    assert 'temperature' not in params
    assert params['system'] == 'S' and params['max_tokens'] == 1200


def test_haiku_no_lleva_ni_temperature_ni_thinking():
    b = _preparar([_Fila('AAPL', 'succeeded', 'sí')])
    lote_fn([PETS[0]], model='claude-haiku-4-5')
    params = b.creados[0][0]['params']
    assert 'temperature' not in params and 'thinking' not in params


def test_se_coge_el_bloque_de_texto_no_el_primero():
    """Con adaptive thinking los bloques de pensamiento van delante."""
    fila = _Fila('AAPL', 'succeeded', 'la respuesta')
    fila.result.message.content.insert(0, types.SimpleNamespace(type='thinking'))
    _preparar([fila])
    assert lote_fn([PETS[0]], model='claude-sonnet-5')['AAPL'] == 'la respuesta'


# ── Ids que la API acepta ─────────────────────────────────────────────────

class TestIdsDeLaApi:
    """El `custom_id` de la Batch API es `^[a-zA-Z0-9_-]{1,64}$` — sin puntos.
    Y aquí los ids son tickers, que los llevan en cuanto salen de EEUU. UN solo
    id con punto hace que la API rechace el LOTE ENTERO: el respaldo lo salva,
    pero se paga el precio completo de todo sin que nadie sepa por qué."""

    def test_los_tickers_con_punto_viajan_saneados(self):
        b = _preparar([_Fila('SAP-DE', 'succeeded', 'ok')])
        r = lote_fn([Peticion('SAP.DE', [{'role': 'user', 'content': 'a'}])],
                    model='claude-sonnet-5')
        assert b.creados[0][0]['custom_id'] == 'SAP-DE'
        # y la respuesta vuelve con el id de quien llamó, no con el de la API
        assert r == {'SAP.DE': 'ok'}

    def test_dos_ids_que_se_sanean_igual_no_se_pisan(self):
        b = _preparar([_Fila('SAP-DE', 'succeeded', 'del punto'),
                       _Fila('SAP-DE-2', 'succeeded', 'del guion')])
        r = lote_fn([Peticion('SAP.DE', [{'role': 'user', 'content': 'a'}]),
                     Peticion('SAP-DE', [{'role': 'user', 'content': 'b'}])],
                    model='claude-sonnet-5')
        enviados = [x['custom_id'] for x in b.creados[0]]
        assert len(set(enviados)) == 2, 'dos peticiones no pueden compartir custom_id'
        assert r == {'SAP.DE': 'del punto', 'SAP-DE': 'del guion'}

    def test_un_id_ya_valido_no_se_toca(self):
        b = _preparar([_Fila('BRK-B', 'succeeded', 'ok')])
        lote_fn([Peticion('BRK-B', [{'role': 'user', 'content': 'a'}])],
                model='claude-sonnet-5')
        assert b.creados[0][0]['custom_id'] == 'BRK-B'
