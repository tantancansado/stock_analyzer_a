"""El repo es público: nada de la cartera real puede ir a docs/ ni a los logs."""
import json

import earnings_options_snapshot as eos
import earnings_thesis_generator as etg
import leaps_monitor as lm
import portfolio_news_monitor as pnm
import portfolio_price_alerts as ppa


def test_el_estado_de_tus_leaps_no_va_a_docs():
    assert 'docs' not in str(lm.STATUS_OUT)


def test_el_registro_de_avisos_no_lleva_el_contrato_en_claro():
    h = lm._huella('ZZZ-65-2027-12-17')
    assert h.startswith('pos-') and 'ZZZ' not in h and '65' not in h


def test_lo_que_va_por_posicion_no_se_publica():
    # Hasta el 29-oct-2026 las tesis por resultados, las opciones previas a
    # resultados, las noticias y el aviso de venta iban a docs/ con los tickers
    # de la cartera como claves. Sin cantidades, pero con la cartera entera
    for ruta in (etg.OUTPUT_PATH, eos.OUT, pnm.SALIDA, pnm._SEEN_CACHE_PATH, ppa.SALIDA):
        assert 'docs' not in ruta.parts, ruta


def test_gitignore_cubre_los_ficheros_personales():
    from pathlib import Path
    gi = (Path(__file__).resolve().parents[1] / '.gitignore').read_text()
    for f in ('privado/', 'docs/leaps_positions_status.json', 'docs/portfolio_watch.json',
              'docs/portfolio_news.json', 'docs/earnings_theses.json', 'docs/earnings_options.json'):
        assert f in gi
