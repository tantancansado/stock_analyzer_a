#!/usr/bin/env python3
"""El watchdog lee pipeline_health.json, que es una FOTO del momento del
pipeline. Si el dato se arregla después, el informe sigue diciendo lo de la
madrugada y el aviso sale igual.

El 22-sep-2026 llegaron dos avisos —uno rojo— por «entry_readiness viene
vacía» en Europa, cuatro horas después de que esa columna estuviera rellena.
Avisar de algo ya resuelto gasta la confianza en el resto de avisos, que es
lo único que los hace útiles.
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import data_freshness_watchdog as w


def _csv(tmp_path, nombre, cabecera, filas):
    p = tmp_path / nombre
    p.write_text(cabecera + "\n" + "\n".join(filas) + "\n")
    return str(p)


class TestRevalidaAntesDeAvisar:

    def test_columna_ya_rellena_no_avisa(self, tmp_path):
        ruta = _csv(tmp_path, "eu.csv", "ticker,entry_readiness",
                    ["SAP.DE,ENTRADA", "AIR.PA,ESPERAR"])
        assert w._ya_esta_poblada(ruta, "entry_readiness") is True

    def test_varias_columnas_todas_tienen_que_estar(self, tmp_path):
        ruta = _csv(tmp_path, "eu.csv", "ticker,entry_readiness,rr_operativo",
                    ["SAP.DE,ENTRADA,", "AIR.PA,ESPERAR,"])
        # rr_operativo sigue vacía: el aviso debe salir.
        assert w._ya_esta_poblada(ruta, "entry_readiness, rr_operativo") is False

    def test_columna_vacia_sigue_avisando(self, tmp_path):
        ruta = _csv(tmp_path, "eu.csv", "ticker,entry_readiness",
                    ["SAP.DE,", "AIR.PA,"])
        assert w._ya_esta_poblada(ruta, "entry_readiness") is False

    def test_ante_la_duda_avisa(self, tmp_path):
        """Sin path, sin fichero o con un formato que no sabe leer, el aviso
        sale: es un vigilante, no un filtro."""
        assert w._ya_esta_poblada(None, "entry_readiness") is False
        assert w._ya_esta_poblada(str(tmp_path / "no_existe.csv"), "x") is False
        assert w._ya_esta_poblada("docs/algo.json", "x") is False


class TestCeroNoEsLoMismoQueNoHaberCorrido:
    """mean reversion y los rebotes pasan semanas sin emitir, y eso es lo
    esperado. El aviso decía «un paso de la cadena no llegó a correr» de un
    escáner que había corrido a las 05:58 y devuelto cero en sus dos
    estrategias."""

    @staticmethod
    def _json(tmp_path, datos):
        p = tmp_path / "mr.json"
        p.write_text(json.dumps(datos))
        return str(p)

    def test_corrio_hoy_y_dio_cero_no_es_un_fallo(self, tmp_path):
        ahora = datetime.now(timezone.utc).isoformat()
        ruta = self._json(tmp_path, {"generated_at": ahora, "total_opportunities": 0})
        assert w._corrio_y_no_encontro(ruta) is True

    def test_fichero_viejo_si_avisa(self, tmp_path):
        viejo = (datetime.now(timezone.utc) - timedelta(days=4)).isoformat()
        ruta = self._json(tmp_path, {"generated_at": viejo, "total_opportunities": 0})
        assert w._corrio_y_no_encontro(ruta) is False

    def test_sin_contador_no_se_da_por_bueno(self, tmp_path):
        """La ausencia de contador no es una afirmación de cero."""
        ahora = datetime.now(timezone.utc).isoformat()
        ruta = self._json(tmp_path, {"generated_at": ahora})
        assert w._corrio_y_no_encontro(ruta) is False

    def test_con_resultados_no_aplica(self, tmp_path):
        ahora = datetime.now(timezone.utc).isoformat()
        ruta = self._json(tmp_path, {"generated_at": ahora, "total_opportunities": 5})
        assert w._corrio_y_no_encontro(ruta) is False


class TestElHealthLlevaElPath:
    """La revalidación necesita saber qué fichero mirar, y eso lo pone el
    pipeline al escribir el informe."""

    def test_el_workflow_guarda_el_path(self):
        from pathlib import Path
        yml = Path(__file__).resolve().parents[1] / ".github/workflows/daily-analysis.yml"
        texto = yml.read_text()
        assert "'path': path" in texto, (
            "sin el path en el health, el watchdog no puede volver a mirar el "
            "fichero y repite el diagnóstico de la madrugada")
