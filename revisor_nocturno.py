#!/usr/bin/env python3
"""Revisor nocturno: lee lo que la app acaba de publicar y busca lo que no cuadra.

Muchos de los arreglos de 2026 no los encontró un test, sino alguien que leyó la
app o el Telegram y vio que algo no cuadraba: FICO llamado EVENTO cuando le
habían congelado el precio, «mejor esperar» en una Prioridad, un 74 % de acierto
de una regla vieja, las ventas de Gartner a -1,3 %, -10,8 % y -1,3 % en tres días.
Esto hace esa lectura cada noche, después del briefing.

Dos partes:
1. Datos que van y vuelven, sin IA y gratis: un campo que hoy vale lo mismo que
   anteayer y ayer valía otra cosa no es la empresa, es el dato.
2. Claude como analista escéptico: lee la lista de Value US, lo que ha cambiado
   desde ayer, las ventas de lo que fue Prioridad y el briefing publicado.
   Cada hallazgo tiene que copiar el dato exacto que lo prueba; si esa cita no
   está en los datos, se descarta, y así no puede inventarse un problema.

Lo que encuentra va a una incidencia de GitHub (etiqueta `revisor`), una por
problema y sin repetir. No toca la lista ni manda Telegram: avisa a quien
arregla, no a quien invierte.

El repositorio es PÚBLICO: solo se lee `docs/`, que ya lo es. Nada de la cartera
(el paso no tiene las claves de Supabase).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import date
from pathlib import Path

import pandas as pd

DOCS = Path('docs')
INFORME = DOCS / 'revisor.json'
ETIQUETA = 'revisor'
MAX_NUEVAS = 5            # incidencias nuevas por noche, como mucho
MAX_TOKENS = 8000         # cubre el pensamiento y la respuesta

# Campos que no deberían moverse de un día a otro sin resultados de por medio.
CAMPOS_VAIVEN = ('rev_growth_yoy', 'eps_growth_yoy', 'target_price_pe', 'target_price_dcf',
                 'fcf_per_share', 'pe_ancla', 'target_price_analyst')
IGUAL = 0.02              # hoy y anteayer, iguales
DISTINTO = 0.20           # ayer, distinto
PUNTOS_MINIMOS = 2.0      # en los crecimientos, además, al menos 2 puntos

# Lo que se le enseña a Claude de cada fila de la lista.
CAMPOS_FICHA = (
    'ticker', 'company_name', 'sector', 'industry', 'value_grupo', 'value_falta', 'value_avisos',
    'value_dobla', 'value_score', 'current_price', 'market_cap', 'per_norm', 'per_mediana_10a',
    'per_z', 'bpa_sobre_tendencia_pct', 'ventas_anual_pct', 'ventas_anual_anio', 'rev_growth_yoy',
    'eps_growth_yoy', 'upside_triangulated_pct', 'recorrido_propio_pct', 'target_price_pe',
    'target_price_dcf', 'target_price_analyst', 'analyst_upside_pct', 'upside_divergence',
    'fcf_yield_pct', 'dividend_yield_pct', 'negative_roe', 'revision_13s_pct', 'days_to_earnings',
    'earnings_date', 'why_cheap', 'why_cheap_resumen',
)

# Lo que se compara cuando una empresa cambia de grupo de un día a otro.
CAMPOS_CAMBIO = ('value_falta', 'value_score', 'current_price', 'per_norm', 'per_z',
                 'bpa_sobre_tendencia_pct', 'ventas_anual_pct', 'rev_growth_yoy', 'eps_growth_yoy',
                 'upside_triangulated_pct', 'recorrido_propio_pct', 'target_price_pe',
                 'target_price_dcf', 'why_cheap')

TIPOS = ('dato_imposible', 'datos_que_se_contradicen', 'texto_contradice_datos',
         'veredicto_dudoso', 'cambio_sin_motivo', 'lista_incumple_su_regla', 'unidades', 'otro')

SYSTEM = """Eres el revisor de calidad de una app de inversión VALUE en EE. UU. Cada noche lees lo que
la app acaba de publicar y buscas lo que NO CUADRA: datos mal, textos que dicen otra cosa que los
números, cambios sin explicación. No opinas sobre si una empresa es buena compra.

Reglas de la casa (son correctas; no las discutas):
- PRIORIDAD = barata según la valoración propia y con ventas sin caer, y además ventas del último año
  >= 10 % y PER más de 1σ bajo su media de 10 años (per_z < -1), o «puede doblar» con el beneficio en
  su tendencia (value_dobla). El resto de la puerta es OBSERVAR, y value_falta dice qué le falta.
- Se veta el beneficio de pico (bpa_sobre_tendencia_pct > 50), el ROE negativo, el consenso por debajo
  del precio y el DETERIORO según las noticias (why_cheap).
- Sin causa de la caída estudiada, una Prioridad se publica en OBSERVAR con value_falta de estudio.
- Lo que fue Prioridad se vende al dejar de serlo (PER por encima de -0,75σ, ventas < 10 %, fuera de la
  puerta, descarte duro o DETERIORO). «No lo sé» no vende.
- Un dato vacío se enseña vacío: eso es correcto, no es un hallazgo.
- why_cheap: SENTIMIENTO, EVENTO o MACRO son caídas circunstanciales; DETERIORO es el negocio. Si el
  resumen describe que un regulador o un competidor le quita precio, cuota o posición de forma
  duradera, eso es DETERIORO aunque las cuentas aún crezcan.

Es un hallazgo:
1. Un dato que no puede ser verdad para esa empresa, o mal escalado (una fracción leída como
   porcentaje, un margen imposible para su sector, ventas de un banco a +300 %).
2. Dos datos de la misma ficha que se contradicen.
3. Un texto (resumen de why_cheap, briefing) que dice otra cosa que los números o que el veredicto.
4. Un cambio desde ayer sin explicación (no ha habido resultados y el dato salta).
5. La lista incumple sus propias reglas.

NO es un hallazgo: tu opinión sobre la regla, que una empresa te parezca cara o mala, un dato vacío,
lo que ya está en "ya_abiertas", "coherencia" o "datos_que_van_y_vuelven", ni el movimiento del
precio.

Para cada hallazgo copia en "cita" un fragmento LITERAL de los datos que te paso (por ejemplo
"rev_growth_yoy": 9.2 o una frase del resumen). Sin cita literal se descarta. Si todo cuadra, devuelve
la lista vacía: es lo normal y es una buena noche.

Responde SOLO con este JSON:
{"hallazgos": [{"ticker": "XXX o null", "tipo": "uno de: """ + ', '.join(TIPOS) + """",
  "titulo": "qué no cuadra, en una línea", "por_que": "una o dos frases", "cita": "fragmento literal",
  "donde_mirar": "qué parte de la app lo calcula, si lo sabes"}]}
Como mucho 5, los más graves primero. En español."""


# ── Lectura de lo publicado ──────────────────────────────────────────────────

def _csv(ruta: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(ruta, low_memory=False)
    except (OSError, ValueError):
        return pd.DataFrame()


def _json(ruta: Path):
    try:
        return json.loads(ruta.read_text())
    except (OSError, ValueError):
        return None


def archivos_anteriores(hoy: str, docs: Path = DOCS) -> list[Path]:
    """Las dos últimas carpetas del archivo diario anteriores a hoy, de vieja a nueva."""
    historia = docs / 'history'
    if not historia.is_dir():
        return []
    dias = sorted(d for d in historia.iterdir()
                  if d.is_dir() and re.fullmatch(r'\d{4}-\d{2}-\d{2}', d.name) and d.name < hoy)
    return dias[-2:]


def _solo_eeuu(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or 'ticker' not in df:
        return df
    df = df.assign(ticker=df['ticker'].astype(str))
    return df[~df['ticker'].str.contains(r'\.', regex=True)].drop_duplicates('ticker').set_index('ticker')


def _dif(a: float, b: float) -> float:
    return abs(b - a) / max(abs(a), abs(b), 1e-9)


def vaivenes(anteayer: pd.DataFrame, ayer: pd.DataFrame, hoy: pd.DataFrame,
             fechas: tuple[str, str, str]) -> list[dict]:
    """Campos que hoy valen lo de anteayer y ayer valían otra cosa."""
    a, b, c = (_solo_eeuu(x) for x in (anteayer, ayer, hoy))
    if a.empty or b.empty or c.empty:
        return []
    hallazgos = []
    for t in sorted(a.index.intersection(b.index).intersection(c.index)):
        for campo in CAMPOS_VAIVEN:
            if campo not in a or campo not in b or campo not in c:
                continue
            v = [pd.to_numeric(x.at[t, campo], errors='coerce') for x in (a, b, c)]
            if any(pd.isna(x) for x in v):
                continue
            v0, v1, v2 = (float(x) for x in v)
            if _dif(v0, v2) >= IGUAL or _dif(v0, v1) < DISTINTO:
                continue
            if 'growth' in campo and abs(v1 - v0) < PUNTOS_MINIMOS:
                continue
            hallazgos.append({
                'clave': f'vaiven:{t}:{campo}', 'ticker': t, 'tipo': 'cambio_sin_motivo',
                'titulo': f'{campo} va y vuelve',
                'por_que': (f'{fechas[0]}: {v0:g} · {fechas[1]}: {v1:g} · {fechas[2]}: {v2:g}. '
                            'Un dato que vuelve al día siguiente no es la empresa: alguna fuente '
                            'devuelve cosas distintas según el día.'),
                'cita': f'{campo}: {v1:g}', 'donde_mirar': 'el cálculo de ese campo y su fuente',
            })
    return hallazgos


def grupos_que_van_y_vuelven(anteayer: pd.DataFrame, ayer: pd.DataFrame, hoy: pd.DataFrame,
                             fechas: tuple[str, str, str]) -> list[dict]:
    """Una Prioridad que sale un día y vuelve al siguiente."""
    a, b, c = (_solo_eeuu(x) for x in (anteayer, ayer, hoy))
    if a.empty or c.empty or 'value_grupo' not in a or 'value_grupo' not in c:
        return []
    def grupo(df, t):
        if t not in df.index or 'value_grupo' not in df:
            return 'fuera'
        g = df.at[t, 'value_grupo']
        return str(g) if pd.notna(g) and str(g) else 'fuera'
    hallazgos = []
    for t in sorted(set(a.index) & set(c.index)):
        g0, g1, g2 = grupo(a, t), grupo(b, t), grupo(c, t)
        if g0 == g2 == 'PRIORIDAD' and g1 != 'PRIORIDAD':
            hallazgos.append({
                'clave': f'vaiven:{t}:value_grupo', 'ticker': t, 'tipo': 'cambio_sin_motivo',
                'titulo': 'sale de Prioridad un día y vuelve al siguiente',
                'por_que': f'{fechas[0]}: {g0} · {fechas[1]}: {g1} · {fechas[2]}: {g2}.',
                'cita': f'value_grupo: {g1}', 'donde_mirar': 'qué dato le cambió ese día',
            })
    return hallazgos


def _limpio(v):
    if isinstance(v, float):
        return None if pd.isna(v) else round(v, 2)
    return None if v is None or (not isinstance(v, str) and pd.isna(v)) else v


def fichas(value: pd.DataFrame) -> list[dict]:
    if value.empty:
        return []
    cols = [c for c in CAMPOS_FICHA if c in value.columns]
    filas = value[cols].to_dict('records')
    return [{k: _limpio(v) for k, v in f.items() if _limpio(v) not in (None, '')} for f in filas]


def cambios_desde_ayer(ayer: pd.DataFrame, hoy: pd.DataFrame) -> dict:
    """Quién entra, quién sale y quién cambia de grupo en Value US."""
    a, h = _solo_eeuu(ayer), _solo_eeuu(hoy)
    if a.empty or h.empty or 'value_grupo' not in a or 'value_grupo' not in h:
        return {}
    cambios = {'entran': sorted(set(h.index) - set(a.index)),
               'salen': sorted(set(a.index) - set(h.index)), 'cambian': []}
    for t in sorted(set(a.index) & set(h.index)):
        if str(a.at[t, 'value_grupo']) != str(h.at[t, 'value_grupo']):
            antes = {c: _limpio(a.at[t, c]) for c in CAMPOS_CAMBIO if c in a}
            ahora = {c: _limpio(h.at[t, c]) for c in CAMPOS_CAMBIO if c in h}
            cambios['cambian'].append({'ticker': t, 'de': str(a.at[t, 'value_grupo']),
                                       'a': str(h.at[t, 'value_grupo']),
                                       'datos_que_cambian': {c: [antes.get(c), ahora.get(c)]
                                                             for c in ahora if antes.get(c) != ahora.get(c)}})
    return cambios


def hechos(hoy: str, docs: Path = DOCS) -> tuple[dict, list[dict]]:
    """(lo que se le enseña a Claude, los vaivenes encontrados sin IA)."""
    value = _csv(docs / 'value_opportunities.csv')
    fund = _csv(docs / 'fundamental_scores.csv')
    anteriores = archivos_anteriores(hoy, docs)
    deterministas: list[dict] = []
    cambios: dict = {}
    if len(anteriores) == 2:
        d0, d1 = anteriores
        fechas = (d0.name, d1.name, hoy)
        deterministas += vaivenes(_csv(d0 / 'fundamental_scores.csv'), _csv(d1 / 'fundamental_scores.csv'),
                                  fund, fechas)
        deterministas += grupos_que_van_y_vuelven(_csv(d0 / 'value_opportunities.csv'),
                                                  _csv(d1 / 'value_opportunities.csv'), value, fechas)
    if anteriores:
        cambios = cambios_desde_ayer(_csv(anteriores[-1] / 'value_opportunities.csv'), value)
    try:
        from position_sizer import motivos_de_venta
        ventas = {t: m for t, m in motivos_de_venta(docs).items() if m}
    except Exception:
        ventas = {}
    briefing = _json(docs / 'daily_briefing.json') or {}
    coherencia = _json(docs / 'coherence_check.json') or {}
    datos = {
        'fecha': hoy,
        'lista_value_us': fichas(value),
        'cambios_desde_ayer': cambios,
        'se_venden_por_dejar_de_ser_prioridad': ventas,
        'briefing_publicado': briefing.get('texto') if briefing.get('fecha') == hoy else None,
        'coherencia': {k: v[:3] for k, v in (coherencia.get('detalle') or {}).items() if v},
        'datos_que_van_y_vuelven': [f"{h['ticker']} {h['titulo']}: {h['por_que']}" for h in deterministas],
    }
    return datos, deterministas


# ── Claude ───────────────────────────────────────────────────────────────────

def _normal(texto: str) -> str:
    return re.sub(r'[\s"\'`]+', '', str(texto)).lower()


def verificar(hallazgos, entrada: str, tickers: set[str]) -> tuple[list[dict], list[str]]:
    """Solo pasa lo que cita literalmente los datos y habla de un ticker que existe."""
    validos, descartados = [], []
    base = _normal(entrada)
    for h in hallazgos if isinstance(hallazgos, list) else []:
        if not isinstance(h, dict) or not str(h.get('titulo') or '').strip():
            continue
        ticker = h.get('ticker')
        ticker = None if ticker in (None, '', 'null') else str(ticker).upper()
        cita = str(h.get('cita') or '').strip()
        if len(_normal(cita)) < 4 or _normal(cita) not in base:
            descartados.append(f'{ticker or "-"}: {h.get("titulo")} (la cita no está en los datos)')
            continue
        if ticker and ticker not in tickers:
            descartados.append(f'{ticker}: {h.get("titulo")} (no es un ticker de lo publicado)')
            continue
        tipo = h.get('tipo') if h.get('tipo') in TIPOS else 'otro'
        clave = f'{tipo}:{ticker}' if ticker else f'{tipo}:' + hashlib.sha1(
            _normal(h['titulo']).encode()).hexdigest()[:10]
        validos.append({'clave': clave, 'ticker': ticker, 'tipo': tipo,
                        'titulo': str(h['titulo']).strip()[:120],
                        'por_que': str(h.get('por_que') or '').strip()[:600], 'cita': cita[:300],
                        'donde_mirar': str(h.get('donde_mirar') or '').strip()[:200]})
    return validos, descartados


def revisar_con_claude(datos: dict, ya_abiertas: list[str]) -> tuple[list[dict], list[str], str | None]:
    """(hallazgos verificados, descartados, motivo si no se pudo preguntar)."""
    if not os.environ.get('ANTHROPIC_API_KEY'):
        return [], [], 'sin ANTHROPIC_API_KEY'
    from claude_research import MODEL, parse_json
    from groq_utils import claude_chat
    entrada = json.dumps({**datos, 'ya_abiertas': ya_abiertas}, ensure_ascii=False, default=str)
    texto = claude_chat([{'role': 'user', 'content': entrada}], model=MODEL, system=SYSTEM,
                        max_tokens=MAX_TOKENS)
    if not texto:
        return [], [], 'Claude no respondió (presupuesto, crédito o API caída)'
    respuesta = parse_json(texto)
    if 'hallazgos' not in respuesta:
        return [], [], 'respuesta sin JSON de hallazgos (¿cortada?)'
    tickers = {f['ticker'] for f in datos['lista_value_us'] if f.get('ticker')}
    tickers |= set((datos.get('cambios_desde_ayer') or {}).get('salen', []))
    tickers |= set(datos.get('se_venden_por_dejar_de_ser_prioridad') or {})
    validos, descartados = verificar(respuesta['hallazgos'], entrada, tickers)
    return validos, descartados, None


# ── GitHub ───────────────────────────────────────────────────────────────────

class GitHub:
    """Lo justo de la API de incidencias, con el token del propio workflow."""

    def __init__(self, repo: str, token: str):
        import requests
        self.s = requests.Session()
        self.s.headers.update({'Authorization': f'Bearer {token}',
                               'Accept': 'application/vnd.github+json',
                               'User-Agent': 'StockAnalyzerResearch/1.0'})
        self.url = f'https://api.github.com/repos/{repo}'

    def conocidas(self) -> dict[str, str]:
        """{clave: título} de lo que no hay que volver a abrir: lo abierto y lo que se
        cerró como «no es un problema» (not_planned). Lo cerrado como arreglado sí
        vuelve a abrirse si reaparece: eso es una recaída."""
        claves = {}
        for pagina in (1, 2, 3):
            r = self.s.get(f'{self.url}/issues', params={'labels': ETIQUETA, 'state': 'all',
                                                         'per_page': 100, 'page': pagina}, timeout=20)
            r.raise_for_status()
            lote = r.json()
            for i in lote:
                if i.get('state') == 'closed' and i.get('state_reason') != 'not_planned':
                    continue
                m = re.search(r'<!-- revisor:(.+?) -->', i.get('body') or '')
                if m:
                    claves[m.group(1)] = i.get('title', '')
            if len(lote) < 100:
                break
        return claves

    def abrir(self, titulo: str, cuerpo: str) -> int:
        self.s.post(f'{self.url}/labels', json={'name': ETIQUETA, 'color': '5319e7',
                                                'description': 'Lo encontró el revisor nocturno'},
                    timeout=20)   # 422 si ya existe: da igual
        r = self.s.post(f'{self.url}/issues', json={'title': titulo, 'body': cuerpo,
                                                    'labels': [ETIQUETA]}, timeout=20)
        r.raise_for_status()
        return int(r.json()['number'])


def cuerpo(h: dict, hoy: str) -> str:
    partes = [f"**Qué no cuadra:** {h['por_que']}", f"**La prueba:** `{h['cita']}`"]
    if h.get('donde_mirar'):
        partes.append(f"**Dónde mirar:** {h['donde_mirar']}")
    partes.append(f'Lo encontró el revisor nocturno el {hoy}.\n\n<!-- revisor:{h["clave"]} -->')
    return '\n\n'.join(partes)


def titulo(h: dict) -> str:
    return f"{h['ticker']}: {h['titulo']}" if h.get('ticker') else h['titulo']


# ── Principal ────────────────────────────────────────────────────────────────

def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--seco', action='store_true', help='no abre incidencias, solo las enseña')
    p.add_argument('--sin-ia', action='store_true', help='solo la parte sin Claude')
    args = p.parse_args(argv)

    hoy = date.today().isoformat()
    informe = {'fecha': hoy, 'estado': 'ok', 'hallazgos': [], 'descartados': [],
               'incidencias_nuevas': [], 'avisos': []}
    token, repo = os.environ.get('GITHUB_TOKEN'), os.environ.get('GITHUB_REPOSITORY')
    gh = GitHub(repo, token) if token and repo and not args.seco else None
    conocidas: dict[str, str] = {}
    try:
        datos, deterministas = hechos(hoy)
        conocidas = gh.conocidas() if gh else {}

        con_ia: list[dict] = []
        if not args.sin_ia:
            con_ia, informe['descartados'], motivo = revisar_con_claude(datos, list(conocidas.values()))
            if motivo:
                informe['avisos'].append(f'sin revisión de Claude: {motivo}')
                if os.environ.get('ANTHROPIC_API_KEY'):
                    con_ia.append(_sobre_si_mismo('sin_claude', 'el revisor no pudo preguntar a Claude',
                                                  motivo))
        hallazgos = deterministas + con_ia
        informe['hallazgos'] = hallazgos
        _abrir_nuevas(gh, hallazgos, conocidas, hoy, informe)
        print(f'[revisor] {len(hallazgos)} hallazgo(s), {len(informe["incidencias_nuevas"])} '
              f'incidencia(s) nueva(s), {len(informe["descartados"])} descartado(s) por no citar los datos')
    except Exception as e:   # el informe se escribe siempre: un revisor caído no puede callar
        informe['estado'] = 'error'
        informe['avisos'].append(f'{type(e).__name__}: {e}'[:300])
        print(f'[revisor] ⚠️  {informe["avisos"][-1]}')
        try:
            _abrir_nuevas(gh, [_sobre_si_mismo(f'error:{type(e).__name__}', 'el revisor nocturno falló',
                                               informe['avisos'][-1])], conocidas, hoy, informe)
        except Exception as e2:
            print(f'[revisor] tampoco pudo abrir la incidencia: {e2}')
    finally:
        INFORME.write_text(json.dumps(informe, ensure_ascii=False, indent=2, default=str))
    return 0


def _sobre_si_mismo(clave: str, titulo_: str, motivo: str) -> dict:
    return {'clave': f'revisor:{clave}', 'ticker': None, 'tipo': 'otro', 'titulo': titulo_,
            'por_que': motivo, 'cita': motivo[:120],
            'donde_mirar': 'el paso «Revisor nocturno» del workflow y docs/revisor.json'}


def _abrir_nuevas(gh, hallazgos: list[dict], conocidas: dict, hoy: str, informe: dict) -> None:
    nuevas = [h for h in hallazgos if h['clave'] not in conocidas][:MAX_NUEVAS]
    for h in nuevas:
        print(f'  • {titulo(h)} — {h["por_que"]}')
        if gh:
            informe['incidencias_nuevas'].append(gh.abrir(titulo(h), cuerpo(h, hoy)))
            conocidas[h['clave']] = titulo(h)


if __name__ == '__main__':
    raise SystemExit(main())
