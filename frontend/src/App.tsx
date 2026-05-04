import React, { useState, useEffect, useCallback, Suspense, lazy } from 'react'
import { Routes, Route, NavLink, Navigate, useLocation } from 'react-router-dom'
import { X, LogOut } from 'lucide-react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { ThemeProvider } from './context/ThemeContext'
import { useAuth } from './context/AuthContext'
import { PersonalPortfolioProvider } from './context/PersonalPortfolioContext'
import { ToastProvider } from './components/Toast'
import { cn } from '@/lib/utils'
import { NAV_CATEGORIES, type NavLinkItem } from '@/lib/nav'
import TopBar from './components/TopBar'
import ProtectedRoute from './components/ProtectedRoute'
import CommandPalette from './components/CommandPalette'
import ShortcutsModal from './components/ShortcutsModal'
import ErrorBoundary from './components/ErrorBoundary'
import ScrollToTop from './components/ScrollToTop'
import Loading from './components/Loading'
import { LogoOrbit } from './components/BrandLogos'
import PageLlama from './components/PageLlama'
import Login from './pages/Login'

const Dashboard        = lazy(() => import('./pages/Dashboard'))
const Value            = lazy(() => import('./pages/Value'))
const EntrySetups      = lazy(() => import('./pages/EntrySetups'))
const Insiders         = lazy(() => import('./pages/Insiders'))
const OptionsFlow      = lazy(() => import('./pages/OptionsFlow'))
const Sectors          = lazy(() => import('./pages/Sectors'))
const MyPortfolio      = lazy(() => import('./pages/MyPortfolio'))
const Backtest         = lazy(() => import('./pages/Backtest'))
const TickerSearch     = lazy(() => import('./pages/TickerSearch'))
const Datos            = lazy(() => import('./pages/Datos'))
const PositionSizing   = lazy(() => import('./pages/PositionSizing'))
const Watchlist        = lazy(() => import('./pages/Watchlist'))
const Macro            = lazy(() => import('./pages/Macro'))
const Calendar         = lazy(() => import('./pages/Calendar'))
const DividendTraps    = lazy(() => import('./pages/DividendTraps'))
const Comparador       = lazy(() => import('./pages/Comparador'))
const Cerebro          = lazy(() => import('./pages/Cerebro'))
const Alerts           = lazy(() => import('./pages/Alerts'))
const BounceTrader     = lazy(() => import('./pages/BounceTrader'))
const Calibration      = lazy(() => import('./pages/Calibration'))
const OwnerEarnings    = lazy(() => import('./pages/OwnerEarnings'))
const Manual           = lazy(() => import('./pages/Manual'))
const LogoPreview      = lazy(() => import('./pages/LogoPreview'))
const Bonds            = lazy(() => import('./pages/Bonds'))
const AdminUsage       = lazy(() => import('./pages/AdminUsage'))
const SignalStats      = lazy(() => import('./pages/SignalStats'))

function NavItem({ item, onClose }: { item: NavLinkItem; onClose: () => void }) {
  return (
    <NavLink
      to={item.path}
      onClick={onClose}
      style={{ '--nav-color': item.color } as React.CSSProperties}
      className={({ isActive }) => cn(
        'nav-link flex items-center gap-2.5 px-3 py-2 lg:py-[9px] rounded-lg text-[0.98rem] lg:text-[1.04rem] font-medium transition-all mb-0.5 relative',
        'text-muted-foreground',
        isActive
          ? 'nav-link-active bg-[color-mix(in_srgb,var(--nav-color)_12%,transparent)] text-foreground'
          : 'hover:bg-[color-mix(in_srgb,var(--nav-color)_8%,transparent)] hover:text-foreground'
      )}
    >
      <span className="nav-icon shrink-0"><item.icon size={15} strokeWidth={1.65} /></span>
      <span className="nav-label flex-1 truncate">{item.label}</span>
    </NavLink>
  )
}

const ADMIN_EMAIL = 'tantancansado@gmail.com'

function SidebarContent({ onClose, onSignOut, userEmail }: Readonly<{ onClose: () => void; onSignOut: () => void; userEmail?: string | null }>) {
  return (
    <>
      {/* Header */}
      <div className="px-4 py-4 border-b border-border/40 relative flex-shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl overflow-hidden flex-shrink-0 shadow-md shadow-primary/10">
            <LogoOrbit size={36} title="Stock Analyzer" />
          </div>
          <div className="min-w-0">
            <h1 className="text-[1rem] lg:text-[1.05rem] font-bold tracking-tight text-foreground leading-tight">Stock Analyzer</h1>
          </div>
        </div>
        <button
          className="absolute top-3.5 right-3.5 flex md:hidden items-center justify-center w-7 h-7 rounded-md text-muted-foreground hover:bg-accent/10 hover:text-foreground transition-colors"
          onClick={onClose}
          aria-label="Cerrar menú"
        >
          <X size={15} strokeWidth={1.75} />
        </button>
      </div>

      {/* Nav Categories */}
      <nav className="flex-1 px-3 py-4 overflow-y-auto min-h-0 custom-scrollbar space-y-6">
        {NAV_CATEGORIES.map(category => (
          <div key={category.name}>
            <div className="px-2 mb-2 text-[0.68rem] font-bold uppercase tracking-[0.14em] text-muted-foreground/60">
              {category.name}
            </div>
            <div className="space-y-0.5">
              {category.items.filter(item => !item.adminOnly || userEmail === ADMIN_EMAIL).map(item => (
                <NavItem key={item.path} item={item} onClose={onClose} />
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* Logout */}
      <div className="px-2 py-2 border-t border-border/30 flex-shrink-0">
        <button
          onClick={onSignOut}
          className="flex w-full items-center gap-2.5 px-3 py-2.5 rounded-lg text-[0.98rem] font-medium text-muted-foreground hover:bg-red-500/10 hover:text-red-400 transition-all"
        >
          <LogOut size={15} strokeWidth={1.65} />
          Cerrar sesión
        </button>
      </div>
    </>
  )
}

export default function App() {
  const { user, signOut } = useAuth()
  const location = useLocation()
  const reduceMotion = useReducedMotion()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [cmdOpen, setCmdOpen]           = useState(false)
  const [shortcutsOpen, setShortcutsOpen] = useState(false)
  const close = () => setSidebarOpen(false)
  const handleSignOut = () => { close(); signOut() }

  // ⌘K / Ctrl+K global shortcut + ? shortcuts modal
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        if (user) setCmdOpen(o => !o)
        return
      }
      // ? key — only when no input/textarea is focused
      if (e.key === '?' && !['INPUT', 'TEXTAREA'].includes((e.target as HTMLElement).tagName)) {
        e.preventDefault()
        if (user) setShortcutsOpen(o => !o)
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [user])


  // Cursor spotlight — feeds --mouse-x/y to .glass::after radial gradient
  useEffect(() => {
    const handleMove = (e: MouseEvent) => {
      const el = (e.target as Element).closest<HTMLElement>('.glass')
      if (!el) return
      const rect = el.getBoundingClientRect()
      el.style.setProperty('--mouse-x', `${e.clientX - rect.left}px`)
      el.style.setProperty('--mouse-y', `${e.clientY - rect.top}px`)
    }
    document.addEventListener('mousemove', handleMove, { passive: true })
    return () => document.removeEventListener('mousemove', handleMove)
  }, [])

  const openCmd = useCallback(() => setCmdOpen(true), [])
  const pageKey = `${location.pathname}${location.search}`

  return (
    <ThemeProvider>
    <ToastProvider>
    <PersonalPortfolioProvider>
      {/* Aurora top line */}
      <div className="aurora-line" aria-hidden="true" />

      {/* Animated gradient orbs */}
      <div className="bg-orbs" aria-hidden="true">
        <div className="orb orb-1" />
        <div className="orb orb-2" />
        <div className="orb orb-3" />
        <div className="orb orb-4" />
        <div className="orb orb-5" />
      </div>

      {/* Liquid glass distortion filter — used by .liquid-glass via backdrop-filter: url(#glass-distortion).
          Hidden SVG, mounted once globally. Subtle turbulence + low displacement scale to feel like
          actual refraction through curved glass, not chromatic distortion. */}
      <svg
        aria-hidden="true"
        className="liquid-glass-defs"
        width="0"
        height="0"
        style={{ position: 'absolute', overflow: 'hidden', pointerEvents: 'none' }}
      >
        <defs>
          <filter id="glass-distortion" x="0%" y="0%" width="100%" height="100%">
            <feTurbulence
              type="fractalNoise"
              baseFrequency="0.012 0.018"
              numOctaves="2"
              seed="7"
              result="noise"
            />
            <feGaussianBlur in="noise" stdDeviation="2" result="softNoise" />
            <feDisplacementMap
              in="SourceGraphic"
              in2="softNoise"
              scale="14"
              xChannelSelector="R"
              yChannelSelector="G"
            />
          </filter>
        </defs>
      </svg>

      {user && (
        <>
          {/* Mobile overlay */}
          <AnimatePresence>
            {sidebarOpen && (
              <motion.button
                type="button"
                aria-label="Cerrar menú"
                className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm md:hidden w-full cursor-default"
                onClick={close}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.18, ease: 'easeOut' }}
              />
            )}
          </AnimatePresence>

          {/* Sidebar */}
          <aside className={cn(
            'fixed inset-y-0 left-0 z-50 flex flex-col w-56',
            'border-r border-white/10 bg-card/20 backdrop-blur-2xl',
            'transition-transform duration-300 ease-[cubic-bezier(0.22,1,0.36,1)]',
            'max-md:-translate-x-full',
            sidebarOpen && 'max-md:translate-x-0 max-md:shadow-2xl',
          )}>
            <SidebarContent onClose={close} onSignOut={handleSignOut} userEmail={user?.email} />
          </aside>

          {/* Command Palette */}
          <CommandPalette open={cmdOpen} onClose={() => setCmdOpen(false)} />

          {/* Shortcuts Modal */}
          <ShortcutsModal open={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />
        </>
      )}

      {/* Main */}
      <div className={cn('flex flex-col min-h-screen min-w-0 relative z-10', user && 'md:ml-56')}>
        {user && <TopBar onMenuClick={() => setSidebarOpen(o => !o)} onOpenCmd={openCmd} />}
        {user && <PageLlama />}
        <ScrollToTop />
        <main className="flex-1 p-5 md:p-8 min-w-0" style={{ overflowX: 'clip' }}>
          <ErrorBoundary resetKey={location.pathname}>
          <Suspense fallback={<Loading />}>
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={pageKey}
              initial={reduceMotion ? false : { opacity: 0, y: 12, filter: 'blur(6px)' }}
              animate={reduceMotion ? { opacity: 1 } : { opacity: 1, y: 0, filter: 'blur(0px)' }}
              exit={reduceMotion ? { opacity: 1 } : { opacity: 0, y: -6, filter: 'blur(4px)' }}
              transition={{ duration: reduceMotion ? 0 : 0.28, ease: [0.22, 1, 0.36, 1] }}
            >
              <Routes location={location}>
                {/* Public route */}
                <Route path="/login" element={<Login />} />

                {/* All other routes require authentication */}
                <Route element={<ProtectedRoute />}>
                  <Route path="/"               element={<Navigate to="/dashboard" replace />} />
                  <Route path="/dashboard"      element={<Dashboard />} />
                  <Route path="/value"          element={<Value />} />
                  <Route path="/value-eu"       element={<Navigate to="/value?region=eu" replace />} />
                  <Route path="/value-global"   element={<Navigate to="/value?region=global" replace />} />
                  <Route path="/entry-setups"   element={<EntrySetups />} />
                  <Route path="/momentum"       element={<Navigate to="/entry-setups?tab=momentum" replace />} />
                  <Route path="/insiders"       element={<Insiders />} />
                  <Route path="/options"        element={<OptionsFlow />} />
                  <Route path="/mean-reversion" element={<Navigate to="/entry-setups?tab=mean-reversion" replace />} />
                  <Route path="/sectors"        element={<Sectors />} />
                  <Route path="/portfolio"      element={<Navigate to="/my-portfolio?tab=signals" replace />} />
                  <Route path="/calibration"   element={<Calibration />} />
                  <Route path="/backtest"       element={<Backtest />} />
                  <Route path="/position-sizing" element={<PositionSizing />} />
                  <Route path="/watchlist"      element={<Watchlist />} />
                  <Route path="/search"         element={<TickerSearch />} />
                  <Route path="/macro-radar"       element={<Macro />} />
                  <Route path="/macro-countries"  element={<Navigate to="/macro-radar?tab=countries" replace />} />
                  <Route path="/earnings"       element={<Calendar />} />
                  <Route path="/catalysts"      element={<Navigate to="/earnings?tab=catalysts" replace />} />
                  <Route path="/dividend-traps"   element={<DividendTraps />} />
                  <Route path="/my-portfolio"  element={<MyPortfolio />} />
                  <Route path="/compare"        element={<Comparador />} />
                  <Route path="/cerebro"        element={<Cerebro />} />
                  <Route path="/alerts"         element={<Alerts />} />
                  <Route path="/bounce"         element={<BounceTrader />} />
                  <Route path="/bonds"          element={<Bonds />} />
                  <Route path="/owner-earnings" element={<OwnerEarnings />} />
                  <Route path="/datos"           element={<Datos />} />
                  <Route path="/manual"          element={<Manual />} />
                  <Route path="/logo-preview"    element={<LogoPreview />} />
                  <Route path="/admin/usage"     element={<AdminUsage />} />
                  <Route path="/signal-stats"    element={<SignalStats />} />
                </Route>
              </Routes>
            </motion.div>
          </AnimatePresence>
          </Suspense>
          </ErrorBoundary>
        </main>
      </div>
    </PersonalPortfolioProvider>
    </ToastProvider>
    </ThemeProvider>
  )
}
