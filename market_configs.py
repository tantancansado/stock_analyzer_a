#!/usr/bin/env python3
"""
MARKET CONFIGURATIONS
Definiciones de mercados internacionales para expansión futura
"""

# USA Markets (actual)
SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
NASDAQ100_URL = "https://en.wikipedia.org/wiki/Nasdaq-100"

# European Markets (futuro)
DAX40_SYMBOLS = [
    # Germany DAX 40 - Top 40 German companies
    "SAP.DE",       # SAP SE
    "SIE.DE",       # Siemens AG
    "AIR.DE",       # Airbus SE
    "ALV.DE",       # Allianz SE
    "BAS.DE",       # BASF SE
    "BAYN.DE",      # Bayer AG
    "BMW.DE",       # BMW AG
    "VOW3.DE",      # Volkswagen AG
    "DB1.DE",       # Deutsche Boerse AG
    "DBK.DE",       # Deutsche Bank AG
    "DTE.DE",       # Deutsche Telekom AG
    "EOAN.DE",      # E.ON SE
    "FRE.DE",       # Fresenius SE
    "HEI.DE",       # HeidelbergCement AG
    "HEN3.DE",      # Henkel AG
    "IFX.DE",       # Infineon Technologies AG
    "MRK.DE",       # Merck KGaA
    "MUV2.DE",      # Munich Re
    "RWE.DE",       # RWE AG
    "DPW.DE",       # Deutsche Post AG
    "ADS.DE",       # Adidas AG
    "BEI.DE",       # Beiersdorf AG
    "CON.DE",       # Continental AG
    "1COV.DE",      # Covestro AG
    "DTG.DE",       # Daimler Truck Holding AG
    "DHL.DE",       # DHL Group
    "FME.DE",       # Fresenius Medical Care AG
    "HNR1.DE",      # Hannover Re
    "LIN.DE",       # Linde plc
    "MTX.DE",       # MTU Aero Engines AG
    "P911.DE",      # Porsche AG
    "PAH3.DE",      # Porsche Automobil Holding SE
    "PUM.DE",       # Puma SE
    "QIA.DE",       # Qiagen NV
    "RHM.DE",       # Rheinmetall AG
    "SAZ.DE",       # Sartorius AG
    "SHL.DE",       # Siemens Healthineers AG
    "SY1.DE",       # Symrise AG
    "VNA.DE",       # Vonovia SE
    "ZAL.DE",       # Zalando SE
]

FTSE100_SYMBOLS = [
    # UK FTSE 100 - Top 100 UK companies
    "SHEL.L",       # Shell plc
    "AZN.L",        # AstraZeneca
    "HSBA.L",       # HSBC Holdings
    "BP.L",         # BP plc
    "ULVR.L",       # Unilever
    "DGE.L",        # Diageo
    "GSK.L",        # GlaxoSmithKline
    "RIO.L",        # Rio Tinto
    "VOD.L",        # Vodafone
    "NG.L",         # National Grid
    # ... (top 10 para empezar, se pueden agregar los 90 restantes)
]

CAC40_SYMBOLS = [
    # France CAC 40 - Top 40 French companies
    "MC.PA",        # LVMH
    "OR.PA",        # L'Oréal
    "SAN.PA",       # Sanofi
    "TTE.PA",       # TotalEnergies
    "AIR.PA",       # Airbus
    "BN.PA",        # Danone
    "SAF.PA",       # Safran
    "CS.PA",        # AXA
    "SU.PA",        # Schneider Electric
    "BNP.PA",       # BNP Paribas
    # ... (top 10 para empezar)
]

# Asian Markets (futuro)
NIKKEI225_SYMBOLS = [
    # Japan Nikkei 225 - Top Japanese companies
    "7203.T",       # Toyota Motor Corp
    "6758.T",       # Sony Group Corp
    "6861.T",       # Keyence Corp
    "9984.T",       # SoftBank Group Corp
    "8306.T",       # Mitsubishi UFJ Financial
    "6902.T",       # Denso Corp
    "9432.T",       # NTT (Nippon Telegraph)
    "6501.T",       # Hitachi Ltd
    "6954.T",       # Fanuc Corp
    "7974.T",       # Nintendo Co Ltd
    # ... (top 10 para empezar)
]

# Market Metadata
MARKETS = {
    "USA": {
        "sp500": {
            "name": "S&P 500",
            "size": 500,
            "currency": "USD",
            "timezone": "America/New_York",
            "exchange": "NYSE/NASDAQ",
            "source": SP500_URL,
            "active": True,
        },
        "nasdaq100": {
            "name": "NASDAQ 100",
            "size": 100,
            "currency": "USD",
            "timezone": "America/New_York",
            "exchange": "NASDAQ",
            "source": NASDAQ100_URL,
            "active": False,  # Para futuro
        },
    },
    "Germany": {
        "dax40": {
            "name": "DAX 40",
            "size": 40,
            "currency": "EUR",
            "timezone": "Europe/Berlin",
            "exchange": "XETRA",
            "symbols": DAX40_SYMBOLS,
            "active": False,  # Para futuro
        },
    },
    "UK": {
        "ftse100": {
            "name": "FTSE 100",
            "size": 100,
            "currency": "GBP",
            "timezone": "Europe/London",
            "exchange": "LSE",
            "symbols": FTSE100_SYMBOLS[:10],  # Top 10 inicial
            "active": False,  # Para futuro
        },
    },
    "France": {
        "cac40": {
            "name": "CAC 40",
            "size": 40,
            "currency": "EUR",
            "timezone": "Europe/Paris",
            "exchange": "Euronext Paris",
            "symbols": CAC40_SYMBOLS[:10],  # Top 10 inicial
            "active": False,  # Para futuro
        },
    },
    "Japan": {
        "nikkei225": {
            "name": "Nikkei 225",
            "size": 225,
            "currency": "JPY",
            "timezone": "Asia/Tokyo",
            "exchange": "TSE",
            "symbols": NIKKEI225_SYMBOLS[:10],  # Top 10 inicial
            "active": False,  # Para futuro
        },
    },
}


def get_active_markets():
    """Retorna solo mercados activos"""
    active = {}
    for region, markets in MARKETS.items():
        for market_id, config in markets.items():
            if config.get("active", False):
                active[f"{region}_{market_id}"] = config
    return active


def get_market_symbols(market_id: str):
    """
    Obtiene símbolos de un mercado específico

    Args:
        market_id: ID del mercado (ej: "Germany_dax40", "USA_sp500")
    """
    region, market = market_id.split("_")

    if region not in MARKETS or market not in MARKETS[region]:
        raise ValueError(f"Mercado no encontrado: {market_id}")

    config = MARKETS[region][market]

    # Si tiene lista de símbolos directa
    if "symbols" in config:
        return config["symbols"]

    # Si tiene URL para scraping (como S&P 500)
    if "source" in config and region == "USA" and market == "sp500":
        import pandas as pd
        df = pd.read_html(config["source"])[0]
        return df['Symbol'].tolist()

    raise ValueError(f"No se pueden obtener símbolos para {market_id}")


if __name__ == "__main__":
    # Test
    print("🌍 MERCADOS CONFIGURADOS:")
    print("=" * 60)

    for region, markets in MARKETS.items():
        print(f"\n{region}:")
        for market_id, config in markets.items():
            status = "✅ ACTIVO" if config.get("active") else "⏸️  FUTURO"
            print(f"  {status} {config['name']} ({config['size']} stocks)")
            print(f"           Exchange: {config['exchange']} | Currency: {config['currency']}")

    print("\n\n🎯 MERCADOS ACTIVOS:")
    print("=" * 60)
    active = get_active_markets()
    for market_id, config in active.items():
        print(f"  {market_id}: {config['name']}")
