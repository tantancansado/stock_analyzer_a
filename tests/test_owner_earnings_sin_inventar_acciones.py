"""
Owner Earnings valoraba empresas de las que no tenía ni un dato.

`shares_proj = _metric(metrics, "shares_diluted", latest_yr) or 250.0`

Un fallback silencioso: 250 millones de acciones para cualquier empresa que no
trajera el dato. El 16-sep-2026 lo cobraban 54 de los 119 tickers con
proyección —exactamente los 54 sin un solo dato histórico— y todos salían con
el MISMO recuento, 247,0135 (los 250 iniciales menos la recompra proyectada).
Visa tiene 2.000 millones de acciones; AutoZone, 16.

De ahí sale `fcf_per_share`, y de ahí el precio objetivo, el precio de compra y
el veredicto. Resultado: 18 de los 21 «BUY» del módulo construidos sobre un
número inventado, y afirmaciones como estas en pantalla:

    WMT   cotiza 107,15 → «compra por debajo de 2.164,15»  (+1.920%)
    JNJ   cotiza 265,58 → «compra por debajo de 1.632,77»  (+515%)
    PG    cotiza 145,27 → «compra por debajo de 860,90»    (+493%)

Nada falló. Los 137 tickers devolvieron un resultado con su veredicto, su color
y su barra de progreso. Es el patrón de siempre: el fallback hace que el hueco
no se note.

CLAUDE.md: "Sin fallbacks silenciosos: si el dato falla → no score, no número
inventado". El propio módulo ya lo cumplía en el bucle histórico, que hace
`continue` cuando faltan las acciones; solo la proyección hacia delante se lo
saltaba.
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _sin_comentarios_py(ruta: Path) -> str:
    """Los comentarios sí nombran el fallback: explican por qué se quitó."""
    return '\n'.join(l.split('#')[0] for l in ruta.read_text().splitlines())


def test_no_hay_recuento_de_acciones_por_defecto():
    src = _sin_comentarios_py(RAIZ / 'owner_earnings.py')
    assert 'or 250.0' not in src, 'volvió el fallback de 250 millones de acciones'
    assert 'sin_acciones = not shares_proj or shares_proj <= 0' in src


def test_sin_acciones_no_se_proyecta_nada():
    """Ni por consenso ni por el camino de NTM: los dos alimentan el objetivo."""
    src = (RAIZ / 'owner_earnings.py').read_text()
    assert 'sorted(forward_est.keys() if not sin_acciones else [])' in src
    assert 'and not sin_acciones:' in src, 'el fallback desde NTM también tiene que quedar fuera'


def test_el_hueco_se_explica():
    """Un NO_DATA sin motivo se lee como «no encontramos nada», que no es lo
    mismo que «no tenemos con qué mirarlo»."""
    src = (RAIZ / 'owner_earnings.py').read_text()
    assert '"sin_datos_motivo"' in src


def test_la_app_tampoco_inventa_el_recuento():
    """En el frontend el fallback era `?? 1`: con UNA acción, la deuda neta por
    acción pasa a ser la deuda entera y el objetivo por EV/EBITDA se convierte
    en la capitalización completa."""
    src = (RAIZ / 'frontend' / 'src' / 'pages' / 'OwnerEarnings.tsx').read_text()
    codigo = re.sub(r'//[^\n]*|/\*.*?\*/', '', src, flags=re.S)
    assert 'forward_shares?.[yr] ?? 1' not in codigo
    assert 'if (!sh || sh <= 0) continue' in codigo
