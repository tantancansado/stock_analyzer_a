"""
Los rebotes técnicos, revisados a fondo el 16-sep-2026.

Ese día el CSV publicaba 12 setups y NINGUNO cuadraba consigo mismo. No por un
fallo: por tres decisiones que por separado parecían razonables.

1. Dos objetivos, uno publicado y otro usado. `target` era la resistencia (HEI:
   354,72, +19,5%) y el `risk_reward` se calculaba contra el objetivo de rebote
   (+7% fijo). La app, el tracker y Telegram leen `target`. Resultado: HEI decía
   «objetivo +19,5%, R:R 3,21» y ese 3,21 correspondía a +7,0%. 0 de 12 fichas
   cuadraban.

2. La zona de entrada no era la operación. Stop, objetivo y R:R se calculaban
   desde `current_price` mientras la ficha decía «entra entre X e Y». HEI
   cotizaba a 296,85 con la zona en 299,38-311,60 —por ENCIMA del precio, porque
   el soporte del que colgaba ya estaba roto—. Siguiendo la instrucción el R:R
   real era 0,28, no 3,21.

3. El veredicto del filtro IA no ataba nada. Diez de los doce lo tenían en
   contra y salían igual; los dos primeros de la lista, marcados
   «⭐⭐⭐ EXCELENTE», eran dos de los rechazados.
"""
import pytest

from mean_reversion_detector import MeanReversionDetector, setup_coherente


def test_el_rr_tiene_que_salir_del_objetivo_que_se_publica():
    """La forma exacta de HEI el 16-sep, con la entrada al precio para aislar
    el fallo: objetivo publicado 354,72 (+19,5%) y R:R 3,21, que es el que sale
    del objetivo de rebote, 317,63 (+7,0%). Dos números correctos por separado
    que juntos mienten."""
    ok, motivo = setup_coherente({
        'ticker': 'HEI', 'current_price': 296.85, 'entry_ref': 296.85,
        'target': 354.72, 'bounce_target': 317.63, 'techo_tecnico': 354.72,
        'stop_loss': 290.38, 'risk_reward': 3.21,
    })
    assert not ok and 'R:R' in motivo, \
        'un R:R calculado contra un objetivo distinto del publicado debe frenarse'


def test_la_zona_de_entrada_tiene_que_ser_alcanzable():
    """HEI pedía entrar entre 299,38 y 311,60 cotizando a 296,85: el soporte
    del que colgaba la zona ya estaba roto. Aquí los números son coherentes
    entre sí —el R:R sale de su propio objetivo y supera el mínimo— y aun así
    el setup no vale, porque manda comprar a un precio que hoy no existe."""
    ok, motivo = setup_coherente({
        'ticker': 'HEI', 'current_price': 296.85, 'entry_ref': 311.60,
        'target': 333.41, 'bounce_target': 333.41, 'techo_tecnico': 354.72,
        'stop_loss': 290.38, 'risk_reward': 1.03,
    })
    assert not ok and 'alcanzable' in motivo, \
        'una zona de entrada un 5% por encima del precio no es una zona de entrada'


def test_el_techo_tecnico_no_puede_quedar_por_debajo_del_objetivo():
    s = {'current_price': 100.0, 'entry_ref': 100.0, 'target': 107.0,
         'techo_tecnico': 104.0, 'bounce_target': 107.0, 'stop_loss': 95.0,
         'risk_reward': 1.4}
    ok, motivo = setup_coherente(s)
    assert not ok and 'techo' in motivo


def test_un_setup_bien_formado_pasa():
    s = {'current_price': 100.0, 'entry_ref': 100.0, 'target': 107.0,
         'techo_tecnico': 112.0, 'bounce_target': 107.0, 'stop_loss': 95.0,
         'risk_reward': 1.4}
    ok, motivo = setup_coherente(s)
    assert ok, motivo


# ── El veredicto del gate manda ──────────────────────────────────────────────

def test_lo_rechazado_por_la_ia_no_se_publica():
    det = MeanReversionDetector()
    salida = det._aplicar_veredicto_ia([
        {'ticker': 'FDS', 'reversion_score': 85, 'ai_confirmation': 'NO',
         'ai_reason': 'RSI 41,6 no es sobreventa'},
        {'ticker': 'HEI', 'reversion_score': 80, 'ai_confirmation': 'YES'},
    ])
    assert [o['ticker'] for o in salida] == ['HEI']


@pytest.mark.parametrize('veredicto', ['CAUTION', None])
def test_sin_un_si_claro_nunca_se_etiqueta_excelente(veredicto):
    """`reversion_score` mide si el patrón está bien formado, no si es operable
    hoy. Mezclar las dos cosas en una etiqueta hacía que la misma fila dijera
    «EXCELENTE» y «NO» a la vez."""
    det = MeanReversionDetector()
    etiqueta = det._etiqueta_calidad(95, veredicto)
    assert 'EXCELENTE' not in etiqueta and 'MUY BUENA' not in etiqueta, etiqueta


def test_sin_gate_la_ficha_lo_dice():
    """Un hueco silencioso se lee como aprobación."""
    assert MeanReversionDetector()._etiqueta_calidad(95, None) == 'SIN VERIFICAR'


# ── El bull flag no se juzga con la vara del oversold ────────────────────────

def test_el_gate_no_exige_sobreventa_a_un_bull_flag():
    """Un Bull Flag Pullback es un retroceso SUAVE en tendencia alcista: no
    tiene ni puede tener RSI<25. La regla anterior («en corrección, solo YES si
    RSI<25») rechazaba el 100% de los bull flags por no ser algo que no
    pretenden ser — los 8 del 16-sep, todos con el mismo motivo literal.
    """
    import inspect
    fuente = inspect.getsource(MeanReversionDetector._ai_filter_batch)
    prompt = fuente[fuente.index('prompt = f"""'):]
    assert 'penalices un RSI>25 en esta estrategia' in prompt
    assert 'Oversold Bounce' in prompt and 'Bull Flag Pullback' in prompt
    # El motivo tiene que citar un número: «R:R bajo» salía en fichas con R:R 11,9
    assert 'DEBE citar un número concreto' in prompt
