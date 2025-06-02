import pandas as pd

def scrape_openinsider():
    # Cargar compras recientes de insiders
    insiders_df = pd.read_csv("reports/insiders_daily.csv")

    # Cargar dataset fundamental más reciente
    fundamentals_df = pd.read_csv("reports/finviz_ml_dataset_with_fundamentals.csv")

    # Convertir columnas necesarias
    fundamentals_df["Ticker"] = fundamentals_df["Ticker"].astype(str).str.upper()
    insiders_df["Ticker"] = insiders_df["Ticker"].astype(str).str.upper()

    # Filtrar compras recientes (últimos 7 días)
    insiders_df["Date"] = pd.to_datetime(insiders_df["Date"], errors="coerce")
    recent = insiders_df[insiders_df["Date"] >= pd.Timestamp.now() - pd.Timedelta(days=7)]

    # Agrupar por ticker para saber cuántas compras ha habido
    signals = (
        recent.groupby("Ticker")
        .agg(InsiderBuys=("Type", "count"))
        .reset_index()
    )

    # Unir con fundamentales
    merged = signals.merge(fundamentals_df, on="Ticker", how="left")

    # Aplicar filtros de "castigadas pero buenas"
    filtered = merged[
        (merged["Debt/Equity"].astype(str) != "nan") &
        (merged["Debt/Equity"].astype(float) < 2) &  # razonable
        ((merged["ROE"].astype(str) != "nan") & (merged["ROE"].astype(float) > 0)) &  # no en pérdidas estructurales
        ((merged["Gross Margin"].astype(str) != "nan") & (merged["Gross Margin"].astype(float) > 0))  # márgenes aún sanos
    ].copy()

    filtered = filtered.sort_values(by="InsiderBuys", ascending=False)

    output_path = "reports/insiders_opportunities.csv"
    filtered.to_csv(output_path, index=False)
    print(f"✅ Posibles oportunidades guardadas en {output_path}")
    print(filtered[["Ticker", "InsiderBuys", "Debt/Equity", "ROE", "Gross Margin"]].head())
    return output_path