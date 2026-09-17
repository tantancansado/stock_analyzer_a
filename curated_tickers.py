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
    'MRSH',    # Marsh & McLennan (Tier 1 insurance/consulting) — era 'MMC'
               # hasta el cambio de ticker; Yahoo dejó de servir MMC ("symbol
               # may be delisted") y la empresa estuvo 15+ corridas sin analizar
               # sin que nada avisara. Verificado 7-ago-2026: MRSH devuelve
               # "Marsh & McLennan Companies, Inc.", NYSE, $193,29, $92B.
    'MA',      # Mastercard
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
    'ISRG',    # Intuitive Surgical
    # Movida desde TIER_4 el 17-sep-2026 a petición del usuario, que la ve «igual
    # o más interesante» que McDonald's. Estaba en TIER_4 desde que se creó el
    # universo (13-abr) y nadie había escrito por qué: de los 33 del tier, solo
    # AVGO tenía motivo.
    #
    # El cambio es de CLASIFICACIÓN, no de visibilidad: desde el mismo día el
    # curado se puntúa entero, así que habría entrado igual quedándose en
    # TIER_4.
    #
    # A favor: crece al 12,2% contra el 3,7% de McDonald's, PER 17,3 contra
    # 20,3, y un consenso a +26,6% con 22 analistas en una horquilla estrecha
    # (147-200, 1,36x).
    #
    # QUÉ VIGILAR: su PER adelantado (19,6) es PEOR que el de hoy (17,3), o
    # sea que se espera que el beneficio BAJE. El crecimiento de BPA de +131%
    # huele a extraordinario, y mientras esté ahí el PER de hoy la hace
    # parecer más barata de lo que está. Si el scoring la premia por múltiplo
    # bajo, es ese extraordinario el que está puntuando.
    'YUM',     # Yum! Brands
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
    # Añadida el 15-sep-2026 a petición del usuario. Margen operativo 54%, ROE
    # 44% y FCF de 30.600 M la ponen en la liga de las Tier 1, pero entra en
    # TIER_4 por lo que hace incierta su valoración, no por la calidad: con PER
    # 43 hoy y 17,5 adelantado, el precio descuenta que el BPA pase de $7,83 a
    # $19,39 — y el rango de objetivos de los 47 analistas va de $216 a $715.
    # Cuando la horquilla es de 3,3x, la mediana no es un precio objetivo.
    'AVGO',    # Broadcom
    'KYCCF',   # Kyocera (OTC)
    'GOOG',    # Alphabet
    'AMZN',    # Amazon
    'CRH',     # CRH plc
    'MLM',     # Martin Marietta Materials
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

def get_universe(include_tier4: bool = True, include_hf_watch: bool = False) -> list:
    """
    Retorna el universo de tickers para scoring: el curado ENTERO.

    El tier es una etiqueta de CALIDAD, no un filtro de entrada. Hasta el
    17-sep-2026 el TIER_4 no se puntuaba, y eso hacía invisibles a 32 empresas
    del universo curado —YUM, AAPL, AMZN, GOOG, META, ORCL, AVGO, HD, UNP,
    BLK, ASML...—: no es que no pasaran el filtro, es que no se medían, y la
    app no podía decir por qué faltaban porque nunca habían estado.

    Lo que decide si algo se recomienda es el `value_score` y los guards, no la
    pertenencia a un tier. Una TIER_4 con números malos sale con score bajo y
    no se publica, que es el resultado correcto; una TIER_4 que un día esté
    barata de verdad ahora se puede ver.

    HF_WATCH sigue fuera por defecto: es una lista de seguimiento de lo que
    compran los fondos, no una selección propia de calidad.
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


# Las europeas duplicadas (AI.PA, AUTO.L, EXPN.L, G24.DE, ITRK.L, LSEG.L) se
# sacaron el 14-sep-2026: estaban AQUÍ y en curated_tickers_eu.py a la vez, así
# que se puntuaban dos veces y salían en la pestaña Value US. AUTO.L llegó a
# verse ahí con su precio en peniques rotulado en dólares. Las seis siguen
# cubiertas al 100% por las listas EU, que es donde les toca; volver a meterlas
# aquí es añadir la línea otra vez.
ALL_TICKERS    = get_universe(include_tier4=True)
SCORED_TICKERS = get_universe()   # el curado entero: T1+T2+T3+T4
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
