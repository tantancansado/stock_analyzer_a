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
        2. config.py (configuración del proyecto)
        3. Variables de entorno (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
        4. Archivo de configuración
        """
        # Intentar importar config.py del proyecto
        project_config = None
        try:
            import config as project_config
        except ImportError:
            pass

        # Intentar cargar desde archivo config
        file_config = self.load_config()

        # Prioridad: parámetros > config.py > env vars > config file
        self.bot_token = (
            bot_token or
            (project_config.TELEGRAM_BOT_TOKEN if project_config else None) or
            os.getenv('TELEGRAM_BOT_TOKEN') or
            file_config.get('bot_token')
        )
        self.chat_id = (
            chat_id or
            (project_config.TELEGRAM_CHAT_ID if project_config else None) or
            os.getenv('TELEGRAM_CHAT_ID') or
            file_config.get('chat_id')
        )

        if not self.bot_token or not self.chat_id:
            raise ValueError("Bot token y chat_id requeridos. Configurar en config.py o variables de entorno")

    def load_config(self):
        """Carga configuración desde archivo"""
        config_path = Path('config/telegram_config.json')
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        return {}

    @staticmethod
    def _safe_float(val, default=0.0):
        """Safely convert a value to float, returning default if not possible"""
        try:
            if val is None:
                return default
            f = float(val)
            import math
            return default if math.isnan(f) else f
        except (ValueError, TypeError):
            return default

    def send_message(self, message, parse_mode='HTML', disable_notification=False):
        """Envía mensaje por Telegram"""
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

        data = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': parse_mode,
            'disable_web_page_preview': False,
            'disable_notification': disable_notification
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
        company = opportunity.get('company_name', ticker)
        score = self._safe_float(opportunity.get('super_score_5d', opportunity.get('super_score_4d', 0)))
        tier = opportunity['tier']
        dims = {k: self._safe_float(v) for k, v in opportunity['dimensions'].items()}

        # Emojis según score
        fire = "🔥" * min(5, int(score / 20))

        quality_score = self._safe_float(dims.get('quality', dims.get('fundamental', 50)))
        message = f"""
🌟 <b>LEGENDARY OPPORTUNITY DETECTED!</b> 🌟
{fire}

<b>{ticker}</b> - {company}
<b>Super Score 5D:</b> {score:.1f}/100
<b>Tier:</b> {tier}

📊 <b>ANÁLISIS 5 DIMENSIONES:</b>

🚀 <b>VCP Pattern:</b> {dims['vcp']:.0f}/100
   └ {self._get_quality_emoji(dims['vcp'])}

👔 <b>Recurring Insiders:</b> {dims['insiders']:.0f}/100
   └ {self._get_quality_emoji(dims['insiders'])}

📈 <b>Sector:</b> {dims['sector']:.0f}/100
   └ {self._get_quality_emoji(dims['sector'])}

🏛️ <b>Institutional:</b> {dims['institutional']:.0f}/100
   └ {self._get_quality_emoji(dims['institutional'])}

🎯 <b>Quality:</b> {quality_score:.0f}/100
   └ {self._get_quality_emoji(quality_score)}
"""

        # Timing Convergence
        if opportunity.get('timing_convergence'):
            message += f"\n🔥 <b>TIMING PERFECTO!</b>\n{opportunity.get('timing_reason', 'VCP + Insider timing aligned')}\n"

        # VCP Repeater
        if opportunity.get('vcp_repeater'):
            count = opportunity.get('repeat_count', 0)
            bonus = opportunity.get('repeater_bonus', 0)
            message += f"\n🔁 <b>VCP REPEATER:</b> {count}x histórico (+{bonus} bonus)\n"

        # Price Target
        upside = self._safe_float(opportunity.get('upside_percent'))
        if upside > 0:
            target = self._safe_float(opportunity.get('price_target', 0))
            current = self._safe_float(opportunity.get('current_price', 0))
            message += f"\n💰 <b>Upside:</b> +{upside:.1f}% (${current:.2f} → ${target:.2f})\n"

        # Whales
        if opportunity.get('institutional_details'):
            inst = opportunity['institutional_details']
            if inst.get('top_whales'):
                message += f"\n🐋 <b>Whales:</b>\n"
                for whale in inst.get('top_whales', [])[:3]:
                    message += f"   • {whale}\n"

        # Investment Thesis (short)
        thesis = opportunity.get('thesis_short')
        if thesis:
            message += f"\n💡 <b>Thesis:</b> {thesis}\n"

        message += f"""
🔗 <b>Ver más:</b>
<a href="https://tantancansado.github.io/stock_analyzer_a/super_dashboard.html">Dashboard completo</a>

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
        Revisa oportunidades 5D y envía alertas para LEGENDARY
        """
        print("🔍 Buscando LEGENDARY opportunities...")

        # Cargar resultados del Super Analyzer 5D
        csv_path = Path('docs/super_opportunities_5d_complete.csv')

        if not csv_path.exists():
            # Fallback a 4D si existe
            csv_path = Path('docs/super_opportunities_4d_complete.csv')
            if not csv_path.exists():
                print("⚠️  No hay datos 5D. Ejecuta: python3 run_super_analyzer_4d.py")
                return

        import pandas as pd
        df = pd.read_csv(csv_path)

        # Usar columna correcta dependiendo del CSV
        score_col = 'super_score_5d' if 'super_score_5d' in df.columns else 'super_score_4d'

        # Filtrar LEGENDARY (score >= 80)
        legendary = df[df[score_col] >= 80]

        if legendary.empty:
            print("ℹ️  No hay LEGENDARY opportunities en este momento")
            return

        print(f"🌟 {len(legendary)} LEGENDARY opportunities encontradas!")

        # Enviar alerta por cada una
        sent = 0
        for _, row in legendary.iterrows():
            opportunity = {
                'ticker': row['ticker'],
                'company_name': row.get('company_name', row['ticker']),
                'super_score_5d': row.get(score_col, 0),
                'tier': row.get('tier', '⭐⭐⭐⭐ LEGENDARY'),
                'dimensions': {
                    'vcp': row.get('vcp_score', 0),
                    'insiders': row.get('insiders_score', 0),
                    'sector': row.get('sector_score', 0),
                    'institutional': row.get('institutional_score', 0),
                    'quality': row.get('fundamental_score', 50)
                },
                'description': 'Confirmación 5D - Probabilidad histórica',
                'timing_convergence': row.get('timing_convergence', False),
                'timing_reason': row.get('timing_reason', ''),
                'vcp_repeater': row.get('vcp_repeater', False),
                'repeat_count': row.get('repeat_count', 0),
                'repeater_bonus': row.get('repeater_bonus', 0),
                'upside_percent': row.get('upside_percent'),
                'price_target': row.get('price_target'),
                'current_price': row.get('current_price'),
                'thesis_short': row.get('thesis_short', ''),
                'institutional_details': {
                    'num_whales': row.get('num_whales', 0),
                    'top_whales': str(row.get('top_whales', '') or '').split(', ') if row.get('top_whales') and not isinstance(row.get('top_whales'), float) else []
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
        Envía resumen diario con top opportunities 5D
        """
        print("📊 Generando resumen diario...")

        import pandas as pd

        # Cargar datos 5D
        csv_path = Path('docs/super_opportunities_5d_complete.csv')
        if not csv_path.exists():
            csv_path = Path('docs/super_opportunities_4d_complete.csv')
            if not csv_path.exists():
                print("⚠️  No hay datos")
                return

        df = pd.read_csv(csv_path)

        # Detectar columna de score
        score_col = 'super_score_5d' if 'super_score_5d' in df.columns else 'super_score_4d'

        # Top 10 por score
        top10 = df.nlargest(10, score_col)

        # Contar por tier
        legendary = len(df[df[score_col] >= 80])
        epic = len(df[(df[score_col] >= 70) & (df[score_col] < 80)])
        excellent = len(df[(df[score_col] >= 60) & (df[score_col] < 70)])

        # Contar features especiales
        timing_conv = len(df[df['timing_convergence'] == True]) if 'timing_convergence' in df.columns else 0
        repeaters = len(df[df['vcp_repeater'] == True]) if 'vcp_repeater' in df.columns else 0

        message = f"""
📊 <b>RESUMEN DIARIO - SISTEMA 5D</b>
📅 {datetime.now().strftime('%Y-%m-%d')}

🎯 <b>OPORTUNIDADES DETECTADAS:</b>
⭐⭐⭐⭐ LEGENDARY: {legendary}
⭐⭐⭐ EXCELENTE: {epic}
⭐⭐ BUENA: {excellent}

🔥 Timing Convergence: {timing_conv}
🔁 VCP Repeaters: {repeaters}

🏆 <b>TOP 5 OPORTUNIDADES:</b>
"""

        for i, (_, row) in enumerate(top10.head(5).iterrows(), 1):
            ticker = row['ticker']
            company = row.get('company_name', ticker)
            if not isinstance(company, str):
                company = str(ticker)
            score = self._safe_float(row.get(score_col, 0))
            emoji = "⭐" * min(4, max(0, int(score / 25)))

            # Badges
            badges = []
            if 'timing_convergence' in row.index and row.get('timing_convergence'):
                badges.append("🔥")
            if 'vcp_repeater' in row.index and row.get('vcp_repeater'):
                badges.append("🔁")
            badge_str = " ".join(badges)

            vcp = self._safe_float(row.get('vcp_score', 0))
            ins = self._safe_float(row.get('insiders_score', 0))
            sec = self._safe_float(row.get('sector_score', 0))

            message += f"""
{i}. <b>{ticker}</b> - {company}
   Score: {score:.1f}/100 {emoji} {badge_str}
   VCP:{vcp:.0f} | INS:{ins:.0f} | SEC:{sec:.0f}
"""

        message += f"""
🔗 <a href="https://tantancansado.github.io/stock_analyzer_a/super_dashboard.html">Ver Dashboard Completo</a>

💡 <i>Sistema 5D operativo con {len(df)} tickers analizados</i>
"""

        if self.send_message(message):
            print("✅ Resumen diario enviado")
        else:
            print("❌ Error enviando resumen")

    def send_timing_convergence_alerts(self):
        """Alerta específica para Timing Convergence (VCP + Insider timing)"""
        print("🔥 Buscando Timing Convergence...")

        import pandas as pd

        csv_path = Path('docs/super_opportunities_5d_complete.csv')
        if not csv_path.exists():
            print("⚠️  No hay datos 5D")
            return

        df = pd.read_csv(csv_path)

        # Filtrar timing convergence (check column exists first)
        if 'timing_convergence' not in df.columns:
            print("ℹ️  No hay columna timing_convergence en el CSV")
            return

        timing = df[df['timing_convergence'] == True]

        if timing.empty:
            print("ℹ️  No hay timing convergence en este momento")
            return

        print(f"🔥 {len(timing)} Timing Convergence detectados!")

        message = f"""
🔥 <b>TIMING CONVERGENCE ALERT!</b> 🔥

Detectados {len(timing)} stocks con timing perfecto:
VCP + Insider buying convergencia

"""

        for _, row in timing.head(5).iterrows():
            ticker = row['ticker']
            company = row.get('company_name', ticker)
            if not isinstance(company, str):
                company = str(ticker)
            score = self._safe_float(row.get('super_score_5d', row.get('super_score_4d', 0)))
            reason = row.get('timing_reason', 'Timing detected')
            if not isinstance(reason, str):
                reason = 'Timing detected'

            message += f"""
<b>{ticker}</b> - {company}
Score: {score:.1f}/100
{reason}

"""

        message += f"""
💡 <b>¿Por qué es importante?</b>
El timing convergence indica que insiders están comprando
justo durante la formación del patrón VCP - señal histórica
de alta probabilidad de éxito.

🔗 <a href="https://tantancansado.github.io/stock_analyzer_a/super_dashboard.html">Ver detalles</a>
"""

        if self.send_message(message):
            print("✅ Timing Convergence alert enviada")
        else:
            print("❌ Error enviando alerta")

    def send_vcp_repeater_alerts(self):
        """Alerta específica para VCP Repeaters"""
        print("🔁 Buscando VCP Repeaters...")

        import pandas as pd

        csv_path = Path('docs/super_opportunities_5d_complete.csv')
        if not csv_path.exists():
            print("⚠️  No hay datos 5D")
            return

        df = pd.read_csv(csv_path)

        # Filtrar repeaters (check column exists first)
        if 'vcp_repeater' not in df.columns:
            print("ℹ️  No hay columna vcp_repeater en el CSV")
            return

        repeaters = df[df['vcp_repeater'] == True]

        if repeaters.empty:
            print("ℹ️  No hay VCP repeaters activos")
            return

        # Sort by repeat count
        repeaters = repeaters.sort_values('repeat_count', ascending=False)

        print(f"🔁 {len(repeaters)} VCP Repeaters activos!")

        message = f"""
🔁 <b>VCP REPEATERS ALERT!</b> 🔁

{len(repeaters)} stocks con historial comprobado de VCP patterns:

"""

        for _, row in repeaters.head(5).iterrows():
            ticker = row['ticker']
            company = row.get('company_name', ticker)
            if not isinstance(company, str):
                company = str(ticker)
            count = int(self._safe_float(row.get('repeat_count', 0)))
            score = self._safe_float(row.get('super_score_5d', row.get('super_score_4d', 0)))
            bonus = int(self._safe_float(row.get('repeater_bonus', 0)))

            message += f"""
<b>{ticker}</b> - {company}
🔁 {count}x VCP históricos (+{bonus} bonus)
Score actual: {score:.1f}/100

"""

        message += f"""
💡 <b>¿Por qué importa?</b>
Los VCP Repeaters tienen track record comprobado.
Stocks que forman VCP múltiples veces tienen mayor
probabilidad de éxito en futuros breakouts.

🔗 <a href="https://tantancansado.github.io/stock_analyzer_a/super_dashboard.html">Ver análisis</a>
"""

        if self.send_message(message):
            print("✅ VCP Repeater alert enviada")
        else:
            print("❌ Error enviando alerta")

    def send_mean_reversion_alerts(self):
        """Alerta específica para oportunidades de Mean Reversion"""
        print("🔄 Buscando oportunidades de Mean Reversion...")

        import pandas as pd

        csv_path = Path('docs/mean_reversion_opportunities.csv')
        if not csv_path.exists():
            print("⚠️  No hay datos de Mean Reversion")
            return

        df = pd.read_csv(csv_path)

        if df.empty:
            print("ℹ️  No hay oportunidades de reversión")
            return

        # Filtrar solo las mejores (score >= 70)
        top_opps = df[df['reversion_score'] >= 70].head(10)

        if top_opps.empty:
            print("ℹ️  No hay oportunidades de alta calidad")
            return

        print(f"🔄 {len(top_opps)} oportunidades de reversión detectadas!")

        # Contar por estrategia
        oversold = len(df[df['strategy'] == 'Oversold Bounce'])
        bull_flag = len(df[df['strategy'] == 'Bull Flag Pullback'])

        message = f"""
🔄 <b>MEAN REVERSION ALERT!</b> 🔄

Detectadas {len(df)} oportunidades de compra en dips:

📉 Oversold Bounce: {oversold}
📊 Bull Flag Pullback: {bull_flag}

<b>🏆 TOP 5 OPORTUNIDADES:</b>

"""

        for _, row in top_opps.head(5).iterrows():
            ticker = row['ticker']
            company = row.get('company_name', ticker)
            strategy = row['strategy']
            score = row['reversion_score']
            quality = row['quality']
            current = row['current_price']
            target = row['target']
            rr = row.get('risk_reward', 0)

            # Emoji según estrategia
            emoji = "📉" if strategy == "Oversold Bounce" else "📊"

            current = self._safe_float(current)
            target = self._safe_float(target)
            score = self._safe_float(score)
            rr = self._safe_float(rr)
            upside_pct = ((target - current) / current * 100) if current > 0 else 0

            message += f"""
{emoji} <b>{ticker}</b> - {company}
Estrategia: {strategy}
Score: {score:.0f}/100 {quality}
Precio: ${current:.2f} → Target: ${target:.2f} (+{upside_pct:.1f}%)
R/R: {rr:.1f}:1

"""

        message += f"""
💡 <b>¿Qué es Mean Reversion?</b>
Comprar stocks de calidad cuando caen significativamente
y tienen alta probabilidad de recuperación. Complementa
la estrategia VCP (breakouts).

<b>Estrategias:</b>
📉 <b>Oversold Bounce:</b> RSI &lt; 30, caída &gt; 20%, cerca de soporte
📊 <b>Bull Flag:</b> Pullback saludable en tendencia alcista

🔗 <a href="https://tantancansado.github.io/stock_analyzer_a/mean_reversion_dashboard.html">Ver dashboard completo</a>
"""

        if self.send_message(message):
            print("✅ Mean Reversion alert enviada")
        else:
            print("❌ Error enviando alerta")

    def send_options_flow_alerts(self):
        """Alerta específica para Whale Activity en opciones"""
        print("🐋 Buscando Whale Activity en opciones...")

        import pandas as pd

        csv_path = Path('docs/options_flow.csv')
        if not csv_path.exists():
            print("⚠️  No hay datos de Options Flow")
            return

        df = pd.read_csv(csv_path)

        if df.empty:
            print("ℹ️  No hay flujos inusuales")
            return

        # Filtrar solo whale activity (score >= 65)
        whale_flows = df[df['flow_score'] >= 65]

        if whale_flows.empty:
            print("ℹ️  No hay whale activity detectada")
            return

        print(f"🐋 {len(whale_flows)} whale flows detectados!")

        # Count by sentiment
        bullish = len(df[df['sentiment'] == 'BULLISH'])
        bearish = len(df[df['sentiment'] == 'BEARISH'])
        neutral = len(df[df['sentiment'] == 'NEUTRAL'])

        message = f"""
🐋 <b>WHALE ACTIVITY ALERT!</b> 🐋

Detectados {len(df)} flujos inusuales de opciones:

🟢 Bullish: {bullish}
🔴 Bearish: {bearish}
🟡 Neutral: {neutral}

<b>🔥 TOP 5 WHALE FLOWS:</b>

"""

        for _, row in whale_flows.head(5).iterrows():
            ticker = row['ticker']
            company = row.get('company_name', ticker)
            sentiment = row['sentiment']
            score = self._safe_float(row['flow_score'])
            quality = row['quality']
            premium = self._safe_float(row['total_premium'])
            pc_ratio = self._safe_float(row['put_call_ratio'])
            exp_date = row.get('expiration_date', 'N/A')
            days_to_exp = row.get('days_to_expiration', 'N/A')

            # Emoji según sentiment
            if sentiment == 'BULLISH':
                emoji = "🟢"
            elif sentiment == 'BEARISH':
                emoji = "🔴"
            else:
                emoji = "🟡"

            message += f"""
{emoji} <b>{ticker}</b> - {company}
Sentiment: {sentiment}
Score: {score:.0f}/100 {quality}
Premium: ${premium/1000:.0f}K
Put/Call: {f'{pc_ratio:.2f}' if pc_ratio < 100 else '∞'}
📅 Vencimiento: {exp_date} ({days_to_exp} días)

"""

        message += f"""
💡 <b>¿Qué es Whale Activity?</b>
Institucionales y fondos dejando huellas de movimientos grandes
en el mercado de opciones. Pueden anticipar movimientos del stock.

<b>Interpretación:</b>
🟢 <b>Bullish Flow:</b> Calls dominantes = expectativas alcistas
🔴 <b>Bearish Flow:</b> Puts dominantes = protección/apuestas bajistas
🟡 <b>Neutral:</b> Flujos balanceados = incertidumbre

🔗 <a href="https://tantancansado.github.io/stock_analyzer_a/options_flow_dashboard.html">Ver dashboard completo</a>
"""

        if self.send_message(message):
            print("✅ Options Flow alert enviada")
        else:
            print("❌ Error enviando alerta")

    def send_ml_scores_alerts(self):
        """Alerta específica para Top ML Scores (predictive analysis)"""
        print("🤖 Buscando Top ML Scores...")

        import pandas as pd

        csv_path = Path('docs/ml_scores.csv')
        if not csv_path.exists():
            print("⚠️  No hay datos de ML Scores")
            return

        df = pd.read_csv(csv_path)

        if df.empty:
            print("ℹ️  No hay ML scores disponibles")
            return

        # Top 10 por ML score
        top_ml = df.nlargest(10, 'ml_score')

        if top_ml.empty:
            print("ℹ️  No hay scores suficientemente altos")
            return

        print(f"🤖 {len(top_ml)} top ML scores detectados!")

        # Estadísticas
        avg_score = df['ml_score'].mean()
        high_scores = len(df[df['ml_score'] >= 70])

        message = f"""
🤖 <b>ML PREDICTIONS ALERT!</b> 🤖

Sistema de Machine Learning detectó {high_scores} stocks
con score predictivo alto (&gt;= 70/100)

📊 <b>ESTADÍSTICAS:</b>
• Stocks analizados: {len(df)}
• Score promedio: {avg_score:.1f}/100
• High scores (≥70): {high_scores}

<b>🏆 TOP 5 ML SCORES:</b>

"""

        for i, (_, row) in enumerate(top_ml.head(5).iterrows(), 1):
            ticker = row['ticker']
            company = row.get('company_name', ticker)
            ml_score = self._safe_float(row['ml_score'])

            # Componentes del score
            momentum = self._safe_float(row.get('momentum_score', 0))
            trend = self._safe_float(row.get('trend_score', 0))
            volume = self._safe_float(row.get('volume_score', 0))

            # Emojis según score
            if ml_score >= 80:
                emoji = "🔥"
            elif ml_score >= 70:
                emoji = "⭐"
            else:
                emoji = "✅"

            message += f"""
{i}. {emoji} <b>{ticker}</b> - {company}
   ML Score: {ml_score:.1f}/100
   Momentum:{momentum:.0f} | Trend:{trend:.0f} | Volume:{volume:.0f}

"""

        message += f"""
💡 <b>¿Qué es ML Score?</b>
Sistema de scoring predictivo basado en 6 dimensiones:
• Momentum (returns 7d/14d/30d)
• Trend (MA alignment)
• Volume (strength vs historical)
• Volatility (contraction)
• Technical indicators (RSI, ATR)
• Position in range

Complementa VCP y otras señales para timing óptimo.

🔗 Ver datos completos: docs/ml_scores.csv
"""

        if self.send_message(message):
            print("✅ ML Scores alert enviada")
        else:
            print("❌ Error enviando alerta")


def main():
    """Main execution"""
    print("🤖 TELEGRAM ALERTS - SISTEMA 5D")
    print("="*80)

    try:
        alerts = TelegramLegendaryAlerts()

        print("\nOpciones:")
        print("1. 🌟 Alertar LEGENDARY (score >= 80)")
        print("2. 📊 Resumen diario completo")
        print("3. 🔥 Timing Convergence alerts")
        print("4. 🔁 VCP Repeater alerts")
        print("5. 🔄 Mean Reversion alerts")
        print("6. 🐋 Options Flow (Whale Activity)")
        print("7. 🤖 ML Scores (Predictive Analysis)")
        print("8. 🚀 Ejecutar TODAS las alertas")
        print("9. 🧪 Test de conexión")

        choice = input("\nSelecciona (1-9): ").strip()

        if choice == '1':
            alerts.check_and_alert_legendary()
        elif choice == '2':
            alerts.send_daily_summary()
        elif choice == '3':
            alerts.send_timing_convergence_alerts()
        elif choice == '4':
            alerts.send_vcp_repeater_alerts()
        elif choice == '5':
            alerts.send_mean_reversion_alerts()
        elif choice == '6':
            alerts.send_options_flow_alerts()
        elif choice == '7':
            alerts.send_ml_scores_alerts()
        elif choice == '8':
            # Ejecutar todas las alertas
            print("\n🚀 Ejecutando pipeline completo de alertas...\n")
            alerts.send_daily_summary()
            print()
            alerts.check_and_alert_legendary()
            print()
            alerts.send_timing_convergence_alerts()
            print()
            alerts.send_vcp_repeater_alerts()
            print()
            alerts.send_mean_reversion_alerts()
            print()
            alerts.send_options_flow_alerts()
            print()
            alerts.send_ml_scores_alerts()
            print("\n✅ Pipeline completo ejecutado!")
        elif choice == '9':
            # Test
            test_msg = f"🧪 Test de conexión - {datetime.now().strftime('%H:%M:%S')}"
            if alerts.send_message(test_msg):
                print("✅ Conexión exitosa!")
            else:
                print("❌ Error de conexión")
        else:
            print("❌ Opción no válida")

    except ValueError as e:
        print(f"\n❌ {e}")
        print("\n📖 Consulta config.py para configuración Telegram")


if __name__ == "__main__":
    main()
