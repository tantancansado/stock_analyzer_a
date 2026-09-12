import { useLocation, Link } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { Clock, Sun, Moon, Menu, Search, Brain, Grid3x3 } from 'lucide-react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { useTheme } from '../context/ThemeContext'
import { useNothingTheme } from '../hooks/useNothingTheme'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { fetchCerebroAlerts, fetchPipelineStatus, type PipelineStatus as PipelineStatusType } from '../api/client'
import { useApi } from '../hooks/useApi'

const ROUTE_TITLES: Record<string, string> = {
  '/dashboard':       'Centro de mando',
  '/value':           'Value',
  '/macro-radar':     'Macro',
  '/insiders':        'Insiders',
  '/bounce':          'Bounce',
  '/my-portfolio':    'Mi cartera',
  '/owner-earnings':  'Valoración',
  '/search':          'Buscar ticker',
  '/entry-setups':    'Entry setups',
  '/options':         'Options flow',
  '/sectors':         'Sectores',
  '/earnings':        'Calendario',
  '/dividend-traps':  'Dividend traps',
  '/position-sizing': 'Position sizing',
  '/backtest':        'Backtest',
  '/compare':         'Comparar',
  '/datos':           'Datos',
  '/calibration':     'Calibración',
}

function PipelineStatus() {
  const [status, setStatus] = useState<PipelineStatusType | null>(null)
  useEffect(() => { fetchPipelineStatus().then(setStatus) }, [])
  if (!status?.run_date) return null

  const today     = new Date().toISOString().slice(0, 10)
  const yesterday = new Date(Date.now() - 86_400_000).toISOString().slice(0, 10)

  let color = '#ef4444'
  let label = status.run_date
  if (status.run_date === today)      { color = '#22c55e'; label = 'Hoy' }
  else if (status.run_date === yesterday) { color = '#f59e0b'; label = 'Ayer' }

  return (
    <span
      className="hidden sm:flex items-center gap-1.5 text-[0.78rem] lg:text-[0.86rem] tabular-nums"
      style={{ color }}
      title={`Pipeline ejecutado: ${status.run_date}`}
    >
      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: color }} />
      {/* "Datos:" no es decoración: el reloj de al lado da la fecha de HOY, y
          un "Ayer" suelto justo a su izquierda se lee como si la app tuviera
          mal la fecha, en vez de como la antigüedad del último pipeline. */}
      <span className="opacity-60">Datos:</span>
      {label}
    </span>
  )
}

interface Props {
  readonly onMenuClick: () => void
  readonly onOpenCmd: () => void
}

export default function TopBar({ onMenuClick, onOpenCmd }: Readonly<Props>) {
  const location = useLocation()
  const reduceMotion = useReducedMotion()
  const [time, setTime]   = useState(new Date())
  const { theme, setTheme } = useTheme()
  const { enabled: nothingEnabled, toggle: toggleNothing } = useNothingTheme()
  const { data: alertsData } = useApi(() => fetchCerebroAlerts(), [])
  const highAlerts = alertsData?.high_count ?? 0

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 30_000)
    return () => clearInterval(t)
  }, [])

  // Título de barra al estilo iOS: mientras la página enseña SU propio título
  // grande, la barra se calla — repetirlo es decir lo mismo dos veces en la
  // misma pantalla. Cuando ese título se va por arriba, aparece aquí.
  //
  // Se detecta el título real en lugar de llevar una lista de rutas: se probó
  // con ROUTE_TITLES como atajo y resultó falso en 10 de 18 rutas (Macro,
  // Insiders, Bounce, Entry setups, Sectores… no pintan ninguno). Un umbral
  // fijo de scroll tampoco vale: en /value el título propio está a 204px, así
  // que a los 56px se solaparían los dos.
  const [mostrarTitulo, setMostrarTitulo] = useState(true)
  useEffect(() => {
    let pendiente = 0
    const medir = () => {
      pendiente = 0
      const propio = [...document.querySelectorAll('main h1, main h2, main h3')]
        .some(el => {
          const r = el.getBoundingClientRect()
          // Visible y por encima de la mitad de la pantalla: es la cabecera
          // de la página, no un encabezado cualquiera del contenido.
          return parseFloat(getComputedStyle(el).fontSize) >= 18 &&
                 r.width > 2 && r.bottom > 50 && r.top < window.innerHeight * 0.5
        })
      setMostrarTitulo(!propio)
    }
    const onScroll = () => {
      if (!pendiente) pendiente = requestAnimationFrame(medir)
    }
    medir()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll, { passive: true })
    // Varias páginas pintan su título DESPUÉS de resolver su carga (el Centro
    // de mando y Mi cartera, por ejemplo). Midiendo solo al montar se las
    // encuentra vacías y la barra enseña un título que sobra un segundo
    // después. El observer vuelve a medir cuando el contenido aparece.
    const main = document.querySelector('main')
    const observer = main ? new MutationObserver(onScroll) : null
    observer?.observe(main!, { childList: true, subtree: true })
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
      observer?.disconnect()
      if (pendiente) cancelAnimationFrame(pendiente)
    }
  }, [location.pathname])

  const title   = ROUTE_TITLES[location.pathname] || 'Stock Analyzer'
  const timeStr = time.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })
  const dateStr = time.toLocaleDateString('es-ES', { weekday: 'short', day: 'numeric', month: 'short' })

  return (
    <header className="sticky top-0 z-50 flex h-[50px] items-center justify-between gap-3 px-6 bg-background/80 backdrop-blur-2xl border-b border-border/60 flex-shrink-0 transition-colors">
      <div className="flex items-center gap-2.5 min-w-0 flex-1">
        <Button
          variant="ghost"
          size="icon"
          className="topbar-action md:hidden flex-shrink-0 h-8 w-8"
          onClick={onMenuClick}
          aria-label="Menú"
        >
          <Menu size={18} strokeWidth={1.75} />
        </Button>
        <div className="min-w-0 overflow-hidden">
          <AnimatePresence mode="wait" initial={false}>
            {mostrarTitulo && (
              <motion.span
                key={title}
                className="block text-[0.9rem] lg:text-[1rem] font-medium text-muted-foreground/72 tracking-wide truncate"
                initial={reduceMotion ? false : { opacity: 0, y: 6, filter: 'blur(4px)' }}
                animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
                exit={reduceMotion ? { opacity: 1 } : { opacity: 0, y: -6, filter: 'blur(4px)' }}
                transition={{ duration: reduceMotion ? 0 : 0.2, ease: [0.22, 1, 0.36, 1] }}
              >
                {title}
              </motion.span>
            )}
          </AnimatePresence>
        </div>
      </div>

      <div className="flex items-center gap-3 flex-shrink-0">
        {/* Search — desktop shows label, mobile shows icon only */}
        <button
          type="button"
          onClick={onOpenCmd}
          className="topbar-action hidden sm:flex items-center gap-2 px-2.5 py-1.5 rounded-lg border border-border/50 bg-transparent hover:bg-accent/10 hover:border-border transition-colors text-muted-foreground/70 hover:text-foreground text-[0.78rem]"
          aria-label="Buscar"
        >
          <Search size={12} strokeWidth={1.75} className="text-muted-foreground/60" />
          <span>Buscar</span>
          <kbd className="hidden lg:inline-flex items-center font-mono text-[0.62rem] px-1 py-0 rounded border border-border/50 bg-muted/20 text-muted-foreground/70 ml-1">⌘K</kbd>
        </button>
        <button
          type="button"
          onClick={onOpenCmd}
          className="topbar-action sm:hidden flex items-center justify-center w-8 h-8 rounded-lg border border-border/50 bg-transparent hover:bg-accent/10 transition-colors"
          aria-label="Buscar"
        >
          <Search size={14} strokeWidth={1.75} className="text-muted-foreground/70" />
        </button>

        {/* Real pipeline freshness indicator */}
        <PipelineStatus />

        {/* Date/time */}
        <span className="hidden md:flex items-center gap-1.5 text-[0.78rem] lg:text-[0.86rem] text-muted-foreground/52 tabular-nums">
          <Clock size={11} strokeWidth={1.5} />
          {dateStr} · {timeStr}
        </span>

        {/* Cerebro alert bell — ping only when there are real alerts */}
        <Link
          to="/dashboard?tab=cerebro"
          className="topbar-action relative flex items-center justify-center h-8 w-8 rounded-lg border border-border/50 hover:bg-accent/10 transition-colors"
          title="Cerebro"
        >
          <Brain size={14} strokeWidth={1.75} className="text-muted-foreground" />
          {highAlerts > 0 && (
            <span className="absolute -top-1 -right-1 flex h-3.5 w-3.5 items-center justify-center">
              <span className="absolute inset-0 rounded-full bg-red-500 animate-ping opacity-50" />
              <span className="relative flex h-3.5 w-3.5 items-center justify-center rounded-full bg-red-500 text-[0.45rem] font-bold text-white leading-none">
                {highAlerts > 9 ? '9+' : highAlerts}
              </span>
            </span>
          )}
        </Link>

        {/* Nothing theme toggle */}
        <Button
          variant="outline"
          size="icon"
          className={`topbar-action h-8 w-8 border-border/50 transition-colors ${nothingEnabled ? 'bg-primary/15 border-primary/50 text-primary' : ''}`}
          onClick={toggleNothing}
          title={nothingEnabled ? 'Desactivar tema matrix' : 'Activar tema matrix'}
          aria-label="Toggle Nothing theme"
        >
          <Grid3x3 size={14} strokeWidth={1.75} />
        </Button>

        {/* Theme cycle: dark → light → noir → dark */}
        <Button
          variant="outline"
          size="icon"
          className={cn(
            'topbar-action h-8 w-8 border-border/50 transition-colors',
            theme === 'noir' && 'border-[hsl(142_72%_50%/0.5)] bg-[hsl(142_72%_50%/0.1)] text-[hsl(142,72%,55%)]'
          )}
          onClick={() => {
            const next = theme === 'dark' ? 'light' : theme === 'light' ? 'noir' : 'dark'
            setTheme(next)
          }}
          aria-label="Cambiar tema"
          title={{ dark: 'Cambiar a claro', light: 'Cambiar a Noir', noir: 'Cambiar a oscuro' }[theme]}
        >
          {theme === 'dark'  && <Sun  size={14} strokeWidth={1.75} />}
          {theme === 'light' && <Moon size={14} strokeWidth={1.75} />}
          {theme === 'noir'  && (
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round">
              <circle cx="7" cy="7" r="5.5" />
              <path d="M7 1.5 A5.5 5.5 0 0 1 7 12.5" fill="currentColor" stroke="none" />
            </svg>
          )}
        </Button>
      </div>
    </header>
  )
}
