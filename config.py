# config.py - Versión modificada para GitHub Actions
import os

# Base directories (mantener tu configuración actual)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "models")

# Telegram Configuration - MODIFICADO para GitHub Actions
# Usar variables de entorno si están disponibles, sino usar valores por defecto
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', "762243037:AAFnEVl8saspHl40caBWePSnhe8CLSXWlvY")
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', "3165866")

# GitHub Actions detection
RUNTIME_MODE = os.getenv('GITHUB_ACTIONS', 'local')
IS_GITHUB_ACTIONS = os.getenv('GITHUB_ACTIONS') == 'true'

# Optional API Keys (si los usas)
FINNHUB_API_KEY = os.getenv('FINNHUB_API_KEY', '')
ALPHA_VANTAGE_KEY = os.getenv('ALPHA_VANTAGE_KEY', '')

# Debugging info
if IS_GITHUB_ACTIONS:
    print("🤖 Running in GitHub Actions mode")
    print(f"📱 Telegram configured: {'✅' if TELEGRAM_BOT_TOKEN else '❌'}")
else:
    print("💻 Running in local mode")
    print(f"📱 Using local Telegram config: {'✅' if TELEGRAM_BOT_TOKEN else '❌'}")

# Trading Configuration
DEFAULT_ANALYSIS_MODE = 'ultra-enhanced'
DEFAULT_DJ_MODE = 'principales'