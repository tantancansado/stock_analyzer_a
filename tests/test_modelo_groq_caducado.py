"""Un nombre de modelo caduca sin avisar, y la cadena de respaldo no servía.

17-sep-2026: `qwen/qwen3.6-27b` dejó de existir en Groq y cada llamada
devolvía 404 model_not_found. `groq_chat` trataba eso como «error que no es
rate-limit» y lo propagaba de inmediato, SIN probar el siguiente modelo de la
cadena — justo en el caso para el que la cadena existe.

Efecto: el gate europeo no pudo verificar ninguno de los 32 picks. Como es
fail-closed por diseño, «no pude verificar» es exclusión, así que
`european_value_opportunities_filtered.csv` se publicó con la cabecera y nada
más. La página europea, vacía.

El sistema lo dijo con todas las letras:

    🔌 25 NO EVALUADOS (sin saldo o fallo de API), no rechazados
       No es lo mismo: un rechazo es el gate funcionando, esto es una avería.

Y nadie lo leyó, porque el health vigilaba el CRUDO europeo (32 filas, tan
ancho como siempre) y no el filtrado.
"""
import groq_utils as g

# Sin stub de `groq`: el módulo solo se importa dentro de las funciones que
# llaman a la API, así que `groq_utils` se importa igual sin el paquete. Un
# stub vacío en sys.modules rompía a otro test que sí hace `from groq import
# Groq`.


class _Err(Exception):
    pass


E404 = _Err("Error code: 404 - {'error': {'message': 'The model "
            "`qwen/qwen3.6-27b` does not exist or you do not have access to "
            "it.', 'type': 'invalid_request_error', 'code': 'model_not_found'}}")
E429 = _Err('Error code: 429 - rate_limit_exceeded')
E500 = _Err('Error code: 500 - internal server error')


class TestQueSeDistingue:
    def test_el_404_de_modelo_se_reconoce(self):
        assert g._es_modelo_inexistente(E404)

    def test_un_rate_limit_no_es_modelo_caducado(self):
        """Ante un 429 tiene sentido esperar y reintentar con el mismo modelo;
        ante un 404 no, hay que saltar ya. Mezclarlos fue el fallo."""
        assert not g._es_modelo_inexistente(E429)
        assert g._is_rate_limit(E429)

    def test_un_error_cualquiera_sigue_propagándose(self):
        """No se convierte en un cajón de sastre que se traga fallos reales."""
        assert not g._es_modelo_inexistente(E500)
        assert not g._is_rate_limit(E500)


def test_el_404_salta_al_siguiente_modelo_en_el_bucle():
    from pathlib import Path
    src = Path(g.__file__).read_text()
    i = src.index('if _is_rate_limit(exc):')
    bloque = src[i:i + 1200]
    assert '_es_modelo_inexistente' in bloque, \
        'un modelo caducado vuelve a propagarse sin probar el respaldo'
    # y antes del `raise` final, no después
    assert bloque.index('_es_modelo_inexistente') < bloque.index('raise  #')


def test_los_nombres_de_modelo_son_de_los_que_groq_sirve_hoy():
    """Comprobación de cordura: el que estaba escrito ya no existía."""
    caducados = {'qwen/qwen3.6-27b', 'qwen/qwen3-32b', 'llama-3.3-70b-versatile'}
    usados = {g.SCOUT_PRIMARY, g.PRIMARY_MODEL, *g.FALLBACK_MODELS, *g.SCOUT_FALLBACK}
    assert not (usados & caducados), f'modelos retirados por Groq: {usados & caducados}'


def test_la_lista_europea_publicada_se_vigila():
    """El health miraba el crudo (32 filas) y no el filtrado (vacío)."""
    from pathlib import Path
    yml = (Path(__file__).resolve().parent.parent / '.github' / 'workflows'
           / 'daily-analysis.yml').read_text()
    i = yml.index('MODULES = {')
    bloque = yml[i:yml.index('COLUMNA_REQUERIDA', i)]
    assert 'european_value_opportunities_filtered.csv' in bloque, \
        'se vigila el crudo europeo pero no lo que se publica'
