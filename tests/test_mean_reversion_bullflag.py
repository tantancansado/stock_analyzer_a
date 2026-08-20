"""Regresión del bull flag pullback (mean_reversion_detector).

Bug encontrado el 5-jul-2026: lookback_days=180 (~124 sesiones) hacía que la
SMA200 cayera SIEMPRE a la SMA50, así que el criterio de tendencia mayor —lo
que DEFINE un bull flag— nunca se evaluaba: trend salía siempre 'Bearish' y
el RSI estaba hardcodeado a None. Estos tests fijan que no vuelva a pasar.
"""
import inspect
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mean_reversion_detector as mrd


def test_lookback_covers_sma200():
    d = mrd.MeanReversionDetector()
    # 300 días de calendario ≈ 205 sesiones; hace falta >=200 para la SMA200
    assert d.lookback_days >= 290


def test_bullflag_no_longer_hardcodes_rsi_none():
    src = inspect.getsource(mrd.MeanReversionDetector.detect_bull_flag_pullback)
    # el rsi ya NO se emite como None fijo
    assert "'rsi': None" not in src
    assert "'rsi': current_rsi_bf" in src
    # y exige 200 sesiones reales en vez de inventar una SMA200
    assert "len(hist) < 200" in src
    assert "else sma_50" not in src  # el fallback falso desapareció


def test_bullflag_computes_rsi_tier():
    src = inspect.getsource(mrd.MeanReversionDetector.detect_bull_flag_pullback)
    assert "calculate_rsi" in src
    assert "rsi_tier_bf" in src


class TestTargetNuncaPorDebajoDelPrecio:
    """Una señal de rebote con el target por debajo del precio es basura.

    El 20-ago-2026 llegaron a producción DVA (precio 177,27 → target 156,76,
    -11,6%) y UNH (388,61 → 347,91, -10,5%): "oportunidades" que pedían
    comprar caro para vender barato. La causa era
    `min(current_price * 1.07, resistance)` sin comprobar que la resistencia
    estuviera por encima del precio.

    Y detrás había algo peor: el RSI marcaba sobreventa (11,9 en DVA) mientras
    el precio estaba un 22-37% POR ENCIMA del soporte. No hay rebote que hacer
    desde ahí — el setup entero era falso, no solo el número.
    """

    def test_el_calculo_de_min_es_el_que_fallaba(self):
        """Reproduce la aritmética exacta que se coló en producción."""
        precio, resistencia = 177.27, 156.76
        target_viejo = round(min(precio * 1.07, resistencia), 2)
        assert target_viejo < precio, 'así salía el target negativo'
        assert round((target_viejo / precio - 1) * 100, 1) == -11.6

    def test_el_detector_descarta_si_la_resistencia_esta_debajo(self):
        from pathlib import Path
        import mean_reversion_detector as mrd
        src = Path(mrd.__file__).read_text()
        # el guard tiene que estar ANTES de calcular el target, en ambos setups
        assert 'if resistance <= current_price:' in src
        assert 'if high_60d <= current_price:' in src

    def test_ninguna_señal_publicada_pide_comprar_caro_para_vender_barato(self):
        """Sobre el CSV real: es la comprobación que habría cazado el fallo."""
        from pathlib import Path
        import pandas as pd
        import pytest
        f = Path(__file__).parent.parent / 'docs' / 'mean_reversion_opportunities.csv'
        if not f.exists():
            pytest.skip('sin CSV de mean reversion')
        d = pd.read_csv(f)
        if d.empty:
            pytest.skip('sin señales hoy')
        precio = pd.to_numeric(d['current_price'], errors='coerce')
        for col in ('target', 'bounce_target'):
            if col not in d.columns:
                continue
            t = pd.to_numeric(d[col], errors='coerce')
            malas = d.loc[t.notna() & precio.notna() & (t <= precio), 'ticker'].tolist()
            assert not malas, f'{col} por debajo del precio en: {malas}'


class TestValidadorDeCoherencia:
    """Puerta única antes de publicar una señal.

    Los detectores calculan stop y target desde niveles técnicos (soporte,
    resistencia, SMA50, máximo de 60d) sin comprobar que caigan del lado
    correcto del precio. El 20-ago-2026 salieron a producción tres fallos de
    esa familia; cada guard suelto arregla un setup, este ataja también los
    que se añadan después.
    """

    def test_corta_el_target_por_debajo_del_precio(self):
        from mean_reversion_detector import setup_coherente
        ok, motivo = setup_coherente({'current_price': 177.27, 'bounce_target': 156.76})
        assert not ok and 'comprar caro' in motivo   # DVA real

    def test_corta_el_stop_por_encima_de_la_entrada(self):
        from mean_reversion_detector import setup_coherente
        ok, motivo = setup_coherente({'current_price': 388.61, 'bounce_target': 415.81,
                                      'stop_loss': 402.08})
        assert not ok and 'stop' in motivo           # UNH real

    def test_corta_el_risk_reward_a_cero(self):
        """Un R:R de 0 sale del `else 0` de la división: el cálculo era
        imposible y publicarlo esconde el problema."""
        from mean_reversion_detector import setup_coherente
        ok, motivo = setup_coherente({'current_price': 100, 'bounce_target': 107,
                                      'stop_loss': 95, 'risk_reward': 0})
        assert not ok and 'risk_reward' in motivo

    def test_deja_pasar_un_setup_correcto(self):
        from mean_reversion_detector import setup_coherente
        ok, motivo = setup_coherente({'current_price': 100.0, 'bounce_target': 107.0,
                                      'stop_loss': 96.0, 'risk_reward': 1.75})
        assert ok and motivo == ''

    def test_el_scan_usa_el_validador(self):
        from pathlib import Path
        import mean_reversion_detector as mrd
        src = Path(mrd.__file__).read_text()
        assert 'setup_coherente(setup)' in src, 'el scan no pasa por el validador'


class TestCatalizadorDeUpside:
    """El catalizador "R:R ≥3" premiaba la peor banda de upside.

    `risk_reward_ratio` no es un factor independiente: el integrator lo calcula
    como `analyst_upside_pct / 8`, así que "R:R ≥3" es "upside ≥24%". Medido
    sobre las señales propias, [10,25) da 77,8% de acierto y +5,67%, mientras
    [25,30) da 27,3% y −3,17%. El 20-ago-2026 los NUEVE tickers marcados tenían
    upside 24-28,6%: la app los pintaba en verde por estar en la peor banda.
    """

    def test_el_catalizador_usa_la_banda_buena_no_el_rr(self):
        from pathlib import Path
        f = Path(__file__).parent.parent / 'frontend' / 'src' / 'pages' / 'CatalystScreener.tsx'
        src = f.read_text()
        assert "id: 'rr_strong'" not in src, 'volvió el catalizador que premiaba upside alto'
        assert "id: 'upside_dorado'" in src
        assert 'analyst_upside_pct ?? 0) < 25' in src


class TestSueloDeRiesgo:
    """Los dos detectores de rebote exigían cosas opuestas.

    `bounce_scanner_broad` filtra por `MIN_RR = 1.5` desde hace meses. El
    detector hermano no exigía NADA y el 20-ago-2026 publicó AJG con R:R 0,51
    —arriesgar 22$ para ganar 11$— etiquetado "⭐⭐ MUY BUENA". La app muestra
    ambas fuentes juntas en Entry Setups, así que el usuario veía dos señales
    del mismo tipo con criterios de riesgo incompatibles.
    """

    def test_corta_el_setup_que_arriesga_mas_de_lo_que_gana(self):
        from mean_reversion_detector import setup_coherente
        ok, motivo = setup_coherente({'current_price': 257.45, 'bounce_target': 268.91,
                                      'stop_loss': 234.97, 'risk_reward': 0.51})
        assert not ok and 'arriesga más' in motivo   # AJG real

    def test_deja_pasar_a_partir_de_uno_a_uno(self):
        from mean_reversion_detector import setup_coherente
        ok, _ = setup_coherente({'current_price': 100, 'bounce_target': 105,
                                 'stop_loss': 95, 'risk_reward': 1.0})
        assert ok

    def test_el_suelo_no_es_un_numero_suelto(self):
        """1.0 es la frontera aritmética, no un parámetro calibrado: si alguien
        lo sube sin datos propios, que sea una decisión consciente."""
        from mean_reversion_detector import RR_MINIMO
        assert RR_MINIMO == 1.0


class TestPublicarElCero:
    """Cero oportunidades es un resultado, y hay que publicarlo.

    `save_results` hacía `return` sin tocar nada cuando el scan salía vacío,
    así que el CSV del día anterior seguía en producción y la app mostraba una
    señal caducada como si fuera de hoy — indefinidamente, hasta que hubiera
    otra. Se vio al aplicar el suelo de R:R: el scan pasó a 0 y AJG se habría
    quedado publicado para siempre.
    """

    def test_escribe_csv_vacio_con_cabecera(self, tmp_path):
        from mean_reversion_detector import MeanReversionDetector
        import pandas as pd
        d = MeanReversionDetector()
        d.results = []
        destino = tmp_path / 'mr.csv'
        d.save_results(str(destino))
        assert destino.exists(), 'no publicar nada deja la señal de ayer viva'
        df = pd.read_csv(destino)
        assert len(df) == 0
        assert 'ticker' in df.columns and 'risk_reward' in df.columns

    def test_el_json_dice_cero_y_no_se_queda_el_de_ayer(self, tmp_path):
        from mean_reversion_detector import MeanReversionDetector
        import json
        d = MeanReversionDetector()
        d.results = []
        destino = tmp_path / 'mr.csv'
        d.save_results(str(destino))
        data = json.loads((tmp_path / 'mr.json').read_text())
        assert data['total_opportunities'] == 0
        assert data['opportunities'] == []


class TestFrescuraPorContenido:
    """El watchdog no puede fiarse del mtime: en CI siempre es de hoy.

    `daily-analysis.yml` lee una clave de fecha DENTRO de cada JSON y, si no la
    encuentra, cae al mtime del fichero. En un runner el mtime es el del
    checkout, así que un módulo que crashea conserva el JSON viejo del repo y
    se marca 'ok' igualmente. mean_reversion escribía `scan_date` mientras el
    watchdog buscaba `generated_at`: llevaba siendo invigilable desde siempre.

    El test recorre TODOS los módulos del workflow, no solo ese: el fallo es de
    clase, y el siguiente que se añada con la clave mal escrita cae aquí.
    """

    def test_cada_json_vigilado_lleva_su_clave_de_fecha(self):
        import json, re
        from pathlib import Path
        raiz = Path(__file__).parent.parent
        src = (raiz / '.github' / 'workflows' / 'daily-analysis.yml').read_text()
        bloque = src[src.index('MODULES = {'):src.index('def _csv_rows')]
        pat = re.compile(r"'([a-z_]+)':\s*\('([^']+)',\s*('([^']*)'|None)")

        sin_clave = []
        for nombre, ruta, _, clave in pat.findall(bloque):
            if not clave or not ruta.endswith('.json'):
                continue
            f = raiz / ruta
            if not f.exists():
                continue          # otro problema, y el watchdog ya lo marca 'missing'
            try:
                d = json.loads(f.read_text())
            except Exception:
                continue
            if not (isinstance(d, dict) and d.get(clave)):
                sin_clave.append(f'{nombre}: {ruta} no tiene "{clave}"')

        assert not sin_clave, (
            'estos módulos caen al mtime y son invigilables en CI:\n  '
            + '\n  '.join(sin_clave))
