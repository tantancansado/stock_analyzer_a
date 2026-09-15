"""Una señal por ticker mientras la anterior siga viva.

El problema
───────────
El detector no tenía memoria: cada día volvía a emitir el mismo ticker mientras
seguía cayendo. Medido sobre el tracker (ago-sep 2026), 69 señales de
MEAN_REVERSION eran en realidad 26 tickers:

    HRI      7 veces   26-ago → 07-sep   158 → 156 → 157 → 151 → 152 → 138 → 139
    7741.T   5 veces   01-sep → 08-sep   24600 → 24420 → 24460 → 24140 → 24145
    KD       7 veces   25-ago → 14-sep

Eso no son siete oportunidades: es la misma acción cayendo, señalada siete
veces. Y tiene dos efectos, los dos malos:

  1. La app presenta como diez oportunidades lo que son cuatro empresas.
  2. El tracker cuenta la misma apuesta perdedora una vez por señal, así que
     las estadísticas del sistema se hunden con las repeticiones. Deduplicando
     por ticker, el acierto a 7d de MEAN_REVERSION sube del 33% al 45%.

Ya existía un dedup en `bounce_alerts.py`, pero vive en la capa de AVISOS y no
llega ni al CSV que lee la app ni al tracker — el mismo patrón que el veto de
catalizador. Este actúa en el detector, que es donde se decide qué es una
señal.

Cuándo se considera cerrada
───────────────────────────
Una señal deja de estar abierta cuando pasa cualquiera de las tres:

  - el precio toca el objetivo  → salió bien, el ticker puede volver a señalar
  - el precio toca el stop      → salió mal, ídem
  - se agota el horizonte       → 30 días, que es el plazo al que se MIDE esta
                                  familia (`horizontes.CORTO_PRINCIPAL`)

Lo que NO se hace es expirarla porque haya pasado un día. Un ticker que sigue
cayendo dentro de su rango sigue siendo la misma apuesta, no una nueva.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

ESTADO = Path(__file__).parent / 'docs' / 'senales_abiertas.json'

# Días que una señal se considera viva si no ha tocado objetivo ni stop. Es el
# horizonte al que se mide esta familia; pasado eso, el resultado ya está
# registrado y el ticker vuelve a estar disponible.
HORIZONTE_DIAS = 30


def _leer() -> dict[str, Any]:
    try:
        return json.loads(ESTADO.read_text()) if ESTADO.exists() else {}
    except Exception:
        return {}


def _escribir(d: dict[str, Any]) -> None:
    try:
        ESTADO.parent.mkdir(parents=True, exist_ok=True)
        ESTADO.write_text(json.dumps(d, indent=2, sort_keys=True))
    except Exception as e:                                    # noqa: BLE001
        print(f'  No se pudo guardar {ESTADO.name}: {e}')


def _clave(estrategia: str, ticker: str) -> str:
    return f'{estrategia}:{ticker.upper()}'


def _cerrada(sig: dict, precio: float | None, hoy: date) -> str | None:
    """Motivo por el que la señal ya no está abierta, o None si sigue viva."""
    try:
        desde = date.fromisoformat(sig['desde'])
    except Exception:
        return 'fecha ilegible'
    if (hoy - desde).days >= HORIZONTE_DIAS:
        return f'horizonte de {HORIZONTE_DIAS}d agotado'
    if precio is None:
        return None
    obj, stop = sig.get('objetivo'), sig.get('stop')
    if obj is not None and precio >= float(obj):
        return 'objetivo alcanzado'
    if stop is not None and precio <= float(stop):
        return 'stop alcanzado'
    return None


def esta_abierta(estrategia: str, ticker: str, precio: float | None = None,
                 hoy: date | None = None) -> bool:
    """¿Hay ya una señal viva para este ticker en esta estrategia?

    Si la hay pero ya tocó objetivo, stop u horizonte, se cierra aquí mismo y
    devuelve False: el ticker vuelve a estar disponible.
    """
    hoy = hoy or date.today()
    d = _leer()
    sig = d.get(_clave(estrategia, ticker))
    if not sig:
        return False
    motivo = _cerrada(sig, precio, hoy)
    if motivo is None:
        return True
    d.pop(_clave(estrategia, ticker), None)
    _escribir(d)
    print(f'   ↩︎  {ticker}: señal anterior cerrada ({motivo}) — vuelve a estar disponible')
    return False


def registrar(estrategia: str, ticker: str, precio: float,
              objetivo: float | None = None, stop: float | None = None,
              hoy: date | None = None) -> None:
    d = _leer()
    d[_clave(estrategia, ticker)] = {
        'desde': (hoy or date.today()).isoformat(),
        'precio': precio,
        'objetivo': objetivo,
        'stop': stop,
    }
    _escribir(d)


def filtrar(setups: list[dict], estrategia: str, hoy: date | None = None) -> tuple[list[dict], list[str]]:
    """Quita los setups cuyo ticker ya tiene señal viva. Registra los que pasan.

    Devuelve (los que pasan, tickers omitidos).
    """
    hoy = hoy or date.today()
    pasan, omitidos = [], []
    for s in setups:
        t = str(s.get('ticker', '')).upper()
        if not t:
            continue
        precio = s.get('current_price')
        try:
            precio = float(precio) if precio is not None else None
        except (TypeError, ValueError):
            precio = None
        if esta_abierta(estrategia, t, precio, hoy):
            omitidos.append(t)
            continue
        pasan.append(s)
        registrar(estrategia, t, precio or 0.0,
                  s.get('target'), s.get('stop_loss'), hoy)
    return pasan, omitidos
