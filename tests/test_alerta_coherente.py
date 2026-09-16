"""Ningún aviso sale con números que se contradigan entre sí.

El 16-sep-2026 llegó por Telegram:

    🔬 CBOE [CURADO] $270.44
       Target $308.62 · Stop $253.49 · R:R 1.1

Los tres números eran correctos por separado y el conjunto era falso: ese 1,1
se calculaba contra `bounce_target` (289,37), no contra el objetivo anunciado.
Con el target del mensaje el R:R real era 2,25.

Veintiún scripts de este repo mandan a Telegram y ninguno comprobaba el mensaje
antes de enviarlo. `setup_coherente` valida el dict DENTRO del detector — entre
ese punto y el envío hay un armado de mensaje que puede romper, y rompió, la
correspondencia entre los números.
"""
import pytest

from alerta_coherente import TOLERANCIA_RR, filtrar, revisar


def aviso(**k):
    base = {'ticker': 'TEST', 'price': 100.0, 'target': 110.0, 'stop': 95.0, 'rr': 2.0}
    base.update(k)
    return base


class TestElCasoReal:
    def test_el_aviso_que_llego_se_bloquea(self):
        fallos = revisar({'ticker': 'CBOE', 'price': 270.44, 'target': 308.62,
                          'stop': 253.49, 'rr': 1.1})
        assert fallos, 'este es exactamente el mensaje que no debió salir'
        assert '2.25' in fallos[0], 'el aviso dice cuál era el R:R de verdad'

    def test_el_mismo_aviso_arreglado_pasa(self):
        """Con el objetivo contra el que SÍ se calculó el R:R."""
        assert revisar({'ticker': 'CBOE', 'price': 270.44, 'target': 289.37,
                        'stop': 253.49, 'rr': 1.12}) == []

    def test_BAC_del_mismo_mensaje_estaba_bien(self):
        assert revisar({'ticker': 'BAC', 'price': 59.52, 'target': 61.90,
                        'stop': 58.03, 'rr': 1.6}) == []


class TestCoherenciaDelRR:
    def test_un_RR_que_no_sale_de_sus_numeros_se_caza(self):
        # (130-100)/(100-95) = 6.0, no 2.0
        assert revisar(aviso(target=130.0, rr=2.0))

    def test_el_redondeo_del_mensaje_no_es_un_fallo(self):
        """Los avisos pintan el R:R con un decimal: 1,64 sale como «1.6»."""
        assert revisar(aviso(price=59.52, target=61.90, stop=58.03, rr=1.6)) == []

    def test_la_tolerancia_es_de_redondeo_y_no_de_descuadre(self):
        assert TOLERANCIA_RR < 0.2, 'una tolerancia amplia deja pasar el bug que motivó esto'

    def test_sin_RR_no_se_puede_contradecir(self):
        assert revisar(aviso(rr=None)) == []


class TestAritmeticaImposible:
    def test_objetivo_por_debajo_del_precio(self):
        fallos = revisar(aviso(target=90.0, rr=None))
        assert fallos and 'comprar caro para vender barato' in fallos[0]

    def test_stop_por_encima_del_precio(self):
        assert revisar(aviso(stop=105.0, rr=None))

    def test_sin_precio_no_sale(self):
        assert revisar(aviso(price=None))
        assert revisar(aviso(price=0))
        assert revisar(aviso(price='—'))

    def test_un_NaN_no_se_cuela(self):
        assert revisar(aviso(price=float('nan')))


class TestPrecioRancio:
    def test_un_precio_muy_alejado_del_real_se_caza(self):
        """Un aviso con el precio de hace días propone una operación que ya no
        existe: la entrada, el stop y el objetivo están calculados sobre otro
        punto de partida."""
        assert revisar(aviso(price=100.0), precio_real=115.0)

    def test_el_movimiento_normal_entre_scan_y_envio_no_molesta(self):
        assert revisar(aviso(price=100.0), precio_real=101.5) == []

    def test_sin_precio_real_no_se_comprueba(self):
        assert revisar(aviso()) == []


class TestFiltrar:
    def test_deja_pasar_los_buenos_y_bloquea_los_malos(self):
        ok, problemas = filtrar([
            aviso(ticker='BUENA'),
            aviso(ticker='MALA', target=130.0, rr=2.0),
        ])
        assert [a['ticker'] for a in ok] == ['BUENA']
        assert len(problemas) == 1 and 'MALA' in problemas[0]

    def test_un_aviso_incoherente_no_tumba_a_los_demas(self):
        ok, _ = filtrar([aviso(ticker='A'), aviso(ticker='B', price=None), aviso(ticker='C')])
        assert [a['ticker'] for a in ok] == ['A', 'C']


class TestEnElCaminoDeEnvio:
    """No basta con que la función exista: tiene que estar ANTES del envío."""

    def test_bounce_alerts_revisa_antes_de_mandar(self):
        import inspect
        import bounce_alerts as ba
        src = inspect.getsource(ba.main)
        i_rev = src.find('alerta_coherente')
        i_env = src.find('_send_telegram')
        assert i_rev != -1, 'bounce_alerts no revisa la coherencia'
        assert i_rev < i_env, 'la revisión tiene que ir ANTES del envío'

    def test_bounce_trader_no_propone_una_orden_incoherente(self):
        import sys, types
        sys.modules.setdefault('ib_insync', types.ModuleType('ib_insync'))
        import bounce_trader as bt
        bt.BOT_TOKEN, bt.CHAT_ID = 'x', 'y'
        # Este mensaje lleva botón de EJECUTAR: rechazar es el lado seguro.
        assert bt._tg_confirm_trade(
            {'ticker': 'X', 'entry': 100, 'target': 120, 'stop': 95, 'rr': 1.1}) is False
