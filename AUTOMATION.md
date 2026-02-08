# 🔄 Automatización del Sistema de Tesis

## ✅ Automatización con GitHub Actions (Recomendado)

El sistema se actualiza **automáticamente** vía GitHub Actions:

### 🤖 Actualización Automática Programada

- **Frecuencia**: Lunes a Viernes a las 18:00 UTC (después del cierre del mercado US)
- **Workflow**: `.github/workflows/update-theses.yml`
- **Qué hace**:
  1. Actualiza datos 5D (sectores, fundamentales, entry scores)
  2. Regenera tesis para top 50 stocks
  3. Hace commit y push automático
  4. Despliega en GitHub Pages

### 🎯 Ejecución Manual desde GitHub

1. Ve a: **Actions** → **Auto Update Investment Theses**
2. Click en **Run workflow**
3. Selecciona número de tesis (25/50/100)
4. Click **Run workflow**

### 📊 Ver Estado de Actualizaciones

- **GitHub Actions**: https://github.com/TU_USUARIO/stock_analyzer_a/actions
- **Artifacts**: Cada ejecución guarda un `update-summary.txt`
- **Commits**: Busca commits con prefijo `chore: Auto-update theses`

### 🔔 Configurar Notificaciones

En tu repo → **Settings** → **Notifications**:
- Activa notificaciones para workflow failures
- Opcional: email cuando se complete cada update

---

## 💻 Actualización Manual Local

Para actualizar datos localmente:

```bash
./auto_update_theses.sh 50
```

Esto hace:
1. Ejecuta `enrich_5d.py` para actualizar datos fundamentales y entry scores
2. Ejecuta `thesis_generator.py 50` para regenerar tesis del top 50
3. Guarda un log en `logs/auto_update_YYYYMMDD_HHMMSS.log`

### Verificar Logs Locales

```bash
# Ver último log
ls -lt logs/ | head -5

# Contenido del último log
tail -50 logs/auto_update_*.log
```

---

## 🚀 Primer Setup en GitHub

1. **Push del código**:
   ```bash
   git push origin main
   ```

2. **Activar GitHub Pages**:
   - Settings → Pages
   - Source: Deploy from branch
   - Branch: `main` → `/docs`
   - Save

3. **Verificar Workflow**:
   - Actions → Check que "Auto Update Investment Theses" aparezca
   - Primera ejecución manual para probar

4. **Acceder al Dashboard**:
   - URL: `https://TU_USUARIO.github.io/stock_analyzer_a/`

---

## ⚙️ Personalización del Workflow

Edita `.github/workflows/update-theses.yml` para cambiar:

**Frecuencia de actualización:**
```yaml
schedule:
  - cron: '0 18 * * 1-5'  # Lunes-Viernes 18:00 UTC
  - cron: '0 20 * * 0'    # + Domingos 20:00 UTC
```

**Número de tesis por defecto:**
```yaml
default: '100'  # Cambiar de 50 a 100
```

**Horario específico (ej: después de cierre mercado español - 17:30 CET = 16:30 UTC):**
```yaml
- cron: '30 16 * * 1-5'
```
