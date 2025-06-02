# enrich_dataset.py

import pandas as pd
import os
from fundamentals.alpha_vantage import get_fundamentals_alpha

INPUT_PATH = "reports/finviz_ml_dataset.csv"
OUTPUT_PATH = "reports/finviz_ml_dataset_with_fundamentals.csv"

def enrich_dataset(input_path, output_path):
    df = pd.read_csv(input_path)

    enriched_rows = []
    for _, row in df.iterrows():
        ticker = row["Ticker"]
        fundamentals = get_fundamentals_alpha(ticker)

        # Combinar datos originales + fundamentales
        enriched_row = row.to_dict()
        enriched_row.update(fundamentals)
        enriched_rows.append(enriched_row)

    df_enriched = pd.DataFrame(enriched_rows)
    df_enriched.to_csv(output_path, index=False)
    print(f"✅ Dataset enriquecido guardado en {output_path}")

if __name__ == "__main__":
    enrich_dataset(INPUT_PATH, OUTPUT_PATH)