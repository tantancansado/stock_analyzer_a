import React, { useState } from 'react'
import { Routes, Route, NavLink, Navigate } from 'react-router-dom'
import {
  Gem, Globe, TrendingUp, Users, Activity,
  ArrowLeftRight, PieChart, BarChart2, FlaskConical, Search, LayoutDashboard, X, Database,
  Ruler, Layers, Star, LogOut, Radar, CalendarDays, AlertTriangle,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { ThemeProvider } from './context/ThemeContext'
import { useAuth } from './context/AuthContext'
import { cn } from '@/lib/utils'
import TopBar from './components/TopBar'
import ProtectedRoute from './components/ProtectedRoute'
import Login from './pages/Login'
import ValueUS from './pages/ValueUS'
import ValueEU from './pages/ValueEU'
import Momentum from './pages/Momentum'
import Insiders from './pages/Insiders'
import OptionsFlow from './pages/OptionsFlow'
import MeanReversion from './pages/MeanReversion'
import SectorRotation from './pages/SectorRotation'
import Portfolio from './pages/Portfolio'
import Backtest from './pages/Backtest'
import TickerSearch from './pages/TickerSearch'
import Datos from './pages/Datos'
import Dashboard from './pages/Dashboard'
import PositionSizing from './pages/PositionSizing'
import IndustryGroups from './pages/IndustryGroups'
import Watchlist from './pages/Watchlist'
import GlobalValue from './pages/GlobalValue'
import MacroRadar from './pages/MacroRadar'
import EarningsCalendar from './pages/EarningsCalendar'
import DividendTraps from './pages/DividendTraps'

type NavSection  = { section: string }
type NavLinkItem = { path: string; icon: LucideIcon; label: string; color: string }
type NavItem = NavSection | NavLinkItem

const NAV: NavItem[] = [
  { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard',          color: '#6366f1' },
  { section: 'Estrategias' },
  { path: '/value',          icon: Gem,            label: 'VALUE US',           color: '#10b981' },
  { path: '/value-eu',       icon: Globe,           label: 'VALUE EU',           color: '#3b82f6' },
  { path: '/value-global',   icon: Globe,           label: 'VALUE Global',       color: '#a855f7' },
  { path: '/momentum',       icon: TrendingUp,      label: 'Momentum',           color: '#f97316' },
  { path: '/macro-radar',    icon: Radar,          label: 'Macro Radar',        color: '#e11d48' },
  { path: '/earnings',       icon: CalendarDays,   label: 'Earnings Calendar',  color: '#f59e0b' },
  { path: '/dividend-traps', icon: AlertTriangle,  label: 'Dividend Traps',     color: '#ef4444' },
  { section: 'Señales' },
  { path: '/insiders',       icon: Users,           label: 'Insiders',           color: '#8b5cf6' },
  { path: '/options',        icon: Activity,        label: 'Options Flow',       color: '#ec4899' },
  { path: '/mean-reversion', icon: ArrowLeftRight,  label: 'Mean Reversion',     color: '#14b8a6' },
  { path: '/sectors',        icon: PieChart,        label: 'Rotación Sectorial', color: '#6366f1' },
  { section: 'Rendimiento' },
  { path: '/portfolio',      icon: BarChart2,       label: 'Portfolio Tracker',  color: '#22c55e' },
  { path: '/backtest',       icon: FlaskConical,    label: 'Backtest',           color: '#a78bfa' },
  { section: 'Análisis' },
  { path: '/industry-groups', icon: Layers,         label: 'Industry Groups',    color: '#0ea5e9' },
  { path: '/position-sizing', icon: Ruler,          label: 'Position Sizing',    color: '#f59e0b' },
  { section: 'Herramientas' },
  { path: '/watchlist',       icon: Star,           label: 'Watchlist',          color: '#f59e0b' },
  { path: '/search',          icon: Search,         label: 'Buscar Ticker',      color: '#94a3b8' },
  { path: '/datos',           icon: Database,       label: 'Datos & Historial',  color: '#64748b' },
]

function SidebarContent({ onClose, onSignOut }: { onClose: () => void; onSignOut: () => void }) {
  return (
    <>
      {/* Header */}
      <div className="px-4 py-5 border-b border-border/60 relative flex-shrink-0">
        <div className="flex items-center gap-2.5 mb-1">
          <div className="sidebar-logo-icon w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0">
            <LayoutDashboard size={14} color="white" strokeWidth={2} />
          </div>
          <h1 className="text-sm font-bold tracking-tight text-foreground">Stock Analyzer</h1>
        </div>
        <span className="text-[0.58rem] text-muted-foreground/60 uppercase tracking-widest font-semibold block">
          Pipeline diario automatizado
        </span>
        <button
          className="absolute top-3.5 right-3.5 flex md:hidden items-center justify-center w-7 h-7 rounded-md text-muted-foreground hover:bg-accent/10 hover:text-foreground transition-colors"
          onClick={onClose}
          aria-label="Cerrar menú"
        >
          <X size={15} strokeWidth={1.75} />
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-3 overflow-y-auto">
        {NAV.map((item, i) =>
          'section' in item ? (
            <div key={i} className="px-3 pt-5 pb-1.5 text-[0.55rem] font-bold uppercase tracking-[0.14em] text-muted-foreground/50">
              {item.section}
            </div>
          ) : (
            <NavLink
              key={item.path}
              to={item.path}
              onClick={onClose}
              style={{ '--nav-color': item.color } as React.CSSProperties}
              className={({ isActive }) => cn(
                'nav-link flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-all mb-0.5 relative',
                'text-muted-foreground',
                isActive
                  ? 'nav-link-active bg-[color-mix(in_srgb,var(--nav-color)_12%,transparent)]'
                  : 'hover:bg-[color-mix(in_srgb,var(--nav-color)_8%,transparent)] hover:text-foreground'
              )}
            >
              <span className="nav-icon">
                <item.icon size={15} strokeWidth={1.65} />
              </span>
              {item.label}
            </NavLink>
          )
        )}
      </nav>

      {/* Logout */}
      <div className="px-2 py-3 border-t border-border/40 flex-shrink-0">
        <button
          onClick={onSignOut}
          className="flex w-full items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium text-muted-foreground hover:bg-red-500/10 hover:text-red-400 transition-all"
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
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const close = () => setSidebarOpen(false)
  const handleSignOut = () => { close(); signOut() }

  return (
    <ThemeProvider>
      {/* Animated gradient orbs */}
      <div className="bg-orbs" aria-hidden="true">
        <div className="orb orb-1" />
        <div className="orb orb-2" />
        <div className="orb orb-3" />
      </div>

      {user && (
        <>
          {/* Mobile overlay */}
          {sidebarOpen && (
            <div
              className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm md:hidden animate-fade-in"
              onClick={close}
            />
          )}

          {/* Sidebar */}
          <aside className={cn(
            'fixed inset-y-0 left-0 z-50 flex flex-col w-56',
            'border-r border-border/60 bg-card/90 backdrop-blur-2xl',
            'transition-transform duration-300 ease-[cubic-bezier(0.22,1,0.36,1)]',
            'max-md:-translate-x-full',
            sidebarOpen && 'max-md:translate-x-0',
          )}>
            <SidebarContent onClose={close} onSignOut={handleSignOut} />
          </aside>
        </>
      )}

      {/* Main */}
      <div className={cn('flex flex-col min-h-screen min-w-0 relative z-10', user && 'md:ml-56')}>
        {user && <TopBar onMenuClick={() => setSidebarOpen(o => !o)} />}
        <main className="flex-1 p-5 md:p-8 overflow-x-hidden min-w-0">
          <Routes>
            {/* Public route */}
            <Route path="/login" element={<Login />} />

            {/* All other routes require authentication */}
            <Route element={<ProtectedRoute />}>
              <Route path="/"               element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard"      element={<Dashboard />} />
              <Route path="/value"          element={<ValueUS />} />
              <Route path="/value-eu"       element={<ValueEU />} />
              <Route path="/value-global"   element={<GlobalValue />} />
              <Route path="/momentum"       element={<Momentum />} />
              <Route path="/insiders"       element={<Insiders />} />
              <Route path="/options"        element={<OptionsFlow />} />
              <Route path="/mean-reversion" element={<MeanReversion />} />
              <Route path="/sectors"        element={<SectorRotation />} />
              <Route path="/portfolio"      element={<Portfolio />} />
              <Route path="/backtest"       element={<Backtest />} />
              <Route path="/industry-groups" element={<IndustryGroups />} />
              <Route path="/position-sizing" element={<PositionSizing />} />
              <Route path="/watchlist"      element={<Watchlist />} />
              <Route path="/search"         element={<TickerSearch />} />
              <Route path="/macro-radar"    element={<MacroRadar />} />
              <Route path="/earnings"       element={<EarningsCalendar />} />
              <Route path="/dividend-traps" element={<DividendTraps />} />
              <Route path="/datos"          element={<Datos />} />
            </Route>
          </Routes>
        </main>
      </div>
    </ThemeProvider>
  )
}
