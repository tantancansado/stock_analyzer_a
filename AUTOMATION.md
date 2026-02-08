# 🤖 GUÍA DE AUTOMATIZACIÓN

Sistema completo de ejecución automática de todos los scanners.

## 📋 Scripts Disponibles

### 1. **run_all_scanners.py** - Ejecución Diaria
Ejecuta todos los scanners del sistema (excepto whale scan).

**Incluye:**
- ✅ VCP Scanner
- ✅ Recurring Insiders
- ✅ Super Analyzer 4D
- ✅ Super Opportunities
- ✅ Auto-commit y push

**Uso:**
```bash
python3 run_all_scanners.py
```

**Frecuencia recomendada:** Diaria (después del cierre de mercado)

---

### 2. **run_weekly_whale_scan.py** - Ejecución Semanal
Escanea whales institucionales (13F filings).

**Incluye:**
- 🐋 Scan de 20 whale investors
- 🔨 Build institutional index
- 🎯 Update análisis 4D
- 📤 Auto-commit y push

**Uso:**
```bash
python3 run_weekly_whale_scan.py
```

**Frecuencia recomendada:** Semanal (Lunes por la mañana)

**⚠️ Nota:** Los 13F filings se publican trimestralmente, pero escaneamos semanalmente para detectar nuevos filings rápidamente.

---

## ⏰ CONFIGURACIÓN CON CRON (Linux/Mac)

### Setup Diario + Semanal

```bash
# Editar crontab
crontab -e

# Añadir estas líneas:

# Ejecutar scanners diarios a las 18:00 (después del cierre)
0 18 * * 1-5 cd /Users/ale/Documents/stock_analyzer_a && python3 run_all_scanners.py >> logs/daily_scan.log 2>&1

# Ejecutar whale scan semanal (Lunes 9:00 AM)
0 9 * * 1 cd /Users/ale/Documents/stock_analyzer_a && python3 run_weekly_whale_scan.py >> logs/whale_scan.log 2>&1
```

### Verificar Cron Jobs

```bash
# Ver cron jobs activos
crontab -l

# Ver logs
tail -f logs/daily_scan.log
tail -f logs/whale_scan.log
```

---

## 🔧 CONFIGURACIÓN CON LAUNCHD (Mac)

### Crear Daily Scanner

Archivo: `~/Library/LaunchAgents/com.stockanalyzer.daily.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.stockanalyzer.daily</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/ale/Documents/stock_analyzer_a/run_all_scanners.py</string>
    </array>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>18</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>/Users/ale/Documents/stock_analyzer_a/logs/daily_scan.log</string>

    <key>StandardErrorPath</key>
    <string>/Users/ale/Documents/stock_analyzer_a/logs/daily_scan.error.log</string>
</dict>
</plist>
```

### Crear Weekly Whale Scanner

Archivo: `~/Library/LaunchAgents/com.stockanalyzer.weekly.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.stockanalyzer.weekly</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/ale/Documents/stock_analyzer_a/run_weekly_whale_scan.py</string>
    </array>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key>
        <integer>1</integer>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>/Users/ale/Documents/stock_analyzer_a/logs/whale_scan.log</string>

    <key>StandardErrorPath</key>
    <string>/Users/ale/Documents/stock_analyzer_a/logs/whale_scan.error.log</string>
</dict>
</plist>
```

### Activar LaunchAgents

```bash
# Cargar daily scanner
launchctl load ~/Library/LaunchAgents/com.stockanalyzer.daily.plist

# Cargar weekly scanner
launchctl load ~/Library/LaunchAgents/com.stockanalyzer.weekly.plist

# Verificar que están cargados
launchctl list | grep stockanalyzer

# Ejecutar manualmente (para testing)
launchctl start com.stockanalyzer.daily
launchctl start com.stockanalyzer.weekly
```

---

## 🐙 GITHUB ACTIONS (Alternativa Cloud)

Archivo: `.github/workflows/auto-scan.yml`

```yaml
name: Auto Scan

on:
  schedule:
    # Diario a las 18:00 UTC (después del cierre USA)
    - cron: '0 18 * * 1-5'
  workflow_dispatch:  # Permite ejecución manual

jobs:
  daily-scan:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run all scanners
        run: |
          python3 run_all_scanners.py

      - name: Commit and push
        run: |
          git config user.name "GitHub Actions Bot"
          git config user.email "actions@github.com"
          git add -A
          git commit -m "Auto-update: Daily scan $(date)" || exit 0
          git push
```

Archivo: `.github/workflows/whale-scan.yml`

```yaml
name: Weekly Whale Scan

on:
  schedule:
    # Lunes a las 9:00 UTC
    - cron: '0 9 * * 1'
  workflow_dispatch:

jobs:
  whale-scan:
    runs-on: ubuntu-latest
    timeout-minutes: 60

    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run whale scan
        run: |
          python3 run_weekly_whale_scan.py

      - name: Commit and push
        run: |
          git config user.name "GitHub Actions Bot"
          git config user.email "actions@github.com"
          git add -A
          git commit -m "Weekly whale scan: $(date +%Y-%m-%d)" || exit 0
          git push
```

---

## 📊 CALENDARIO DE EJECUCIÓN

```
LUNES:
├─ 09:00 - 🐋 Whale Scan (semanal)
└─ 18:00 - 📊 Daily Scanners

MARTES-VIERNES:
└─ 18:00 - 📊 Daily Scanners

SÁBADO-DOMINGO:
└─ (Sin ejecuciones - mercado cerrado)
```

---

## 🔍 MONITOREO

### Ver Últimos Logs

```bash
# Daily scanner
tail -50 logs/daily_scan.log

# Whale scanner
tail -50 logs/whale_scan.log

# Ver en tiempo real
tail -f logs/daily_scan.log
```

### Verificar Última Ejecución

```bash
# Ver último commit
git log -1

# Ver archivos modificados recientemente
ls -lt docs/*.html | head -5
```

---

## 🚨 TROUBLESHOOTING

### Script No Se Ejecuta

```bash
# Verificar permisos
chmod +x run_all_scanners.py
chmod +x run_weekly_whale_scan.py

# Verificar Python
which python3
python3 --version
```

### Cron No Funciona

```bash
# Ver logs del sistema
tail -f /var/log/syslog | grep CRON

# Verificar PATH en cron
* * * * * echo $PATH > /tmp/cronpath.txt
```

### GitHub Actions Falla

1. Verificar que el repo tenga permisos de escritura
2. Settings → Actions → General → Workflow permissions → "Read and write"
3. Verificar secrets si usas APIs externas

---

## ✅ CHECKLIST DE SETUP

- [ ] Scripts creados y con permisos de ejecución
- [ ] Logs directory creado (`mkdir -p logs`)
- [ ] Cron configurado o LaunchAgents instalados
- [ ] GitHub Actions configurado (opcional)
- [ ] Primera ejecución manual exitosa
- [ ] Verificar que auto-commit funciona

---

## 📈 BENEFICIOS

✅ **Datos siempre actualizados**
✅ **Sin intervención manual**
✅ **Detección temprana de oportunidades**
✅ **GitHub Pages actualizado automáticamente**
✅ **Logs para debugging**
✅ **Backup automático en git**

---

## 🎯 SIGUIENTE NIVEL

Para llevar la automatización al máximo:

1. **Alertas por email/Slack** cuando se detecten LEGENDARY opportunities
2. **Dashboard de salud del sistema** con uptime monitoring
3. **Rollback automático** si un scan falla
4. **A/B testing** de diferentes estrategias de scoring

---

**¿Preguntas?** Revisa los logs o ejecuta manualmente para debugging.
