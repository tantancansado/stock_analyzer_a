import pandas as pd
import os

csv_path = "reports/insiders_daily.csv"
html_path = "reports/insiders_report.html"

df = pd.read_csv(csv_path)

def generate_image_tag(path):
    return f'<img src="{path}" alt="Chart" width="320">' if isinstance(path, str) and os.path.exists(path) else ""

html_content = """
<html>
<head>
    <meta charset="UTF-8">
    <title>Informe de Compras de Insiders</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; }
        h1 { text-align: center; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #ccc; padding: 8px; text-align: center; vertical-align: middle; }
        th { background-color: #f4f4f4; }
        img { max-height: 160px; }
    </style>
</head>
<body>
    <h1>📊 Informe de Compras de Insiders</h1>
    <table>
        <tr>
            <th>Ticker</th>
            <th>InsiderBuys</th>
            <th>Date</th>
            <th>Chart Diario</th>
            <th>Chart Semanal</th>
        </tr>
"""

for _, row in df.iterrows():
    html_content += f"""
        <tr>
            <td>{row.get('Ticker', '')}</td>
            <td>{row.get('InsiderBuys', '')}</td>
            <td>{row.get('Date', '')}</td>
            <td>{generate_image_tag(row.get('Chart_Daily', ''))}</td>
            <td>{generate_image_tag(row.get('Chart_Weekly', ''))}</td>
        </tr>
    """

html_content += """
    </table>
</body>
</html>
"""

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"✅ HTML generado en {html_path}")

# --- Generar ZIP con el HTML y los gráficos ---
import zipfile

zip_path = "reports/insiders_report_bundle.zip"
with zipfile.ZipFile(zip_path, "w") as zipf:
    zipf.write(html_path, arcname=os.path.basename(html_path))
    for path in df["Chart_Daily"].dropna().tolist() + df["Chart_Weekly"].dropna().tolist():
        if isinstance(path, str) and os.path.exists(path):
            zipf.write(path, arcname=os.path.join("graphs", os.path.basename(path)))
print(f"✅ ZIP generado en {zip_path}")

import requests
import os

def descargar_grafico_finviz_con_cache(ticker: str, timeframe: str = "d", output_dir: str = "reports/graphs") -> str:
    """
    Descarga el gráfico de finviz si no existe ya en disco y valida que sea una imagen.

    Args:
        ticker (str): símbolo de la acción.
        timeframe (str): 'd' o 'w'.
        output_dir (str): directorio destino.

    Returns:
        str: ruta del gráfico o None si falló.
    """
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{ticker}_{timeframe}.png")
    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        print(f"⏭️ Ya existe {output_path}, se omite descarga.")
        return output_path

    url = f"https://finviz.com/chart.ashx?t={ticker}&ty=c&ta=1&p={timeframe}&s=l"
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code == 200:
            content_type = response.headers.get("Content-Type", "")
            if "image" not in content_type or response.content[:4] != b'\x89PNG':
                print(f"❌ Respuesta no válida para {ticker} ({timeframe}), tipo: {content_type}")
                return None
            with open(output_path, "wb") as f:
                f.write(response.content)
            print(f"✅ Gráfico descargado para {ticker} ({timeframe}) en {output_path}")
            return output_path
        else:
            print(f"❌ Error HTTP {response.status_code} al descargar gráfico de {ticker} ({timeframe})")
            return None
    except Exception as e:
        print(f"❌ Excepción al descargar gráfico de {ticker} ({timeframe}): {e}")
        return None