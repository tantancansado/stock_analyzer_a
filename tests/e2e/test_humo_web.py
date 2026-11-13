#!/usr/bin/env python3
"""Prueba de humo de la web construida: cada página del menú, en un móvil, con la API caída.

Lo que mira es lo que el usuario vería roto y ningún test unitario ve, porque
vive entre piezas: una excepción que deja la pantalla en blanco, un «NaN» o un
«undefined» pintado, la página más ancha que el móvil, o la cabecera que
desaparece cuando la API no responde.

Usa `docs/app` tal y como se publica, con los datos de `docs/` de este mismo
commit: las peticiones a GitHub Pages se sirven desde el disco. Railway y
Supabase se cortan a propósito: la API caída es justo el caso que más se rompe.

Se salta sin Playwright (el CI normal no lo instala); lo corre `e2e.yml`.
"""
import functools
import http.server
import json
import mimetypes
import re
import threading
import time
from pathlib import Path

import pytest

sync_api = pytest.importorskip('playwright.sync_api')

RAIZ = Path(__file__).resolve().parents[2]
DOCS = RAIZ / 'docs'
PAGES = 'https://tantancansado.github.io/stock_analyzer_a/'
ANCHO = 390
TEXTO_ROTO = re.compile(r'(?<![\w-])(NaN|undefined|Infinity|\[object Object\])(?![\w-])')


def _rutas() -> list[str]:
    fuente = (RAIZ / 'frontend/src/lib/prefetch.ts').read_text()
    return ['/'] + re.findall(r"^\s+'(/[^']*)':", fuente, re.M)


@pytest.fixture(scope='module')
def servidor(tmp_path_factory):
    if not (DOCS / 'app' / 'index.html').exists():
        pytest.skip('docs/app no está construido')
    raiz = tmp_path_factory.mktemp('web')
    (raiz / 'stock_analyzer_a').symlink_to(DOCS)
    manejador = functools.partial(_Silencioso, directory=str(raiz))
    httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), manejador)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f'http://127.0.0.1:{httpd.server_address[1]}/stock_analyzer_a/app/'
    httpd.shutdown()


class _Silencioso(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def _desde_disco(route):
    """Lo que la app pide a GitHub Pages sale de docs/ de este commit."""
    ruta = DOCS / route.request.url.split(PAGES, 1)[1].split('?', 1)[0]
    if ruta.is_file():
        tipo = mimetypes.guess_type(ruta.name)[0] or 'application/octet-stream'
        route.fulfill(status=200, body=ruta.read_bytes(), headers={'content-type': tipo})
    else:
        route.fulfill(status=404, body='')


@pytest.fixture(scope='module')
def navegador():
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        yield b
        b.close()


def _pagina(navegador, tema, ancho=ANCHO, extra=''):
    sesion = {'access_token': 'x', 'token_type': 'bearer', 'expires_in': 3600,
              'expires_at': int(time.time()) + 3600, 'refresh_token': 'x',
              'user': {'id': '00000000-0000-0000-0000-000000000001', 'email': 'prueba@example.com',
                       'aud': 'authenticated', 'role': 'authenticated'}}
    movil = ancho < 640
    ctx = navegador.new_context(viewport={'width': ancho, 'height': 844 if movil else 1000}, is_mobile=movil,
                                has_touch=movil, device_scale_factor=2, service_workers='block')
    ctx.add_init_script(
        f"localStorage.setItem('sb-rkcqkivnvhhwgtbndbyi-auth-token', {json.dumps(json.dumps(sesion))});"
        f"localStorage.setItem('sa-theme', '{tema}');{extra}")
    ctx.route(f'{PAGES}**', _desde_disco)
    for corte in ('**/*.up.railway.app/**', '**/*.supabase.co/**', '**/*sentry.io/**'):
        ctx.route(corte, lambda r: r.abort())
    return ctx, ctx.new_page()


_LA_DE_LA_DIRECCION = ("const p = document.querySelectorAll('main [data-ruta]'); "
                       "const destino = location.hash.slice(1) || '/';")


@pytest.mark.parametrize('tema', ['dark', 'light'])
def test_cada_pagina_se_pinta_entera_en_el_movil(servidor, navegador, tema):
    ctx, pagina = _pagina(navegador, tema)
    errores_js: list[str] = []
    pagina.on('pageerror', lambda e: errores_js.append(str(e)[:200]))
    fallos = []
    for ruta in _rutas():
        errores_js.clear()
        pagina.goto(f'{servidor}#{ruta}')
        try:
            pagina.wait_for_load_state('networkidle', timeout=15000)
        except sync_api.TimeoutError:
            pass
        # Cambiar solo el hash no es una navegación: `networkidle` vuelve al
        # momento aunque la página aún esté bajando su código, y mientras sale
        # la anterior su <h1> sigue ahí. /portfolio redirige a una pestaña de Mi
        # cartera que se carga aparte, y en CI tardaba más de los 800 ms: «0
        # <h1>» dos veces el 12-nov con la página bien. Se espera a que la
        # página que se ve sea la de la dirección (`data-ruta`, App.tsx) y
        # tenga su título; si no llega, se dice cuál se quedó.
        try:
            pagina.wait_for_function(f'() => {{ {_LA_DE_LA_DIRECCION} return p.length === 1 '
                                     '&& p[0].dataset.ruta === destino && !!p[0].querySelector("h1") }',
                                     timeout=10000)
        except sync_api.TimeoutError:
            pass
        pagina.wait_for_timeout(800)
        mostrada, destino = pagina.evaluate(
            f'() => {{ {_LA_DE_LA_DIRECCION} return [[...p].map(e => e.dataset.ruta), destino] }}')
        if mostrada != [destino]:
            fallos.append(f'{ruta}: enseña {mostrada} en vez de {destino}')
        h1 = pagina.locator('h1').count()
        texto = pagina.locator('main').inner_text() if pagina.locator('main').count() else ''
        roto = sorted(set(TEXTO_ROTO.findall(texto)))
        ancho = pagina.evaluate('document.documentElement.scrollWidth')
        if errores_js:
            fallos.append(f'{ruta}: excepción — {errores_js[0]}')
        if h1 != 1:
            fallos.append(f'{ruta}: {h1} <h1> (tiene que haber uno, también con la API caída)')
        if roto:
            fallos.append(f'{ruta}: pinta {roto}')
        if ancho > ANCHO + 1:
            fallos.append(f'{ruta}: {ancho}px de ancho en un móvil de {ANCHO}')
    ctx.close()
    assert not fallos, f'tema {tema}:\n' + '\n'.join(fallos)


# Lo que en una fila de Value US dice lo contrario de su grupo. El 12-nov la vista
# completa enseñaba ESPERA, EXIT y TRAP al lado de las tres de Prioridad, y el
# usuario no sabía si eran para entrar sin abrir la ficha.
CONTRARIO = re.compile(r'\b(espera|esperar|exit|trap|evitar|hard reject)\b|mejor (esperar|verlos)|revísala',
                       re.I)


@pytest.mark.parametrize('ancho', [ANCHO, 1440])
@pytest.mark.parametrize('vista', ['sencilla', 'mas_datos'])
def test_cada_fila_de_value_us_dice_su_grupo_y_nada_en_contra(servidor, navegador, ancho, vista):
    ctx, pagina = _pagina(navegador, 'dark', ancho,
                          f"localStorage.setItem('sa-mas-datos:value', '{int(vista == 'mas_datos')}');")
    pagina.goto(f'{servidor}#/value')
    pagina.locator('[data-fila-value]:visible').first.wait_for(timeout=20000)
    filas = [f.inner_text() for f in pagina.locator('[data-fila-value]').all() if f.is_visible()]
    ctx.close()
    assert filas, 'Value US no pinta ninguna fila'
    fallos = []
    for texto in filas:
        cabeza = texto.split()[0] if texto.split() else '?'
        grupos = [g for g in ('Prioridad', 'Observar') if g in texto]
        if len(grupos) != 1:
            fallos.append(f'{cabeza}: no dice su grupo ({grupos})')
        elif grupos == ['Prioridad'] and CONTRARIO.search(texto):
            fallos.append(f'{cabeza}: Prioridad con «{CONTRARIO.search(texto).group(0)}»')
    assert not fallos, f'{ancho}px, vista {vista}:\n' + '\n'.join(fallos)


@pytest.mark.parametrize('ancho', [ANCHO, 1440])
@pytest.mark.parametrize('ruta', ['/dashboard', '/value'])
def test_la_vista_por_defecto_no_contradice_a_la_lista(servidor, navegador, ruta, ancho):
    """Por defecto, lo que se entiende sin conocer la regla (12-nov: «tiene que ser
    intuitivo para un usuario»). Ni ahí ni en ningún sitio de la vista sencilla puede
    salir un esperar, evitar, EXIT o TRAP: eso era el Centro de mando de antes."""
    ctx, pagina = _pagina(navegador, 'dark', ancho)
    pagina.goto(f'{servidor}#{ruta}')
    try:
        pagina.wait_for_load_state('networkidle', timeout=15000)
    except sync_api.TimeoutError:
        pass
    pagina.wait_for_timeout(800)
    texto = pagina.locator('main').inner_text()
    ctx.close()
    assert any(f in texto for f in ('Prioridad', 'puedes comprar', 'nada que comprar')), \
        f'{ruta}: no dice qué se compra hoy'
    choque = CONTRARIO.search(texto)
    assert not choque, f'{ruta} a {ancho}px dice «{choque.group(0)}» en la vista por defecto'
