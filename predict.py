import pandas as pd
import joblib
import os

# Cargar modelo
model_path = "ai/model.pkl"
if not os.path.exists(model_path):
    raise FileNotFoundError("❌ Modelo no encontrado. Asegúrate de haber ejecutado train_model.py")

model = joblib.load(model_path)

# Cargar nuevo dataset para predecir
data_path = "reports/finviz_ml_dataset.csv"
df = pd.read_csv(data_path)

# Columnas esperadas por el modelo
columns = [
    "Price", "P/E", "EPS (ttm)", "ROA", "ROE", "ROI", "Insider Activity",
    "Debt/Eq", "Gross Margin", "Oper. Margin", "Profit Margin", "SMA20", "SMA50", "SMA200"
]

# Procesar porcentajes
def convert_percent(val):
    try:
        return float(str(val).strip('%')) / 100
    except:
        return val

for col in ["SMA20", "SMA50", "SMA200", "Gross Margin", "Oper. Margin", "Profit Margin"]:
    if col in df.columns:
        df[col] = df[col].apply(convert_percent)

# Eliminar filas con valores nulos
df_clean = df[columns + ["Ticker"]].dropna()

# Predecir
X = df_clean[columns]
preds = model.predict(X)
probs = model.predict_proba(X)[:, 1]

# Añadir resultados al dataframe
df_clean["Predicted"] = preds
df_clean["Probability"] = probs

# Filtrar predicciones positivas
positives = df_clean[df_clean["Predicted"] == 1]

# Guardar resultados
os.makedirs("reports", exist_ok=True)
output_path = "reports/predictions.csv"
positives.to_csv(output_path, index=False)

# Mostrar resultados
print(f"\n✅ Predicciones completadas. Se encontraron {len(positives)} acciones con alta probabilidad.")
print(f"💾 Resultados guardados en {output_path}")
print(positives[["Ticker", "Probability"]].sort_values(by="Probability", ascending=False).head())