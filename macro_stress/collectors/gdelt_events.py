"""GDELT 2.0 DOC API collector — free, no key required."""
from __future__ import annotations

import logging
import time
from typing import Optional

import pandas as pd
import requests

log = logging.getLogger(__name__)

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

REGION_QUERIES = {
    "hormuz": '"Strait of Hormuz" OR Hormuz',
    "suez": '"Suez Canal" OR Suez',
    "red_sea": '"Red Sea" OR Houthi',
    "black_sea": '"Black Sea"',
    "taiwan_strait": '"Taiwan Strait"',
    "panama": '"Panama Canal"',
}


def _build_query(regions: list[str], keywords: list[str]) -> str:
    region_q = " OR ".join(REGION_QUERIES.get(r, r) for r in regions)
    kw_q = " OR ".join(keywords)
    if region_q and kw_q:
        return f"({region_q}) AND ({kw_q})"
    return region_q or kw_q


# GDELT pide una petición cada 5 segundos y contesta 429 si no. Antes se
# hacían dos seguidas (24h y 30d) y caían siempre.
ESPERA_429 = 6.0


def _fetch_timeline(query: str, timespan: str) -> Optional[pd.DataFrame]:
    """Nº de artículos por día. El modo ArtList devolvía como mucho 75
    artículos en cada ventana, así que un día con 75 noticias daba 75 frente a
    75/30 de media: escalada 100 siempre que hubiera algo de ruido."""
    params = {
        "query": query,
        "mode": "TimelineVolRaw",
        "format": "json",
        "timespan": timespan,
    }
    resp = None
    for intento in range(2):
        try:
            resp = requests.get(GDELT_URL, params=params, timeout=30)
        except Exception as e:
            log.warning("GDELT fetch failed: %s", e)
            return None
        if resp.status_code != 429:
            break
        if intento == 0:
            time.sleep(ESPERA_429)
    if resp is None or resp.status_code != 200:
        log.warning("GDELT fetch failed: HTTP %s", getattr(resp, "status_code", "?"))
        return None
    try:
        data = resp.json()["timeline"][0]["data"]
    except (ValueError, KeyError, IndexError, TypeError):
        log.warning("GDELT respuesta sin timeline para query=%s", query[:80])
        return None
    df = pd.DataFrame({
        "value": [pd.to_numeric(p.get("value"), errors="coerce") for p in data],
        "norm": [pd.to_numeric(p.get("norm"), errors="coerce") for p in data],
    }, index=pd.to_datetime([p.get("date") for p in data], format="%Y%m%dT%H%M%SZ",
                            errors="coerce", utc=True))
    df = df[df.index.notna()].dropna(subset=["value"])
    return df if not df.empty else None


def _dias_completos(df: pd.DataFrame, ahora: pd.Timestamp) -> pd.DataFrame:
    """Quita el día en curso (a las 05:30 UTC lleva cinco horas) y, si GDELT da
    el total de artículos procesados (`norm`), los días con la ingesta a medias:
    el 26-oct-2026 traía 15 noticias de la consulta frente a ~500 de un día
    normal, y eso es GDELT con retraso, no el Estrecho en calma."""
    dias = df[df.index < ahora.floor("D")]
    norm = dias["norm"].dropna()
    if not norm.empty:
        return dias[dias["norm"] >= 0.5 * norm.median()]
    # Sin `norm` no se distingue retraso de calma; un desplome de la consulta
    # en los últimos días es casi siempre lo primero. Se cortan esos días del
    # final: peor un día menos que un cero que pasa por tranquilidad.
    suelo = 0.25 * dias["value"].median()
    while len(dias) and dias["value"].iloc[-1] < suelo:
        dias = dias.iloc[:-1]
    return dias


def fetch(regions: list[str], keywords: list[str]) -> Optional[dict]:
    """Return `{event_count_24h, event_count_30d, escalation_score}` or None on failure."""
    query = _build_query(regions, keywords)
    if not query:
        return None

    df = _fetch_timeline(query, "1m")
    if df is None:
        return None
    dias = _dias_completos(df, pd.Timestamp.now(tz="UTC"))
    if len(dias) < 10:
        log.warning("GDELT: solo %d días completos, sin base para comparar", len(dias))
        return None

    # Cuota de noticias sobre el total procesado si GDELT la da: un domingo
    # hay menos de todo, no menos tensión.
    medida = dias["value"] / dias["norm"] if dias["norm"].notna().all() else dias["value"]
    ultimo = float(medida.iloc[-1])
    base = float(medida.iloc[:-1].median())
    ratio = ultimo / base if base > 0 else 0.0
    count_24h = int(dias["value"].iloc[-1])
    count_30d = int(dias["value"].sum())

    # escalation: 0..100 where 100 = 4x normal or worse
    escalation_score = int(max(0.0, min(100.0, (ratio / 4.0) * 100.0)))

    return {
        "event_count_24h": count_24h,
        "event_count_30d": count_30d,
        "escalation_score": escalation_score,
        "query": query,
    }
