#!/usr/bin/env python3
"""Resumen diario por correo: tu cartera, tesis rotas confirmadas por IA e ideas nuevas.

De momento solo para el usuario. Resend en modo prueba (`onboarding@resend.dev`)
solo puede escribir al dueño de la cuenta; abrirlo a otros suscriptores pide un
dominio propio verificado, y eso cuesta dinero (decisión del 27-oct-2026: no).

Coste: el resumen del día es el texto del briefing ya escrito; la IA solo se
llama para confirmar las tesis que el vigilante marca en posiciones que tienes
de verdad, que suelen ser cero o una.

Uso: python3 daily_digest_email.py [--dry-run ruta.html]
"""
from __future__ import annotations

import html
import json
import os
import sys
import urllib.request
from datetime import date
from pathlib import Path

DOCS = Path('docs')
BRIEFING = DOCS / 'daily_briefing.json'
DRIFT = DOCS / 'portfolio_tracker' / 'thesis_drift_alerts.json'
LEAPS = DOCS / 'leaps_opportunities.json'
APP_URL = 'https://tantancansado.github.io/stock_analyzer_a/app/'
REMITENTE = 'Stock Analyzer <onboarding@resend.dev>'


def _json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


# ── 1. Tu cartera ────────────────────────────────────────────────────────────

def cartera() -> list[dict] | None:
    """Acciones de la cartera real con precio de hoy. None si Supabase no responde."""
    from supabase_positions import fetch_position_rows
    filas = fetch_position_rows('ticker,shares,avg_price,asset_type')
    if filas is None:
        return None
    acciones = [f for f in filas if str(f.get('asset_type') or 'stock').lower() == 'stock'
                and f.get('ticker') and f.get('shares')]
    if not acciones:
        return []
    import yfinance as yf
    out = []
    for f in acciones:
        t = str(f['ticker']).upper()
        try:
            h = yf.Ticker(t).history(period='5d')['Close'].dropna()
        except Exception:
            h = None
        if h is None or len(h) < 2:
            out.append({'ticker': t, 'sin_precio': True})
            continue
        precio, ayer = float(h.iloc[-1]), float(h.iloc[-2])
        coste = float(f.get('avg_price') or 0)
        n = float(f['shares'])
        out.append({
            'ticker': t, 'acciones': n, 'precio': precio,
            'dia_pct': (precio / ayer - 1) * 100,
            'pl_pct': (precio / coste - 1) * 100 if coste > 0 else None,
            'valor': precio * n,
        })
    return out


# ── 2. Tesis rotas, confirmadas por IA ───────────────────────────────────────

def _estado_leaps() -> list[dict]:
    """Estado de tus LEAPS, calculado en el momento (ya no se publica en docs/)."""
    try:
        import leaps_analyzer as la
        import leaps_monitor as lm
        posiciones = lm.load_option_positions()
        if not posiciones:
            return []
        senales = la.load_app_signals()
        return [lm.analyze_position(p, senales) for p in posiciones]
    except Exception as e:
        print(f'  sin estado de LEAPS ({type(e).__name__})')
        return []


def posibles_rupturas(tenidos: set[str]) -> list[dict]:
    """Lo que los vigilantes marcan en posiciones que tienes de verdad."""
    out = []
    for a in _json(DRIFT).get('alerts') or []:
        if str(a.get('ticker', '')).upper() in tenidos:
            out.append({'ticker': a['ticker'], 'origen': 'acción',
                        'señal': a.get('reason') or a.get('type'), 'gravedad': a.get('severity')})
    for p in _estado_leaps():
        for al in p.get('alerts') or []:
            # leaps_monitor las guarda como pares [tipo, mensaje]
            tipo, msg = (al[0], al[1]) if isinstance(al, (list, tuple)) else (al.get('type'), al.get('reason'))
            if tipo == 'THESIS_BREAK':
                out.append({'ticker': p.get('ticker'), 'origen': 'LEAPS',
                            'señal': msg, 'gravedad': 'HIGH'})
    return out


def confirmar(posible: dict) -> dict:
    """Pide a la IA que confirme o descarte. Sin respuesta, queda «sin confirmar»."""
    from groq_utils import CLAUDE_HAIKU, claude_chat
    prompt = (
        f"Una posición de un inversor value a 12 meses: {posible['ticker']} ({posible['origen']}).\n"
        f"El vigilante automático ha marcado esto: {posible['señal']}\n\n"
        "¿Se ha roto la tesis de inversión (deterioro real del negocio o de la razón por la que "
        "se compró), o es ruido de precio? Usa solo lo que te doy; si no basta para decirlo, "
        "responde rota=false.\n"
        'Responde SOLO JSON: {"rota": true|false, "motivo": "una frase", '
        '"que_hacer": "una frase concreta"}'
    )
    texto = claude_chat([{'role': 'user', 'content': prompt}], model=CLAUDE_HAIKU,
                        max_tokens=400, temperature=0.0)
    try:
        t = (texto or '').strip()
        d = json.loads(t[t.index('{'): t.rindex('}') + 1])
        return {**posible, 'confirmada': bool(d.get('rota')), 'motivo': d.get('motivo', ''),
                'que_hacer': d.get('que_hacer', '')}
    except Exception:
        return {**posible, 'confirmada': None, 'motivo': 'la IA no respondió', 'que_hacer': ''}


# ── 3. Ideas nuevas ──────────────────────────────────────────────────────────

def ideas() -> dict:
    hechos = _json(BRIEFING).get('hechos') or {}
    leaps = _json(LEAPS)
    hoy = date.today().isoformat()
    return {
        'value_nuevas': hechos.get('picks_nuevos') or [],
        'comprables': [c.get('ticker') for c in hechos.get('comprables') or []],
        'leaps': [{'ticker': o['ticker'],
                   'contrato': (o.get('recommended_contract') or {}),
                   'nueva': o.get('publicada_desde') == hoy}
                  for o in leaps.get('opportunities') or []],
        'leaps_rotas': [r for r in leaps.get('retiradas') or [] if r.get('rompe')],
    }


# ── Correo ───────────────────────────────────────────────────────────────────

def _h2(t: str) -> str:
    return (f'<h2 style="font-size:15px;margin:24px 0 8px;color:#1d1d1f;'
            f'border-bottom:1px solid #e5e5ea;padding-bottom:4px">{t}</h2>')


def construir_html(pos: list[dict] | None, rupturas: list[dict], ide: dict, resumen: str) -> str:
    e = html.escape
    partes = [f'<div style="font-family:-apple-system,Helvetica,Arial,sans-serif;max-width:600px;'
              f'margin:0 auto;color:#1d1d1f;font-size:14px;line-height:1.5">',
              f'<h1 style="font-size:18px;margin:0 0 4px">Tu resumen · {date.today():%d-%m-%Y}</h1>']

    confirmadas = [r for r in rupturas if r.get('confirmada')]
    dudosas = [r for r in rupturas if r.get('confirmada') is None]
    if confirmadas:
        partes.append(_h2('🔴 Tesis rotas (confirmado por IA)'))
        for r in confirmadas:
            partes.append(f"<p><b>{e(str(r['ticker']))}</b> ({e(r['origen'])}): {e(r['motivo'])}"
                          f"<br><i>Qué hacer:</i> {e(r['que_hacer'])}</p>")
    if dudosas:
        partes.append(_h2('Para revisar (la IA no pudo confirmarlo)'))
        for r in dudosas:
            partes.append(f"<p><b>{e(str(r['ticker']))}</b>: {e(str(r['señal']))}</p>")

    partes.append(_h2('Tu cartera'))
    if pos is None:
        partes.append('<p>No se pudo leer tu cartera hoy.</p>')
    elif not pos:
        partes.append('<p>No tienes acciones añadidas en la app.</p>')
    else:
        filas = []
        for p in sorted(pos, key=lambda x: -(x.get('valor') or 0)):
            if p.get('sin_precio'):
                filas.append(f"<tr><td><b>{e(p['ticker'])}</b></td><td colspan=3>sin precio hoy</td></tr>")
                continue
            pl = f"{p['pl_pct']:+.1f}%" if p.get('pl_pct') is not None else '—'
            filas.append(f"<tr><td><b>{e(p['ticker'])}</b></td><td>{p['precio']:.2f}</td>"
                         f"<td>{p['dia_pct']:+.1f}% hoy</td><td>{pl} total</td></tr>")
        partes.append('<table cellpadding="4" style="border-collapse:collapse;font-size:13px">'
                      + ''.join(filas) + '</table>')

    lineas = []
    if ide['comprables']:
        lineas.append(f"<b>Para entrar hoy (Value):</b> {e(', '.join(ide['comprables']))}")
    if ide['value_nuevas']:
        lineas.append(f"<b>Nuevas en la lista Value:</b> {e(', '.join(ide['value_nuevas']))}")
    for l in ide['leaps']:
        c = l['contrato']
        marca = ' (nueva)' if l['nueva'] else ''
        lineas.append(f"<b>LEAPS{marca}:</b> {e(l['ticker'])} call {c.get('strike')} "
                      f"vence {e(str(c.get('expiry')))} · {c.get('cost_per_contract', 0):,.0f} $")
    for r in ide['leaps_rotas']:
        lineas.append(f"<b>LEAPS que ya no vale:</b> {e(r['ticker'])} — {e(r['motivo'])}")
    partes.append(_h2('Ideas'))
    partes.append('<p>' + ('<br>'.join(lineas) if lineas else 'Hoy no hay ideas nuevas.') + '</p>')

    if resumen:
        partes.append(_h2('El día en el mercado'))
        partes.append('<p>' + resumen.replace('\n', '<br>') + '</p>')

    partes.append(f'<p style="margin-top:28px;font-size:12px;color:#6e6e73">'
                  f'<a href="{APP_URL}">Abrir la app</a></p></div>')
    return ''.join(partes)


def asunto(rupturas: list[dict], ide: dict) -> str:
    n = sum(1 for r in rupturas if r.get('confirmada'))
    if n:
        return f'🔴 {n} tesis rota{"s" if n > 1 else ""} en tu cartera · resumen del día'
    if ide['comprables'] or any(l['nueva'] for l in ide['leaps']):
        return 'Hay ideas nuevas · resumen del día'
    return 'Tu resumen del día'


def enviar(destino: str, titulo: str, cuerpo: str) -> bool:
    clave = os.environ.get('RESEND_API_KEY', '')
    if not clave:
        print('  sin RESEND_API_KEY — no se envía')
        return False
    datos = json.dumps({'from': REMITENTE, 'to': [destino], 'subject': titulo,
                        'html': cuerpo}).encode()
    # Sin User-Agent propio, Cloudflare (delante de Resend) rechaza con 403
    # «error code: 1010» la firma por defecto de urllib.
    req = urllib.request.Request('https://api.resend.com/emails', data=datos, headers={
        'Authorization': f'Bearer {clave}', 'Content-Type': 'application/json',
        'User-Agent': 'stock-analyzer-digest/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            print(f'  correo enviado ({r.status})')
            return True
    except Exception as ex:
        cuerpo_err = getattr(ex, 'read', lambda: b'')().decode(errors='ignore')[:200]
        print(f'  ⚠️  Resend rechazó el envío: {ex} {cuerpo_err}')
        return False


def main() -> None:
    dry = '--dry-run' in sys.argv
    pos = cartera()
    tenidos = {p['ticker'] for p in pos or []}
    rupturas = [confirmar(r) for r in posibles_rupturas(tenidos)]
    ide = ideas()
    resumen = (_json(BRIEFING).get('texto') or '') if _json(BRIEFING).get('fecha') == date.today().isoformat() else ''
    cuerpo = construir_html(pos, rupturas, ide, resumen)
    titulo = asunto(rupturas, ide)
    print(f'  {len(pos or [])} posiciones · {len(rupturas)} posibles rupturas '
          f'({sum(1 for r in rupturas if r.get("confirmada"))} confirmadas) · asunto: {titulo}')
    if dry:
        destino = sys.argv[sys.argv.index('--dry-run') + 1] if len(sys.argv) > sys.argv.index('--dry-run') + 1 else 'resumen.html'
        Path(destino).write_text(cuerpo)
        print(f'  dry-run → {destino}')
        return
    destino = os.environ.get('DIGEST_EMAIL_TO', '').strip()
    if not destino:
        print('  sin DIGEST_EMAIL_TO — no se envía')
        return
    enviar(destino, titulo, cuerpo)


if __name__ == '__main__':
    main()
