def descargar_grafico_finviz_con_cache(ticker: str, timeframe: str = "d", output_dir: str = "reports/graphs") -> str:
    """
    Descarga el gráfico del ticker desde Finviz en timeframe diario ('d') o semanal ('w') si no existe ya en disco.

    Args:
        ticker (str): símbolo de la acción.
        timeframe (str): 'd' para diario, 'w' para semanal.
        output_dir (str): carpeta donde guardar el gráfico.

    Returns:
        str: ruta local del archivo de imagen, o None si falla.
    """
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{ticker}_{timeframe}.png")

    # Si ya existe y es una imagen válida, no descargar de nuevo
    if os.path.exists(output_path):
        try:
            with open(output_path, "rb") as f:
                header = f.read(8)
                if header.startswith(b"\x89PNG") or header.startswith(b"\xff\xd8"):
                    return output_path
        except Exception as e:
            print(f"⚠️ Error comprobando imagen local {output_path}: {e}")

    url = f"https://finviz.com/chart.ashx?t={ticker}&ty=c&ta=1&p={timeframe}&s=l"
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        content_type = response.headers.get("Content-Type", "")
        if response.status_code == 200 and "image" in content_type:
            with open(output_path, "wb") as f:
                f.write(response.content)
            print(f"✅ Gráfico descargado para {ticker} ({timeframe}) en {output_path}")
            return output_path
        else:
            print(f"❌ Respuesta no válida para {ticker} ({timeframe}), tipo: {content_type}")
            return None
    except Exception as e:
        print(f"❌ Excepción al descargar gráfico de {ticker}: {e}")
        return None