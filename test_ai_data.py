import pandas as pd
from finvizfinance.quote import finvizfinance
import os
import pdfplumber
import time

def extract_tickers_from_pdf(pdf_path):
    tickers = set()
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                for row in table[1:]:  # saltar encabezado
                    if row and len(row) > 1:
                        ticker = row[1].strip()
                        if ticker:
                            tickers.add(ticker)
    return list(tickers)

pdf_path = "WIDE moat.pdf"
tickers = extract_tickers_from_pdf(pdf_path)

# tickers = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA"]

dataset = []
fallos = []

print(f"📊 Obteniendo datos de Finviz para {len(tickers)} acciones...\n")

for t in tickers:
    try:
        print(f"🔍 Analizando {t}...")
        f = finvizfinance(t)
        data = f.ticker_fundament()
        data["Ticker"] = t

        # Procesar columna de insiders
        insider_raw = data.get("Insider Trans", "")
        try:
            data["Insider Activity"] = float(insider_raw.strip('%')) / 100
        except:
            data["Insider Activity"] = None

        dataset.append(data)
        time.sleep(5)
    except Exception as e:
        print(f"❌ Error con {t}: {e}")
        fallos.append(t)
        time.sleep(5)

# Convertir a DataFrame
df = pd.DataFrame(dataset)
os.makedirs("reports", exist_ok=True)
output_path = "reports/finviz_ml_dataset.csv"
df.to_csv(output_path, index=False)

print(f"\n✅ Dataset guardado en: {output_path}")
print(f"📈 {len(df)} filas generadas")
if fallos:
    print(f"⚠️ Fallos en: {', '.join(fallos)}")

print(df.head())