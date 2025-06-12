import os

CRON_LINE = '0 9 * * * cd /Users/alejandroordonezvillar/Desktop/stockAnalyzer/stock_analyzer_a/to/stock_analyzer_a && python3 insider_trading_unified.py --auto'

def set_cron_job():
    # Borra el crontab actual y deja solo la línea deseada
    os.system(f'(echo "{CRON_LINE}") | crontab -')
    print("✅ Ahora solo tienes la tarea deseada en tu crontab.")

if __name__ == "__main__":
    set_cron_job()