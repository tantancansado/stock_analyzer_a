# Seeking Alpha Fallback Setup

## 📋 Overview

El ticker analyzer ahora usa **Seeking Alpha como fallback** para tickers que no están en el cache. Esto permite analizar cualquier ticker sin depender de Yahoo Finance (que tiene rate limiting estricto).

## 🔄 Estrategia de Datos (Prioridad)

```
1. Cache pre-poblado (docs/ticker_data_cache.json)
   └─ ~140 tickers del pipeline diario
   └─ ✅ Instant, sin API calls, 100% reliable

2. Seeking Alpha API (fallback)
   └─ Cualquier ticker USA
   └─ ⚠️ Requiere cookies de tu sesión
   └─ ✅ Menos rate limiting que Yahoo Finance

3. yfinance (último recurso)
   └─ Solo si Seeking Alpha falla
   └─ ⚠️ Puede ser bloqueado con 429
   └─ 2 segundos de delay para reducir risk
```

## 🚀 Configuración en Railway

### Paso 1: Obtener Cookies de Seeking Alpha

1. Abre Chrome/Firefox
2. Ve a https://seekingalpha.com
3. Login con tu cuenta (si no tienes, créala gratis)
4. Abre DevTools (F12)
5. Ve a la pestaña **Network**
6. Navega a cualquier ticker: https://seekingalpha.com/symbol/FISV
7. Click en cualquier request a `seekingalpha.com`
8. En **Request Headers**, busca `Cookie:`
9. **Copia TODA la línea** (será muy larga):

```
machine_cookie=fkgbuug19c1770905087; session_id=dce97517-4b45-421a-8bb0-f22dcc7471ed; _sasource=; _pxvid=cab3f8a8-081b-11f1-b4b2-42839afd720b; pxcts=cab401f7-081b-11f1-b4b3-f564c0713693; _hjSession_65666=eyJpZCI6IjFiY2NjODVhLTIzN2EtNGYxMC1hZWRkLTFkMjVmODljZmU4NCIsImMiOjE3NzA5MDUwODk3NjQsInMiOjAsInIiOjAsInNiIjowLCJzciI6MCwic2UiOjAsImZzIjoxfQ==; sa-u-source=google; sa-u-date=2026-02-12T14:04:49.889Z; ...
```

### Paso 2: Añadir Variable de Entorno en Railway

1. Ve a tu proyecto en Railway: https://railway.app
2. Click en tu servicio `stockanalyzera-production`
3. Ve a **Variables**
4. Click **New Variable**
5. Name: `SEEKING_ALPHA_COOKIES`
6. Value: Pega la cookie completa que copiaste
7. Click **Add**
8. Railway hará auto-deploy

### Paso 3: Verificar que Funciona

1. Ve al ticker analyzer: https://alejandroalsa.github.io/stock_analyzer_a/docs/ticker_analyzer.html
2. Prueba con un ticker **NO en el cache** (ejemplo: `BA`, `DIS`, `WMT`)
3. Deberías ver:
   ```
   ✅ Análisis completado
   Data Source: seeking_alpha
   ```

## 🔄 Actualizar Cookies (Cuando Expiren)

Las cookies de Seeking Alpha expiran después de ~30 días. Cuando notes que el fallback deja de funcionar:

1. Repite **Paso 1** para obtener cookies frescas
2. Ve a Railway > Variables
3. Click en **Edit** junto a `SEEKING_ALPHA_COOKIES`
4. Pega las nuevas cookies
5. Railway hará auto-deploy

## 📊 Comportamiento del Sistema

### Ticker en Cache (ejemplo: NVDA)
```
Request: Analyze NVDA
  ↓
✅ Found in cache (instant)
  ↓
Analysis completes in ~1 second
```

### Ticker NO en Cache (ejemplo: BA)

**Con Seeking Alpha configurado:**
```
Request: Analyze BA
  ↓
⚠️  Not in cache
  ↓
🌐 Fetching from Seeking Alpha...
  ↓
✅ Got basic data (price, company name)
  ↓
📊 Fetch historical from yfinance (with delay)
  ↓
Analysis completes in ~5 seconds
```

**Sin Seeking Alpha:**
```
Request: Analyze BA
  ↓
⚠️  Not in cache
  ↓
⚠️  No Seeking Alpha cookies
  ↓
📊 Try yfinance (may fail with 429)
  ↓
❌ Rate limited / Error
```

## 🎯 Recomendaciones

1. **Mantén el cache actualizado** con tus tickers favoritos:
   - Edita `generate_test_cache.py`
   - Añade tus tickers a la lista
   - Ejecuta: `python3 generate_test_cache.py`
   - Commit y push

2. **Usa Seeking Alpha solo cuando necesario**:
   - Para tickers que analizas frecuentemente, añádelos al cache
   - Para análisis one-off, Seeking Alpha funciona bien

3. **Actualiza cookies proactivamente**:
   - Cada ~2-3 semanas, refresca las cookies antes de que expiren
   - Así no hay downtime

## ⚠️ Limitaciones

- **Seeking Alpha gratuito** no proporciona datos históricos completos
  - Solo precio actual, market cap, info básica
  - Para históricos (MA, VCP analysis) aún necesita yfinance como backup

- **Cookies son de sesión personal**
  - Solo funcionan para ti
  - Si compartes el proyecto, cada usuario necesita sus propias cookies

- **yfinance aún puede fallar**
  - Si Railway IP está bloqueada, el fallback completo puede fallar
  - Pero es menos probable que solo yfinance

## 🔒 Seguridad

- Las cookies se guardan como **variable de entorno** en Railway
- No se exponen en el código ni en GitHub
- Solo tú tienes acceso a las variables de Railway
- Seeking Alpha usa las cookies para autenticación, no hay riesgo de seguridad
- Las cookies solo dan acceso a datos públicos de Seeking Alpha

---

**Last Updated**: 2025-02-12
**Status**: ✅ Production Ready
