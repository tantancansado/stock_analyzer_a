"""164 tickers publicados como «SIN_DATOS» por un parámetro que faltaba.

El 18-sep-2026 el pipeline entero salió sin veredictos de Claude: GOOG, META,
LMT, GGG, AUTO.L en el scoring, y SYY, GS y ADSK en los rebotes — todos con
«SIN_DATOS · 0 fuentes» y un 400 invalid_request_error detrás.

La causa, en la documentación de la herramienta: desde `web_search_20260209`,
`allowed_callers` vale por defecto `['code_execution_20260120']`, o sea que la
búsqueda corre dentro de la ejecución de código (filtrado dinámico) en vez de
llamarse directamente. Textualmente: «Models that don't support programmatic
tool calling require this setting. Without it, the API returns a 400 error
that tells you to set it.»

Y aunque no diera 400 seguiría sin servir: con filtrado dinámico los
resultados llegan ANIDADOS dentro de los bloques de la ejecución de código, y
`_extract` solo mira los de primer nivel. De ahí el «0 fuentes».

Lo que convirtió un fallo de configuración en un día perdido:

1. `ask_with_search` devuelve '' ante CUALQUIER excepción, y quien llama lo
   trata como «este ticker no tiene datos» — indistinguible de una empresa
   sin noticias. El pipeline terminó en verde.
2. El mensaje se cortaba a 80 caracteres, y un 400 gasta los primeros ochenta
   en la envoltura: el log repetía «Error code: 400 - {'type': 'error',
   'error': {'type': 'invalid_request_error', ')» sin llegar al motivo.
"""
import claude_research as cr


class TestLaHerramienta:
    def test_la_busqueda_se_llama_directamente(self):
        assert cr.WEB_SEARCH_TOOL.get('allowed_callers') == ['direct']

    def test_el_motivo_queda_escrito_junto_al_parametro(self):
        """Sin el porqué, el siguiente que lo vea lo quita por parecer de más."""
        fuente = open(cr.__file__).read()
        from conftest import cabecera_de
        cabecera = cabecera_de(fuente, 'WEB_SEARCH_TOOL = ')
        assert 'allowed_callers' in cabecera
        assert '400' in cabecera


class TestElErrorSeLee:
    def test_saca_el_tipo_y_el_motivo_de_un_400(self):
        e = Exception("Error code: 400 - {'type': 'error', 'error': "
                      "{'type': 'invalid_request_error', 'message': "
                      "'web search requires allowed_callers'}}")
        r = cr._resumen_error(e)
        assert 'invalid_request_error' in r
        assert 'allowed_callers' in r, 'el motivo es lo único que sirve para arreglar'

    def test_un_error_sin_formato_conocido_no_se_pierde(self):
        assert 'boom' in cr._resumen_error(Exception('boom'))


class TestFalloSistematico:
    def setup_method(self):
        cr._FALLOS.clear()
        cr._AVISADO.clear()

    def test_un_fallo_suelto_no_alarma(self):
        cr._anotar_fallo(Exception('timeout'))
        assert cr.fallos_sistematicos() == {}

    def test_el_mismo_error_repetido_sí(self):
        """Un 400 no es «este ticker no tiene datos»: falla para todos."""
        e = Exception("Error code: 400 - {'type': 'error', 'error': "
                      "{'type': 'invalid_request_error', 'message': 'x'}}")
        for _ in range(cr.FALLOS_PARA_SOSPECHAR):
            cr._anotar_fallo(e)
        assert cr.fallos_sistematicos(), 'cinco iguales seguidos no es casualidad'

    def test_errores_distintos_no_se_suman_entre_si(self):
        for i in range(cr.FALLOS_PARA_SOSPECHAR):
            cr._anotar_fallo(Exception(f'fallo distinto {i}'))
        assert cr.fallos_sistematicos() == {}

    def test_solo_avisa_una_vez_por_error(self, capsys):
        e = Exception('mismo error')
        for _ in range(cr.FALLOS_PARA_SOSPECHAR * 3):
            cr._anotar_fallo(e)
        salida = capsys.readouterr().out
        assert salida.count('llamadas seguidas fallando') == 1
