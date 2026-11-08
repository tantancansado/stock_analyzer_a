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
sector_rotation → bandas_per → super_score_integrator → ai_quality_filter
→ entry_exit → thesis_generator → super_dashboard_generator → portfolio_tracker → ticker_data_cache
```

## Reglas críticas de código

### Python (backend)
- **NUNCA dar scores cuando el dato es default/missing**: `fundamental_score == 50.0` y `ml_score == 50.0` significan dato ausente — no puntuar
- `negative_roe == True` → `value_score = 0` (HARD REJECT)
- `analyst_upside_pct < 0` → `value_score = 0` (sobrevalorado)
- `analyst_upside_pct >= 30` (`UPSIDE_ALTO`) NO es un descarte: decide la **valoración propia** (DCF/P-E, `value_bands.respaldo_propio`). Con respaldo propio cuenta como cualquier otro; sin él se penaliza. El usuario (27-oct-2026): «las valoraciones de los analistas están bien, pero nosotros también calculamos precio objetivo y sabemos hacerlo». El antiguo «0% de acierto» eran 14 empresas de software/datos
- **Idea VALUE = barata según NUESTRA valoración** (`respaldo_propio`: triangulado ≥10% y sin divergencia ALTA) **y con las ventas sin caer**, ni en el último trimestre ni en el último año cerrado (`rev_growth_yoy ≥ 0`, `ventas_anual_pct ≥ 0`; sin el dato trimestral, fuera). Lo aplica `value_bands.motivo_fuera_de_value` en US y Europa. Una buena empresa a precio justo no es VALUE
- **La nota de Value US no es una suma** (`value_bands.nota_value`, 7-nov-2026). PRIORIDAD (80-100): ventas del último año ≥10% **y** PER a más de 1σ bajo su media de 10 años. OBSERVAR (40-60): el resto de la puerta, con `value_falta` diciendo qué le falta. Dentro de cada grupo ordena lo barata (PER contra su historia y FCF yield). NO añadir puntos a la nota: había más de 25 ajustes (insiders, opciones, Cerebro, Piotroski, analistas, antigüedad...) y medidos no predecían o iban al revés; quedan como datos de la ficha. Medido contra el universo actual en dos periodos: PRIORIDAD +8,8 a 12 meses en 2020-25 (SPY +5,6) y +6,4 / +13,1 a 90 / 180 días en 2026; crecer sin estar barata -7,5 y -4,1; la puerta sola -0,4 / -0,2. Son pocas empresas y 2024 salió -17: es lo mejor medido, no una garantía
- **Las que pueden doblar (`value_bands.puede_doblar`, 8-nov-2026)**: si DCF y P/E propios (sin el consenso, `recorrido_propio`) le ven +100 % o más, decide la tendencia del beneficio (`bpa_sobre_tendencia_pct`). Con el BPA más de un 50 % sobre su tendencia es beneficio de pico y se VETA (-9,9 y -28,5 a 12 meses en 2020-23 y 2024-26: OXY, NUE, COF, PGR...). Con el beneficio en su tendencia sube a PRIORIDAD aunque no crezca al 10 % (`value_dobla`; +23,5 y +21,6). Sin tendencia, ni una cosa ni otra. Más recorrido NO gana por sí solo (>=100 % en general: -4,9), y con ventas cayendo tampoco (+26 y luego -11): no hay excepción a la puerta. Es lo más fino de lo medido; el tracker lo guarda aparte
- **Avisos de PRIORIDAD (`value_avisos`): se dicen, no puntúan.** Frenazo (último trimestre más de 10 puntos bajo el año, +4,1 frente a +7,6 a 90 días en 2026) y recorte de consenso de BPA de más del 5 % en 13 semanas. En noviembre las «ventas del último año» son un ejercicio cerrado hace diez meses (BSX: +19,9 con el trimestre en +1,4). Si aparece medida suficiente para vetar, se veta; hasta entonces, un aviso no cambia ni grupo ni nota
- **Medir contra el universo ACTUAL.** La puerta parecía dar +5 porque se comparaba con el universo de entonces, más amplio y peor (894 empresas en feb-mar). Y separar por ventas ANUALES, no trimestrales: un trimestre engaña (HHH +330% con el año en -16%)
- **Dentro de la puerta, caer no resta**: lo que está bajo su media descendente (ESPERAR) sale mejor a 12 meses en 2020-25 (+3,9 contra -0,7) y a 90 días en 2026 (+2,4 contra -8,0 lo que no ha caído). El timing es dato de la ficha: no ordena ni veta en Value US
- **El objetivo por P/E sale de TIKR** (`bandas_per`: mediana de 10 años × BPA normalizado) y se reescribe en `fundamental_scores.csv` para que todos lean el mismo número; yfinance solo donde TIKR no llega. Rango del múltiplo 8-45x (`value_bands`). El margen operativo es de 12 meses (`operating_margin_base`), no del último trimestre: el de Yahoo engaña en empresas estacionales
- **Para entrar en el universo curado hay que mejorar lo que ya hay** (`curated_tickers.py`, 7-nov-2026). El listón son las medianas de lo curado en 10 años de cuentas de la SEC, sin 2020-21 en las caídas; luego, un negocio que aguante. El usuario: «solo lo mejor de lo mejor». Pasar el listón no basta: ANET lo pasa y se quedó fuera por ser más del mismo ciclo de IA. LRCX entró el 8-nov por petición del usuario: «si una es mejor que otra, la app debería discernir»; entre empresas del mismo ciclo decide el peso en cartera, no el universo
- **El tracker registra TODO lo publicado** en Value US, con `value_grupo`. No volver a ponerle filtros propios: medía una cartera que la app no enseñaba
- Zona dorada de upside: **[10, 30)** — ya no puntúa en Value US; la usan Europa y el constructor de cartera. No es una regla de exclusión
- Las bandas de upside viven en `value_bands.py` (UPSIDE_MIN/GOLDEN_MAX/UPSIDE_ALTO) — integrator, tracker y conviction las importan de ahí; NUNCA hardcodear una banda inline
- `dividendYield` en yfinance ya viene en porcentaje (0.38 = 0.38%), NO decimal
- `profit_margin_pct` está en `earnings_details`, NO en `health_details`
- MA filter: si falla por rate-limit ("Too Many Requests"), NO penalizar (-20pts se salta)
- Sin fallbacks silenciosos: si el dato falla → no score, no número inventado

### CSS / Frontend
- **NUNCA usar `overflow: hidden` en `.glass`** — usar `overflow: clip`
  - `overflow: hidden` crea un scroll container que rompe `position: sticky` en los thead
  - `overflow: clip` tiene idéntico efecto visual pero NO crea scroll container
- **`.liquid-glass` (desenfoque con brillo y biselado, `index.css`) solo en elementos hero**: modales, tarjeta líder de una página, toolbars/barras siempre visibles. **NUNCA en listas o tablas**: pesa más que `.glass`, que es lo que va en todo lo demás
- **`backdrop-filter` se escribe solo, sin `-webkit-` al lado.** Con las dos líneas el minificador deja únicamente la prefijada y Chrome se queda sin desenfoque; con la estándar sola genera las dos. Y nunca con `url()`: se copia al prefijo y Safari, que no lo entiende, lo perdería entero. Hay test en `css.test.ts`
  - Si un elemento `.liquid-glass` necesita scroll interno (ej. una barra horizontal), el `overflow-x-auto`/`overflow-y-auto` va en un div INTERNO, nunca en el propio `.liquid-glass` — este ya fija `overflow: clip` para sus pseudo-elementos y lo pisaría
  - Tiene piel propia para modo claro (`:root:not(.dark) .liquid-glass`, sección "MODO CLARO — tranquilo"): los highlights blancos del oscuro se lavan sobre fondo claro, así que ahí no imita cristal — es la misma tarjeta blanca elevada un piso más, con sombra en vez de brillo
- Las tablas usan `thead th` con `position: sticky; top: var(--topbar-height, 50px)`
- **Un dato → un único dispositivo de énfasis.** El kit de la app tiene 8 formas de marcar "esto importa" (borde de color, badge bg+border+texto, ring/glow, `.glow-border` rotatorio, text-shadow glow, barra de acento, clases `.grade-A/B/C/D`, punto pulsante). Para un mismo dato (ej. "este pick es bueno"), usar SOLO UNO — nunca apilar borde de Card + badge del mismo color + icono del mismo color + barra de progreso del mismo color encima. Si ya hay un ring/glow o un badge marcando el dato, la tarjeta que lo contiene va neutra (`.glass` sin borde de color)
- **Dos voces, no una con dos brillos.** Oscuro = glassmorphism + Cybertruck
  (cian eléctrico `194 100% 48%`, esquinas de `0.25rem`, orbes, brillos). Claro =
  Apple tranquilo (`#f5f5f7` de fondo, tarjeta blanca, `#1d1d1f` de texto, UN
  acento azul `210 100% 43%`, esquinas de `0.75rem`, elevación por sombra y nada
  de brillo ni animación de fondo). El claro NO es el oscuro con más luz: los
  realces que dan profundidad sobre casi-negro se lavan sobre casi-blanco, y
  compensarlos subiendo saturación es lo que hacía que se leyera como ruido
- **Contraste verificado, no supuesto.** Todo color nuevo del modo claro se mide
  contra fondo (`#f5f5f7`), tarjeta (`#fff`) y relleno (`#e5e5ea`) antes de
  entrar: AA de texto normal es 4.5, y aquí casi todo es texto pequeño. El azul y
  el verde de Apple no llegan tal cual (4.31 y 4.04) — van dos puntos de
  luminosidad más abajo
- **Mobile-first, el usuario usa la app sobre todo en el móvil**:
  - Todo `grid-cols-N` nuevo (N≥2) empieza en `grid-cols-1` salvo que el contenido de cada celda ya sea compacto de forma demostrable (texto ≤0.75rem, ≤2 líneas) — entonces puede ir fijo en 2-3 columnas sin prefijo
  - Toda fila `flex` con 3+ hermanos (badges, filtros, stats) lleva `flex-wrap`
  - Elementos clicables (no decorativos) con texto `text-[0.5rem]` a `text-[0.68rem]` necesitan padding suficiente para un área de toque razonable — ver el bloque `@media (max-width: 640px)` en `index.css` (tap targets, overflow de StatCards, gap de filter bars)
  - El suelo de tamaño de fuente en `index.css:128-142` (`text-[0.5rem]`–`text-[0.68rem]` → mínimo legible en mobile) ya existe — no hace falta repetirlo por página
- **Nada de emoji como icono.** Los pinta el sistema, a todo color y con su
  propio estilo, así que junto a texto en versalitas y a otros iconos se ve que
  están pegados y no diseñados. Todo icono sale de `lucide-react`. Excepciones
  permitidas: banderas de país (no hay equivalente de línea) y símbolos
  tipográficos que se pintan con la fuente y el color del texto (← ↑ ✓ ✗ ⌘ ★).
  Hay un test (`src/test/sinEmoji.test.ts`) que lo comprueba y también vigila
  que no vuelvan `slate/zinc/gray/neutral/stone`, que son tonos fijos y no
  cambian con el tema
- **Señales de ticker → `SignalBadge`** (TRAP, EXIT, SMART MONEY, SQUEEZE,
  EARNINGS, LISTO…): cinco tonos con significado (`favor`, `aviso`, `alarma`,
  `info`, `neutro`) y dos tamaños (`micro` para filas densas, `normal` para
  tarjetas). Cada página las dibujaba por su cuenta y no coincidía ninguna
- **Convención de tamaño de icono** (lucide-react `size={N}`): 3 pasos, no valores sueltos — `12` (micro, inline junto a texto `text-[0.6-0.68rem]`: badges, pills de filtro, stats compactas), `16` (estándar, la mayoría de iconos de UI: botones, filas de lista, `PageHeader`), `20-22` (hero, solo títulos de página o tarjetas líder). No introducir tamaños intermedios (14, 18) en código nuevo
- **Componentes canon a preferir sobre reimplementar a mano**: `PageShell`
  (cabecera + loading + error de una página, ver abajo), `PageHeader`
  (título+subtítulo de página), `EmptyState` (icono+título+subtítulo centrado
  para "sin datos"; con `compact` para huecos dentro de una tabla o tarjeta, que
  es donde el normal —`py-16`, icono `4xl`— no cabe), `.filter-btn`/`.filter-label`
  (pills de filtro con estado activo, variantes `.active`/`.active-red`/`.active-amber`),
  `.table-x-wrap` (scroll horizontal de tablas sin romper sticky thead), `Button`
  (shadcn, solo para CTAs reales — no para pills de filtro/tab, que fuerza
  `h-9`+`[&_svg]:size-4` y agranda controles pensados para ser compactos)
- **La cabecera de página NUNCA va después del early return de loading/error.**
  Era el patrón de 26 páginas (`if (error) return <ErrorState/>` antes de pintar
  nada), y el efecto es que cuando la API no responde la pantalla se queda con un
  mensaje de error y sin decir en qué sección estás. Usar `PageShell`, o extraer
  la cabecera a una constante y devolverla también en esos caminos
- **No añadir padding propio al div raíz de una página**: `<main>` ya aplica
  `p-5 md:p-8`. Cuatro páginas se lo sumaban y acababan con márgenes distintos al
  resto de la app
- **Objetivo táctil**: el mínimo del HIG de Apple es 44×44pt. Los controles de la
  app son más pequeños a propósito (densidad), así que la zona sensible se amplía
  con un pseudo-elemento —`.topbar-action::after` / `.filter-btn::after`— en vez
  de agrandar el control. Al añadir un control compacto nuevo, darle ese
  tratamiento en lugar de subir su tamaño
- **Pestañas dentro de una página**: dos familias y solo dos — `.seg-tab`
  (segmented, con `.active`) y `.underline-tab` (subrayado, para grupos de
  muchas). `PageTabs` añade encima su indicador deslizante (`layoutId`). No
  inventar una tercera: llegó a haber cinco implementaciones distintas
- **Desplegables**: `.select-control`, mismo lenguaje que `.filter-btn`
- **Nada de colores de paleta ajena** (`text-slate-*`, `zinc`, `gray`…): son
  tonos fijos que no cambian con el tema. Usar los tokens (`text-muted-foreground`)
  o `var(--token)` en línea
- **Los tokens de color YA SON colores**, no tripletes sueltos: `--primary: hsl(210 100% 43%)`.
  Se usan `var(--primary)` a secas, y para opacidad
  `color-mix(in oklab, var(--primary) 20%, transparent)` — nunca `hsl(var(--primary))`
  ni `hsl(var(--primary) / .2)`. Con un triplete dentro, cualquier `color-mix` o
  cualquier hoja ajena que consuma el token se cae entera y en silencio: así se
  rompían 46 de los 89 tokens de HeroUI. Hay dos tests en `css.test.ts` que lo vigilan
- **Un `<h1>` por página, y solo uno.** Si la página es pestaña de un
  contenedor, el h1 lo pone la subpágina, no el contenedor. Si el título ya lo
  dice la pestaña activa, usar `tituloOculto` en `PageHeader`: el h1 sigue ahí
  para lectores de pantalla pero no se ve, y así no se dice dos veces lo mismo
  en la misma pantalla (le pasaba a /value y al Centro de mando)
- **La barra superior enseña el título solo cuando la página no lo está
  enseñando ya** (patrón de iOS). Lo detecta sola buscando un encabezado
  visible en `main`: no hay lista que mantener, pero un título que se pinte
  tras cargar necesita que el `MutationObserver` de `TopBar` lo vea
- **Precarga de rutas**: `lib/prefetch.ts` mapea cada ruta del menú a su
  `import()`. Al añadir una ruta nueva hay que añadirla ahí también — hay un
  test que lo comprueba, porque olvidarlo no da ningún síntoma
- **Tipografía en móvil**: el bloque "ESCALA TIPOGRÁFICA EN MÓVIL" de `index.css`
  colapsa los ~32 tamaños arbitrarios a cinco escalones (11/12/13/14/16px) con
  suelo de 11px. Si se usa un `text-[N rem]` nuevo, añadirlo a ese bloque o no
  quedará normalizado

### Frontend (React)
- **Nunca escribir `$` delante de un precio.** Usar `precio()` de `lib/moneda.ts`,
  que deduce la divisa del sufijo de bolsa. La lista principal tiene 13 tickers
  que no cotizan en dólares, y **Londres cotiza en PENIQUES**: Auto Trader a
  489,80 se enseñaba como "$489.80" cuando son 4,90 £. Un `.L → '£'` tampoco
  vale — el símbolo correcto con la magnitud equivocada engaña más
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
- **Vende a PRECIO OBJETIVO por valoración, no a un % fijo de ganancia.** No
  existe un "objetivo del 5-10%" — eso figuraba aquí y el usuario lo desmintió
  el 11-ago-2026. Nunca proponer salidas por porcentaje ganado ni por niveles
  técnicos: el objetivo se calcula (múltiplo × BPA limpio, DCF, consenso).
- **La calidad del negocio modula la salida**: en una empresa excepcional
  (tipo MCO — margen operativo 49%, ROE 77%) aguanta hasta el objetivo
  completo; en una que no lo es tanto, vende antes de alcanzarlo. Así que un
  veredicto de venta necesita DOS cosas: el precio objetivo y qué tan buena es
  la empresa comparada con las mejores de su cartera.
- **El horizonte mínimo de medición es 90 días** (`horizontes.py`). Nada de
  7/14/30d: el usuario vende a precio objetivo por valoración, no a fecha, y
  medido sobre el tracker el edge del sistema NO EXISTE a corto (29% de
  aciertos a 7d, 55% a 90d, 71% a 180d). Un 29% a una semana no dice que el
  sistema falle, dice que todavía no ha pasado nada. **Excepción**: rebotes
  técnicos y setups de entrada (`MEAN_REVERSION`, `BOUNCE_BROAD`,
  `ENTRY_SETUP`) sí son de corto plazo por diseño y llevan su propio plazo.
  Hay un test que impide bajar el mínimo
- Busca empresas **baratas por algo circunstancial, sin que empeoren el negocio ni los números** (5-nov-2026). Dijo también que no compra cerca de máximos salvo negocio excepcional (tipo MSFT), pero el mismo día pidió que decidieran los datos («la idea es ganar dinero, descubre qué funciona mejor») y medido no restaba: la app filtra por lo que sí separa, las ventas cayendo. **Excepcional**, para modular la venta = margen en el cuartil alto y además ROE alto (MCO) o ventas ≥10% (MSFT) Medido el 7-nov-2026 con la puerta actual: dentro de la lista, lo que no ha caído es lo peor, así que su intuición tenía base aunque la distancia al máximo sola no separe
- Prefiere 0 señales antes que señales falsas
- Evitar sugerir compras sin análisis fundamentales sólidos

## Antes de modificar

1. Leer el archivo antes de editarlo
2. No crear archivos nuevos a menos que sea imprescindible
3. No añadir abstracciones para uso único
4. No añadir comentarios obvios ni docstrings a código no modificado
5. Ante errores de build: diagnosticar causa raíz, no hacer `--no-verify`
