#!/usr/bin/env python3
"""
Commodity Scanner — ETFs de materias primas via yfinance.

Outputs docs/commodity_opportunities.csv con precio vs media histórica,
momentum, señal de ciclo y VALUE rating.

Universe:
  Metales preciosos: GLD, SLV, PPLT (platino), PALL (paladio)
  Energía: USO (petróleo), UNG (gas natural), BNO (Brent)
  Metales industriales: COPX (cobre mineras), DBB (metales base)
  Agrícolas: WEAT (trigo), CORN (maíz), SOYB (soja), JO (café), NIB (cacao), BAL (algodón), CANE (azúcar)
  Diversificados: DJP, DBC, PDBC (sin rollover cost), GSG

Todos los tickers del universo son ETFs domiciliados en EEUU — PRIIPS/KID
los bloquea para minoristas UE (igual que SGOV en bonos), IBKR Ireland
incluido. `ibkr_ireland` refleja eso (False para todos). `eu_alternative`
apunta al ETC UCITS equivalente verificado (yfinance, precio real) que SÍ es
comprable — mismo patrón que IB01.L en bond_scanner.py.
"""
from __future__ import annotations

import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

DOCS   = Path("docs")
OUTPUT = DOCS / "commodity_opportunities.csv"

# ─── Universe ────────────────────────────────────────────────────────────────
# (ticker, display_name, commodity_type, sector, currency, eu_alternative)
# eu_alternative: ETC UCITS verificado por yfinance (precio real, ver commit),
# comprable en IBKR Ireland. None si no se encontró equivalente líquido.
UNIVERSE = [
    # ── Metales preciosos ─────────────────────────────────────────────────────
    ("GLD",     "SPDR Gold Shares",               "Precious_Metal", "Oro",            "USD", "SGLN.L"),
    ("SLV",     "iShares Silver Trust",            "Precious_Metal", "Plata",          "USD", "PHAG.L"),
    ("PPLT",    "Aberdeen Platinum ETF",           "Precious_Metal", "Platino",        "USD", "PHPT.L"),
    ("PALL",    "Aberdeen Palladium ETF",          "Precious_Metal", "Paladio",        "USD", "PHPD.L"),
    # ── Energía ───────────────────────────────────────────────────────────────
    ("USO",     "United States Oil Fund",          "Energy",         "Petróleo WTI",  "USD", "CRUD.L"),
    ("BNO",     "United States Brent Oil",         "Energy",         "Petróleo Brent","USD", "BRNT.L"),
    ("UNG",     "United States Natural Gas",       "Energy",         "Gas Natural",   "USD", "NGAS.L"),
    # ── Metales industriales ──────────────────────────────────────────────────
    # COPX es equity de mineras de cobre, no cobre físico — COPA.L (físico) es
    # el proxy UCITS más líquido disponible; no es exposición idéntica.
    ("COPX",    "Global X Copper Miners ETF",      "Industrial",     "Cobre",          "USD", "COPA.L"),
    ("DBB",     "Invesco DB Base Metals Fund",     "Industrial",     "Metales Base",   "USD", "AIGI.L"),
    # ── Agrícolas ─────────────────────────────────────────────────────────────
    ("WEAT",    "Teucrium Wheat Fund",             "Agricultural",   "Trigo",          "USD", "WEAT.L"),
    ("CORN",    "Teucrium Corn Fund",              "Agricultural",   "Maíz",           "USD", "CORN.L"),
    ("SOYB",    "Teucrium Soybean Fund",           "Agricultural",   "Soja",           "USD", "SOYB.L"),
    ("JO",      "iPath Bloomberg Coffee ETN",      "Agricultural",   "Café",           "USD", "COFF.L"),
    ("NIB",     "iPath Bloomberg Cocoa ETN",       "Agricultural",   "Cacao",          "USD", "COCO.L"),
    ("BAL",     "iPath Bloomberg Cotton ETN",      "Agricultural",   "Algodón",        "USD", "COTN.L"),
    ("CANE",    "Teucrium Sugar Fund",             "Agricultural",   "Azúcar",         "USD", "SUGA.L"),
    # ── Diversificados ────────────────────────────────────────────────────────
    ("PDBC",    "Invesco Optimum Yield Diversified","Diversified",   "Diversificado",  "USD", "CMOD.L"),
    ("DBC",     "Invesco DB Commodity Index",      "Diversified",    "Diversificado",  "USD", "AIGC.L"),
    ("GSG",     "iShares GSCI Commodity ETF",      "Diversified",    "Diversificado",  "USD", "CMOD.L"),
]

# Yield histórico de precio medio a 5 años (precio medio aprox en USD)
# Fuente: medias históricas conocidas para comparar si está caro/barato
# Se usan como referencia de "valor justo" en ausencia de yield explícito
HIST_AVG_PRICE_RATIO = {
    # ratio actual/media5a > 1.15 → caro, < 0.85 → atractivo
    # valores curados manualmente basados en datos históricos
    "GLD":  1.0,   # se calcula dinámicamente con 52w
    "SLV":  1.0,
    "PPLT": 1.0,
    "PALL": 1.0,
    "USO":  1.0,
    "BNO":  1.0,
    "UNG":  1.0,
    "COPX": 1.0,
    "DBB":  1.0,
    "WEAT": 1.0,
    "CORN": 1.0,
    "SOYB": 1.0,
    "JO":   1.0,
    "NIB":  1.0,
    "BAL":  1.0,
    "CANE": 1.0,
    "PDBC": 1.0,
    "DBC":  1.0,
    "GSG":  1.0,
}

# Descripción de ciclo por tipo de commodity
CYCLE_CONTEXT = {
    "Precious_Metal": {
        "driver":   "tipos reales, dólar, riesgo geopolítico",
        "bullish":  "tipos reales bajos o negativos, dólar débil, incertidumbre macro",
        "bearish":  "tipos reales altos, dólar fuerte, risk-on prolongado",
    },
    "Energy": {
        "driver":   "OPEC+, crecimiento global, inventarios, geopolítica",
        "bullish":  "OPEC+ recorta producción, demanda China fuerte, tensiones Oriente Medio",
        "bearish":  "recesión global, shale USA en máximos, acuerdo nuclear Irán",
    },
    "Industrial": {
        "driver":   "ciclo industrial global, demanda China, transición energética",
        "bullish":  "expansión China, inversión en infraestructura, déficit de oferta",
        "bearish":  "recesión China, exceso oferta, manufactura global débil",
    },
    "Agricultural": {
        "driver":   "clima, estacionalidad, geopolítica, costes energéticos",
        "bullish":  "La Niña/El Niño, conflictos exportadores, costes fertilizante altos",
        "bearish":  "cosecha récord, invierno suave, oferta abundante",
    },
    "Diversified": {
        "driver":   "mezcla energía, metales y agrícolas — proxy inflación",
        "bullish":  "inflación al alza, debilidad dólar, ciclo expansion",
        "bearish":  "desinflación, dólar fuerte, recesión",
    },
}

# Señales estacionales conocidas (mes → tipo → sesgo)
SEASONALITY = {
    "Agricultural": {
        1: "neutral",  2: "neutral",  3: "bullish",  4: "bullish",
        5: "bullish",  6: "neutral",  7: "bearish",  8: "bearish",
        9: "neutral", 10: "neutral", 11: "neutral", 12: "neutral",
    },
    "Energy": {
        1: "bullish",  2: "neutral",  3: "neutral",  4: "bullish",
        5: "neutral",  6: "bearish",  7: "neutral",  8: "neutral",
        9: "bullish", 10: "neutral", 11: "neutral", 12: "bearish",
    },
    "Precious_Metal": {
        1: "bullish",  2: "neutral",  3: "neutral",  4: "neutral",
        5: "neutral",  6: "neutral",  7: "neutral",  8: "bullish",
        9: "bullish", 10: "neutral", 11: "neutral", 12: "neutral",
    },
    "Industrial": {
        1: "neutral",  2: "bullish",  3: "bullish",  4: "bullish",
        5: "neutral",  6: "neutral",  7: "bearish",  8: "bearish",
        9: "neutral", 10: "bullish", 11: "neutral", 12: "neutral",
    },
    "Diversified": {
        m: "neutral" for m in range(1, 13)
    },
}

DISLOCATION_BUY  = -15.0   # % bajo 52w high → compra potencial
DISLOCATION_SELL =  -2.0   # % bajo 52w high → cerca de máximos → caro


def _safe(val, default=None):
    if val is None:
        return default
    try:
        if isinstance(val, float) and math.isnan(val):
            return default
    except Exception:
        pass
    return val


def _fetch_commodity_data(ticker: str) -> dict | None:
    """Fetch commodity ETF data from yfinance."""
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}

        # Precio actual
        price = _safe(info.get("regularMarketPrice") or info.get("navPrice"))
        if price is None or price <= 0:
            fi = getattr(t, "fast_info", None)
            if fi:
                price = _safe(getattr(fi, "last_price", None))
        if price is None or price <= 0:
            print(f"  [SKIP] {ticker}: no price")
            return None

        week52_high = _safe(info.get("fiftyTwoWeekHigh"))
        week52_low  = _safe(info.get("fiftyTwoWeekLow"))
        pct_from_high = round((price / week52_high - 1) * 100, 2) if week52_high and week52_high > 0 else None
        pct_from_low  = round((price / week52_low  - 1) * 100, 2) if week52_low  and week52_low  > 0 else None

        # Rango 52 semanas normalizado (0=mínimo, 1=máximo)
        if week52_high and week52_low and week52_high > week52_low:
            range_position = round((price - week52_low) / (week52_high - week52_low), 3)
        else:
            range_position = None

        # Volatilidad implícita o histórica 30d si disponible
        volume = _safe(info.get("volume") or info.get("averageVolume"))
        avg_volume = _safe(info.get("averageVolume10days") or info.get("averageDailyVolume10Day") or info.get("averageVolume"))

        # Volume ratio vs media (proxy de interés / señal técnica)
        vol_ratio = round(volume / avg_volume, 2) if volume and avg_volume and avg_volume > 0 else None

        # Momentum precio: retorno YTD si disponible
        prev_close = _safe(info.get("previousClose") or info.get("regularMarketPreviousClose"))
        change_1d  = round((price / prev_close - 1) * 100, 2) if prev_close and prev_close > 0 else None

        short_name  = _safe(info.get("shortName") or info.get("longName"), ticker)
        expense_ratio = _safe(info.get("annualReportExpenseRatio"))
        if expense_ratio and expense_ratio < 0.005:
            expense_ratio = round(expense_ratio * 100, 3)
        elif expense_ratio:
            expense_ratio = round(expense_ratio, 3)

        # Distribución/dividend (algunos commodity ETFs distribuyen)
        raw_yield = _safe(info.get("yield") or info.get("trailingAnnualDividendYield") or info.get("dividendYield"))
        if raw_yield is not None and 0 < raw_yield < 0.20:
            dist_yield_pct = round(raw_yield * 100, 2)
        elif raw_yield is not None and raw_yield >= 0.20:
            dist_yield_pct = round(raw_yield, 2)
        else:
            dist_yield_pct = 0.0

        # Precio medio histórico aproximado via historia reciente
        try:
            hist = t.history(period="2y", interval="1mo")
            if not hist.empty and len(hist) >= 6:
                avg_2y = round(float(hist["Close"].mean()), 2)
                pct_vs_2y_avg = round((price / avg_2y - 1) * 100, 2)
            else:
                avg_2y = None
                pct_vs_2y_avg = None
        except Exception:
            avg_2y = None
            pct_vs_2y_avg = None

        return {
            "price":           round(price, 2),
            "week52_high":     round(week52_high, 2) if week52_high else None,
            "week52_low":      round(week52_low, 2)  if week52_low  else None,
            "pct_from_high":   pct_from_high,
            "pct_from_low":    pct_from_low,
            "range_position":  range_position,
            "avg_2y_price":    avg_2y,
            "pct_vs_2y_avg":   pct_vs_2y_avg,
            "vol_ratio":       vol_ratio,
            "change_1d":       change_1d,
            "dist_yield_pct":  dist_yield_pct,
            "expense_ratio_pct": expense_ratio,
            "short_name":      short_name,
        }

    except Exception as e:
        print(f"  [ERROR] {ticker}: {e}")
        return None


def _value_rating(
    commodity_type: str,
    pct_from_high: float | None,
    pct_vs_2y_avg: float | None,
    range_position: float | None,
    seasonality_signal: str,
) -> str:
    """Score VALUE rating para commodities."""
    score = 0

    # 1. Precio vs media 2 años (señal más fiable si disponible)
    if pct_vs_2y_avg is not None:
        if pct_vs_2y_avg <= -15:
            score += 3    # muy por debajo de media → atractivo
        elif pct_vs_2y_avg <= -5:
            score += 2
        elif pct_vs_2y_avg <= 0:
            score += 1    # ligeramente bajo media
        elif pct_vs_2y_avg <= 10:
            score -= 1    # sobre media
        else:
            score -= 2    # muy sobre media → caro

    # 2. Posición en rango 52 semanas (0=mínimo, 1=máximo)
    if range_position is not None:
        if range_position <= 0.20:
            score += 2    # cerca de mínimos anuales
        elif range_position <= 0.35:
            score += 1
        elif range_position >= 0.85:
            score -= 2    # cerca de máximos anuales
        elif range_position >= 0.70:
            score -= 1

    # 3. Estacionalidad
    if seasonality_signal == "bullish":
        score += 1
    elif seasonality_signal == "bearish":
        score -= 1

    # Umbrales por tipo de activo
    if score >= 4:
        return "MUY_ATRACTIVO"
    elif score >= 2:
        return "ATRACTIVO"
    elif score >= 0:
        return "NEUTRAL"
    else:
        return "CARO"


def _momentum_signal(
    pct_from_high: float | None,
    range_position: float | None,
    pct_vs_2y_avg: float | None,
) -> str:
    """Señal técnica de momentum: SOBRECOMPRADO / NEUTRAL / SOBREVENDIDO."""
    score = 0
    if range_position is not None:
        if range_position >= 0.80:
            score += 2
        elif range_position >= 0.60:
            score += 1
        elif range_position <= 0.25:
            score -= 2
        elif range_position <= 0.40:
            score -= 1
    if pct_vs_2y_avg is not None:
        if pct_vs_2y_avg >= 15:
            score += 1
        elif pct_vs_2y_avg <= -10:
            score -= 1
    if score >= 2:
        return "SOBRECOMPRADO"
    elif score <= -2:
        return "SOBREVENDIDO"
    return "NEUTRAL"


def _recommendation(
    commodity_type: str,
    sector: str,
    value_rating: str,
    momentum: str,
    seasonality: str,
    pct_vs_2y_avg: float | None,
    range_position: float | None,
) -> str:
    ctx = CYCLE_CONTEXT.get(commodity_type, {})

    if value_rating in ("MUY_ATRACTIVO", "ATRACTIVO"):
        if momentum == "SOBREVENDIDO":
            return f"{sector}: precio en zona de valor con momentum negativo — posible acumulación gradual. {ctx.get('bullish', '')}"
        if seasonality == "bullish":
            return f"{sector}: atractivo por precio Y viento estacional a favor. Entrada con convicción. {ctx.get('bullish', '')}"
        return f"{sector}: por debajo de su media histórica. Buena zona de entrada si el catalizador acompaña. {ctx.get('bullish', '')}"

    if value_rating == "NEUTRAL":
        return f"{sector}: precio en zona justa según medias históricas. Esperar señal técnica o catalizador. {ctx.get('driver', '')}"

    # CARO
    if momentum == "SOBRECOMPRADO":
        return f"{sector}: precio extendido sobre media histórica y sobrecomprado técnicamente. Evitar entrada nueva, gestionar stop si ya tienes posición. {ctx.get('bearish', '')}"
    return f"{sector}: caro respecto a media histórica. No es momento de entrada. {ctx.get('bearish', '')}"


def scan() -> pd.DataFrame:
    now = datetime.now(timezone.utc)
    current_month = now.month
    rows = []

    print(f"\n{'='*60}")
    print(f"Commodity Scanner — {now.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}")

    for ticker, name, commodity_type, sector, currency, eu_alt in UNIVERSE:
        print(f"  Fetching {ticker:8s} ({sector})...", end=" ")
        data = _fetch_commodity_data(ticker)
        time.sleep(0.5)  # rate limit

        if data is None:
            print("SKIP")
            continue

        # Estacionalidad del mes actual
        seas_map = SEASONALITY.get(commodity_type, {})
        seasonality_signal = seas_map.get(current_month, "neutral")

        value_rating = _value_rating(
            commodity_type     = commodity_type,
            pct_from_high      = data["pct_from_high"],
            pct_vs_2y_avg      = data["pct_vs_2y_avg"],
            range_position     = data["range_position"],
            seasonality_signal = seasonality_signal,
        )

        momentum = _momentum_signal(
            pct_from_high  = data["pct_from_high"],
            range_position = data["range_position"],
            pct_vs_2y_avg  = data["pct_vs_2y_avg"],
        )

        recommendation = _recommendation(
            commodity_type = commodity_type,
            sector         = sector,
            value_rating   = value_rating,
            momentum       = momentum,
            seasonality    = seasonality_signal,
            pct_vs_2y_avg  = data["pct_vs_2y_avg"],
            range_position = data["range_position"],
        )

        ctx = CYCLE_CONTEXT.get(commodity_type, {})

        rows.append({
            "ticker":            ticker,
            "name":              name,
            "short_name":        data["short_name"],
            "commodity_type":    commodity_type,
            "sector":            sector,
            "currency":          currency,
            "ibkr_ireland":      False,   # ticker US, bloqueado PRIIPS — ver eu_alternative
            "eu_alternative":    eu_alt or "",
            "price":             data["price"],
            "week52_high":       data["week52_high"],
            "week52_low":        data["week52_low"],
            "pct_from_high":     data["pct_from_high"],
            "pct_from_low":      data["pct_from_low"],
            "range_position":    data["range_position"],
            "avg_2y_price":      data["avg_2y_price"],
            "pct_vs_2y_avg":     data["pct_vs_2y_avg"],
            "vol_ratio":         data["vol_ratio"],
            "change_1d":         data["change_1d"],
            "dist_yield_pct":    data["dist_yield_pct"],
            "expense_ratio_pct": data["expense_ratio_pct"],
            "momentum_signal":   momentum,
            "seasonality":       seasonality_signal,
            "value_rating":      value_rating,
            "recommendation":    recommendation,
            "cycle_driver":      ctx.get("driver", ""),
            "cycle_bullish":     ctx.get("bullish", ""),
            "cycle_bearish":     ctx.get("bearish", ""),
            "generated_at":      now.isoformat(),
        })

        rating_emoji = {"MUY_ATRACTIVO": "🟢", "ATRACTIVO": "🟡", "NEUTRAL": "⚪", "CARO": "🔴"}.get(value_rating, "❓")
        print(f"{rating_emoji} {value_rating:15s} rng={data.get('range_position', '?')} 2y={data.get('pct_vs_2y_avg', '?')}%")

    df = pd.DataFrame(rows)
    if df.empty:
        print("\n[WARN] No data fetched — output empty")
        return df

    # Ordenar: mejor rating primero, luego por range_position ascendente (más barato primero)
    rating_order = {"MUY_ATRACTIVO": 0, "ATRACTIVO": 1, "NEUTRAL": 2, "CARO": 3, "SIN_DATO": 4}
    df["_r"] = df["value_rating"].map(rating_order).fillna(4)
    df["_rng"] = df["range_position"].fillna(0.5)
    df = df.sort_values(["_r", "_rng"]).drop(columns=["_r", "_rng"]).reset_index(drop=True)

    DOCS.mkdir(exist_ok=True)
    df.to_csv(OUTPUT, index=False)
    print(f"\n✅ Guardado: {OUTPUT} ({len(df)} commodities)")

    # Resumen
    for rating in ["MUY_ATRACTIVO", "ATRACTIVO", "NEUTRAL", "CARO"]:
        n = len(df[df["value_rating"] == rating])
        if n:
            tickers = ", ".join(df[df["value_rating"] == rating]["ticker"].tolist())
            print(f"  {rating}: {n} — {tickers}")

    return df


if __name__ == "__main__":
    scan()
