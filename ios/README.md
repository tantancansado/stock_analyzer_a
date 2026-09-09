# Stock Analyzer — app nativa iOS

App SwiftUI para las pantallas de **decidir una entrada**. No es un port de la
web: la web tiene 49 páginas / 26 destinos de menú y en el móvil solo se abren
unas pocas. Aquí van cuatro, hechas nativas de verdad.

| Pestaña | Estado | Fuente de datos |
|---|---|---|
| Hoy (Centro de mando) | pendiente | API Railway (necesita JWT de Supabase) |
| Value | **funcionando** | `value_opportunities_filtered.csv` en GitHub Pages |
| Entry setups | pendiente | `momentum_opportunities.csv`, `mean_reversion_opportunities.json` |
| LEAPS | pendiente | `leaps_opportunities.json` |

## Por qué SwiftUI y no Capacitor / React Native

Capacitor es un webview: exactamente lo que ya hay en Pages, cero ganancia en
fluidez. React Native suena a "reaprovecho React", pero shadcn y Tailwind no
portan, así que se reescriben los componentes igual y encima queda un puente
en medio. Lo único reutilizable de verdad era la capa de datos (~1k líneas),
que en Swift se rehace en un rato.

## El backend no se toca

Las listas salen de ficheros estáticos publicados en GitHub Pages
(`https://tantancansado.github.io/stock_analyzer_a`), que son públicos y no
piden auth — la misma fuente que usa la web en producción (`VITE_CSV_BASE`),
no la API de Railway, que solo tiene el snapshot del deploy. Lo que sí
necesitará JWT es Cerebro / régimen / cartera, cuando se haga la pestaña Hoy.

## Compilar

El proyecto `.xcodeproj` **no está en git**: se genera desde `project.yml`.

```bash
cd ios
xcodegen generate          # brew install xcodegen
open StockAnalyzer.xcodeproj
```

Desde línea de comandos, si `xcode-select` apunta a las Command Line Tools
(no hace falta sudo para esto):

```bash
export DEVELOPER_DIR=/Applications/Xcode-beta.app/Contents/Developer
xcodebuild -project StockAnalyzer.xcodeproj -scheme StockAnalyzer \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' build
```

## Instalar en el iPhone

Con cuenta de desarrollador de pago la firma dura un año (con Apple ID gratis
caducaría cada 7 días):

1. Xcode → target `StockAnalyzer` → *Signing & Capabilities* → marcar
   *Automatically manage signing* y elegir el equipo. El `DEVELOPMENT_TEAM` no
   se commitea a propósito, para no clavar un ID de cuenta en el repo.
2. Conectar el iPhone, seleccionarlo como destino y ⌘R.
3. En el móvil: *Ajustes → General → VPN y gestión de dispositivos* → confiar
   en el certificado la primera vez.

No pasa por App Store ni hace falta revisión.

## Convenciones

- **Skin Cybertruck**, igual que la web: fondo oscuro, cian `hsl(194 100% 48%)`
  y esquinas afiladas (`radius: 4pt`). Los valores están en `Core/Theme.swift`;
  si cambian en `frontend/src/index.css`, hay que cambiarlos aquí a mano.
- **Un dato, un solo dispositivo de énfasis** (misma regla que la web): el
  veredicto lo lleva el badge y la tarjeta va neutra.
- **Sin datos inventados**: `CSV.number()` devuelve `nil` ante `nan`/`None`/
  vacío, nunca 0. Un 0 por defecto es el fallo silencioso que el backend tiene
  prohibido.
- **Cero picks no es un error**: el gate de calidad es fail-closed a propósito,
  así que la lista vacía tiene su propio estado y su propio texto, distinto del
  de fallo de red.
