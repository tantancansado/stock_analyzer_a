"""
El token de TIKR caducaba a mitad de la pasada semanal.

Cognito da un token de ~1 h y la pasada tarda ~1,5 h. Del minuto 60 en adelante
cada /tf y cada /est devolvian 503: en la pasada del 27-sep 75 de 143 tickers
salieron sin cuentas, y ADSK, AMZN, MANH, META y RMD no las habian tenido nunca
porque, al no haber nada previo que conservar, el arrastre de semanas anteriores
no podia rescatarlos. Meses de cobertura entre el 47% y el 81% venian de aqui.

El token se pide una vez al principio; hay que renovarlo antes de que caduque.
"""
import textwrap
from pathlib import Path

from conftest import bloque_de_codigo

RAIZ = Path(__file__).resolve().parent.parent
SRC = (RAIZ / 'tikr_scraper.py').read_text()


def _helper(get_fresh_token):
    """`_token_vigente` ejecutada sola: tikr_scraper no se importa aqui porque
    depende de `pycognito`, que solo esta en el runner."""
    bloque = bloque_de_codigo(SRC, 'TOKEN_MAX_EDAD = ', '# ── Session')
    ns = {'time': __import__('time'), 'Optional': __import__('typing').Optional,
          'get_fresh_token': get_fresh_token}
    exec(textwrap.dedent(bloque), ns)
    return ns['_token_vigente'], ns['TOKEN_MAX_EDAD']


def test_un_token_reciente_no_se_toca():
    llamadas = []
    vigente, _ = _helper(lambda: llamadas.append(1) or 'nuevo')
    assert vigente('viejo', emitido=1000.0, ahora=1000.0 + 60) == ('viejo', 1000.0)
    assert not llamadas


def test_un_token_de_40_minutos_se_renueva():
    vigente, max_edad = _helper(lambda: 'nuevo')
    t0 = 5000.0
    token, emitido = vigente('viejo', emitido=t0, ahora=t0 + max_edad)
    assert token == 'nuevo'
    assert emitido == t0 + max_edad


def test_se_renueva_con_margen_antes_de_la_hora_de_vida():
    _, max_edad = _helper(lambda: 'x')
    assert max_edad <= 45 * 60, 'el token dura ~1 h; renovar a los 60 min llega tarde'


def test_si_la_renovacion_falla_sigue_con_el_viejo_y_lo_dice(capsys):
    def falla():
        raise RuntimeError('cognito caido')
    vigente, max_edad = _helper(falla)
    t0 = 100.0
    assert vigente('viejo', emitido=t0, ahora=t0 + max_edad + 1) == ('viejo', t0)
    assert 'cognito caido' in capsys.readouterr().out


def test_el_token_fallido_se_reintenta_en_la_siguiente_vuelta():
    """Si falla, `emitido` no se toca: la siguiente iteracion vuelve a intentarlo
    en vez de esperar otros 40 minutos con un token ya caducado."""
    intentos = []
    def falla_y_luego_va():
        intentos.append(1)
        if len(intentos) == 1:
            raise RuntimeError('503')
        return 'nuevo'
    vigente, max_edad = _helper(falla_y_luego_va)
    t0 = 0.0
    token, emitido = vigente('viejo', t0, ahora=max_edad + 1)
    token, emitido = vigente(token, emitido, ahora=max_edad + 30)
    assert token == 'nuevo'


def test_run_renueva_en_las_dos_fases_largas():
    fase1 = bloque_de_codigo(SRC, 'Fase 1/4', 'Fase 2/4')
    fase3 = bloque_de_codigo(SRC, 'Fase 3/4', '_save_output(results, errors)\n    print(f"\\nCompletado')
    for nombre, f in (('fase 1', fase1), ('fase 3', fase3)):
        assert 'token, token_emitido = _token_vigente(token, token_emitido)' in f, \
            f'{nombre}: el bucle no renueva el token'
