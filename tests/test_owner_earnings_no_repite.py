"""
El paso más caro del pipeline repetía el mismo trabajo seis días de cada siete.

`owner_earnings_validator` tarda 13,5 minutos al día (el 27% de `core-scoring`)
más tokens de Groq. Su entrada es `owner_earnings_batch.json`, que solo cambia
cuando se refresca TIKR — y TIKR es SEMANAL. Medido sobre el histórico de git:

    tikr_earnings_data.json    commits los domingos
    owner_earnings_batch.json  commits los lunes, uno por semana desde julio

Los otros seis días el fichero de entrada es byte a byte el mismo. Así que no es
que el veredicto rara vez cambie: es que **no puede cambiar**. Y se volvía a
preguntar igualmente — comprobado en la ejecución del 15-sep-2026, un día sin
refresco de TIKR: «Owner Earnings AI Validator — success — 13.5 min».

Esto no cachea por ticker ni adivina nada. El validador es determinista respecto
a su entrada: mismo fichero → mismo prompt por ticker → mismo veredicto. Se
compara la huella de la entrada entera, y o es la misma —y la salida anterior ya
es la respuesta— o no lo es y se valida todo.
"""
import json
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.modules.setdefault('groq', types.SimpleNamespace(Groq=object))
import owner_earnings_validator as v  # noqa: E402


@pytest.fixture
def entrada():
    return [{'ticker': 'MCO', 'current_price': 466.98, 'historical_fcf': {'2025': 2575.0}},
            {'ticker': 'CBOE', 'current_price': 267.4, 'historical_fcf': {'2025': 1153.1}}]


def _salida(tmp_path, monkeypatch, **campos):
    f = tmp_path / 'validated.json'
    f.write_text(json.dumps(campos, default=str))
    monkeypatch.setattr(v, 'OUT_JSON', f)
    return f


def test_la_huella_es_estable_para_la_misma_entrada(entrada):
    assert v._huella_entrada(entrada) == v._huella_entrada(list(entrada))


def test_y_cambia_si_cambia_una_cifra(entrada):
    otra = [dict(entrada[0], current_price=470.0), entrada[1]]
    assert v._huella_entrada(entrada) != v._huella_entrada(otra)


def test_con_la_misma_entrada_no_se_revalida(entrada, tmp_path, monkeypatch):
    _salida(tmp_path, monkeypatch, huella_entrada=v._huella_entrada(entrada),
            model=v.MODEL, validated_at=datetime.now(timezone.utc).isoformat())
    assert v._ya_validado(entrada) is not None


def test_si_cambian_las_cuentas_se_revalida_ese_mismo_dia(entrada, tmp_path, monkeypatch):
    """No se espera al lunes: el disparador es el DATO, no el calendario."""
    _salida(tmp_path, monkeypatch, huella_entrada='otra',
            model=v.MODEL, validated_at=datetime.now(timezone.utc).isoformat())
    assert v._ya_validado(entrada) is None


def test_se_revalida_al_pasar_el_plazo(entrada, tmp_path, monkeypatch):
    """Aunque la entrada sea idéntica: por si cambia el criterio del validador."""
    viejo = datetime.now(timezone.utc) - timedelta(days=v.REVALIDAR_CADA_DIAS + 1)
    _salida(tmp_path, monkeypatch, huella_entrada=v._huella_entrada(entrada),
            model=v.MODEL, validated_at=viejo.isoformat())
    assert v._ya_validado(entrada) is None


def test_cambiar_de_modelo_invalida_el_veredicto(entrada, tmp_path, monkeypatch):
    """Otro modelo puede opinar distinto sobre las mismas cifras."""
    _salida(tmp_path, monkeypatch, huella_entrada=v._huella_entrada(entrada),
            model='otro-modelo', validated_at=datetime.now(timezone.utc).isoformat())
    assert v._ya_validado(entrada) is None


def test_sin_salida_previa_se_valida(entrada, tmp_path, monkeypatch):
    monkeypatch.setattr(v, 'OUT_JSON', tmp_path / 'no_existe.json')
    assert v._ya_validado(entrada) is None


def test_la_huella_se_guarda_en_la_salida():
    """Sin guardarla, mañana no hay forma de saber que la validación sobra."""
    import inspect
    fuente = inspect.getsource(v.run)
    assert '"huella_entrada": _huella_entrada(results)' in fuente


def test_se_puede_forzar():
    import inspect
    assert 'forzar' in inspect.signature(v.run).parameters
    assert '--force' in inspect.getsource(v.main)
