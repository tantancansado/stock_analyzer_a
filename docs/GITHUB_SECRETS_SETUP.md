# GitHub Secrets Setup for Telegram Alerts

Para que las alertas de Telegram funcionen automáticamente en GitHub Actions, necesitas configurar dos secrets:

## 📱 Paso 1: Ir a GitHub Settings

1. Ve a tu repositorio en GitHub: https://github.com/tantancansado/stock_analyzer_a
2. Click en **Settings** (⚙️)
3. En el menú lateral izquierdo, click en **Secrets and variables** → **Actions**
4. Click en **New repository secret**

## 🔑 Paso 2: Añadir TELEGRAM_BOT_TOKEN

1. Click en **New repository secret**
2. **Name**: `TELEGRAM_BOT_TOKEN`
3. **Secret**: Pega el token de tu bot (el que empieza con números:letras)
   ```
   Tu token actual del bot stocksSuggestor
   ```
4. Click en **Add secret**

## 💬 Paso 3: Añadir TELEGRAM_CHAT_ID

1. Click en **New repository secret** de nuevo
2. **Name**: `TELEGRAM_CHAT_ID`
3. **Secret**: Pega tu chat ID (el número que empieza con -)
   ```
   Tu chat ID actual
   ```
4. Click en **Add secret**

## ✅ Verificar

Una vez configurados, deberías ver en tu página de Secrets:
- ✅ TELEGRAM_BOT_TOKEN
- ✅ TELEGRAM_CHAT_ID

## 🚀 Prueba Manual

Después de configurar los secrets, puedes probar el workflow manualmente:

1. Ve a la pestaña **Actions** en GitHub
2. Click en **Daily Market Analysis - Full Pipeline**
3. Click en **Run workflow** → **Run workflow**
4. Espera ~5-10 minutos
5. Deberías recibir las alertas en Telegram!

## 📅 Ejecución Automática

Una vez configurado, el pipeline se ejecutará automáticamente:
- **Lunes a Viernes** a las **6:00 AM UTC** (2:00 AM EST / 8:00 AM CET)
- Recibirás alertas de Telegram cada mañana con:
  - 🌟 Legendary Opportunities
  - 🔥 Timing Convergence
  - 🔁 VCP Repeaters
  - 🔄 Mean Reversion
  - 🐋 Options Flow (whale activity)

## 🔒 Seguridad

Los secrets están encriptados y solo GitHub Actions puede acceder a ellos. Nunca se muestran en logs ni commits.
