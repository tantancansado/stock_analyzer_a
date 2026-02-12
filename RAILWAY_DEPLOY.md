# 🚀 Deploy to Railway - Ticker Analyzer API

## Prerequisitos

- ✅ Cuenta en Railway.app (gratis)
- ✅ Repo en GitHub con el código
- ✅ Railway CLI instalado (opcional)

---

## 🚀 Deploy Rápido (desde Railway Dashboard)

### 1. Crear Nuevo Proyecto en Railway

1. Ve a [railway.app](https://railway.app)
2. Click **"New Project"**
3. Selecciona **"Deploy from GitHub repo"**
4. Autoriza Railway a acceder a tu GitHub
5. Selecciona el repo `stock_analyzer_a`

### 2. Railway Auto-Detecta Python

Railway automáticamente detecta:
- ✅ `requirements.txt` → Instala dependencias
- ✅ `Procfile` → Ejecuta gunicorn
- ✅ `runtime.txt` → Usa Python 3.9.20

### 3. Configurar Variables de Entorno

En el dashboard de Railway:

**Settings → Variables**

```bash
FLASK_ENV=production
FLASK_DEBUG=False
```

Railway automáticamente añade:
```bash
PORT=<puerto-dinámico>
```

### 4. Deploy!

Railway automáticamente:
1. ✅ Clona el repo
2. ✅ Instala dependencias de `requirements.txt`
3. ✅ Ejecuta `gunicorn ticker_analyzer_api:app`
4. ✅ Te da una URL pública

**Tu URL será algo como:**
```
https://stock-analyzer-production.up.railway.app
```

---

## 📝 Actualizar Frontend

Una vez deployado, copia la URL de Railway y actualiza:

**`docs/ticker_analyzer.html`** (línea ~443):

```javascript
// Cambiar de:
const API_URL = 'http://localhost:5001';

// A tu URL de Railway:
const API_URL = 'https://stock-analyzer-production.up.railway.app';
```

Commit y push:
```bash
git add docs/ticker_analyzer.html
git commit -m "feat: Update API URL to Railway"
git push
```

GitHub Pages ahora llamará a tu backend en Railway! 🎉

---

## 🔄 Auto-Deploy (CI/CD)

Railway auto-deploya cada vez que haces push a main:

```bash
git add .
git commit -m "feat: Add new feature"
git push

# Railway automáticamente:
# 1. Detecta el push
# 2. Rebuild
# 3. Redeploy
# ✅ Tu API se actualiza en ~2-3 minutos
```

---

## 🛠️ Railway CLI (Opcional)

### Instalar CLI:
```bash
npm i -g @railway/cli
railway login
```

### Deploy desde terminal:
```bash
railway link  # Link to your project
railway up    # Deploy
railway logs  # Ver logs
```

---

## 📊 Monitoreo

**Railway Dashboard → Deployments:**
- ✅ Build logs
- ✅ Runtime logs
- ✅ CPU/Memory usage
- ✅ Request metrics

**Ver logs en tiempo real:**
```bash
railway logs --follow
```

---

## ⚡ Troubleshooting

### Build Fails

**Error:** `No module named 'flask'`

**Fix:** Asegúrate que `requirements.txt` existe con todas las deps:
```bash
git add requirements.txt
git commit -m "Add requirements.txt"
git push
```

### App Crashes

**Error:** `Address already in use`

**Fix:** El `Procfile` debe usar `$PORT`:
```
web: gunicorn ticker_analyzer_api:app --bind 0.0.0.0:$PORT
```

### CORS Errors

**Error:** Frontend no puede llamar al backend

**Fix:** Verifica que `flask-cors` está en `requirements.txt` y CORS está habilitado:
```python
from flask_cors import CORS
app = Flask(__name__)
CORS(app)  # ✅ Esto debe estar
```

### Timeout en análisis largos

**Error:** Request timeout después de 30s

**Fix:** Ya configurado en `Procfile`:
```
--timeout 120  # 120 segundos
```

---

## 💰 Costos

**Railway Free Tier:**
- ✅ $5 de crédito gratis/mes
- ✅ 500 horas de ejecución
- ✅ Perfecto para este proyecto

**Uso estimado de este proyecto:**
- ~$0.20/día con uso moderado
- ~$6/mes si está 24/7

**Para ahorrar recursos:**
1. Railway pone la app en "sleep" si no hay tráfico
2. Primera request después de sleep tarda ~10s
3. Luego es instant

---

## 🔒 Seguridad

### Rate Limiting (Opcional)

Si quieres limitar requests, añade a `ticker_analyzer_api.py`:

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100 per hour"]
)
```

Y en `requirements.txt`:
```
Flask-Limiter==3.5.0
```

---

## 📈 Performance

### Optimizaciones Aplicadas:

1. **Gunicorn con 2 workers**
   ```
   --workers 2
   ```

2. **Timeout de 120s**
   ```
   --timeout 120
   ```

3. **Caching de análisis** (TODO - futuro)
   - Redis para cachear resultados
   - Evita re-analizar mismo ticker

---

## 🎯 URLs Finales

Una vez deployado:

**Backend API:**
```
https://stock-analyzer-production.up.railway.app
```

**Frontend (GitHub Pages):**
```
https://YOUR_USERNAME.github.io/stock_analyzer_a/ticker_analyzer.html
```

**Health Check:**
```
https://stock-analyzer-production.up.railway.app/api/health
```

**Analyze Ticker:**
```
https://stock-analyzer-production.up.railway.app/api/analyze/NVDA
```

---

## ✅ Checklist de Deploy

- [ ] Push código a GitHub
- [ ] Crear proyecto en Railway
- [ ] Link repo de GitHub
- [ ] Esperar auto-deploy (~2-3 min)
- [ ] Copiar URL de Railway
- [ ] Actualizar `API_URL` en frontend
- [ ] Push frontend actualizado
- [ ] Probar en GitHub Pages
- [ ] ✅ ¡Funciona desde cualquier lugar!

---

**¡Listo! Tu Stock Analyzer está en la nube 🚀**

Para cualquier problema, revisa los logs:
```bash
railway logs --follow
```

O contacta en Railway Discord: [discord.gg/railway](https://discord.gg/railway)
