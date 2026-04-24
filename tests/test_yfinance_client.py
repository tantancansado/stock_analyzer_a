#!/usr/bin/env python3
"""
Tests para yfinance_client — el cliente centralizado.

Mocks yfinance para no hacer llamadas reales. Verifica:
  - Rate limit cushion respetado entre llamadas
  - RateLimitError lanzado en 'Too Many Requests' (no DataNotFoundError!)
  - DataNotFoundError cuando info/history vacío
  - Stats contadores incrementados correctamente
"""
import os
import sys
import time
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import pandas as pd

import yfinance_client as yc
from yfinance_client import (
    RateLimitError, DataNotFoundError, YFClientError,
    get_info, get_history, get_calendar, get_current_price,
    get_stats, reset_stats, set_min_gap_seconds,
)


@pytest.fixture(autouse=True)
def _reset_stats_and_gap():
    """Limpia stats antes de cada test; gap bajo para tests rápidos."""
    reset_stats()
    set_min_gap_seconds(0.0)
    yield
    reset_stats()
    set_min_gap_seconds(0.15)


# ── Error classification ──────────────────────────────────────────────────────

class TestRateLimitClassification:

    def test_too_many_requests_raises_rate_limit_error(self):
        mock_tk = MagicMock()
        mock_tk.info = MagicMock(side_effect=Exception("Too Many Requests from Yahoo"))
        type(mock_tk).info = property(lambda self: (_ for _ in ()).throw(Exception("Too Many Requests")))

        with patch('yfinance_client.yf.Ticker', return_value=mock_tk):
            with pytest.raises(RateLimitError):
                get_info('AAPL')

        stats = get_stats()
        assert stats['rate_limited'] == 1
        assert stats['calls_ok'] == 0

    def test_429_in_message_raises_rate_limit_error(self):
        mock_tk = MagicMock()
        type(mock_tk).info = property(lambda self: (_ for _ in ()).throw(Exception("HTTP 429")))

        with patch('yfinance_client.yf.Ticker', return_value=mock_tk):
            with pytest.raises(RateLimitError):
                get_info('X')

    def test_other_error_raises_yfclient_error(self):
        mock_tk = MagicMock()
        type(mock_tk).info = property(lambda self: (_ for _ in ()).throw(Exception("Network unreachable")))

        with patch('yfinance_client.yf.Ticker', return_value=mock_tk):
            with pytest.raises(YFClientError) as exc_info:
                get_info('X')
            assert not isinstance(exc_info.value, RateLimitError)

        stats = get_stats()
        assert stats['other_errors'] == 1


# ── Data-missing errors ───────────────────────────────────────────────────────

class TestDataMissing:

    def test_empty_info_raises_data_not_found(self):
        mock_tk = MagicMock()
        mock_tk.info = {}

        with patch('yfinance_client.yf.Ticker', return_value=mock_tk):
            with pytest.raises(DataNotFoundError):
                get_info('DELISTED')

        assert get_stats()['data_missing'] == 1

    def test_missing_required_fields_raises_data_not_found(self):
        mock_tk = MagicMock()
        mock_tk.info = {'unrelatedField': 1}

        with patch('yfinance_client.yf.Ticker', return_value=mock_tk):
            with pytest.raises(DataNotFoundError):
                get_info('X', required_fields=['currentPrice', 'previousClose'])

    def test_empty_history_raises_data_not_found(self):
        mock_tk = MagicMock()
        mock_tk.history.return_value = pd.DataFrame()

        with patch('yfinance_client.yf.Ticker', return_value=mock_tk):
            with pytest.raises(DataNotFoundError):
                get_history('X')

    def test_history_too_few_rows_raises(self):
        mock_tk = MagicMock()
        mock_tk.history.return_value = pd.DataFrame({'Close': [100, 101, 102]})

        with patch('yfinance_client.yf.Ticker', return_value=mock_tk):
            with pytest.raises(DataNotFoundError):
                get_history('X', min_rows=50)

    def test_empty_calendar_raises(self):
        mock_tk = MagicMock()
        mock_tk.calendar = {}

        with patch('yfinance_client.yf.Ticker', return_value=mock_tk):
            with pytest.raises(DataNotFoundError):
                get_calendar('X')


# ── Happy path ────────────────────────────────────────────────────────────────

class TestHappyPath:

    def test_get_info_returns_dict_and_increments_ok(self):
        mock_tk = MagicMock()
        mock_tk.info = {'currentPrice': 150.0, 'longName': 'Apple Inc'}

        with patch('yfinance_client.yf.Ticker', return_value=mock_tk):
            info = get_info('AAPL', required_fields=['currentPrice'])

        assert info['currentPrice'] == 150.0
        stats = get_stats()
        assert stats['calls_ok'] == 1
        assert stats['rate_limited'] == 0

    def test_get_history_returns_dataframe(self):
        df_expected = pd.DataFrame({'Close': list(range(260))})
        mock_tk = MagicMock()
        mock_tk.history.return_value = df_expected

        with patch('yfinance_client.yf.Ticker', return_value=mock_tk):
            df = get_history('AAPL', min_rows=250)

        assert len(df) == 260

    def test_get_current_price_uses_first_available(self):
        mock_tk = MagicMock()
        mock_tk.info = {'previousClose': 99.5}  # no currentPrice, no regularMarketPrice

        with patch('yfinance_client.yf.Ticker', return_value=mock_tk):
            price = get_current_price('AAPL')
        assert price == pytest.approx(99.5)


# ── Rate cushion ──────────────────────────────────────────────────────────────

class TestRateCushion:

    def test_consecutive_calls_wait_min_gap(self):
        set_min_gap_seconds(0.05)  # 50ms

        mock_tk = MagicMock()
        mock_tk.info = {'currentPrice': 100}

        with patch('yfinance_client.yf.Ticker', return_value=mock_tk):
            t0 = time.monotonic()
            get_info('A', required_fields=['currentPrice'])
            get_info('B', required_fields=['currentPrice'])
            get_info('C', required_fields=['currentPrice'])
            elapsed = time.monotonic() - t0

        # 3 calls con 50ms de gap → al menos 100ms (2 gaps entre 3 calls)
        # Tolerancia generosa por scheduler variance
        assert elapsed >= 0.08, f"Expected ≥80ms, got {elapsed * 1000:.0f}ms"


# ── Stats ─────────────────────────────────────────────────────────────────────

class TestStats:

    def test_stats_tracks_errors_by_ticker(self):
        mock_tk = MagicMock()
        type(mock_tk).info = property(lambda self: (_ for _ in ()).throw(Exception("Too Many Requests")))

        with patch('yfinance_client.yf.Ticker', return_value=mock_tk):
            for _ in range(3):
                with pytest.raises(RateLimitError):
                    get_info('BADTICKER')

        stats = get_stats()
        assert stats['rate_limited'] == 3
        assert stats['top_failures'].get('BADTICKER') == 3

    def test_ok_rate_computed(self):
        mock_ok = MagicMock()
        mock_ok.info = {'currentPrice': 100}
        mock_fail = MagicMock()
        type(mock_fail).info = property(lambda self: (_ for _ in ()).throw(Exception("Too Many Requests")))

        with patch('yfinance_client.yf.Ticker', side_effect=[mock_ok, mock_ok, mock_fail]):
            get_info('A', required_fields=['currentPrice'])
            get_info('B', required_fields=['currentPrice'])
            with pytest.raises(RateLimitError):
                get_info('C')

        stats = get_stats()
        assert stats['calls_total'] == 3
        assert stats['calls_ok'] == 2
        assert stats['ok_rate'] == pytest.approx(0.667, abs=0.01)
