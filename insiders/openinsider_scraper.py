import time
from alerts.plot_utils import descargar_grafico_finviz
from alerts.telegram_utils import send_message, send_file, send_image_telegram

def run_daily(ticker):
    d_path = descargar_grafico_finviz(ticker, "d")
    time.sleep(3)
    w_path = descargar_grafico_finviz(ticker, "w")
    time.sleep(3)

    send_message(f"Gráficos diarios y semanales para {ticker} generados.")
    send_file(d_path)
    send_file(w_path)