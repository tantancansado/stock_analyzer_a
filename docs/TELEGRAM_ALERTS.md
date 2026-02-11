# 📱 Sistema de Alertas de Telegram

Sistema automatizado de notificaciones para oportunidades 5D detectadas por el stock analyzer.

## 🎯 Tipos de Alertas

### 1. 🌟 LEGENDARY Opportunities
**Trigger:** Score >= 80/100
**Contenido:**
- Ticker + Nombre de empresa
- Score 5D completo
- Breakdown de las 5 dimensiones
- Timing Convergence (si aplica)
- VCP Repeater bonus (si aplica)
- Price targets y upside
- Investment thesis corta
- Top whales institucionales

### 2. 📊 Resumen Diario
**Frecuencia:** Diaria
**Contenido:**
- Total de oportunidades por tier
- Count de timing convergence
- Count de VCP repeaters
- Top 5 oportunidades
- Link al dashboard completo

### 3. 🔥 Timing Convergence
**Trigger:** VCP + Insider buying timing alineado
**Contenido:**
- Stocks con perfect timing
- Razón específica del timing
- Explicación de por qué es importante

### 4. 🔁 VCP Repeaters
**Trigger:** Stocks con historial de VCP patterns
**Contenido:**
- Count de apariciones históricas
- Bonus aplicado
- Score actual
- Por qué los repeaters son importantes

## 🚀 Uso

### Ejecución Manual

```bash
# Opción 1: Script bash (recomendado)
./send_telegram_alerts.sh

# Opción 2: Script Python directo
python3 auto_telegram_alerts.py

# Opción 3: Interactivo (seleccionar alertas específicas)
python3 telegram_legendary_alerts.py
```

### Ejecución Automática

El sistema se ejecuta automáticamente al final de:
- `./run_full_pipeline.sh` - Pipeline completo
- GitHub Actions weekly VCP scan (próximamente)

### Configuración de Cron (Opcional)

Para alertas diarias automáticas a las 9:00 AM:

```bash
# Editar crontab
crontab -e

# Añadir esta línea:
0 9 * * * cd /ruta/al/proyecto && ./send_telegram_alerts.sh >> /tmp/telegram_alerts.log 2>&1
```

## ⚙️ Configuración

### Bot Token y Chat ID

Ya configurado en `config.py`:
```python
TELEGRAM_BOT_TOKEN = "762243037:AAFnEVl8saspHl40caBWePSnhe8CLSXWlvY"
TELEGRAM_CHAT_ID = "3165866"
```

### Variables de Entorno (Alternativa)

```bash
export TELEGRAM_BOT_TOKEN="tu_token"
export TELEGRAM_CHAT_ID="tu_chat_id"
```

## 📋 Requisitos

### Datos Necesarios

El sistema requiere que exista:
```
docs/super_opportunities_5d_complete.csv
```

Si no existe, ejecutar primero:
```bash
python3 run_super_analyzer_4d.py
```

### Dependencias Python

```bash
pip install requests
```

(Ya incluido si instalaste los requirements del proyecto)

## 🔧 Troubleshooting

### Error: "No hay datos 5D"
**Solución:** Ejecuta primero el análisis 5D
```bash
python3 run_super_analyzer_4d.py
```

### Error: "Bot token requerido"
**Solución:** Verifica `config.py` o variables de entorno

### Error: "Error enviando mensaje"
**Posibles causas:**
1. Token incorrecto
2. Chat ID incorrecto
3. Bot no tiene permisos en el chat
4. Problemas de conexión

**Test de conexión:**
```bash
python3 telegram_legendary_alerts.py
# Seleccionar opción 6 (Test)
```

## 📊 Ejemplos de Alertas

### LEGENDARY Alert
```
🌟 LEGENDARY OPPORTUNITY DETECTED! 🌟
🔥🔥🔥🔥

NCLH - Norwegian Cruise Line
Super Score 5D: 77.9/100
Tier: ⭐⭐⭐ EXCELENTE

📊 ANÁLISIS 5 DIMENSIONES:
🚀 VCP Pattern: 82/100
   └ 🟢 Excelente
👔 Recurring Insiders: 85/100
   └ 🟢 Excelente
...
```

### Daily Summary
```
📊 RESUMEN DIARIO - SISTEMA 5D
📅 2026-02-11

🎯 OPORTUNIDADES DETECTADAS:
⭐⭐⭐⭐ LEGENDARY: 2
⭐⭐⭐ EXCELENTE: 15
⭐⭐ BUENA: 45

🔥 Timing Convergence: 3
🔁 VCP Repeaters: 12

🏆 TOP 5 OPORTUNIDADES:
1. NCLH - Norwegian Cruise Line
   Score: 77.9/100 ⭐⭐⭐ 🔁
...
```

## 🔄 Flujo de Trabajo

```
VCP Scan (semanal)
    ↓
5D Analyzer
    ↓
Generate Opportunities CSV
    ↓
Auto Telegram Alerts
    ├─ Daily Summary
    ├─ LEGENDARY Alerts
    ├─ Timing Convergence
    └─ VCP Repeaters
```

## 📈 Mejoras Futuras

- [ ] Alertas en tiempo real (webhooks)
- [ ] Alertas de breakouts inminentes
- [ ] Gráficos automáticos adjuntos
- [ ] Comandos interactivos en Telegram
- [ ] Alertas personalizadas por usuario
- [ ] Integración con trading view alerts

## 📝 Notas

- Las alertas se envían en HTML format para mejor visualización
- Los mensajes largos se dividen automáticamente (límite 4096 caracteres)
- El sistema es tolerante a fallos (no crítico si falla una alerta)
- Todas las alertas incluyen timestamp y link al dashboard

## 🆘 Soporte

Para problemas o sugerencias, revisar:
- `config.py` - Configuración del bot
- `telegram_legendary_alerts.py` - Sistema de alertas
- `auto_telegram_alerts.py` - Pipeline automatizado
