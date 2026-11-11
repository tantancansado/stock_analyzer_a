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


def _pagina(navegador, tema):
    sesion = {'access_token': 'x', 'token_type': 'bearer', 'expires_in': 3600,
              'expires_at': int(time.time()) + 3600, 'refresh_token': 'x',
              'user': {'id': '00000000-0000-0000-0000-000000000001', 'email': 'prueba@example.com',
                       'aud': 'authenticated', 'role': 'authenticated'}}
    ctx = navegador.new_context(viewport={'width': ANCHO, 'height': 844}, is_mobile=True, has_touch=True,
                                device_scale_factor=2, service_workers='block')
    ctx.add_init_script(
        f"localStorage.setItem('sb-rkcqkivnvhhwgtbndbyi-auth-token', {json.dumps(json.dumps(sesion))});"
        f"localStorage.setItem('sa-theme', '{tema}');")
    ctx.route(f'{PAGES}**', _desde_disco)
    for corte in ('**/*.up.railway.app/**', '**/*.supabase.co/**', '**/*sentry.io/**'):
        ctx.route(corte, lambda r: r.abort())
    return ctx, ctx.new_page()


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
        pagina.wait_for_timeout(800)
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
