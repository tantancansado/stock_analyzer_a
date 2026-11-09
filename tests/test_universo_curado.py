"""El curado se puntúa entero. El tier clasifica, no excluye.

Hasta el 17-sep-2026, `SCORED_TICKERS` y el flag `--curated` del scorer dejaban
fuera el TIER_4: 32 empresas de la propia lista curada que NUNCA se medían —
YUM, AAPL, AMZN, GOOG, META, ORCL, AVGO, HD, UNP, BLK, ASML...

El usuario preguntó por qué salía McDonald's y no Yum, y la respuesta honesta
era que Yum ni se miraba. Peor: como nunca había estado, la app tampoco podía
decir por qué faltaba. Su criterio: «si está en el universo curado deberían
entrar todas; las que no entran son las del universo ampliado».

Lo que decide si algo se recomienda es el score y los guards, no el tier. Una
TIER_4 con números malos sale con score bajo y no se publica —resultado
correcto—; una que un día esté barata de verdad ahora se puede ver.
"""
import curated_tickers as ct
import curated_tickers_eu as eu


def test_el_universo_puntuado_es_el_curado_entero():
    assert set(ct.SCORED_TICKERS) == set(ct.ALL_TICKERS)


def test_ninguna_curada_se_queda_sin_medir():
    faltan = [t for t in ct.TIER_1 + ct.TIER_2 + ct.TIER_3 + ct.TIER_4
              if t not in ct.SCORED_TICKERS and not ct.apagada(t)]
    assert faltan == [], f'del curado, sin puntuar: {faltan}'


def test_tokio_esta_apagada_sin_borrar_a_nadie():
    """9-nov-2026: el usuario no compra en Tokio. Se apaga la bolsa, no las empresas:
    siguen en su tier para volver a encenderlas con una línea."""
    tokio = ('7741.T', '4684.T', '6383.T')
    for universo in (ct.SCORED_TICKERS, ct.ALL_TICKERS, ct.HF_UNIVERSE,
                     ct.get_universe(include_hf_watch=True)):
        assert not [t for t in universo if t in tokio]
    assert all(ct.get_tier(t) in ('2', '4') for t in tokio)
    # `.T` no es `.TO`: Toronto sigue dentro.
    assert 'CSU.TO' in ct.SCORED_TICKERS and 'DOL.TO' in ct.SCORED_TICKERS


def test_los_nombres_del_caso_estan_dentro():
    """Los que el usuario vio faltar, y los mayores del tier."""
    for t in ('YUM', 'AAPL', 'AMZN', 'GOOG', 'META', 'ASML', 'ORCL', 'AVGO'):
        assert t in ct.SCORED_TICKERS, t


def test_el_tier_sigue_existiendo_como_etiqueta():
    """Se quita como filtro, no como información: sirve para ordenar y avisar."""
    assert ct.get_tier('AAPL') == '4'
    assert ct.get_tier_label('4') == 'No apta'


def test_hf_watch_sigue_fuera_por_defecto():
    """Es lo que compran otros, no una selección propia de calidad."""
    solo_hf = [t for t in ct.HF_WATCH
               if t not in ct.TIER_1 + ct.TIER_2 + ct.TIER_3 + ct.TIER_4]
    if solo_hf:
        assert solo_hf[0] not in ct.get_universe()


def test_europa_usa_el_mismo_criterio():
    for t in eu.TIER_4_EU:
        assert t in eu.SCORED_EU_TICKERS, t


def test_china_sigue_siendo_referencia_no_seleccion():
    solo_china = [t for t in eu.TIER_CHINA if t not in
                  eu.TIER_1_EU + eu.TIER_2_EU + eu.TIER_3_EU + eu.TIER_4_EU]
    if solo_china:
        assert solo_china[0] not in eu.SCORED_EU_TICKERS


def test_el_scorer_no_vuelve_a_excluir_el_tier4():
    """El default de `get_universe` ya no basta: el pipeline llama con
    `--curated`, que pasaba `include_tier4=False` a mano y se saltaba el
    cambio. Aquí se fija que ese `False` no vuelva."""
    from pathlib import Path
    src = (Path(__file__).resolve().parent.parent / 'fundamental_scorer.py').read_text()
    from conftest import bloque_de_codigo
    bloque = bloque_de_codigo(src, 'elif args.curated or args.curated_all:')
    assert 'include_tier4=' not in bloque, 'el scorer vuelve a decidir el tier por su cuenta'


def test_las_de_noviembre_se_puntuan_y_no_estan_repetidas():
    import curated_tickers as ct
    for t in ('LLY', 'MNST', 'BKNG', 'NVDA', 'KLAC', 'AMAT', 'ADBE', 'LRCX'):
        assert t in ct.SCORED_TICKERS, t
    todas = ct.TIER_1 + ct.TIER_2 + ct.TIER_3 + ct.TIER_4 + ct.HF_WATCH
    repetidas = {t for t in todas if todas.count(t) > 1}
    assert not repetidas, repetidas

