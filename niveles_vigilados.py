#!/usr/bin/env python3
"""Niveles de precio que el usuario decide vigilar, con el porqué al lado.

Las alertas que había eran genéricas —objetivo del analista alcanzado, stop del
8%, recuperación— y ninguna responde a la pregunta que se hace de verdad
después de estudiar un valor: «me interesa a 127, avísame si llega».

El 17-sep-2026, tras el estudio de YUM, la decisión fue esperar a 127 porque
ahí coinciden dos cosas independientes: el soporte de 126,49 (aguantó 3 de 4
veces, sin visitar en 20 meses) y la valoración con crecimiento del 6% y coste
de capital del 8% (124 $). Sin un sitio donde anotar eso, la decisión vive en
una conversación y se pierde.

El fichero guarda TAMBIÉN el motivo. Un nivel sin su razón es un número que
dentro de tres meses nadie sabe de dónde salió, y entonces o se ignora o se
obedece sin saber por qué — las dos cosas malas.

Output: docs/niveles_vigilados.json (estado + los que se han tocado hoy)
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

DOCS = Path('docs')
CONFIG = DOCS / 'niveles_vigilados.json'

# Margen para avisar ANTES de que toque el nivel: si esperas a que lo cruce, el
# aviso llega cuando ya hay que decidir con prisa.
MARGEN_AVISO_PCT = 1.5


def _cargar() -> Optional[dict]:
    """El fichero, o None si no se pudo leer.

    None es «no lo sé», no «no hay niveles»: quien lo consuma no debe concluir
    que no hay nada que vigilar porque el fichero esté ilegible.
    """
    if not CONFIG.exists():
        return {'niveles': [], 'generated_at': None}
    try:
        d = json.loads(CONFIG.read_text())
    except Exception:
        return None
    return d if isinstance(d, dict) else None


def revisar(precios: dict[str, float]) -> list[dict]:
    """Qué niveles se han tocado o están a punto, dado un mapa ticker→precio.

    `precios` se pasa desde fuera para que esto sea comprobable sin red.
    """
    datos = _cargar()
    if not datos:
        return []
    out = []
    for n in datos.get('niveles') or []:
        t = str(n.get('ticker', '')).upper()
        nivel = n.get('nivel')
        precio = precios.get(t)
        if not t or nivel is None or precio is None:
            continue
        try:
            nivel, precio = float(nivel), float(precio)
        except (TypeError, ValueError):
            continue
        if nivel <= 0:
            continue

        hacia = str(n.get('direccion', 'abajo')).lower()
        dist = (precio / nivel - 1) * 100
        if hacia == 'abajo':
            tocado = precio <= nivel
            cerca = 0 < dist <= MARGEN_AVISO_PCT
        else:
            tocado = precio >= nivel
            cerca = -MARGEN_AVISO_PCT <= dist < 0

        if not (tocado or cerca):
            continue
        out.append({
            'ticker': t,
            'nivel': round(nivel, 2),
            'precio': round(precio, 2),
            'distancia_pct': round(dist, 2),
            'estado': 'TOCADO' if tocado else 'CERCA',
            'direccion': hacia,
            'motivo': n.get('motivo'),
            'decidido_el': n.get('decidido_el'),
            'accion': n.get('accion'),
        })
    return out


def frase(aviso: dict) -> str:
    """Una línea para Telegram, con el motivo delante del número.

    El motivo va primero a propósito: cuando llegue el aviso, lo que hay que
    recordar no es el precio —ese se ve en cualquier sitio— sino por qué se
    eligió ese precio y no otro.
    """
    verbo = 'ha llegado a' if aviso['estado'] == 'TOCADO' else 'está a un paso de'
    motivo = f" — {aviso['motivo']}" if aviso.get('motivo') else ''
    accion = f"\n   Lo que decidiste: {aviso['accion']}" if aviso.get('accion') else ''
    fecha = f" (decidido el {aviso['decidido_el']})" if aviso.get('decidido_el') else ''
    return (f"{aviso['ticker']} {verbo} {aviso['nivel']:.2f} "
            f"(ahora {aviso['precio']:.2f}){motivo}{fecha}{accion}")


def anadir(ticker: str, nivel: float, motivo: str, accion: str = '',
           direccion: str = 'abajo') -> None:
    """Añade o actualiza un nivel. Un ticker puede tener varios."""
    datos = _cargar()
    if datos is None:
        raise RuntimeError('niveles_vigilados.json ilegible: no se sobrescribe')
    niveles = [n for n in (datos.get('niveles') or [])
               if not (str(n.get('ticker', '')).upper() == ticker.upper()
                       and abs(float(n.get('nivel', 0)) - nivel) < 0.01)]
    niveles.append({
        'ticker': ticker.upper(),
        'nivel': round(float(nivel), 2),
        'direccion': direccion,
        'motivo': motivo,
        'accion': accion,
        'decidido_el': date.today().isoformat(),
    })
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(
        {'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
         'niveles': niveles}, indent=2, ensure_ascii=False))


def main() -> int:
    import yfinance as yf
    datos = _cargar()
    if datos is None:
        print('[fatal] niveles_vigilados.json ilegible — no se publica nada')
        return 1
    niveles = datos.get('niveles') or []
    if not niveles:
        print('[info] no hay niveles vigilados')
        return 0

    precios: dict[str, float] = {}
    for t in sorted({str(n.get('ticker', '')).upper() for n in niveles if n.get('ticker')}):
        try:
            i = yf.Ticker(t).info
            p = i.get('currentPrice') or i.get('regularMarketPrice')
            if p:
                precios[t] = float(p)
        except Exception as exc:
            print(f'  [warn] {t}: sin precio ({exc})')

    avisos = revisar(precios)
    print(f'Niveles vigilados: {len(niveles)} · precios leídos: {len(precios)} · '
          f'avisos: {len(avisos)}')
    for a in avisos:
        print(f'  🔔 {frase(a)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
