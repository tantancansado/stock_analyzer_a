import os
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from joblib import dump

from config import MODEL_DIR

ALL_FEATURES = [
    "P/E", "EPS (ttm)", "Insider Own", "Shs Outstand", "Perf Week", "Perf Month",
    "Perf Quarter", "Perf Half Y", "Perf Year", "ROA", "ROE", "ROI",
    "Current Ratio", "Quick Ratio", "LT Debt/Eq", "Debt/Eq", "Gross Margin",
    "Oper. Margin", "Profit Margin"
]

def train_model(df, label_column, model_file):
    available_features = [f for f in ALL_FEATURES if f in df.columns]
    if len(available_features) == 0:
        print(f"⚠️ No hay columnas válidas para entrenar {label_column}.")
        return

    df = df.replace('%', '', regex=True)
    df[available_features] = df[available_features].apply(pd.to_numeric, errors="coerce")
    df = df.dropna(subset=available_features + [label_column])

    print(f"✅ Filas válidas para {label_column}: {len(df)}")
    if len(df) < 20:
        print(f"⚠️ No hay datos suficientes para entrenar {label_column}.")
        return

    X = df[available_features]
    y = df[label_column]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    clf = RandomForestClassifier(random_state=42)
    clf.fit(X_train, y_train)
    dump(clf, model_file)
    print(f"✅ Modelo {label_column} entrenado y guardado en {model_file}")

if __name__ == "__main__":
    df = pd.read_csv("reports/finviz_labeled_dataset.csv")
    for label_column, model_name in [
        ("label_30d", "model_30d.pkl"),
        ("label_90d", "model_90d.pkl"),
        ("label_180d", "model_180d.pkl"),
        ("label_1y", "model_1y.pkl")
    ]:
        train_model(df.copy(), label_column, os.path.join(MODEL_DIR, model_name))