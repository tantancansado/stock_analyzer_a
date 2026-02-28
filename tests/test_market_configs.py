#!/usr/bin/env python3
"""Unit tests for market_configs.py"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from market_configs import (
    DAX40_SYMBOLS, FTSE100_SYMBOLS, CAC40_SYMBOLS,
    IBEX35_SYMBOLS, AEX25_SYMBOLS, SMI20_SYMBOLS, FTSEMIB_SYMBOLS,
    get_all_european_symbols, get_european_market_for_ticker
)


class TestEuropeanSymbols:
    def test_no_duplicates_within_lists(self):
        """Each market list should have no internal duplicates"""
        for name, symbols in [
            ('DAX40', DAX40_SYMBOLS), ('FTSE100', FTSE100_SYMBOLS),
            ('CAC40', CAC40_SYMBOLS), ('IBEX35', IBEX35_SYMBOLS),
            ('AEX25', AEX25_SYMBOLS), ('SMI20', SMI20_SYMBOLS),
            ('FTSEMIB', FTSEMIB_SYMBOLS)
        ]:
            assert len(symbols) == len(set(symbols)), f"Duplicates in {name}: {[s for s in symbols if symbols.count(s) > 1]}"

    def test_correct_suffixes(self):
        """Each market should have correct yfinance suffixes"""
        suffix_map = {
            'DAX40': '.DE', 'FTSE100': '.L', 'CAC40': '.PA',
            'IBEX35': '.MC', 'AEX25': '.AS', 'SMI20': '.SW',
            'FTSEMIB': '.MI'
        }
        for name, expected_suffix in suffix_map.items():
            symbols = globals().get(f'{name}_SYMBOLS', [])
            for s in symbols:
                assert '.' in s, f"{s} in {name} has no suffix"
                actual_suffix = '.' + s.split('.')[-1]
                assert actual_suffix == expected_suffix, f"{s} in {name} has wrong suffix {actual_suffix}, expected {expected_suffix}"

    def test_get_all_european_no_duplicates(self):
        all_eu = get_all_european_symbols()
        assert len(all_eu) == len(set(all_eu))

    def test_get_european_market_for_ticker(self):
        # DAX ticker
        assert get_european_market_for_ticker('SAP.DE') == 'DAX40'
        # FTSE ticker
        assert 'FTSE' in get_european_market_for_ticker('SHEL.L')
        # Unknown ticker returns 'OTHER' or similar
        result = get_european_market_for_ticker('AAPL')
        assert result not in ('DAX40', 'FTSE100', 'CAC40', 'IBEX35', 'AEX25', 'SMI20', 'FTSEMIB')

    def test_minimum_counts(self):
        """Each market should have reasonable number of tickers"""
        assert len(DAX40_SYMBOLS) >= 15
        assert len(FTSE100_SYMBOLS) >= 20
        assert len(CAC40_SYMBOLS) >= 20
        assert len(IBEX35_SYMBOLS) >= 15
        assert len(AEX25_SYMBOLS) >= 15
        assert len(SMI20_SYMBOLS) >= 15
        assert len(FTSEMIB_SYMBOLS) >= 15


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
