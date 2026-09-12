/**
 * Precarga del código de una ruta antes de entrar en ella.
 *
 * Cada página va en su propio chunk (`lazy()`), así que la primera visita
 * paga la descarga: medido con la CPU 4 veces más lenta, entrar en LEAPS por
 * primera vez costaba 1209ms, y en el Centro de mando 651ms — casi todo
 * esperando el chunk, no pintando.
 *
 * Al apuntar o tocar una entrada del menú hay un margen de unos cientos de
 * milisegundos hasta que el dedo levanta y la navegación ocurre. Ahí cabe la
 * descarga. No se precarga nada "por si acaso": solo lo que el usuario está a
 * punto de abrir.
 */

// El mismo import() que usa el lazy() de App.tsx. Tiene que ser un literal
// para que Vite lo reconozca y reutilice el chunk ya generado — con una ruta
// construida en tiempo de ejecución crearía un módulo aparte.
const RUTAS: Record<string, () => Promise<unknown>> = {
  '/dashboard':       () => import('../pages/Dashboard'),
  '/value':           () => import('../pages/Value'),
  '/entry-setups':    () => import('../pages/EntrySetups'),
  '/insiders':        () => import('../pages/Insiders'),
  '/options':         () => import('../pages/OptionsFlow'),
  '/leaps':           () => import('../pages/Leaps'),
  '/sectors':         () => import('../pages/Sectors'),
  '/my-portfolio':    () => import('../pages/MyPortfolio'),
  '/backtest':        () => import('../pages/Backtest'),
  '/search':          () => import('../pages/TickerSearch'),
  '/datos':           () => import('../pages/Datos'),
  '/position-sizing': () => import('../pages/PositionSizing'),
  '/macro-radar':     () => import('../pages/Macro'),
  '/earnings':        () => import('../pages/Calendar'),
  '/dividend-traps':  () => import('../pages/DividendTraps'),
  '/compare':         () => import('../pages/Comparador'),
  '/bounce':          () => import('../pages/BounceTrader'),
  '/calibration':     () => import('../pages/Calibration'),
  '/owner-earnings':  () => import('../pages/OwnerEarnings'),
  '/manual':          () => import('../pages/Manual'),
  '/bonds':           () => import('../pages/Bonds'),
  '/signal-stats':    () => import('../pages/SignalStats'),
  '/commodities':     () => import('../pages/Commodities'),
  '/corrupcion':      () => import('../pages/CorrupcionInstitucional'),
  '/portfolio':       () => import('../pages/Portfolio'),
  '/admin/usage':     () => import('../pages/AdminUsage'),
}

const yaPedidas = new Set<string>()

/** Pide el chunk de esa ruta si no se ha pedido antes. Silencioso: si falla, la
 *  navegación normal lo reintentará y mostrará el error como siempre. */
export function prefetchRuta(path: string): void {
  if (yaPedidas.has(path)) return
  const cargar = RUTAS[path]
  if (!cargar) return
  yaPedidas.add(path)
  cargar().catch(() => yaPedidas.delete(path))
}
