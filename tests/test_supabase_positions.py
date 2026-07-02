#!/usr/bin/env python3
"""Tests para supabase_positions — el fallback que inmuniza contra el drift
del secret SUPABASE_MONITOR_USER_ID (0 filas con filtro → reintento sin filtro)."""
import io
import json
import os
import sys
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import supabase_positions as sp


def _fake_urlopen_factory(responses_by_url_fragment):
    """urlopen falso: responde según qué fragmento aparezca en la URL."""
    def _fake_urlopen(req, timeout=15):
        url = req.full_url
        for fragment, payload in responses_by_url_fragment.items():
            if fragment in url:
                body = json.dumps(payload).encode()
                m = mock.MagicMock()
                m.__enter__ = lambda s: s
                m.__exit__ = lambda s, *a: False
                m.read = lambda: body
                return m
        raise AssertionError(f'URL inesperada: {url}')
    return _fake_urlopen


ENV = {
    'SUPABASE_URL': 'https://fake.supabase.co',
    'SUPABASE_SERVICE_ROLE_KEY': 'sk-fake',
    'SUPABASE_MONITOR_USER_ID': 'stale-uuid',
}


class TestFetchPositionRows:
    def test_user_filter_with_rows_returns_them(self):
        rows = [{'ticker': 'AAPL'}]
        with mock.patch.dict(os.environ, ENV), \
             mock.patch.object(sp.urllib.request, 'urlopen',
                               _fake_urlopen_factory({'user_id=eq.stale-uuid': rows})):
            assert sp.fetch_position_rows('ticker') == rows

    def test_stale_user_id_falls_back_to_unfiltered(self):
        # El bug real: filtro devuelve 0 filas, sin filtro hay posiciones
        real = [{'ticker': 'CRH.L'}, {'ticker': 'SAP.DE'}]
        def router(req, timeout=15):
            url = req.full_url
            payload = [] if 'user_id=eq.' in url else real
            body = json.dumps(payload).encode()
            m = mock.MagicMock()
            m.__enter__ = lambda s: s
            m.__exit__ = lambda s, *a: False
            m.read = lambda: body
            return m
        with mock.patch.dict(os.environ, ENV), \
             mock.patch.object(sp.urllib.request, 'urlopen', router):
            assert sp.fetch_position_rows('ticker') == real

    def test_no_user_id_env_queries_unfiltered_directly(self):
        env = {k: v for k, v in ENV.items() if k != 'SUPABASE_MONITOR_USER_ID'}
        env['SUPABASE_MONITOR_USER_ID'] = ''
        rows = [{'ticker': 'WMT'}]
        calls = []
        def router(req, timeout=15):
            calls.append(req.full_url)
            body = json.dumps(rows).encode()
            m = mock.MagicMock()
            m.__enter__ = lambda s: s
            m.__exit__ = lambda s, *a: False
            m.read = lambda: body
            return m
        with mock.patch.dict(os.environ, env), \
             mock.patch.object(sp.urllib.request, 'urlopen', router):
            assert sp.fetch_position_rows('ticker') == rows
        assert len(calls) == 1 and 'user_id' not in calls[0]

    def test_unconfigured_returns_none(self):
        env = dict(ENV, SUPABASE_URL='', SUPABASE_SERVICE_ROLE_KEY='')
        with mock.patch.dict(os.environ, env):
            assert sp.fetch_position_rows('ticker') is None

    def test_network_error_returns_none(self):
        def boom(req, timeout=15):
            raise OSError('connection refused')
        with mock.patch.dict(os.environ, ENV), \
             mock.patch.object(sp.urllib.request, 'urlopen', boom):
            assert sp.fetch_position_rows('ticker') is None

    def test_extra_filter_is_appended(self):
        calls = []
        def router(req, timeout=15):
            calls.append(req.full_url)
            body = json.dumps([{'ticker': 'BAC'}]).encode()
            m = mock.MagicMock()
            m.__enter__ = lambda s: s
            m.__exit__ = lambda s, *a: False
            m.read = lambda: body
            return m
        with mock.patch.dict(os.environ, ENV), \
             mock.patch.object(sp.urllib.request, 'urlopen', router):
            sp.fetch_position_rows('ticker,option_strike', extra_filter='&asset_type=eq.option')
        assert '&asset_type=eq.option' in calls[0]
