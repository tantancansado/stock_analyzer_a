import requests
import os

def descargar_grafico_finviz(ticker: str, timeframe: str = "d", output_dir: str = "reports/graphs") -> str:
    """
    Descarga el gráfico del ticker desde Finviz en timeframe diario ('d') o semanal ('w').

    Args:
        ticker (str): símbolo de la acción.
        timeframe (str): 'd' para diario, 'w' para semanal.
        output_dir (str): carpeta donde guardar el gráfico.

    Returns:
        str: ruta local del archivo de imagen, o None si falla.
    """
    os.makedirs(output_dir, exist_ok=True)
    url = f"https://finviz.com/chart.ashx?t={ticker}&ty=c&ta=1&p={timeframe}&s=l"
    output_path = os.path.join(output_dir, f"{ticker}_{timeframe}.png")

    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(response.content)
            print(f"✅ Gráfico descargado para {ticker} ({timeframe}) en {output_path}")
            return output_path
        else:
            print(f"❌ Error al descargar gráfico de {ticker} ({timeframe}) - Código: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Excepción al descargar gráfico de {ticker}: {e}")
        return None