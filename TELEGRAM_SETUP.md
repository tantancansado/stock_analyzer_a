# 📱 GUÍA DE CONFIGURACIÓN - TELEGRAM ALERTS

Sistema de alertas automáticas por Telegram para oportunidades LEGENDARY.

---

## 🎯 ¿Qué hace?

Envía notificaciones automáticas cuando se detectan oportunidades con **Super Score 4D ≥ 85** (tier LEGENDARY):

- ✅ **Alertas instantáneas** cuando se ejecutan los scanners
- ✅ **Resúmenes diarios** con top opportunities
- ✅ **Integrado con GitHub Actions** para automatización completa
- ✅ **Funciona localmente y en la nube**

---

## 📋 PASO 1: Crear Bot de Telegram

### 1.1 Hablar con BotFather

1. Abre Telegram y busca: **@BotFather**
2. Envía el comando: `/newbot`
3. Sigue las instrucciones:
   - **Nombre del bot:** "Stock Analyzer Alerts" (o el que prefieras)
   - **Username:** `stock_analyzer_alerts_bot` (debe terminar en `_bot`)

4. **BotFather te enviará un token**, algo como:
   ```
   123456789:ABCdefGHIjklMNOpqrsTUVwxyz1234567890
   ```

5. **GUARDA ESTE TOKEN** - lo necesitarás después

### 1.2 Configurar el Bot

Envía estos comandos a BotFather para configurar tu bot:

```
/setdescription
@tu_bot_username
Sistema de alertas automáticas para oportunidades de trading LEGENDARY

/setabouttext
@tu_bot_username
Alertas automáticas del Stock Analyzer 4D

/setuserpic
@tu_bot_username
(Opcional: sube una imagen para el bot)
```

---

## 📋 PASO 2: Obtener tu Chat ID

### 2.1 Iniciar conversación con tu bot

1. Busca tu bot en Telegram (el username que creaste)
2. Presiona **START** o envía `/start`
3. Envía cualquier mensaje, por ejemplo: "Hola"

### 2.2 Obtener el Chat ID

Abre esta URL en tu navegador (reemplaza `<TU_TOKEN>` con el token de BotFather):

```
https://api.telegram.org/bot<TU_TOKEN>/getUpdates
```

**Ejemplo:**
```
https://api.telegram.org/bot123456789:ABCdef.../getUpdates
```

Verás una respuesta JSON como esta:

```json
{
  "ok": true,
  "result": [
    {
      "update_id": 123456789,
      "message": {
        "message_id": 1,
        "from": {
          "id": 987654321,     <-- ESTE ES TU CHAT_ID
          "is_bot": false,
          "first_name": "Tu Nombre"
        },
        "chat": {
          "id": 987654321,      <-- TAMBIÉN AQUÍ
          "first_name": "Tu Nombre",
          "type": "private"
        },
        "text": "Hola"
      }
    }
  ]
}
```

El `chat.id` (número como `987654321`) es tu **CHAT_ID**.

---

## 🔧 PASO 3: Configuración Local

### Opción A: Archivo de Configuración (Recomendado)

Crea el archivo `config/telegram_config.json`:

```bash
mkdir -p config
cat > config/telegram_config.json << 'EOF'
{
  "bot_token": "TU_BOT_TOKEN_AQUI",
  "chat_id": "TU_CHAT_ID_AQUI"
}
EOF
```

**Ejemplo real:**
```json
{
  "bot_token": "123456789:ABCdefGHIjklMNOpqrsTUVwxyz1234567890",
  "chat_id": "987654321"
}
```

### Opción B: Variables de Entorno

Añade a tu `.bashrc`, `.zshrc` o `.bash_profile`:

```bash
export TELEGRAM_BOT_TOKEN="123456789:ABCdefGHIjklMNOpqrsTUVwxyz1234567890"
export TELEGRAM_CHAT_ID="987654321"
```

Luego recarga:
```bash
source ~/.bashrc  # o ~/.zshrc
```

### 🔒 Seguridad

**IMPORTANTE:** Añade el archivo de configuración al `.gitignore`:

```bash
echo "config/telegram_config.json" >> .gitignore
```

---

## ✅ PASO 4: Test de Conexión

Prueba que todo funciona:

```bash
python3 telegram_legendary_alerts.py
```

Selecciona opción **3** (Test de conexión).

Si funciona, verás:
```
✅ Conexión exitosa!
```

Y recibirás un mensaje de prueba en Telegram.

---

## 🐙 PASO 5: Configurar GitHub Actions (Opcional)

Para que las alertas funcionen en GitHub Actions automáticamente:

### 5.1 Añadir Secrets a GitHub

1. Ve a tu repositorio en GitHub
2. Settings → Secrets and variables → Actions
3. Click **New repository secret**
4. Añade dos secrets:

   **Secret 1:**
   - Name: `TELEGRAM_BOT_TOKEN`
   - Value: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz1234567890`

   **Secret 2:**
   - Name: `TELEGRAM_CHAT_ID`
   - Value: `987654321`

### 5.2 Verificar Workflows

Los workflows ya están configurados:
- `.github/workflows/daily-scan.yml` → Envía alertas diarias
- `.github/workflows/whale-scan.yml` → Envía alertas semanales

No necesitas modificar nada más.

---

## 🚀 USO

### Alertas Automáticas

Una vez configurado, las alertas se envían automáticamente cuando:

#### Ejecución Local
```bash
# Daily scanners (incluye alertas)
python3 run_all_scanners.py

# Weekly whale scan (incluye alertas)
python3 run_weekly_whale_scan.py
```

#### GitHub Actions
- **Diario:** Lunes-Viernes 18:00 UTC
- **Semanal:** Lunes 9:00 UTC

### Alertas Manuales

```bash
python3 telegram_legendary_alerts.py
```

Opciones:
1. **Buscar y alertar LEGENDARY** - Escanea y envía alertas solo para score ≥ 85
2. **Enviar resumen diario** - Top 10 oportunidades del día
3. **Test de conexión** - Verificar que funciona

---

## 📊 Ejemplo de Alerta

Así se ve una alerta LEGENDARY:

```
🌟 LEGENDARY OPPORTUNITY DETECTED! 🌟
🔥🔥🔥🔥🔥

Ticker: AAPL
Super Score 4D: 92.5/100
Tier: ⭐⭐⭐⭐ LEGENDARY

📊 ANÁLISIS 4 DIMENSIONES:

🚀 VCP Pattern: 95/100
   └ Patrón técnico 🟢 Excelente

🔁 Recurring Insiders: 88/100
   └ Compras ejecutivos 🟢 Excelente

📊 Sector State: 92/100
   └ Estado sectorial 🟢 Excelente

🏛️ Institutional: 95/100
   └ Whales acumulando 🟢 Excelente

🐋 Whales Holding:
   • Vanguard Group Inc - 8.2%
   • BlackRock Inc - 7.5%
   • State Street Corp - 4.3%

💡 Razón:
Confirmación cuádruple - Probabilidad histórica

🔗 Ver más:
Dashboard completo

⏰ Detectado: 2026-02-08 18:30
```

---

## 🔍 TROUBLESHOOTING

### Error: "Bot token y chat_id requeridos"

**Solución:**
- Verifica que `config/telegram_config.json` existe y tiene el formato correcto
- O que las variables de entorno están configuradas
- Ejecuta el test: `python3 telegram_legendary_alerts.py` (opción 3)

### Error: "Error enviando mensaje"

**Causas comunes:**
1. **Token incorrecto** - Verifica que copiaste el token completo
2. **Chat ID incorrecto** - Debe ser un número, no texto
3. **No iniciaste el bot** - Debes enviar `/start` a tu bot primero
4. **Internet** - Verifica tu conexión

**Verificar token:**
```bash
curl https://api.telegram.org/bot<TU_TOKEN>/getMe
```

Debe retornar información de tu bot.

### No recibo alertas en GitHub Actions

**Checklist:**
1. ✅ Secrets configurados en GitHub (Settings → Secrets)
2. ✅ Nombres exactos: `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`
3. ✅ Workflow activado (Actions → Check workflow runs)
4. ✅ Hay oportunidades LEGENDARY (score ≥ 85)

**Ver logs:**
- GitHub → Actions → Daily Market Scan → Click en el último run
- Buscar la sección "FASE 8: TELEGRAM ALERTS"

### "No hay LEGENDARY opportunities"

Esto es **normal** - significa que el scanner no encontró oportunidades con score ≥ 85.

Para recibir más alertas, puedes:
- Ajustar el threshold en el código (cambiar `>= 85` a `>= 75`)
- Esperar a que el mercado genere mejores setups
- Verificar que todos los scanners se ejecutan correctamente

---

## 🎯 PERSONALIZACIÓN

### Cambiar threshold de alertas

Edita `telegram_legendary_alerts.py`, línea 141:

```python
# De:
legendary = df[df['super_score_4d'] >= 85]

# A (para recibir más alertas):
legendary = df[df['super_score_4d'] >= 75]  # ÉPICAS también
```

### Añadir alertas para otros eventos

Puedes crear alertas personalizadas en `run_all_scanners.py`:

```python
# Después de VCP scan
if vcp_results_count > 0:
    alerts.send_message(f"🚀 {vcp_results_count} nuevos VCP patterns detectados!")
```

### Cambiar formato de mensajes

Modifica `format_legendary_alert()` en `telegram_legendary_alerts.py` para personalizar el estilo.

---

## 📈 MONITOREO

### Ver últimas alertas enviadas

Los logs se guardan en:
```bash
tail -f logs/daily_scan.log | grep "TELEGRAM"
```

### Estadísticas

```python
# Contar alertas enviadas hoy
grep "alertas enviadas" logs/daily_scan.log | tail -1
```

---

## 🔐 SEGURIDAD

**IMPORTANTE:**
- ✅ Nunca subas `config/telegram_config.json` a GitHub
- ✅ Usa GitHub Secrets para automatización
- ✅ No compartas tu bot token públicamente
- ✅ Si expones el token accidentalmente, revócalo con @BotFather (`/revoke`)

**Regenerar token:**
```
@BotFather → /revoke → selecciona tu bot → /token
```

---

## ✅ CHECKLIST FINAL

- [ ] Bot creado con @BotFather
- [ ] Bot token obtenido y guardado
- [ ] Chat ID obtenido
- [ ] Configuración local creada (`config/telegram_config.json` o env vars)
- [ ] Test de conexión exitoso
- [ ] GitHub Secrets configurados (si usas Actions)
- [ ] Primera alerta recibida correctamente

---

## 🎊 ¡LISTO!

Tu sistema de alertas está configurado. Ahora recibirás notificaciones automáticas cada vez que se detecten oportunidades LEGENDARY.

**Próximos pasos:**
1. Ejecuta `python3 run_all_scanners.py` para el primer scan
2. Configura cron o GitHub Actions para automatización
3. Ajusta thresholds según tus preferencias

---

**¿Problemas?** Ejecuta el test y revisa los logs:
```bash
python3 telegram_legendary_alerts.py  # Opción 3
tail -50 logs/daily_scan.log
```
