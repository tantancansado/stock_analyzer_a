# Stock Analyzer — Instrucciones para Claude Code

## Arquitectura general

Sistema dual VALUE + MOMENTUM:
- `super_score_integrator.py` → `docs/value_opportunities.csv` + `docs/momentum_opportunities.csv`
- `fundamental_scorer.py` → `docs/fundamental_scores.csv`
- `ticker_api.py` → API Flask en Railway
- `portfolio_tracker.py` → seguimiento de recomendaciones (7d/14d/30d)
- Frontend: React + Vite + shadcn/ui + Tailwind v4, desplegado en `docs/app/` (GitHub Pages)

Orden del pipeline (GitHub Actions):
```
sector_rotation → mean_reversion → super_score_integrator → ai_quality_filter
→ entry_exit → thesis_generator → super_dashboard_generator → portfolio_tracker → ticker_data_cache
```

## Reglas críticas de código

### Python (backend)
- **NUNCA dar scores cuando el dato es default/missing**: `fundamental_score == 50.0` y `ml_score == 50.0` significan dato ausente — no puntuar
- `negative_roe == True` → `value_score = 0` (HARD REJECT)
- `analyst_upside_pct < 0` → `value_score = 0` (sobrevalorado)
- `analyst_upside_pct >= 30` → `value_score = 0` (HARD REJECT — value trap: 0% win en 55 señales reales; gap enorme del target = el precio se desplomó por algo que el modelo no ve)
- Zona dorada de upside: **[10, 25)** (+4.73% / 83% win en backtest). Premiar esta banda, NO el upside alto
- Las bandas de upside viven en `value_bands.py` (UPSIDE_MIN/GOLDEN_MAX/HARD_REJECT) — integrator, tracker y conviction las importan de ahí; NUNCA hardcodear una banda inline
- `dividendYield` en yfinance ya viene en porcentaje (0.38 = 0.38%), NO decimal
- `profit_margin_pct` está en `earnings_details`, NO en `health_details`
- MA filter: si falla por rate-limit ("Too Many Requests"), NO penalizar (-20pts se salta)
- Sin fallbacks silenciosos: si el dato falla → no score, no número inventado

### CSS / Frontend
- **NUNCA usar `overflow: hidden` en `.glass`** — usar `overflow: clip`
  - `overflow: hidden` crea un scroll container que rompe `position: sticky` en los thead
  - `overflow: clip` tiene idéntico efecto visual pero NO crea scroll container
- **`.liquid-glass` (refracción real vía SVG `feDisplacementMap`, `index.css`) solo en elementos hero**: modales, tarjeta líder de una página, toolbars/barras siempre visibles. **NUNCA en listas o tablas** — el filtro SVG se repinta cada frame, es caro. Para todo lo demás usar `.glass` (blur plano, sin distorsión)
  - Si un elemento `.liquid-glass` necesita scroll interno (ej. una barra horizontal), el `overflow-x-auto`/`overflow-y-auto` va en un div INTERNO, nunca en el propio `.liquid-glass` — este ya fija `overflow: clip` para sus pseudo-elementos y lo pisaría
  - Tiene piel propia para modo claro (`:root:not(.dark) .liquid-glass` en la sección Cybertruck Light) — los highlights blancos del modo oscuro se lavan sobre fondo claro, ahí se usan tonos acero/cian en su lugar
- Las tablas usan `thead th` con `position: sticky; top: var(--topbar-height, 50px)`
- **Un dato → un único dispositivo de énfasis.** El kit de la app tiene 8 formas de marcar "esto importa" (borde de color, badge bg+border+texto, ring/glow, `.glow-border` rotatorio, text-shadow glow, barra de acento, clases `.grade-A/B/C/D`, punto pulsante). Para un mismo dato (ej. "este pick es bueno"), usar SOLO UNO — nunca apilar borde de Card + badge del mismo color + icono del mismo color + barra de progreso del mismo color encima. Si ya hay un ring/glow o un badge marcando el dato, la tarjeta que lo contiene va neutra (`.glass` sin borde de color)
- Tema: dark glassmorphism + Cybertruck skin (cyan eléctrico `194 100% 48%`, esquinas afiladas `--radius: 0.25rem`)
- **Mobile-first, el usuario usa la app sobre todo en el móvil**:
  - Todo `grid-cols-N` nuevo (N≥2) empieza en `grid-cols-1` salvo que el contenido de cada celda ya sea compacto de forma demostrable (texto ≤0.75rem, ≤2 líneas) — entonces puede ir fijo en 2-3 columnas sin prefijo
  - Toda fila `flex` con 3+ hermanos (badges, filtros, stats) lleva `flex-wrap`
  - Elementos clicables (no decorativos) con texto `text-[0.5rem]` a `text-[0.68rem]` necesitan padding suficiente para un área de toque razonable — ver el bloque `@media (max-width: 640px)` en `index.css` (tap targets, overflow de StatCards, gap de filter bars)
  - El suelo de tamaño de fuente en `index.css:128-142` (`text-[0.5rem]`–`text-[0.68rem]` → mínimo legible en mobile) ya existe — no hace falta repetirlo por página

### Frontend (React)
- CSVs en producción vienen de GitHub Pages (`VITE_CSV_BASE`), NO de Railway
- Railway API solo tiene snapshot del momento del deploy
- `getCsvUrl()` / `downloadCsv()` en `frontend/src/api/client.ts`
- Watchlist persiste en localStorage con key `sa-watchlist-v1`

## Archivos clave

| Archivo | Descripción |
|---------|-------------|
| `docs/fundamental_scores.csv` | Datos fundamentales por ticker |
| `docs/value_opportunities.csv` | Output VALUE (sin filtrar) |
| `docs/value_opportunities_filtered.csv` | VALUE filtrado por IA |
| `docs/momentum_opportunities.csv` | Output MOMENTUM |
| `docs/portfolio_tracker/recommendations.csv` | Historial de recomendaciones |
| `docs/portfolio_tracker/summary.json` | Resumen de performance |
| `ticker_api.py` | Flask API — todos los endpoints |
| `frontend/src/pages/` | Páginas React |
| `frontend/src/hooks/useTechnicalData.ts` | Cache compartido de señales técnicas (patrón listener) |

## Perfil del usuario

- Inversor VALUE/GARP estilo Lynch, NO trader momentum Minervini
- Objetivo: ganancias consistentes 5-10%, alta tasa de acierto
- Prefiere 0 señales antes que señales falsas
- Evitar sugerir compras sin análisis fundamentales sólidos

## Antes de modificar

1. Leer el archivo antes de editarlo
2. No crear archivos nuevos a menos que sea imprescindible
3. No añadir abstracciones para uso único
4. No añadir comentarios obvios ni docstrings a código no modificado
5. Ante errores de build: diagnosticar causa raíz, no hacer `--no-verify`
