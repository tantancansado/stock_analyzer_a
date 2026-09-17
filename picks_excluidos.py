#!/usr/bin/env python3
"""Quién se quedó fuera de la lista publicada, y por qué.

El 17-sep-2026 Broadridge desapareció de VALUE con el segundo mejor score de
toda la lista (87,8), y con ella otros diez. Para averiguar por qué hubo que
bajarse el log de GitHub Actions y leerlo a mano: el CSV publicado no deja
rastro de lo que NO contiene, así que «lo echamos por un dato incoherente» y
«nunca estuvo» se ven exactamente igual.

Los dos guards que preceden a la publicación —rangos imposibles
(`data_integrity`) y coherencia de la ficha (`ai_pick_verifier`)— sí saben el
motivo en el momento de echar a cada uno. Solo que lo imprimían y lo perdían.
Aquí se guarda, para que el aviso de desaparecidos pueda decir la causa y para
que el watchdog pueda avisar sin que nadie tenga que preguntar.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

RUTA = Path('docs/picks_excluidos.json')


def registrar(lista: str, excluidos: list[dict], *,
              candidatas: int, publicadas: int, ruta: Optional[Path] = None) -> None:
    """Apunta quién se quedó fuera de `lista` en esta ejecución.

    Cada excluido: {'ticker', 'paso', 'motivo', 'score'}. Se reescribe la
    entrada de esa lista y se respetan las demás: value y momentum se publican
    en llamadas distintas y una no debe borrar a la otra.
    """
    ruta = ruta or RUTA
    datos: dict[str, Any] = {'listas': {}}
    if ruta.exists():
        try:
            previo = json.loads(ruta.read_text())
            if isinstance(previo, dict) and isinstance(previo.get('listas'), dict):
                datos = previo
        except Exception:
            pass   # ilegible: se empieza de cero, pero nunca se calla el registro nuevo

    datos['generated_at'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    datos['listas'][lista] = {
        'candidatas': candidatas,
        'publicadas': publicadas,
        'excluidos': excluidos,
    }
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, indent=2, ensure_ascii=False, default=str))


def leer(ruta: Optional[Path] = None) -> Optional[dict]:
    """El registro, o None si no se pudo leer.

    None es «no lo sé», no «no hubo excluidos»: quien lo consuma no debe
    concluir que la lista salió entera.
    """
    ruta = ruta or RUTA
    if not ruta.exists():
        return None
    try:
        datos = json.loads(ruta.read_text())
    except Exception:
        return None
    return datos if isinstance(datos, dict) else None


def motivo_de(ticker: str, ruta: Optional[Path] = None) -> Optional[dict]:
    """{'paso', 'motivo', 'lista', ...} del ticker, o None si no consta."""
    datos = leer(ruta or RUTA)
    if not datos:
        return None
    for lista, cuerpo in (datos.get('listas') or {}).items():
        for e in (cuerpo or {}).get('excluidos') or []:
            if str(e.get('ticker', '')).upper() == str(ticker).upper():
                return {**e, 'lista': lista}
    return None
