"""
Fallos de la app que se ven a simple vista y nadie caza.

El usuario los reporta uno a uno desde hace semanas —«siempre tenemos fallos con
las tablas que no se ven bien»— y siempre son el mismo puñado de causas.
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SRC = RAIZ / 'frontend' / 'src'


def test_el_ticker_sobrevive_al_juntar_insiders_us_y_eu():
    """`load_csv_file` pone el TICKER como índice, y `ignore_index=True` lo tira.

    El resultado no tenía ticker ni en el índice ni en las columnas:

      · `/api/recurring-insiders` devolvía filas sin ticker, y la página las
        pintaba con un «?» en vez del logo y sin símbolo;
      · `_row(DF_INSIDERS, ticker)` busca POR ÍNDICE, así que la ficha de cada
        valor salía sin datos de insiders — en silencio.

    Solo pasaba con la lista europea presente: sin ella el `else` devuelve el
    dataframe de US intacto. Por eso apareció cuando empezó a haber insiders EU.
    """
    import pandas as pd

    from ticker_api_data import load_csv_file, load_static_datasets

    us = load_csv_file(RAIZ / 'docs' / 'recurring_insiders.csv')
    eu = load_csv_file(RAIZ / 'docs' / 'eu_recurring_insiders.csv')
    if us.empty or eu.empty:
        import pytest
        pytest.skip('sin CSV de insiders para comprobar')

    # La forma exacta del bug, para que quede escrita:
    roto = pd.concat([us, eu], ignore_index=True)
    assert roto.index.name is None and 'ticker' not in roto.columns

    d = load_static_datasets(str(RAIZ / 'docs'))
    assert d.df_insiders.index.name == 'ticker', 'el ticker tiene que seguir siendo el índice'
    servido = d.df_insiders.reset_index()
    assert 'ticker' in servido.columns
    assert servido['ticker'].notna().all(), 'ninguna fila puede llegar sin ticker'
    assert len(d.df_insiders) == len(us) + len(eu)


def test_ninguna_tabla_va_dentro_de_un_scroll_container_crudo():
    """Un `overflow-x-auto` a pelo crea un scroll container y eso ROMPE el
    `position: sticky` del thead — la cabecera se despega y queda flotando
    sobre las filas. Le pasaba a la tabla de alertas de Rotación Sectorial.

    El envoltorio canónico es `.table-x-wrap`: usa `overflow-x: clip` en
    escritorio —mismo efecto visual, sin crear scroll container— y solo en
    móvil pasa a `auto` con el thead estático. Está en CLAUDE.md.
    """
    scroll = re.compile(r'overflow-(?:x-|y-)?(?:auto|scroll)')
    tabla = re.compile(r'<Table\b(?!Head|Body|Row|Cell)|<table\b')
    culpables = []
    for f in sorted(SRC.rglob('*.tsx')):
        if 'test' in f.parts:
            continue
        lineas = f.read_text().split('\n')
        for i, l in enumerate(lineas):
            codigo = l.split('//')[0]
            if not scroll.search(codigo) or 'table-x-wrap' in codigo:
                continue
            if tabla.search('\n'.join(lineas[i + 1:i + 7])):
                culpables.append(f'{f.relative_to(SRC)}:{i + 1}')
    assert not culpables, (
        'tablas con scroll container crudo (rompe el thead sticky); usa .table-x-wrap: '
        + ', '.join(culpables))


def test_ninguna_barra_usa_una_pista_invisible():
    """`--muted` contra `--card` da 1,08 de contraste en oscuro, 1,07 en noir y
    1,24 en claro. Con opacidad al 20-30%, entre 1,01 y 1,06. Un separador
    necesita ~1,3 para distinguirse, así que la pista no se veía y quedaba el
    relleno de color flotando sobre nada: la barra parecía un guion suelto.

    Le pasaba a 22 barras en 11 páginas — «la tabla de materias primas se ve
    rara» era esto. La clase canónica es `.barra-pista`
    (`--muted-foreground` al 25%: 1,59 / 1,45 / 1,37).
    """
    pista = re.compile(r'class[Nn]ame="([^"]*)"')
    culpables = []
    for f in sorted(SRC.rglob('*.tsx')):
        if 'test' in f.parts:
            continue
        for i, l in enumerate(f.read_text().split('\n'), 1):
            for m in pista.finditer(l):
                cls = m.group(1)
                es_barra = (re.search(r'\bh-(?:1|1\.5|2|2\.5|3)\b', cls)
                            and 'rounded-full' in cls)
                if es_barra and re.search(r'\bbg-muted(?:/\d+)?\b(?!-)', cls):
                    culpables.append(f'{f.relative_to(SRC)}:{i}')
    assert not culpables, (
        'pistas de barra invisibles (usa .barra-pista): ' + ', '.join(culpables))


def test_la_clase_de_la_pista_existe_y_lleva_sus_numeros():
    css = (SRC / 'index.css').read_text()
    assert '.barra-pista {' in css
    assert 'muted-foreground) 25%' in css, 'el valor medido, no otro'
    assert '1,08' in css, 'los números de la medición se quedan escritos'


def test_ninguna_tabla_visible_en_movil_se_queda_sin_scroll():
    """Sin `.table-x-wrap` la tabla se corta en móvil y no hay forma de llegar a
    las columnas de la derecha.

    Las que están dentro de un `hidden sm:block` no cuentan: en móvil no se
    pintan (esas páginas enseñan tarjetas en su lugar), así que envolverlas no
    aportaría nada. La comprobación mira el contenedor antes de exigir nada —
    un chequeo que pide envoltorio donde no hace falta acaba ignorado.
    """
    oculta = re.compile(r'hidden\s+(?:sm|md|lg):(?:block|table|flex|grid)')
    tabla = re.compile(r'<Table\b(?!Head|Body|Row|Cell)|<table\b')
    culpables = []
    for f in sorted(SRC.rglob('*.tsx')):
        if 'test' in f.parts:
            continue
        s = f.read_text()
        if 'table-x-wrap' in s:
            continue
        lineas = s.split('\n')
        for i, l in enumerate(lineas):
            if not tabla.search(l):
                continue
            contexto = '\n'.join(lineas[max(0, i - 8):i])
            if oculta.search(contexto):
                continue
            culpables.append(f'{f.relative_to(SRC)}:{i + 1}')
    assert not culpables, (
        'tablas visibles en móvil sin .table-x-wrap (se cortan sin scroll): '
        + ', '.join(culpables))


def test_el_cristal_liquido_no_reacciona_al_raton():
    """`.liquid-glass` no se usa en nada pulsable —los siete sitios son modales,
    banners y tarjetas líder— así que no debe moverse al pasar el ratón: el
    movimiento promete una acción que no existe.

    Tenía un `:hover` que levantaba el elemento 2px y le pintaba un borde
    interior casi blanco (74% arriba). En el «Plan del Día» del Centro de mando
    se veía como una tarjeta que salta y se enmarca sola.
    """
    css = (SRC / 'index.css').read_text()
    sin_comentarios = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    assert '.liquid-glass:hover' not in sin_comentarios, \
        'volvió el hover sobre la clase entera; si algo es pulsable, dáselo a él'
