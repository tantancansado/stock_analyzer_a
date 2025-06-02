import pandas as pd
import os

def add_labels(df, price_col="Price", future_days_30=10, future_days_1y=60):
    df = df[df[price_col].notna()].copy()  # Asegura que 'Price' no sea NaN

    # Calcular precios futuros
    df["Future_Price_30d"] = df[price_col].shift(-future_days_30)
    df["Future_Price_1y"] = df[price_col].shift(-future_days_1y)

    # Eliminar filas donde no se pueden calcular etiquetas
    df = df.dropna(subset=["Future_Price_30d", "Future_Price_1y"])

    # Generar etiquetas binarias
    df["label_30d"] = ((df["Future_Price_30d"] - df[price_col]) / df[price_col] > 0.10).astype(int)
    df["label_1y"] = ((df["Future_Price_1y"] - df[price_col]) / df[price_col] > 0.30).astype(int)

    return df.drop(columns=["Future_Price_30d", "Future_Price_1y"])

if __name__ == "__main__":
    input_path = "reports/finviz_ml_dataset_with_fundamentals.csv"
    output_path = "reports/finviz_labeled_dataset.csv"

    if not os.path.exists(input_path):
        print(f"❌ No se encontró el dataset: {input_path}")
        exit(1)

    df = pd.read_csv(input_path)

    if "Price" not in df.columns:
        print("❌ La columna 'Price' no está presente en el dataset.")
        exit(1)

    df_labeled = add_labels(df)
    df_labeled.to_csv(output_path, index=False)

    print(f"✅ Dataset etiquetado guardado en: {output_path}")
    print(df_labeled[["Ticker", "label_30d", "label_1y"]].head())