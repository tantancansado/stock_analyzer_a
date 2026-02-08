#!/usr/bin/env python3
"""
TELEGRAM LEGENDARY ALERTS
Envía alertas por Telegram cuando se detectan oportunidades LEGENDARY
"""
import requests
import json
import os
from pathlib import Path
from datetime import datetime

class TelegramLegendaryAlerts:
    """Sistema de alertas para oportunidades LEGENDARY"""

    def __init__(self, bot_token=None, chat_id=None):
        """
        Inicializar con credenciales de Telegram

        Para obtener:
        1. Bot Token: Habla con @BotFather en Telegram
        2. Chat ID: Envía mensaje a tu bot y ve https://api.telegram.org/bot<TOKEN>/getUpdates

        Prioridad de credenciales:
        1. Parámetros directos
        2. Variables de entorno (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
        3. Archivo de configuración
        """
        # Intentar cargar desde config
        config = self.load_config()

        # Prioridad: parámetros > env vars > config file
        self.bot_token = (
            bot_token or
            os.getenv('TELEGRAM_BOT_TOKEN') or
            config.get('bot_token')
        )
        self.chat_id = (
            chat_id or
            os.getenv('TELEGRAM_CHAT_ID') or
            config.get('chat_id')
        )

        if not self.bot_token or not self.chat_id:
            raise ValueError("Bot token y chat_id requeridos. Ver TELEGRAM_SETUP.md")

    def load_config(self):
        """Carga configuración desde archivo"""
        config_path = Path('config/telegram_config.json')
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        return {}

    def send_message(self, message, parse_mode='HTML'):
        """Envía mensaje por Telegram"""
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

        data = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': parse_mode,
            'disable_web_page_preview': False
        }

        try:
            response = requests.post(url, json=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Error enviando mensaje: {e}")
            return False

    def format_legendary_alert(self, opportunity):
        """
        Formatea oportunidad LEGENDARY para Telegram

        Args:
            opportunity: Dict con datos de la oportunidad
        """
        ticker = opportunity['ticker']
        score = opportunity['super_score_4d']
        tier = opportunity['tier']
        dims = opportunity['dimensions']

        # Emojis según score
        fire = "🔥" * min(5, int(score / 20))

        message = f"""
🌟 <b>LEGENDARY OPPORTUNITY DETECTED!</b> 🌟
{fire}

<b>Ticker:</b> {ticker}
<b>Super Score 4D:</b> {score:.1f}/100
<b>Tier:</b> {tier}

📊 <b>ANÁLISIS 4 DIMENSIONES:</b>

🚀 <b>VCP Pattern:</b> {dims['vcp']:.0f}/100
   └ Patrón técnico {self._get_quality_emoji(dims['vcp'])}

🔁 <b>Recurring Insiders:</b> {dims['insiders']:.0f}/100
   └ Compras ejecutivos {self._get_quality_emoji(dims['insiders'])}

📊 <b>Sector State:</b> {dims['sector']:.0f}/100
   └ Estado sectorial {self._get_quality_emoji(dims['sector'])}

🏛️ <b>Institutional:</b> {dims['institutional']:.0f}/100
   └ Whales acumulando {self._get_quality_emoji(dims['institutional'])}
"""

        # Añadir detalles institucionales si existen
        if opportunity.get('institutional_details'):
            inst = opportunity['institutional_details']
            message += f"""
🐋 <b>Whales Holding:</b>
"""
            for whale in inst.get('top_whales', [])[:3]:
                message += f"   • {whale}\n"

        # Añadir razón
        message += f"""
💡 <b>Razón:</b>
{opportunity.get('description', 'Confirmación cuádruple detectada')}

🔗 <b>Ver más:</b>
<a href="https://tantancansado.github.io/stock_analyzer_a/super_opportunities.html">Dashboard completo</a>

⏰ <i>Detectado: {datetime.now().strftime('%Y-%m-%d %H:%M')}</i>
"""
        return message

    def _get_quality_emoji(self, score):
        """Retorna emoji según score"""
        if score >= 80:
            return "🟢 Excelente"
        elif score >= 60:
            return "🟡 Bueno"
        elif score >= 40:
            return "🟠 Moderado"
        else:
            return "🔴 Débil"

    def check_and_alert_legendary(self):
        """
        Revisa oportunidades 4D y envía alertas para LEGENDARY
        """
        print("🔍 Buscando LEGENDARY opportunities...")

        # Cargar resultados del Super Analyzer 4D
        csv_path = Path('docs/super_opportunities_4d_complete.csv')

        if not csv_path.exists():
            print("⚠️  No hay datos 4D. Ejecuta: python3 run_super_analyzer_4d.py")
            return

        import pandas as pd
        df = pd.read_csv(csv_path)

        # Filtrar LEGENDARY (score >= 85)
        legendary = df[df['super_score_4d'] >= 85]

        if legendary.empty:
            print("ℹ️  No hay LEGENDARY opportunities en este momento")
            return

        print(f"🌟 {len(legendary)} LEGENDARY opportunities encontradas!")

        # Enviar alerta por cada una
        sent = 0
        for _, row in legendary.iterrows():
            opportunity = {
                'ticker': row['ticker'],
                'super_score_4d': row['super_score_4d'],
                'tier': row.get('tier', '⭐⭐⭐⭐ LEGENDARY'),
                'dimensions': {
                    'vcp': row.get('vcp_score', 0),
                    'insiders': row.get('insiders_score', 0),
                    'sector': row.get('sector_score', 0),
                    'institutional': row.get('institutional_score', 0)
                },
                'description': 'Confirmación cuádruple - Probabilidad histórica',
                'institutional_details': {
                    'num_whales': row.get('num_whales', 0),
                    'top_whales': row.get('top_whales', '').split(', ') if row.get('top_whales') else []
                }
            }

            message = self.format_legendary_alert(opportunity)

            if self.send_message(message):
                print(f"   ✅ Alerta enviada: {row['ticker']}")
                sent += 1
            else:
                print(f"   ❌ Error enviando alerta: {row['ticker']}")

        print(f"\n📤 Total alertas enviadas: {sent}/{len(legendary)}")

    def send_daily_summary(self):
        """
        Envía resumen diario con top opportunities
        (Para integrar con tu análisis diario existente)
        """
        print("📊 Generando resumen diario...")

        import pandas as pd

        # Cargar datos
        csv_path = Path('docs/super_opportunities_4d_complete.csv')
        if not csv_path.exists():
            print("⚠️  No hay datos")
            return

        df = pd.read_csv(csv_path)

        # Top 10 por score
        top10 = df.nlargest(10, 'super_score_4d')

        # Contar por tier
        legendary = len(df[df['super_score_4d'] >= 85])
        epic = len(df[(df['super_score_4d'] >= 75) & (df['super_score_4d'] < 85)])
        excellent = len(df[(df['super_score_4d'] >= 65) & (df['super_score_4d'] < 75)])

        message = f"""
📊 <b>RESUMEN DIARIO - SUPER ANALYZER 4D</b>
📅 {datetime.now().strftime('%Y-%m-%d')}

🎯 <b>OPORTUNIDADES DETECTADAS:</b>
⭐⭐⭐⭐ LEGENDARY: {legendary}
⭐⭐⭐ ÉPICAS: {epic}
⭐⭐ EXCELENTES: {excellent}

🏆 <b>TOP 5 OPORTUNIDADES:</b>
"""

        for i, (_, row) in enumerate(top10.head(5).iterrows(), 1):
            emoji = "⭐" * min(4, int(row['super_score_4d'] / 25))
            message += f"""
{i}. <b>{row['ticker']}</b> - {row['super_score_4d']:.1f} {emoji}
   VCP:{row.get('vcp_score', 0):.0f} | INS:{row.get('insiders_score', 0):.0f} | SEC:{row.get('sector_score', 0):.0f} | INST:{row.get('institutional_score', 0):.0f}
"""

        message += f"""
🔗 <a href="https://tantancansado.github.io/stock_analyzer_a">Ver Dashboard Completo</a>

💡 <i>Sistema 4D operativo con {len(df)} tickers analizados</i>
"""

        if self.send_message(message):
            print("✅ Resumen diario enviado")
        else:
            print("❌ Error enviando resumen")


def main():
    """Main execution"""
    print("🤖 TELEGRAM LEGENDARY ALERTS")
    print("="*80)

    try:
        alerts = TelegramLegendaryAlerts()

        print("\nOpciones:")
        print("1. Buscar y alertar LEGENDARY (score >= 85)")
        print("2. Enviar resumen diario (top 10)")
        print("3. Test de conexión")

        choice = input("\nSelecciona (1-3): ").strip()

        if choice == '1':
            alerts.check_and_alert_legendary()
        elif choice == '2':
            alerts.send_daily_summary()
        else:
            # Test
            test_msg = f"🧪 Test de conexión - {datetime.now().strftime('%H:%M:%S')}"
            if alerts.send_message(test_msg):
                print("✅ Conexión exitosa!")
            else:
                print("❌ Error de conexión")

    except ValueError as e:
        print(f"\n❌ {e}")
        print("\n📖 Consulta TELEGRAM_SETUP.md para configuración")


if __name__ == "__main__":
    main()
