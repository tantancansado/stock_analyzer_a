#!/usr/bin/env python3
"""
CURATED TICKER UNIVERSE
Universo de ~120 empresas de alta calidad seleccionadas con filtros estrictos.
Organizadas en 4 tiers por solidez del moat y calidad de negocio.

Source: Análisis curado por analista de datos financieros (Abril 2026)
"""

# ── TIER 1 — Élite (★★★★★) ────────────────────────────────────────────────────
# Negocios con fosos defensivos excepcionales, retornos sobre capital sostenidos,
# pricing power demostrado. Las mejores del mundo en su categoría.

TIER_1 = [
    'VRSK',    # Verisk Analytics — data/analytics monopoly
    'RELX',    # RELX Group — information services
    'WTKWY',   # Wolters Kluwer — professional info (ADR)
    'WCN',     # Waste Connections
    'WM',      # Waste Management
    'V',       # Visa
    'CTAS',    # Cintas
    'LIN',     # Linde
    'ROP',     # Roper Technologies
    'ADP',     # Automatic Data Processing
    'ROL',     # Rollins (pest control)
    'MSI',     # Motorola Solutions
    'SPGI',    # S&P Global
    'COST',    # Costco
    'CPRT',    # Copart
    'MMC',     # Marsh & McLennan (Tier 1 insurance/consulting)
    'MA',      # Mastercard
    'AI.PA',   # Air Liquide (Euronext Paris)
    'CME',     # CME Group
    'RSG',     # Republic Services
    'HESAY',   # Hermès International (ADR)
    'VRSN',    # VeriSign
]

# ── TIER 2 — Alta convicción (★★★★☆) ─────────────────────────────────────────
# Negocios de alta calidad con moats sólidos. Pueden tener ciclicidad moderada
# o mayor dependencia del crecimiento futuro para justificar valoración.

TIER_2 = [
    'BR',      # Broadridge Financial Solutions
    'CSU.TO',  # Constellation Software (Toronto)
    'ZTS',     # Zoetis
    'MSFT',    # Microsoft
    'KO',      # Coca-Cola
    'MSCI',    # MSCI Inc.
    'MCO',     # Moody's Corp
    'INTU',    # Intuit
    'PAYX',    # Paychex
    'PG',      # Procter & Gamble
    'IDXX',    # IDEXX Laboratories
    'GVDNY',   # Givaudan (ADR)
    'SYK',     # Stryker
    'TW',      # Tradeweb Markets
    'TMO',     # Thermo Fisher Scientific
    'AON',     # Aon
    'VLTO',    # Veralto
    'TYL',     # Tyler Technologies
    'SHW',     # Sherwin-Williams
    'WMT',     # Walmart
    'FICO',    # Fair Isaac (FICO)
    'VEEV',    # Veeva Systems
    'ERIE',    # Erie Indemnity
    'CLPBY',   # Coloplast (ADR)
    'ECL',     # Ecolab
    'LRLCY',   # L'Oréal (ADR)
    'AJG',     # Arthur J. Gallagher
    'CNI',     # Canadian National Railway
    'ICE',     # Intercontinental Exchange
    'LSEG.L',  # London Stock Exchange Group (LSE)
    'AZO',     # AutoZone
    'DBOEY',   # Deutsche Börse AG (ADR)
    'WST',     # West Pharmaceutical Services
    'MCD',     # McDonald's
    'MTD',     # Mettler-Toledo
    'DSGX',    # Descartes Systems (logistics software)
    'BRO',     # Brown & Brown (insurance)
    '7741.T',  # Hoya Corporation (Tokyo)
    'ORLY',    # O'Reilly Automotive
]

# ── TIER 3 — Convicción parcial (★★★☆☆) ──────────────────────────────────────
# Buenas empresas con moats reales pero con más matices: valoración exigente,
# ciclicidad, transición de negocio, o ventaja competitiva más estrecha.

TIER_3 = [
    'RACE',    # Ferrari
    'SAP',     # SAP SE (ADR)
    'NOW',     # ServiceNow
    'BRK-B',   # Berkshire Hathaway B
    'DHR',     # Danaher
    'OTIS',    # Otis Worldwide
    'EXPN.L',  # Experian (LSE)
    'HEI',     # HEICO
    'SXYAY',   # Sika AG (ADR)
    'ITW',     # Illinois Tool Works
    'CDNS',    # Cadence Design Systems
    'CHD',     # Church & Dwight
    'ASAZY',   # Assa Abloy AB (ADR)
    'ETN',     # Eaton Corporation
    'ABT',     # Abbott Laboratories
    'IT',      # Gartner
    'NDAQ',    # Nasdaq Inc.
    'SBGSY',   # Schneider Electric (ADR)
    'TT',      # Trane Technologies
    'CB',      # Chubb
    'FDS',     # FactSet Research
    'FAST',    # Fastenal
    'PGR',     # Progressive Corp
    'EQIX',    # Equinix
    'CL',      # Colgate-Palmolive
    'AME',     # AMETEK
    'ATLKY',   # Atlas Copco (ADR)
    'NDSN',    # Nordson
    'TNE.AX',  # Technology One (ASX)
    'AWK',     # American Water Works
    'PEP',     # PepsiCo
    'AXP',     # American Express
    'ESLOY',   # EssilorLuxottica (ADR)
    'TJX',     # TJX Companies
    'CP',      # Canadian Pacific Railway (Kansas City)
    'JNJ',     # Johnson & Johnson
    'CBOE',    # Cboe Global Markets
    'MKC',     # McCormick & Co.
    'GWW',     # W.W. Grainger
    'JKHY',    # Jack Henry & Associates
    'AUTO.L',  # Auto Trader Group (LSE)
    'ITRK.L',  # Intertek Group (LSE)
    'G24.DE',  # Scout24 (Xetra)
    'ISRG',    # Intuitive Surgical
]

# ── TIER 4 — No apta para portfolios apalancados (★★☆☆☆) ─────────────────────
# Empresas reconocibles con negocios de calidad, pero que presentan alguno de:
# valoración extrema, moat en deterioro, disrupción tecnológica, o dependencia
# excesiva del ciclo. No recomendadas para posiciones concentradas.
# Incluidas como referencia de universo completo.

TIER_4 = [
    'ADSK',    # Autodesk
    'BLK',     # BlackRock
    'ODFL',    # Old Dominion Freight Line
    'APH',     # Amphenol
    'ATO',     # Atmos Energy
    'DOL.TO',  # Dollarama (Toronto)
    '4684.T',  # Obic (Tokyo)
    'TLC.AX',  # The Lottery Corporation (ASX)
    'MANH',    # Manhattan Associates
    'UNP',     # Union Pacific
    'VCISY',   # Vinci SA (ADR)
    'SGSOY',   # SGS SA (ADR)
    'FERG',    # Ferguson Enterprises
    'ORCL',    # Oracle
    'PSA',     # Public Storage
    'HD',      # Home Depot
    'ASML',    # ASML Holding
    'KYCCF',   # Kyocera (OTC)
    'GOOG',    # Alphabet
    'AMZN',    # Amazon
    'CRH',     # CRH plc
    'MLM',     # Martin Marietta Materials
    'YUM',     # Yum! Brands
    'FTNT',    # Fortinet
    'HLT',     # Hilton Worldwide
    'LMT',     # Lockheed Martin
    'EFX',     # Equifax
    'RMD',     # ResMed
    '6383.T',  # Daifuku (Tokyo)
    'AAPL',    # Apple
    'GGG',     # Graco
    'META',    # Meta Platforms
]


# ── HF WATCH — Carteras de grandes inversores (seguimiento, no scoring curado) ─
# Tickers mantenidos por Buffett/Ackman/Tepper que NO están en Tier 1-4.
# Se incluyen en el scoring pipeline como universo ampliado para detectar
# oportunidades VALUE que el sistema curado no cubre.
# NO se usan para momentum ni para señales de alta convicción por defecto.

HF_WATCH = [
    # ── Berkshire Hathaway (Buffett) ──────────────────────────────────────────
    'OXY',    # Occidental Petroleum — posición masiva de Buffett
    'BAC',    # Bank of America — segunda posición de Berkshire
    'COF',    # Capital One Financial — bancos/crédito
    'CVX',    # Chevron — energía
    'DVA',    # DaVita — diálisis
    'KHC',    # Kraft Heinz — consumo (posición problemática de Buffett)
    'KR',     # Kroger — supermercados
    'UNH',    # UnitedHealth Group — seguros/salud
    'ALLY',   # Ally Financial — banco digital
    'CHTR',   # Charter Communications — cable/broadband
    'NVR',    # NVR Inc — homebuilder premium
    'POOL',   # Pool Corp — distribuidor de piscinas
    'STZ',    # Constellation Brands — alcohol premium
    'NUE',    # Nucor — acero (mejor operador del sector)
    'DPZ',    # Domino's Pizza
    'NYT',    # New York Times — medios con suscripción recurrente
    'LPX',    # Louisiana-Pacific — building products
    'LEN',    # Lennar — homebuilder

    # ── Pershing Square (Ackman) ──────────────────────────────────────────────
    'BN',     # Brookfield Corporation — asset management alternativo
    'QSR',    # Restaurant Brands (Burger King / Tim Hortons / Popeyes)
    'UBER',   # Uber Technologies
    'HHH',    # Howard Hughes Holdings — real estate dev

    # ── Appaloosa (Tepper) — solo posiciones con suficiente liquidez ──────────
    'TEVA',   # Teva Pharmaceutical — genéricos, posición de valor
    'KVUE',   # Kenvue — consumer health (spinoff J&J)
    'THC',    # Tenet Healthcare — hospitales
    'GPK',    # Graphic Packaging — packaging
    'TECK',   # Teck Resources — minería de cobre
    'HRI',    # Herc Holdings — alquiler de equipos
    'FHN',    # First Horizon National — banca regional
    'FCNCA',  # First Citizens BancShares — banca regional (adquirió SVB)
    'KD',     # Kyndryl Holdings — IT services (spinoff IBM)
]


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_universe(include_tier4: bool = False, include_hf_watch: bool = False) -> list:
    """
    Retorna el universo de tickers para scoring.
    Por defecto Tier 1+2+3 (excluye Tier 4 'No apta' y HF_WATCH).
    """
    universe = TIER_1 + TIER_2 + TIER_3
    if include_tier4:
        universe += TIER_4
    if include_hf_watch:
        universe += HF_WATCH
    return list(dict.fromkeys(universe))  # deduplicate, preserve order


def get_tier(ticker: str) -> str:
    """Retorna el tier de un ticker ('1','2','3','4','HF','?')."""
    t = ticker.upper()
    if t in [x.upper() for x in TIER_1]:
        return '1'
    if t in [x.upper() for x in TIER_2]:
        return '2'
    if t in [x.upper() for x in TIER_3]:
        return '3'
    if t in [x.upper() for x in TIER_4]:
        return '4'
    if t in [x.upper() for x in HF_WATCH]:
        return 'HF'
    return '?'


def get_tier_label(tier: str) -> str:
    return {
        '1':  'Élite',
        '2':  'Alta convicción',
        '3':  'Convicción parcial',
        '4':  'No apta',
        'HF': 'HF Watch',
    }.get(tier, 'Desconocido')


ALL_TICKERS    = get_universe(include_tier4=True)
SCORED_TICKERS = get_universe(include_tier4=False)  # default scoring universe
HF_UNIVERSE    = get_universe(include_tier4=False, include_hf_watch=True)

if __name__ == '__main__':
    print(f"Tier 1 ({len(TIER_1)} tickers): {', '.join(TIER_1)}")
    print(f"Tier 2 ({len(TIER_2)} tickers): {', '.join(TIER_2)}")
    print(f"Tier 3 ({len(TIER_3)} tickers): {', '.join(TIER_3)}")
    print(f"Tier 4 ({len(TIER_4)} tickers): {', '.join(TIER_4)}")
    print(f"HF Watch ({len(HF_WATCH)} tickers): {', '.join(HF_WATCH)}")
    print(f"\nUniverse (T1+T2+T3): {len(SCORED_TICKERS)} tickers")
    print(f"HF Universe (T1+T2+T3+HF): {len(HF_UNIVERSE)} tickers")
    print(f"Full universe (all): {len(ALL_TICKERS)} tickers")
