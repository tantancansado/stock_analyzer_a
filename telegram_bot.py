#!/usr/bin/env python3
"""
TELEGRAM ALERTS BOT
Sistema de alertas automáticas para oportunidades 5D
"""
import requests
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import os


class TelegramBot:
    """Bot de Telegram para alertas de trading"""

    def __init__(self, token: str = None, chat_id: str = None):
        """
        Initialize Telegram Bot

        Args:
            token: Bot token from @BotFather
            chat_id: Chat ID where to send messages (channel/group)
        """
        # Try to load from environment variables if not provided
        self.token = token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')

        # Or load from config file
        if not self.token or not self.chat_id:
            config_path = Path('config/telegram_config.json')
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self.token = self.token or config.get('bot_token')
                    self.chat_id = self.chat_id or config.get('chat_id')

        if not self.token:
            raise ValueError("Bot token not found. Set TELEGRAM_BOT_TOKEN env var or config file")

        if not self.chat_id:
            raise ValueError("Chat ID not found. Set TELEGRAM_CHAT_ID env var or config file")

        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def send_message(self, text: str, parse_mode: str = 'HTML',
                    disable_notification: bool = False) -> bool:
        """
        Send a message to Telegram

        Args:
            text: Message text (max 4096 chars)
            parse_mode: 'HTML' or 'Markdown'
            disable_notification: Silent message

        Returns:
            True if successful
        """
        url = f"{self.base_url}/sendMessage"

        # Split long messages
        if len(text) > 4096:
            chunks = [text[i:i+4096] for i in range(0, len(text), 4096)]
            for chunk in chunks:
                self._send_chunk(chunk, parse_mode, disable_notification)
            return True
        else:
            return self._send_chunk(text, parse_mode, disable_notification)

    def _send_chunk(self, text: str, parse_mode: str,
                   disable_notification: bool) -> bool:
        """Send a single message chunk"""
        url = f"{self.base_url}/sendMessage"

        payload = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'disable_notification': disable_notification
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"❌ Error sending Telegram message: {e}")
            return False

    def send_photo(self, photo_path: str, caption: str = None) -> bool:
        """Send a photo to Telegram"""
        url = f"{self.base_url}/sendPhoto"

        try:
            with open(photo_path, 'rb') as photo:
                files = {'photo': photo}
                data = {'chat_id': self.chat_id}
                if caption:
                    data['caption'] = caption
                    data['parse_mode'] = 'HTML'

                response = requests.post(url, files=files, data=data, timeout=30)
                response.raise_for_status()
                return True
        except Exception as e:
            print(f"❌ Error sending photo: {e}")
            return False

    def send_document(self, doc_path: str, caption: str = None) -> bool:
        """Send a document (CSV, PDF, etc.) to Telegram"""
        url = f"{self.base_url}/sendDocument"

        try:
            with open(doc_path, 'rb') as doc:
                files = {'document': doc}
                data = {'chat_id': self.chat_id}
                if caption:
                    data['caption'] = caption
                    data['parse_mode'] = 'HTML'

                response = requests.post(url, files=files, data=data, timeout=30)
                response.raise_for_status()
                return True
        except Exception as e:
            print(f"❌ Error sending document: {e}")
            return False


class TelegramAlerts:
    """Sistema de alertas para oportunidades 5D"""

    def __init__(self, bot: TelegramBot):
        self.bot = bot

    def send_top_opportunities(self, opportunities: List[Dict], top_n: int = 5):
        """Envía las mejores oportunidades del día"""

        if not opportunities:
            return

        # Sort by score
        top_opps = sorted(opportunities,
                         key=lambda x: x.get('super_score_5d', 0),
                         reverse=True)[:top_n]

        # Build message
        message = f"🎯 <b>TOP {top_n} OPORTUNIDADES 5D</b>\n"
        message += f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"

        for i, opp in enumerate(top_opps, 1):
            ticker = opp.get('ticker', 'N/A')
            company = opp.get('company_name', ticker)
            score = opp.get('super_score_5d', 0)
            tier = opp.get('tier', 'N/A')

            # Get thesis short
            thesis = opp.get('thesis_short', 'Multiple signals')

            # Scores
            vcp = opp.get('vcp_score', 0)
            insiders = opp.get('insiders_score', 0)
            sector = opp.get('sector_score', 0)

            # Price target
            upside = opp.get('upside_percent')
            upside_str = f" | 🎯 +{upside:.0f}%" if upside else ""

            message += f"<b>{i}. {ticker}</b> - {company}\n"
            message += f"   ⭐ Score: <b>{score:.1f}/100</b> {tier}\n"
            message += f"   📊 VCP:{vcp:.0f} | 👔 Insiders:{insiders:.0f} | 📈 Sector:{sector:.0f}{upside_str}\n"
            message += f"   💡 {thesis}\n\n"

        message += "📊 Ver dashboard completo: [link a GitHub Pages]\n"
        message += "🤖 Sistema 5D Auto-Alerts"

        self.bot.send_message(message)

    def send_timing_convergence_alert(self, opportunities: List[Dict]):
        """Alerta de timing perfecto (VCP + Insider timing)"""

        # Filter timing convergence opportunities
        timing_opps = [o for o in opportunities
                      if o.get('timing_convergence', False)]

        if not timing_opps:
            return

        message = "🔥 <b>TIMING CONVERGENCE DETECTADO!</b>\n\n"
        message += f"Se detectaron {len(timing_opps)} oportunidades con timing perfecto:\n\n"

        for opp in timing_opps[:5]:  # Top 5
            ticker = opp.get('ticker', 'N/A')
            company = opp.get('company_name', ticker)
            score = opp.get('super_score_5d', 0)
            reason = opp.get('timing_reason', 'Timing detected')

            message += f"<b>{ticker}</b> - {company}\n"
            message += f"   ⭐ Score: {score:.1f}/100\n"
            message += f"   {reason}\n\n"

        message += "⚡ Estas oportunidades tienen convergencia de VCP + Insider timing\n"
        message += "🤖 Auto-Alert System"

        self.bot.send_message(message)

    def send_vcp_repeater_alert(self, opportunities: List[Dict]):
        """Alerta de VCP Repeaters detectados"""

        repeaters = [o for o in opportunities
                    if o.get('vcp_repeater', False)]

        if not repeaters:
            return

        # Sort by repeat count
        repeaters.sort(key=lambda x: x.get('repeat_count', 0), reverse=True)

        message = "🔁 <b>VCP REPEATERS ACTIVOS</b>\n\n"
        message += f"Stocks con historial comprobado de VCP patterns:\n\n"

        for opp in repeaters[:5]:
            ticker = opp.get('ticker', 'N/A')
            company = opp.get('company_name', ticker)
            count = opp.get('repeat_count', 0)
            score = opp.get('super_score_5d', 0)

            message += f"<b>{ticker}</b> - {company}\n"
            message += f"   🔁 {count}x VCP patterns históricos\n"
            message += f"   ⭐ Score actual: {score:.1f}/100\n\n"

        message += "💡 Los repeaters tienen mayor probabilidad de éxito\n"
        message += "🤖 Auto-Alert System"

        self.bot.send_message(message)

    def send_daily_summary(self, opportunities: List[Dict], vcp_count: int):
        """Resumen diario del sistema"""

        message = "📊 <b>RESUMEN DIARIO - SISTEMA 5D</b>\n"
        message += f"📅 {datetime.now().strftime('%Y-%m-%d')}\n\n"

        # Stats
        total_opps = len(opportunities)
        legendary = len([o for o in opportunities if '⭐⭐⭐⭐' in o.get('tier', '')])
        excelente = len([o for o in opportunities if '⭐⭐⭐' in o.get('tier', '') and '⭐⭐⭐⭐' not in o.get('tier', '')])
        timing = len([o for o in opportunities if o.get('timing_convergence', False)])
        repeaters = len([o for o in opportunities if o.get('vcp_repeater', False)])

        message += f"📈 <b>VCP Patterns:</b> {vcp_count}\n"
        message += f"🎯 <b>Oportunidades 5D:</b> {total_opps}\n\n"

        message += f"🌟 Legendary: {legendary}\n"
        message += f"⭐ Excelente: {excelente}\n"
        message += f"🔥 Timing Convergence: {timing}\n"
        message += f"🔁 VCP Repeaters: {repeaters}\n\n"

        # Top 3
        if opportunities:
            top3 = sorted(opportunities,
                         key=lambda x: x.get('super_score_5d', 0),
                         reverse=True)[:3]

            message += "<b>🏆 TOP 3:</b>\n"
            for i, opp in enumerate(top3, 1):
                ticker = opp.get('ticker', 'N/A')
                score = opp.get('super_score_5d', 0)
                message += f"  {i}. {ticker}: {score:.1f}/100\n"

        message += "\n🤖 Sistema 5D Auto-Alerts"

        self.bot.send_message(message)

    def send_new_scan_alert(self, scan_file: str):
        """Alerta cuando hay un nuevo VCP scan"""

        message = "🚀 <b>NUEVO VCP SCAN COMPLETADO</b>\n\n"
        message += f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        message += f"📁 {Path(scan_file).name}\n\n"
        message += "El sistema 5D se actualizará automáticamente.\n"
        message += "🤖 Auto-Alert System"

        self.bot.send_message(message)


def main():
    """Test del bot"""
    try:
        # Initialize bot
        bot = TelegramBot()
        alerts = TelegramAlerts(bot)

        # Test message
        message = "🤖 <b>Telegram Bot Activado!</b>\n\n"
        message += "Sistema de alertas 5D configurado correctamente.\n\n"
        message += "Tipos de alertas:\n"
        message += "• 🎯 Top Oportunidades diarias\n"
        message += "• 🔥 Timing Convergence\n"
        message += "• 🔁 VCP Repeaters\n"
        message += "• 📊 Resumen diario\n"
        message += "• 🚀 Nuevos VCP scans\n\n"
        message += f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        success = bot.send_message(message)

        if success:
            print("✅ Telegram bot configurado correctamente!")
            print(f"   Chat ID: {bot.chat_id}")
            print("   Mensaje de prueba enviado")
        else:
            print("❌ Error enviando mensaje de prueba")

    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Pasos para configurar:")
        print("1. Crea config/telegram_config.json con:")
        print('   {"bot_token": "tu_token", "chat_id": "tu_chat_id"}')
        print("2. O usa variables de entorno:")
        print("   export TELEGRAM_BOT_TOKEN=tu_token")
        print("   export TELEGRAM_CHAT_ID=tu_chat_id")


if __name__ == "__main__":
    main()
