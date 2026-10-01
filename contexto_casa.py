"""Lo que la app ya sabe de un ticker y un modelo no puede saber solo.

La causa de una caída se investiga una vez (why_cheap, con búsqueda web) y el
estado de entrada sale del motor técnico. Los textos que Claude escribe sobre
el mismo ticker —tesis de Value, veredicto de LEAPS— no los veían y
conjeturaban: el 1-oct-2026 Claude llamó "cíclica" a la caída de MCD cuando la
casa ya tenía "EVENTO — Investor Day". Pasárselos al prompt no añade llamadas.
"""
from __future__ import annotations


def _texto(v) -> str | None:
    """Un campo de CSV vacío llega como NaN (un float, y verdadero): se descarta."""
    if isinstance(v, str) and v.strip() and v.strip().lower() != 'nan':
        return v.strip()
    return None


def contexto_para_prompt(d: dict) -> str:
    """Causa de la caída y estado de entrada de un ticker, en líneas para un prompt."""
    lineas = []
    causa, resumen = _texto(d.get('why_cheap')), _texto(d.get('why_cheap_resumen'))
    if causa and causa != 'SIN_DATOS':
        lineas.append(f"  Por qué ha caído (investigado con búsqueda web, es el dato bueno): "
                      f"{causa}" + (f" — {resumen}" if resumen else ''))
    else:
        lineas.append("  Por qué ha caído: la casa no lo ha investigado — dilo, no lo supongas.")
    estado, motivo = _texto(d.get('entry_readiness')), _texto(d.get('entry_readiness_reason'))
    if estado:
        lineas.append(f"  Estado de entrada de la ACCIÓN (el que enseña la ficha): {estado}"
                      + (f" — {motivo}" if motivo else ''))
    return '\n'.join(lineas)
