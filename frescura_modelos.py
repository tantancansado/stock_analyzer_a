#!/usr/bin/env python3
"""¿Los datos que sirve la app se generaron con el código de ahora?

El 18-sep-2026 pasó tres veces en el mismo día. El pipeline corre de
madrugada, los arreglos entran durante la mañana, y hasta la ejecución
siguiente la app sirve los datos de antes del arreglo sin decirlo:

    ancla del P/E arreglada 12:36   ·  value_opportunities.csv de las 08:06
      → MSFT salía «un 45% cara» cuando con su múltiplo propio sale un 27%
        barata, y cuatro de los ocho LEAPS llevaban el aviso equivocado
    filtro de rebotes puesto 08:08  ·  bounce_setups_broad.json de las 06:01
      → GS y SYY publicados con esperanza negativa; con el código de ahora
        GS pasa (+1,68%) y SYY se descarta (-2,12%)
    DCF de bancos bloqueado         ·  BAC con un objetivo DCF de 28,43

No es un fallo del pipeline: corrió bien y con el código que había. Es que
nadie compara la fecha del dato con la fecha del modelo que lo produce, y un
número viejo se lee exactamente igual que uno nuevo.

Esto lo compara y escribe docs/frescura_modelos.json. El que lo consuma
avisa; aquí no se decide nada ni se borra ningún dato: un dato de ayer sigue
siendo el mejor que hay hasta que el pipeline vuelva a correr.

Uso: python3 frescura_modelos.py        (lo llama el build del frontend)
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

DOCS = Path('docs')
SALIDA = DOCS / 'frescura_modelos.json'

# Qué módulos producen cada dato. Solo los que DECIDEN el número publicado:
# tocar el formato de un print no invalida nada, y meter aquí medio repo
# haría saltar el aviso cada día hasta que se dejara de mirar.
MODELOS: dict[str, dict] = {
    'value': {
        'fichero': 'value_opportunities.csv',
        'etiqueta': 'oportunidades VALUE',
        'modulos': ['fundamental_scorer.py', 'super_score_integrator.py',
                    'financial_cross_check.py', 'value_bands.py',
                    'upside_triangulation.py'],
    },
    'leaps': {
        'fichero': 'leaps_opportunities.json',
        'etiqueta': 'LEAPS',
        'modulos': ['leaps_analyzer.py', 'fundamental_scorer.py',
                    'upside_triangulation.py'],
    },
    'rebotes': {
        'fichero': 'bounce_setups_broad.json',
        'etiqueta': 'rebotes',
        'modulos': ['bounce_scanner_broad.py', 'tasa_base.py'],
    },
    'reversion': {
        'fichero': 'mean_reversion_opportunities.json',
        'etiqueta': 'reversión a la media',
        'modulos': ['mean_reversion_detector.py', 'tasa_base.py'],
    },
    'catalizadores': {
        'fichero': 'catalysts.json',
        'etiqueta': 'calendario de catalizadores',
        'modulos': ['catalyst_scanner.py'],
    },
}


def _ultimo_commit(ruta: str) -> str | None:
    """Fecha ISO del último commit que tocó el fichero, o None."""
    try:
        r = subprocess.run(
            ['git', 'log', '-1', '--format=%cI', '--', ruta],
            capture_output=True, text=True, timeout=20)
    except Exception:
        return None
    s = r.stdout.strip()
    return s or None


def _generado_el(fichero: Path) -> str | None:
    """`generated_at` del fichero de datos. None = no se pudo leer.

    Para un CSV no hay campo, así que se usa la fecha del commit que lo
    escribió: es cuando el pipeline lo publicó. La fecha del sistema de
    ficheros no vale — un `git checkout` la cambia sin que el dato cambie.
    """
    if not fichero.exists():
        return None
    if fichero.suffix == '.json':
        try:
            d = json.loads(fichero.read_text())
            g = d.get('generated_at') if isinstance(d, dict) else None
            if g:
                return g if g.endswith('Z') or '+' in g[10:] else g + 'Z'
        except Exception:
            pass
    return _ultimo_commit(str(fichero))


def _a_utc(s: str) -> datetime | None:
    try:
        d = datetime.fromisoformat(s.replace('Z', '+00:00'))
    except Exception:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def revisar() -> dict:
    out: dict = {
        'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'modelos': {},
    }
    for clave, cfg in MODELOS.items():
        datos = DOCS / cfg['fichero']
        gen = _generado_el(datos)
        cambios = []
        for m in cfg['modulos']:
            c = _ultimo_commit(m)
            if c:
                cambios.append((m, c))

        entrada = {
            'etiqueta': cfg['etiqueta'],
            'fichero': cfg['fichero'],
            'datos_del': gen,
            'desfasado': None,          # None = no se pudo determinar
            'modulos_mas_nuevos': [],
        }
        fg = _a_utc(gen) if gen else None
        if fg and cambios:
            nuevos = [(m, c) for m, c in cambios
                      if (d := _a_utc(c)) is not None and d > fg]
            entrada['desfasado'] = bool(nuevos)
            entrada['modulos_mas_nuevos'] = [
                {'modulo': m, 'cambiado_el': c} for m, c in sorted(nuevos)]
        out['modelos'][clave] = entrada

    desfasados = [k for k, v in out['modelos'].items() if v['desfasado']]
    out['hay_desfase'] = bool(desfasados)
    out['desfasados'] = desfasados
    return out


def main() -> int:
    d = revisar()
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(d, indent=2, ensure_ascii=False))
    for k, v in d['modelos'].items():
        if v['desfasado']:
            mods = ', '.join(m['modulo'] for m in v['modulos_mas_nuevos'])
            print(f"  [desfase] {v['etiqueta']}: datos del {v['datos_del']}, "
                  f"cambiados después: {mods}")
        elif v['desfasado'] is None:
            print(f"  [?] {v['etiqueta']}: no se pudo determinar")
    if not d['hay_desfase']:
        print('  todos los datos se generaron con el código actual')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
