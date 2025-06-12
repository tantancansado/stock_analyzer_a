import os

CRON_LINE = '0 9 * * * cd /Users/alejandroordonezvillar/Desktop/stockAnalyzer/stock_analyzer_a/to/stock_analyzer_a && python3 insider_trading_unified.py --auto\n'

def add_cron_job():
    # Leer el crontab actual
    stream = os.popen('crontab -l')
    current_cron = stream.read()
    
    # Si ya está, no volver a añadirla
    if CRON_LINE.strip() in current_cron:
        print("✅ La tarea ya está en el crontab.")
        return

    # Añadir la nueva línea
    new_cron = current_cron + CRON_LINE

    # Escribir el nuevo crontab
    os.system(f'(echo "{new_cron.strip()}") | crontab -')
    print("✅ Tarea programada añadida al crontab.")

if __name__ == "__main__":
    add_cron_job()