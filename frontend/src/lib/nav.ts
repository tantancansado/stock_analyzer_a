import {
  TrendingUp, Users, Activity,
  PieChart, FlaskConical, Search, LayoutDashboard, Database,
  Ruler, Star, Radar, CalendarDays, AlertTriangle,
  DollarSign, Wallet, Bell, Brain,
  Crosshair, Calculator, Shuffle, BookOpen, Landmark, BarChart2,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export type NavLinkItem = { path: string; icon: LucideIcon; label: string; color: string; logo?: string; keywords?: string[] }
export type NavCategory = { name: string; items: NavLinkItem[] }

export const NAV_CATEGORIES: NavCategory[] = [
  {
    name: 'Portfolio',
    items: [
      { path: '/dashboard',      icon: LayoutDashboard, label: 'Dashboard',      color: '#6366f1', logo: 'llama-charts.png',        keywords: ['inicio', 'home', 'resumen'] },
      { path: '/my-portfolio',   icon: Wallet,          label: 'Mi cartera',     color: '#10b981', logo: 'llama-safe.png',          keywords: ['mis posiciones', 'personal', 'posiciones', 'mi cartera'] },
      { path: '/watchlist',       icon: Star,          label: 'Watchlist',       color: '#f59e0b', keywords: ['watchlist', 'seguimiento', 'favoritos'] },
      { path: '/alerts',          icon: Bell,          label: 'Alertas',         color: '#f59e0b', keywords: ['alertas', 'email', 'notificaciones', 'precio'] },
      { path: '/portfolio',        icon: BarChart2,      label: 'Portfolio tracker', color: '#10b981', keywords: ['portfolio', 'tracker', 'señales', 'rendimiento', 'win rate', 'estadísticas'] },
    ]
  },
  {
    name: 'Discovery',
    items: [
      { path: '/search',         icon: Search,          label: 'Buscar',         color: '#94a3b8', logo: 'llama-hands-growth.png',  keywords: ['buscar', 'ticker', 'search', 'analisis'] },
      { path: '/value',          icon: DollarSign,      label: 'Value',          color: '#10b981', logo: 'llama-glasses-arrow.png', keywords: ['value', 'fundamental', 'us', 'eu', 'europa', 'global', 'acciones'] },
      { path: '/entry-setups',    icon: TrendingUp,    label: 'Entry setups',    color: '#f97316', keywords: ['momentum', 'vcp', 'mean reversion', 'rebote', 'oversold', 'tendencia'] },
      { path: '/bounce',         icon: Crosshair,       label: 'Rebotes técnicos', color: '#f97316', logo: 'llama-shield.png',      keywords: ['bounce', 'rebote', 'corto plazo', 'oversold', 'rsi extremo'] },
      { path: '/options',         icon: Activity,      label: 'Options flow',    color: '#ec4899', keywords: ['options', 'opciones', 'flujo', 'institucional'] },
      { path: '/sectors',         icon: PieChart,      label: 'Sectores',        color: '#6366f1', keywords: ['sector', 'rotacion', 'sectorial'] },
      { path: '/insiders',       icon: Users,           label: 'Insiders',       color: '#8b5cf6', logo: 'llama-bags.png',          keywords: ['insiders', 'directivos', 'compras'] },
    ]
  },
  {
    name: 'Market Pulse',
    items: [
      { path: '/macro-radar',    icon: Radar,           label: 'Macro',          color: '#e11d48', logo: 'llama-network.png',       keywords: ['macro', 'radar', 'economía', 'países', 'pib', 'global', 'country'] },
      { path: '/bonds',          icon: Landmark,        label: 'Bonos',          color: '#06b6d4',                                 keywords: ['bonos', 'renta fija', 'yield', 'treasury', 'etf', 'corporativo', 'tlt', 'ief'] },
      { path: '/earnings',        icon: CalendarDays,  label: 'Calendario',      color: '#f59e0b', keywords: ['earnings', 'resultados', 'calendario', 'catalyst', 'catalizador', 'fda', 'pdufa'] },
      { path: '/dividend-traps',  icon: AlertTriangle, label: 'Dividend traps',  color: '#ef4444', keywords: ['dividendo', 'trampa', 'yield trap'] },
      { path: '/compare',         icon: Shuffle,       label: 'Comparar',        color: '#0ea5e9', keywords: ['comparar', 'comparador', 'compare'] },
    ]
  },
  {
    name: 'Tools',
    items: [
      { path: '/cerebro',        icon: Brain,           label: 'Cerebro',        color: '#8b5cf6', logo: 'llama-magnify.png',       keywords: ['cerebro', 'ia', 'agente', 'proactivo', 'convergencia', 'alertas', 'entrada'] },
      { path: '/owner-earnings', icon: Calculator,      label: 'Valoración',     color: '#06b6d4', logo: 'llama-plant.png',         keywords: ['owner earnings', 'valoracion', 'compra', 'buffett', 'fcf', 'precio objetivo', 'dcf'] },
      { path: '/position-sizing', icon: Ruler,         label: 'Position sizing', color: '#f59e0b', keywords: ['position', 'tamaño', 'kelly', 'sizing'] },
      { path: '/backtest',        icon: FlaskConical,  label: 'Backtest',        color: '#6366f1', keywords: ['backtest', 'historico', 'simulacion'] },
      { path: '/datos',           icon: Database,      label: 'Exportar datos',  color: '#64748b', keywords: ['datos', 'historial', 'csv', 'descarga', 'exportar'] },
      { path: '/manual',          icon: BookOpen,      label: 'Manual',          color: '#94a3b8', keywords: ['manual', 'ayuda', 'help', 'guia', 'documentacion', 'como funciona'] },
    ]
  }
]

// All items flat (for command palette)
export const NAV_LINKS: NavLinkItem[] = NAV_CATEGORIES.flatMap(cat => cat.items)

// Legacy export — kept so CommandPalette doesn't break
export type NavSection = { section: string }
export type NavItem = NavSection | NavLinkItem
export const NAV: NavItem[] = NAV_LINKS
