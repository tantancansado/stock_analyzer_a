#!/usr/bin/env python3
"""
Smoke tests para endpoints críticos de ticker_api.py.

Objetivo: detectar regresiones estructurales — endpoints que devuelven 500
por un cambio inocente en la lógica de carga de CSVs, cambios de shape de
respuesta que rompen el frontend, auth roto accidentalmente.

NO validan la calidad de los datos devueltos (eso lo hacen otros tests).
NO hacen assertions sobre tickers/empresas concretas (datos cambian a diario).
SÍ validan: 200 OK, content-type, shape básico de la respuesta.

Si un endpoint devuelve 200 pero shape raro, el test falla y sabes antes de
que el frontend explote en producción.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Forzar modo dev antes de importar ticker_api (bypass auth en tests)
os.environ.pop('FLASK_ENV', None)
os.environ['AUTH_BYPASS'] = 'true'

import pytest

# Algunos endpoints dependen de CSVs presentes en docs/. Si faltan, tests
# toleran 404 pero NO 500 — esa es la distinción clave (404 = no data,
# 500 = código roto).
DOCS = Path(__file__).parent.parent / 'docs'


@pytest.fixture(scope='module')
def client():
    """Flask test client con auth bypass."""
    from ticker_api import app
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


def _assert_ok_or_no_data(resp, endpoint: str):
    """Fail only on 5xx. 404 = archivo no generado aún, aceptable en tests."""
    assert resp.status_code < 500, \
        f"{endpoint} devolvió {resp.status_code} (server error): {resp.get_data(as_text=True)[:300]}"
    if resp.status_code == 404:
        pytest.skip(f"{endpoint}: recurso no disponible (CSV no generado en este entorno)")


# ── Endpoints core (siempre deben responder 200) ──────────────────────────────

class TestCoreEndpoints:

    def test_health_returns_200(self, client):
        resp = client.get('/api/health')
        assert resp.status_code == 200
        body = resp.get_json()
        assert body is not None
        assert 'status' in body or 'ok' in body or 'tickers_cached' in body

    def test_tickers_list_returns_list(self, client):
        resp = client.get('/api/tickers')
        assert resp.status_code == 200
        body = resp.get_json()
        assert isinstance(body, (list, dict))


# ── Dataset endpoints (toleran 404 si CSV no existe) ──────────────────────────

@pytest.mark.parametrize('endpoint', [
    '/api/value-opportunities',
    '/api/eu-value-opportunities',
    '/api/momentum-opportunities',
    '/api/mean-reversion',
    '/api/bounce-broad',
    '/api/options-flow',
    '/api/recurring-insiders',
    '/api/sector-rotation',
    '/api/market-regime',
    '/api/macro-radar',
    '/api/entry-verdicts',
    '/api/analyst-revisions',
    '/api/economic-calendar',
])
def test_dataset_endpoint_returns_valid_shape(client, endpoint):
    """Cada endpoint devuelve 200 (con dict/list) o 404 — pero NUNCA 500."""
    resp = client.get(endpoint)
    _assert_ok_or_no_data(resp, endpoint)
    body = resp.get_json()
    assert body is not None, f"{endpoint} devolvió respuesta no-JSON"
    assert isinstance(body, (dict, list)), f"{endpoint} debe devolver dict o list, got {type(body).__name__}"


# ── Per-ticker endpoints (toleran 404 si ticker no existe) ────────────────────

class TestPerTickerEndpoints:

    def test_analyze_known_ticker_returns_200(self, client):
        """AAPL debería estar en el cache siempre — es T1."""
        resp = client.get('/api/analyze/AAPL')
        # Puede ser 200 (cached) o 500 (live fetch rate-limited en CI)
        # En local con cache poblado debería ser 200
        assert resp.status_code in (200, 503), \
            f"/api/analyze/AAPL devolvió {resp.status_code}"
        if resp.status_code == 200:
            body = resp.get_json()
            assert body is not None
            assert 'ticker' in body or 'data' in body

    def test_analyze_invalid_ticker_is_handled(self, client):
        """Un ticker inventado NO debe reventar el server con 500."""
        resp = client.get('/api/analyze/NOTAREALTICKER123')
        assert resp.status_code < 500, \
            f"Server error con ticker inválido: {resp.get_data(as_text=True)[:300]}"


# ── Portfolio + Pipeline health (JSON files) ─────────────────────────────────

class TestPortfolioAndPipeline:

    def test_portfolio_tracker_returns_summary(self, client):
        resp = client.get('/api/portfolio-tracker')
        _assert_ok_or_no_data(resp, '/api/portfolio-tracker')
        body = resp.get_json()
        assert isinstance(body, dict)

    def test_portfolio_signals_returns_list_or_dict(self, client):
        resp = client.get('/api/portfolio-tracker/signals')
        _assert_ok_or_no_data(resp, '/api/portfolio-tracker/signals')
        body = resp.get_json()
        assert body is not None


# ── Download map (CSV exports) ────────────────────────────────────────────────

class TestDownloadEndpoint:

    def test_unknown_dataset_returns_404(self, client):
        resp = client.get('/api/download/this-does-not-exist')
        assert resp.status_code == 404

    @pytest.mark.parametrize('dataset', [
        'value-us', 'value-eu', 'mean-reversion',
        'bounce-broad', 'fundamental',
    ])
    def test_known_dataset_returns_200_or_404(self, client, dataset):
        """404 permitido si CSV aún no existe; 500 no."""
        resp = client.get(f'/api/download/{dataset}')
        assert resp.status_code in (200, 404), \
            f"/api/download/{dataset} devolvió {resp.status_code}"


# ── Rate limits en endpoints que llaman a Claude bajo demanda ────────────────

class TestClaudeCostEndpointsRateLimited:
    """Con varios usuarios (self-signup, 25-ago-2026) el límite genérico
    (100/hora, para toda la API) no protegía el GASTO — alguien mirando
    tickers uno tras otro en /api/leaps, /api/analyze-ai o /api/options-chain
    podía disparar decenas de llamadas pagadas a Claude sin darse cuenta,
    cada una fuera del presupuesto controlado del pipeline diario.

    No hay precedente en el repo de testear el 429 real de un rate limit
    (ni el ya existente de analyze_personal_portfolio lo tiene) — mockear
    yfinance/Claude para las tres rutas solo para probar un decorador sale
    caro para lo que aporta. Se comprueba a nivel de fuente que el decorador
    sigue ahí: si alguien lo quita sin querer en un refactor, salta aquí.
    """

    ENDPOINTS_CON_CLAUDE = [
        ("/api/leaps/<ticker>", 'leaps_ticker'),
        ("/api/analyze-ai/<ticker>", 'analyze_ticker_ai'),
        ("/api/options-chain/<ticker>", 'options_chain'),
    ]

    @pytest.mark.parametrize('route,func_name', ENDPOINTS_CON_CLAUDE)
    def test_tiene_limiter_por_hora(self, route, func_name):
        src = Path(__file__).parent.parent.joinpath('ticker_api.py').read_text()
        bloque = src[src.index(f"@app.route('{route}')"):]
        bloque = bloque[:bloque.index(f'def {func_name}') + len(f'def {func_name}')]
        assert '@limiter.limit(' in bloque, \
            f"{route} llama a Claude sin condición pero no tiene @limiter.limit — " \
            f"con varios usuarios esto es gasto sin techo por sesión"
