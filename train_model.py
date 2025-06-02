import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib
import os

# Leer el dataset
df = pd.read_csv("reports/finviz_ml_dataset.csv")

# Seleccionar features numéricas clave
columns_to_use = [
    "Price", "P/E", "EPS (ttm)", "ROA", "ROE", "ROI", "Insider Activity",
    "Debt/Eq", "Gross Margin", "Oper. Margin", "Profit Margin", "SMA20", "SMA50", "SMA200"
]

# Eliminar filas con valores faltantes
df = df[columns_to_use + ["Target Price"]].dropna()

# Convertir strings como '2.3%' a float
def convert_percent(val):
    try:
        return float(str(val).strip('%')) / 100
    except:
        return val

for col in ["SMA20", "SMA50", "SMA200", "Gross Margin", "Oper. Margin", "Profit Margin"]:
    df[col] = df[col].apply(convert_percent)

# Crear etiqueta: ¿Target Price >= +15% del precio actual?
df["label"] = (df["Target Price"] >= df["Price"] * 1.15).astype(int)

# Separar features y etiquetas
X = df[columns_to_use]
y = df["label"]

# División train/test
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Entrenar modelo
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Evaluar
print("✅ Entrenamiento completado.")
print("\n📊 Evaluación del modelo:\n")
print(classification_report(y_test, model.predict(X_test)))

# Guardar modelo entrenado
os.makedirs("ai", exist_ok=True)
joblib.dump(model, "ai/model.pkl")
print("\n💾 Modelo guardado en ai/model.pkl")