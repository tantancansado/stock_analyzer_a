import StaleDataBanner from '../components/StaleDataBanner'
import { useState, useRef, useEffect, useMemo, lazy, Suspense } from 'react'
import { Link } from 'react-router-dom'
import {
  fetchCerebroInsights, fetchCerebroConvergence, fetchCerebroAlerts, fetchCerebroCalibration,
  fetchCerebroEntrySignals, fetchCerebroExitSignals, fetchCerebroValueTraps, fetchCerebroSmartMoney,
  fetchCerebroInsiderClusters, fetchCerebroDividendSafety, fetchCerebroPiotroski,
  fetchCerebroStressTest, fetchCerebroBriefing, fetchMeanReversion,
  fetchCerebroShortSqueeze, fetchCerebroQualityDecay, fetchEarningsCalendar, fetchPortfolioPrices, type CerebroAlert, type EntrySignal, type MeanReversionItem,
  type ShortSqueezeSetup, type QualityDecay, type CerebroSignal, type ExitSignal,
  type ValueTrap, type SmartMoneySignal, type EarningsEntry,
} from '../api/client'
import { useApi } from '../hooks/useApi'
import { supabase } from '@/lib/supabase'
import { useAuth } from '@/context/AuthContext'
import Loading, { ErrorState } from '../components/Loading'
import AiNarrativeCard from '../components/AiNarrativeCard'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import TickerLogo from '../components/TickerLogo'
import {
  Brain, Crosshair, Bell, SlidersHorizontal, TrendingUp, TrendingDown, Minus, ChevronRight,
  Zap, CheckCircle2, Newspaper, Bot, AlertOctagon, ShieldAlert,
  Building2, Users, Wallet, BarChart2, Activity, Repeat2, Sparkles, MessageCircle, CalendarDays,
  GitBranch, Target, Check, X, TriangleAlert,
  type LucideIcon,
} from 'lucide-react'
import { nlAlert } from '@/lib/nl'
import ScoreAlerts from '../components/ScoreAlerts'
import EmptyState from '@/components/EmptyState'
import CifrasClave from '../components/CifrasClave'
import { colorUpside, enZonaDorada } from '../lib/bandasUpside'
import { precio } from '../lib/moneda'

const ThesisDriftTab       = lazy(() => import('./ThesisDrift'))
const ContrarianDiscovery  = lazy(() => import('./ContrarianDiscovery'))

// ── helpers ───────────────────────────────────────────────────────────────────

type CerebroTab = 'briefing' | 'myportfolio' | 'entry' | 'bounces' | 'convergence' | 'agents' | 'alerts' | 'calibration' | 'thesis' | 'contrarian' | 'novedades'

type CoachTone = 'risk' | 'opportunity' | 'watch' | 'calm'

interface CoachAction {
  id: string
  tab: CerebroTab
  tone: CoachTone
  eyebrow: string
  title: string
  body: string
  meta?: string
  ticker?: string
  icon: LucideIcon
}

const COACH_TONE: Record<CoachTone, { panel: string; icon: string; pill: string }> = {
  risk: {
    panel: 'border-red-500/25 bg-red-500/5 hover:border-red-500/40',
    icon: 'bg-red-500/15 text-red-400 border-red-500/25',
    pill: 'text-red-300 bg-red-500/10 border-red-500/20',
  },
  opportunity: {
    panel: 'border-emerald-500/25 bg-emerald-500/5 hover:border-emerald-500/40',
    icon: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/25',
    pill: 'text-emerald-300 bg-emerald-500/10 border-emerald-500/20',
  },
  watch: {
    panel: 'border-cyan-500/25 bg-cyan-500/5 hover:border-cyan-500/40',
    icon: 'bg-cyan-500/15 text-cyan-400 border-cyan-500/25',
    pill: 'text-cyan-300 bg-cyan-500/10 border-cyan-500/20',
  },
  calm: {
    panel: 'border-border/35 bg-muted/10 hover:border-border/60',
    icon: 'bg-muted/20 text-muted-foreground border-border/30',
    pill: 'text-muted-foreground bg-muted/15 border-border/30',
  },
}

function CoachActionButton({ action, onOpen }: { action: CoachAction; onOpen: (tab: CerebroTab) => void }) {
  const Icon = action.icon
  const tone = COACH_TONE[action.tone]
  return (
    <button
      type="button"
      onClick={() => onOpen(action.tab)}
      className={`group w-full rounded-xl border p-3 text-left transition-all active:scale-[0.99] ${tone.panel}`}
    >
      <div className="flex items-start gap-3">
        <span className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border ${tone.icon}`}>
          <Icon size={16} strokeWidth={1.8} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex flex-wrap items-center gap-2">
            <span className={`rounded-full border px-2 py-0.5 text-micro font-bold uppercase tracking-[0.14em] ${tone.pill}`}>
              {action.eyebrow}
            </span>
            {action.ticker && <span className="font-mono text-mini font-bold text-primary">{action.ticker}</span>}
          </div>
          <p className="text-cuerpo font-semibold leading-snug text-foreground">{action.title}</p>
          <p className="mt-1 text-mini leading-relaxed text-muted-foreground">{action.body}</p>
          {action.meta && <p className="mt-2 text-micro font-medium text-muted-foreground">{action.meta}</p>}
        </div>
        <ChevronRight size={16} className="mt-2 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary" />
      </div>
    </button>
  )
}

// ── Ideas del día ─────────────────────────────────────────────────────────────

const SIGNAL_COLOR = {
  STRONG_BUY: { card: 'border-emerald-500/30 bg-emerald-500/5', badge: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/25', label: 'FUERTE COMPRA' },
  BUY:        { card: 'border-cyan-500/25 bg-cyan-500/5',       badge: 'bg-cyan-500/15 text-cyan-300 border-cyan-500/25',         label: 'COMPRA' },
  MONITOR:    { card: 'border-border/40 bg-muted/5',            badge: 'bg-muted/20 text-muted-foreground border-border/30',      label: 'VIGILAR' },
  WAIT:       { card: 'border-border/30 bg-muted/5',            badge: 'bg-muted/20 text-muted-foreground border-border/25',      label: 'ESPERAR' },
}

function oneLiner(sig: EntrySignal): string {
  const fired = sig.signals_fired
  if (fired.includes('FCF alto') && fired.includes('Insider buying'))   return 'FCF sólido con compras de insiders'
  if (fired.includes('Insider buying'))                                  return 'Insiders comprando — señal de convicción interna'
  if (fired.includes('FCF alto') && fired.includes('Piotroski fuerte')) return 'Balance sólido con alta generación de caja'
  if (fired.includes('Piotroski fuerte'))                                return 'Balance financiero entre los más fuertes del universo'
  if (fired.includes('FCF alto'))                                        return `FCF ${sig.fcf_yield_pct?.toFixed(1)}% — se paga a sí misma`
  // Aquí había dos titulares que vendían la zona de trampa como virtud:
  // «X% de upside validado por analistas» con upside >30 —el HARD REJECT, 0%
  // de acierto en 55 señales reales— y «R:R 4x — riesgo asimétrico
  // excepcional», que es upside ≥32%, todavía más adentro. `risk_reward_ratio`
  // no es gestión del riesgo: el integrator lo calcula como
  // `analyst_upside_pct / 8`. Mismo fallo que CatalystScreener ya corrigió.
  const up = sig.analyst_upside_pct ?? null
  if (enZonaDorada(up)) return `${up!.toFixed(0)}% de upside, dentro de la banda que funciona`
  return `${sig.signals_fired.slice(0, 2).join(' · ')}`
}

function IdeasHoy({ signals, onVerDetalle }: { signals: EntrySignal[]; onVerDetalle: () => void }) {
  const [expanded, setExpanded] = useState<string | null>(null)

  // Deduplicate by ticker, keep highest entry_score
  const deduped = Object.values(
    signals.reduce<Record<string, EntrySignal>>((acc, s) => {
      if (!acc[s.ticker] || s.entry_score > acc[s.ticker].entry_score) acc[s.ticker] = s
      return acc
    }, {})
  ).sort((a, b) => b.entry_score - a.entry_score).slice(0, 5)

  if (deduped.length === 0) return null

  return (
    <div className="mb-5 animate-fade-in-up">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Zap size={16} className="text-emerald-400" />
          <span className="etiqueta-seccion tracking-[0.18em]">Ideas de hoy</span>
          <span className="text-micro px-1.5 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-bold">{deduped.length}</span>
        </div>
        <button onClick={onVerDetalle} className="text-micro text-muted-foreground hover:text-primary transition-colors">
          Ver análisis completo →
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-2">
        {deduped.map(sig => {
          const style = SIGNAL_COLOR[sig.signal] ?? SIGNAL_COLOR.MONITOR
          const isOpen = expanded === sig.ticker
          return (
            <button
              key={sig.ticker}
              type="button"
              onClick={() => setExpanded(isOpen ? null : sig.ticker)}
              className={`text-left rounded-xl border p-3.5 transition-all active:scale-[0.98] hover:border-opacity-60 ${style.card} ${isOpen ? 'ring-1 ring-primary/20' : ''}`}
            >
              {/* Top row */}
              <div className="flex items-start justify-between gap-1 mb-2">
                <div>
                  <div className="font-mono font-bold text-primary text-cuerpo leading-none">{sig.ticker}</div>
                  <div className="text-micro text-muted-foreground mt-0.5 leading-tight truncate max-w-[120px]">{sig.company_name.split(' ').slice(0, 2).join(' ')}</div>
                </div>
                <span className={`text-micro font-bold px-1.5 py-0.5 rounded border shrink-0 ${style.badge}`}>{style.label}</span>
              </div>

              {/* Key numbers */}
              <div className="flex gap-2 flex-wrap mb-2">
                {sig.analyst_upside_pct != null && (
                  <span className="text-mini">
                    <span className="text-muted-foreground">↑</span>{' '}
                    <strong className="text-emerald-400">+{sig.analyst_upside_pct.toFixed(0)}%</strong>
                  </span>
                )}
                {sig.risk_reward_ratio != null && (
                  <span className="text-mini">
                    <span className="text-muted-foreground">R:R</span>{' '}
                    <strong className="text-foreground">{sig.risk_reward_ratio.toFixed(1)}x</strong>
                  </span>
                )}
                {sig.fcf_yield_pct != null && (
                  <span className="text-mini">
                    <span className="text-muted-foreground">FCF</span>{' '}
                    <strong className={sig.fcf_yield_pct >= 5 ? 'text-emerald-400' : 'text-foreground'}>{sig.fcf_yield_pct.toFixed(1)}%</strong>
                  </span>
                )}
              </div>

              {/* One-liner */}
              <p className="text-micro text-muted-foreground leading-snug">{oneLiner(sig)}</p>

              {/* Earnings warning */}
              {sig.earnings_warning && sig.days_to_earnings != null && (
                <div className="mt-1.5 text-micro text-amber-400 flex items-center gap-1">
                  <Bell size={12} /> Earnings {sig.days_to_earnings}d
                </div>
              )}

              {/* Expanded: entry levels */}
              {isOpen && (
                <div className="mt-2.5 pt-2.5 border-t border-border/30 space-y-0.5">
                  <div className="etiqueta-seccion mb-1">Niveles</div>
                  {sig.current_price != null && (
                    <div className="flex justify-between text-micro">
                      <span className="text-muted-foreground">Precio</span>
                      <strong className="text-foreground">{sig.current_price.toLocaleString()}</strong>
                    </div>
                  )}
                  {sig.days_to_earnings != null && !sig.earnings_warning && (
                    <div className="flex justify-between text-micro">
                      <span className="text-muted-foreground">Earnings en</span>
                      <strong className="text-foreground">{sig.days_to_earnings}d</strong>
                    </div>
                  )}
                  <div className="flex justify-between text-micro">
                    <span className="text-muted-foreground">Score</span>
                    <strong className="text-foreground">{sig.value_score.toFixed(0)}</strong>
                  </div>
                  {sig.signals_fired.length > 0 && (
                    <div className="mt-1.5 flex flex-wrap gap-1">
                      {sig.signals_fired.slice(0, 3).map(s => (
                        <span key={s} className="text-micro px-1 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/15">{s}</span>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}

function CerebroCoachPanel({
  headline,
  subline,
  actions,
  onOpenTab,
}: {
  headline: string
  subline: string
  actions: CoachAction[]
  onOpenTab: (tab: CerebroTab) => void
}) {
  return (
    <Card className="liquid-glass mb-5 overflow-clip animate-fade-in-up rounded-xl">
      <CardContent className="p-0">
        <div className="grid gap-0 lg:grid-cols-[1.05fr_0.95fr]">
          <div className="relative p-5 md:p-6">
            <div className="mb-4 flex items-center gap-2">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl border border-violet-500/25 bg-violet-500/10 text-violet-300">
                <MessageCircle size={16} strokeWidth={1.75} />
              </span>
              <div>
                <div className="etiqueta-seccion tracking-[0.18em] text-violet-300">Cerebro te diría</div>
                <div className="text-mini text-muted-foreground">Resumen operativo, sin jerga</div>
              </div>
            </div>

            {/* <p>, no <h1>: Cerebro es una PESTAÑA del Centro de mando, que ya
                pone el h1 de la página. Ponerlo aquí daba dos encabezados de
                nivel 1 compitiendo, y además este es el titular del día, que
                cambia con los datos — no el nombre de la sección. */}
            <p className="max-w-2xl text-pagina font-extrabold leading-tight tracking-tight text-foreground md:text-cifra">
              {headline}
            </p>
            <p className="mt-3 max-w-xl text-cuerpo leading-relaxed text-muted-foreground">{subline}</p>

            <div className="mt-5 flex flex-wrap gap-2">
              <button type="button" onClick={() => onOpenTab(actions[0]?.tab ?? 'briefing')} className="filter-btn active">
                Ir a lo importante
              </button>
              <button type="button" onClick={() => onOpenTab('briefing')} className="filter-btn">
                Ver briefing
              </button>
              <button type="button" onClick={() => onOpenTab('agents')} className="filter-btn">
                Revisar riesgos
              </button>
            </div>
          </div>

          <div className="border-t border-border/20 p-4 lg:border-l lg:border-t-0">
            <div className="mb-2 flex items-center gap-2 px-1">
              <Sparkles size={16} className="text-primary" />
              <span className="etiqueta-seccion tracking-[0.16em]">Siguiente foco</span>
            </div>
            <div className="space-y-2">
              {actions.map(action => (
                <CoachActionButton key={action.id} action={action} onOpen={onOpenTab} />
              ))}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function buildCoachActions({
  entrySignals,
  exits,
  traps,
  alerts,
  convergences,
  topBounces,
  smartMoney,
  squeezeSetups,
  decayItems,
}: {
  entrySignals: EntrySignal[]
  exits: ExitSignal[]
  traps: ValueTrap[]
  alerts: CerebroAlert[]
  convergences: CerebroSignal[]
  topBounces: MeanReversionItem[]
  smartMoney: SmartMoneySignal[]
  squeezeSetups: ShortSqueezeSetup[]
  decayItems: QualityDecay[]
}): CoachAction[] {
  const actions: CoachAction[] = []
  const highExit = exits.find(item => item.severity === 'HIGH') ?? exits[0]
  const highTrap = traps.find(item => item.severity === 'HIGH') ?? traps[0]
  const highDecay = decayItems.find(item => item.severity === 'HIGH') ?? decayItems[0]
  const topEntry = entrySignals.find(item => item.signal === 'STRONG_BUY') ?? entrySignals.find(item => item.signal === 'BUY')
  const triple = convergences
    .filter(item => item.strategy_count >= 3)
    .sort((a, b) => b.convergence_score - a.convergence_score)[0]
  const bounce = topBounces[0]
  const alert = alerts.find(item => item.severity === 'HIGH')
  const squeeze = squeezeSetups.find(item => item.severity === 'HIGH') ?? squeezeSetups[0]
  const smart = smartMoney[0]

  if (highExit) {
    actions.push({
      id: `exit-${highExit.ticker}`,
      tab: 'agents',
      tone: 'risk',
      eyebrow: 'Primero',
      ticker: highExit.ticker,
      icon: ShieldAlert,
      title: `Revisa ${highExit.ticker} antes de buscar compras.`,
      body: 'Cerebro detecta deterioro suficiente como para no dejarlo escondido en una tabla.',
      meta: highExit.reasons.slice(0, 2).join(' · '),
    })
  }

  if (highTrap && actions.length < 3) {
    actions.push({
      id: `trap-${highTrap.ticker}`,
      tab: 'agents',
      tone: 'risk',
      eyebrow: 'Cuidado',
      ticker: highTrap.ticker,
      icon: AlertOctagon,
      title: `${highTrap.ticker} parece barato, pero no limpio.`,
      body: 'Puede ser una trampa de valor. Si está en cartera, merece una revisión fría.',
      meta: `Riesgo ${highTrap.trap_score}/10 · ${highTrap.flags.slice(0, 2).join(' · ')}`,
    })
  }

  if (topEntry && actions.length < 3) {
    actions.push({
      id: `entry-${topEntry.ticker}`,
      tab: 'entry',
      tone: 'opportunity',
      eyebrow: topEntry.signal === 'STRONG_BUY' ? 'Accionable' : 'Candidata',
      ticker: topEntry.ticker,
      icon: Zap,
      title: `${topEntry.ticker} es la idea más clara para mirar hoy.`,
      body: 'La señal combina calidad, precio y punto de entrada. No significa comprar automático: significa empezar aquí.',
      meta: `Entry score ${topEntry.entry_score} · ${topEntry.signals_fired.slice(0, 3).join(' · ')}`,
    })
  }

  if (triple && actions.length < 3) {
    actions.push({
      id: `conv-${triple.ticker}`,
      tab: 'convergence',
      tone: 'watch',
      eyebrow: 'Confluencia',
      ticker: triple.ticker,
      icon: Crosshair,
      title: `${triple.ticker} aparece por varias vías a la vez.`,
      body: 'Cuando varias estrategias apuntan al mismo ticker, merece estar arriba en la pila de revisión.',
      meta: `${triple.strategy_count} estrategias · score ${triple.convergence_score}`,
    })
  }

  if (bounce && actions.length < 3) {
    actions.push({
      id: `bounce-${bounce.ticker}`,
      tab: 'bounces',
      tone: 'watch',
      eyebrow: 'Táctico',
      ticker: bounce.ticker,
      icon: Repeat2,
      title: `${bounce.ticker} tiene rebote interesante, pero con disciplina.`,
      body: 'Es una lectura más táctica que de convicción larga. Entrada, stop y target importan más que la historia.',
      meta: `Score ${bounce.reversion_score} · ${bounce.quality}`,
    })
  }

  if (highDecay && actions.length < 3) {
    actions.push({
      id: `decay-${highDecay.ticker}`,
      tab: 'agents',
      tone: 'risk',
      eyebrow: 'Deterioro',
      ticker: highDecay.ticker,
      icon: TrendingDown,
      title: `${highDecay.ticker} muestra señales de calidad empeorando.`,
      body: 'No es ruido de precio: Cerebro ve empeoramiento en métricas internas.',
      meta: highDecay.flags.slice(0, 2).join(' · '),
    })
  }

  if (alert && actions.length < 3) {
    actions.push({
      id: `alert-${alert.ticker}-${alert.type}`,
      tab: 'alerts',
      tone: 'risk',
      eyebrow: 'Alerta',
      ticker: alert.ticker,
      icon: Bell,
      title: `${alert.ticker} necesita atención puntual.`,
      body: nlAlert({ type: alert.type, ticker: alert.ticker, severity: alert.severity, details: alert.message }),
      meta: alert.title,
    })
  }

  if (squeeze && actions.length < 3) {
    actions.push({
      id: `squeeze-${squeeze.ticker}`,
      tab: 'agents',
      tone: 'watch',
      eyebrow: 'Volátil',
      ticker: squeeze.ticker,
      icon: Activity,
      title: `${squeeze.ticker} puede moverse fuerte.`,
      body: 'Tiene ingredientes de short squeeze. Trátalo como operación de riesgo, no como inversión tranquila.',
      meta: `${squeeze.short_pct_float.toFixed(1)}% short float · squeeze ${squeeze.squeeze_score}/10`,
    })
  }

  if (smart && actions.length < 3) {
    actions.push({
      id: `smart-${smart.ticker}`,
      tab: 'agents',
      tone: 'watch',
      eyebrow: 'Dinero listo',
      ticker: smart.ticker,
      icon: Building2,
      title: `${smart.ticker} tiene dinero sofisticado mirando.`,
      body: 'Hedge funds e insiders aparecen en la misma zona. No es una orden, pero sí una pista que merece lectura.',
      meta: `${smart.n_hedge_funds} fondos · ${smart.n_insiders} insiders`,
    })
  }

  if (actions.length === 0) {
    actions.push({
      id: 'calm-market',
      tab: 'briefing',
      tone: 'calm',
      eyebrow: 'Calma',
      icon: Brain,
      title: 'No hay una urgencia clara ahora mismo.',
      body: 'Hoy Cerebro no ve nada que obligue a actuar. Mantener disciplina también es una decisión.',
      meta: 'Revisa el briefing y evita forzar operaciones.',
    })
  }

  return actions.slice(0, 3)
}

function alertIcon(type: string) {
  if (type === 'MR_ZONE')         return <TrendingDown size={16} className="text-teal-400" />
  if (type === 'INSIDER_BUYING')  return <TrendingUp size={16} className="text-purple-400" />
  if (type === 'EARNINGS_WARNING') return <Bell size={16} className="text-amber-400" />
  if (type === 'NEW_CONVERGENCE') return <Crosshair size={16} className="text-cyan-400" />
  return <Minus size={16} className="text-muted-foreground" />
}

function alertColor(severity: CerebroAlert['severity']) {
  if (severity === 'HIGH')   return 'border-red-500/25 bg-red-500/5'
  if (severity === 'MEDIUM') return 'border-amber-500/20 bg-amber-500/5'
  return 'border-border/30 bg-muted/5'
}

// ── Sorted, NL-enriched alerts tab ───────────────────────────────────────────

const SEV_ORDER: Record<string, number> = { HIGH: 0, MEDIUM: 1, LOW: 2 }

function AlertsTab({ alerts, showAll, onToggleAll }: {
  alerts: CerebroAlert[]
  showAll: boolean
  onToggleAll: () => void
}) {
  const sorted = useMemo(() => [...alerts].sort((a, b) => {
    const so = (SEV_ORDER[a.severity] ?? 3) - (SEV_ORDER[b.severity] ?? 3)
    return so !== 0 ? so : (a.ticker < b.ticker ? -1 : 1)
  }), [alerts])

  const highAlerts = sorted.filter(a => a.severity === 'HIGH')
  const displayed  = showAll ? sorted : highAlerts

  if (alerts.length === 0) {
    return <Card className="glass"><CardContent className="py-12 text-center text-muted-foreground">Sin alertas activas hoy</CardContent></Card>
  }

  return (
    <div className="space-y-2 animate-fade-in-up">
      <div className="flex items-center justify-between">
        <span className="etiqueta-seccion">
          {showAll ? `Todas las alertas (${sorted.length})` : `HIGH priority (${highAlerts.length})`}
        </span>
        <button onClick={onToggleAll} className="filter-btn">
          {showAll ? `Solo HIGH (${highAlerts.length})` : `Ver todas (${sorted.length})`}
        </button>
      </div>

      {highAlerts.length === 0 && !showAll && (
        <Card className="glass"><CardContent className="py-12 text-center text-muted-foreground">Sin alertas HIGH hoy</CardContent></Card>
      )}

      {displayed.map((alert, i) => {
        const nlSummary = nlAlert({ type: alert.type, ticker: alert.ticker, severity: alert.severity, details: alert.message })
        const sameAsMessage = nlSummary === alert.message
        return (
          <div key={`${alert.ticker}-${alert.type}-${i}`}
            className={`flex items-start gap-3 p-4 rounded-xl border animate-fade-in-up ${alertColor(alert.severity)}`}
            style={{ animationDelay: `${i * 50}ms` }}>
            <div className="mt-0.5 shrink-0">{alertIcon(alert.type)}</div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <Link to={`/search?q=${alert.ticker}`} className="font-mono font-bold text-primary text-apoyo hover:underline">
                  {alert.ticker}
                </Link>
                <span className={`text-micro font-bold px-1.5 py-0.5 rounded border ${
                  alert.severity === 'HIGH'
                    ? 'bg-red-500/15 text-red-400 border-red-500/30'
                    : alert.severity === 'MEDIUM'
                    ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                    : 'bg-muted/20 text-muted-foreground border-border/30'
                }`}>{alert.severity}</span>
                <span className="text-micro font-semibold text-foreground/70">{alert.title}</span>
              </div>
              {/* NL plain-language summary */}
              <p className="text-mini text-foreground/80 leading-relaxed font-medium">
                {nlSummary}
              </p>
              {/* Original message if different from NL summary */}
              {!sameAsMessage && alert.message && (
                <p className="text-micro text-muted-foreground mt-0.5 leading-relaxed">
                  {alert.message}
                </p>
              )}
            </div>
            <Link to={`/search?q=${alert.ticker}`} className="shrink-0 text-muted-foreground hover:text-primary mt-0.5 transition-colors" title="Analizar ticker">
              <ChevronRight size={16} />
            </Link>
          </div>
        )
      })}
    </div>
  )
}

function strategyBadge(s: string) {
  const styles: Record<string, string> = {
    VALUE:    'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    INSIDERS: 'bg-purple-500/15 text-purple-400 border-purple-500/30',
    MR:       'bg-teal-500/15 text-teal-400 border-teal-500/30',
    OPTIONS:  'bg-pink-500/15 text-pink-400 border-pink-500/30',
    MOMENTUM: 'bg-orange-500/15 text-orange-400 border-orange-500/30',
  }
  return (
    <span key={s} className={`text-micro font-bold px-1.5 py-0.5 rounded border ${styles[s] ?? 'bg-muted/15 text-muted-foreground border-border/30'}`}>
      {s}
    </span>
  )
}

// ── Entry signal helpers ───────────────────────────────────────────────────────

// Las etiquetas llevaban un punto de color delante (🟢🟡🔵⚪) que repetía
// exactamente lo que ya dicen `border`, `bg`, `badge` y `scoreColor`: el mismo
// dato marcado dos veces, con un emoji que el sistema pinta a su manera.
const SIGNAL_STYLES: Record<EntrySignal['signal'], { label: string; border: string; bg: string; badge: string; scoreColor: string }> = {
  STRONG_BUY: { label: 'STRONG BUY', border: 'border-emerald-500/60', bg: 'bg-emerald-500/15', badge: 'bg-emerald-500/25 text-emerald-400 border-emerald-500/40', scoreColor: 'text-emerald-400' },
  BUY:        { label: 'BUY',        border: 'border-amber-500/50',   bg: 'bg-amber-500/10',   badge: 'bg-amber-500/25 text-amber-400 border-amber-500/40',       scoreColor: 'text-amber-400'   },
  MONITOR:    { label: 'MONITOR',    border: 'border-blue-500/30',    bg: 'bg-blue-500/10',    badge: 'bg-blue-500/20 text-blue-400 border-blue-500/30',          scoreColor: 'text-blue-400'    },
  WAIT:       { label: 'WAIT',       border: 'border-border/20',      bg: 'bg-transparent',    badge: 'bg-muted/20 text-muted-foreground border-border/30',       scoreColor: 'text-muted-foreground' },
}

function EntryScoreBar({ score }: { score: number }) {
  const color = score >= 75 ? 'bg-emerald-500' : score >= 50 ? 'bg-amber-500' : score >= 30 ? 'bg-blue-500' : 'bg-muted/40'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 rounded-full barra-pista overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className="tabular-nums text-cuerpo font-extrabold w-8 text-right">{score}</span>
    </div>
  )
}

function EntrySignalCard({ sig }: Readonly<{ sig: EntrySignal }>) {
  const style = SIGNAL_STYLES[sig.signal]
  const [expanded, setExpanded] = useState(false)
  return (
    <Card className={`glass border ${style.border} ${style.bg} transition-all`}>
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <TickerLogo ticker={sig.ticker} size="sm" className="mt-0.5 shrink-0" />
          <div className="flex-1 min-w-0">
            {/* Header row */}
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <Link to={`/search?q=${sig.ticker}`} className="font-mono font-bold text-primary text-cuerpo hover:underline">
                {sig.ticker}
              </Link>
              <span className={`text-micro font-bold px-1.5 py-0.5 rounded border ${style.badge}`}>{style.label}</span>
              {sig.conviction_grade && (
                <Badge variant={sig.conviction_grade === 'A' ? 'green' : sig.conviction_grade === 'B' ? 'blue' : 'yellow'} className="text-micro">
                  {sig.conviction_grade}
                </Badge>
              )}
              <span className="text-micro text-muted-foreground ml-auto">{sig.region} · {sig.days_in_value}d en VALUE</span>
            </div>

            <div className="text-mini text-muted-foreground mb-2">{sig.company_name} · {sig.sector}</div>

            {/* Score bar */}
            <div className="mb-2">
              <div className="etiqueta-seccion mb-1">Entry score</div>
              <EntryScoreBar score={sig.entry_score} />
            </div>

            {/* Key metrics */}
            <div className="flex flex-wrap gap-3 text-mini mb-2">
              {sig.value_score != null && <span>Score VALUE: <strong className="text-foreground">{sig.value_score.toFixed(0)}</strong></span>}
              {sig.analyst_upside_pct != null && <span>Upside: <strong className={sig.analyst_upside_pct >= 15 ? 'text-emerald-400' : 'text-foreground'}>{sig.analyst_upside_pct >= 0 ? '+' : ''}{sig.analyst_upside_pct.toFixed(1)}%</strong></span>}
              {sig.fcf_yield_pct != null && <span>FCF: <strong className={sig.fcf_yield_pct >= 5 ? 'text-emerald-400' : 'text-foreground'}>{sig.fcf_yield_pct.toFixed(1)}%</strong></span>}
              {sig.risk_reward_ratio != null && <span>R:R: <strong className={sig.risk_reward_ratio >= 2 ? 'text-emerald-400' : 'text-foreground'}>{sig.risk_reward_ratio.toFixed(1)}x</strong></span>}
              {sig.rsi != null && <span>RSI: <strong className={sig.rsi <= 30 ? 'text-teal-400' : 'text-foreground'}>{sig.rsi.toFixed(0)}</strong></span>}
            </div>

            {/* Signals fired */}
            {sig.signals_fired.length > 0 && (
              <div className="flex flex-wrap gap-1 mb-2">
                {sig.signals_fired.map(s => (
                  <span key={s} className="flex items-center gap-0.5 text-micro px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    <CheckCircle2 size={12} /> {s}
                  </span>
                ))}
              </div>
            )}

            {/* Optional extra signals — toggle */}
            {sig.signals_missing.length > 0 && (
              <button
                onClick={() => setExpanded(e => !e)}
                className="flex items-center gap-1 text-micro text-muted-foreground hover:text-muted-foreground transition-colors"
              >
                <Minus size={12} className="text-muted-foreground" />
                {expanded ? 'Ocultar' : `+${sig.signals_missing.length} señales extra posibles`}
                <ChevronRight size={12} className={`transition-transform ${expanded ? 'rotate-90' : ''}`} />
              </button>
            )}
            {expanded && (
              <div>
                <p className="text-micro text-muted-foreground mb-1">Confirmaciones adicionales que aumentarían la convicción (no son requisitos):</p>
                <div className="flex flex-wrap gap-1">
                  {sig.signals_missing.map(s => (
                    <span key={s} className="flex items-center gap-0.5 text-micro px-1.5 py-0.5 rounded bg-muted/20 text-muted-foreground border border-border/30">
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {sig.earnings_warning && sig.days_to_earnings != null && (
              <div className="mt-2 text-micro text-amber-400 flex items-center gap-1">
                <Bell size={12} /> Earnings en {sig.days_to_earnings}d — riesgo de entrada
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function Cerebro({ embedded = false }: { embedded?: boolean } = {}) {
  const { data: insights,    loading: loadingI }   = useApi(() => fetchCerebroInsights(), [])
  const { data: convergence, loading: loadingC }   = useApi(() => fetchCerebroConvergence(), [])
  const { data: alertsData,  loading: loadingA }   = useApi(() => fetchCerebroAlerts(), [])
  const { data: calibration, loading: loadingCal } = useApi(() => fetchCerebroCalibration(), [])
  const { data: entryData,   loading: loadingE }   = useApi(() => fetchCerebroEntrySignals(), [])
  const { data: exitData }    = useApi(() => fetchCerebroExitSignals(), [])
  const { data: trapsData }   = useApi(() => fetchCerebroValueTraps(), [])
  const { data: smData }      = useApi(() => fetchCerebroSmartMoney(), [])
  const { data: clustersData }= useApi(() => fetchCerebroInsiderClusters(), [])
  const { data: divData }     = useApi(() => fetchCerebroDividendSafety(), [])
  const { data: piotrData }   = useApi(() => fetchCerebroPiotroski(), [])
  const { data: stressData }  = useApi(() => fetchCerebroStressTest(), [])
  const { data: briefingData }= useApi(() => fetchCerebroBriefing(), [])
  const { data: squeezeData } = useApi(() => fetchCerebroShortSqueeze(), [])
  const { data: decayData }   = useApi(() => fetchCerebroQualityDecay(), [])
  const { data: mrRaw }       = useApi(() => fetchMeanReversion(), [])
  const { data: earningsRaw } = useApi(() => fetchEarningsCalendar(), [])

  const { user } = useAuth()
  interface PortfolioPos { id: string; ticker: string; shares: number; avg_price: number; currency: string }
  const [portfolioPositions, setPortfolioPositions] = useState<PortfolioPos[]>([])
  const [livePrices, setLivePrices] = useState<Record<string, number>>({})
  const portfolioTickers = useMemo(() => portfolioPositions.map(p => p.ticker), [portfolioPositions])

  useEffect(() => {
    if (!user) return
    supabase
      .from('personal_portfolio_positions')
      .select('*')
      .eq('user_id', user.id)
      .then(({ data }) => {
        if (data) {
          const positions = data.map((r: { id: string; ticker: string; shares: number; avg_price: number; currency: string }) => ({
            id: r.id, ticker: r.ticker, shares: r.shares, avg_price: r.avg_price, currency: r.currency,
          }))
          setPortfolioPositions(positions)
          if (positions.length) {
            fetchPortfolioPrices(positions.map(p => p.ticker)).then(setLivePrices)
          }
        }
      })
  }, [user])

  const portfolioEarnings = useMemo<EarningsEntry[]>(() => {
    if (!earningsRaw?.earnings || !portfolioTickers.length) return []
    const tSet = new Set(portfolioTickers.map(t => t.toUpperCase()))
    return earningsRaw.earnings.filter(
      e => tSet.has(e.ticker.toUpperCase()) && e.days_to_earnings != null && e.days_to_earnings >= 0 && e.days_to_earnings <= 14
    ).sort((a, b) => (a.days_to_earnings ?? 99) - (b.days_to_earnings ?? 99))
  }, [earningsRaw, portfolioTickers])

  const [activeTab, setActiveTab] = useState<CerebroTab>('briefing')
  const scrollToTabs = (tab: CerebroTab) => {
    setActiveTab(tab)
    setTimeout(() => {
      document.getElementById('cerebro-tabs-anchor')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 50)
  }
  const [entryFilter, setEntryFilter] = useState<'ACTIONABLE' | 'STRONG_BUY' | 'BUY' | 'MONITOR'>('ACTIONABLE')
  const [focusedIdx, setFocusedIdx] = useState(-1)
  const [showAllAlerts, setShowAllAlerts] = useState(false)
  const [showAllConvergences, setShowAllConvergences] = useState(false)

  // pagedRef must be declared before early returns (React Rules of Hooks)
  const pagedRef = useRef<EntrySignal[]>([])

  // Keyboard navigation
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'j' || e.key === 'ArrowDown') { e.preventDefault(); setFocusedIdx(i => Math.min(i + 1, pagedRef.current.length - 1)) }
      if (e.key === 'k' || e.key === 'ArrowUp')   { e.preventDefault(); setFocusedIdx(i => Math.max(i - 1, 0)) }
      if (e.key === 'Escape') setFocusedIdx(-1)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const loading = loadingI && loadingC && loadingA && loadingCal && loadingE
  if (loading) return <Loading />
  const anyError = !insights && !convergence && !alertsData && !entryData
  if (anyError) return <ErrorState message="El Cerebro aún no ha publicado análisis. Lo genera el pipeline diario — si lleva más de un día así, revisa que haya corrido." />

  const signals       = convergence?.convergences ?? []
  const alerts        = alertsData?.alerts ?? []
  const entrySignals  = entryData?.signals ?? []
  const briefingSections = {
    regime: briefingData?.sections?.regime ?? '',
    strong_buy_count: briefingData?.sections?.strong_buy_count ?? 0,
    buy_count: briefingData?.sections?.buy_count ?? 0,
    top_entries: briefingData?.sections?.top_entries ?? [],
    top_convergences: briefingData?.sections?.top_convergences ?? [],
    high_alerts: briefingData?.sections?.high_alerts ?? [],
    traps_warning: briefingData?.sections?.traps_warning ?? [],
    exit_warnings: (briefingData?.sections?.exit_warnings ?? []) as unknown as [string, string, string, number, number][],
    smart_money: briefingData?.sections?.smart_money ?? [],
    macro_stress: briefingData?.sections?.macro_stress ?? [],
  }

  // Mean reversion bounces
  const mrRawObj = mrRaw as Record<string, unknown> | null
  const mrItems: MeanReversionItem[] = Array.isArray(mrRawObj?.opportunities)
    ? (mrRawObj!.opportunities as MeanReversionItem[])
    : Array.isArray(mrRawObj?.data) ? (mrRawObj!.data as MeanReversionItem[]) : []
  const topBounces = mrItems
    .filter(i => (i.quality || '').toUpperCase().includes('EXCELENTE') || (i.quality || '').toUpperCase().includes('MUY BUENA'))
    .sort((a, b) => (b.reversion_score ?? 0) - (a.reversion_score ?? 0))
  const filteredEntry = entryFilter === 'ACTIONABLE'
    ? entrySignals.filter(s => s.signal === 'STRONG_BUY' || s.signal === 'BUY')
    : entrySignals.filter(s => s.signal === entryFilter)
  // eslint-disable-next-line react-hooks/refs -- keeps keyboard navigation in sync without rebinding the listener on every filter change.
  pagedRef.current = filteredEntry

  const coachActions = buildCoachActions({
    entrySignals,
    exits: exitData?.exits ?? [],
    traps: trapsData?.traps ?? [],
    alerts,
    convergences: signals,
    topBounces,
    smartMoney: smData?.signals ?? [],
    squeezeSetups: squeezeData?.setups ?? [],
    decayItems: decayData?.decays ?? [],
  })

  const highRiskCount =
    (exitData?.high_count ?? 0) +
    (trapsData?.high_count ?? 0) +
    (decayData?.high_count ?? 0) +
    alerts.filter(a => a.severity === 'HIGH').length
  const topEntry = entrySignals.find(s => s.signal === 'STRONG_BUY') ?? entrySignals.find(s => s.signal === 'BUY')
  // Portfolio-specific risk signals (needed for coach and tabs)
  const pSet = new Set(portfolioTickers.map(t => t.toUpperCase()))
  const portfolioExitHigh  = (exitData?.exits  ?? []).filter(e => pSet.has(e.ticker.toUpperCase()) && e.severity === 'HIGH')
  const portfolioTrapsHigh = (trapsData?.traps ?? []).filter(t => pSet.has(t.ticker.toUpperCase()) && t.severity === 'HIGH')
  const portfolioDecayHigh = ((decayData as { decays?: { ticker: string; severity: string }[] } | null)?.decays ?? []).filter(d => pSet.has(d.ticker.toUpperCase()) && d.severity === 'HIGH')
  const portfolioRiskCount = portfolioExitHigh.length + portfolioTrapsHigh.length + portfolioDecayHigh.length

  // Coach: portfolio-aware headline
  const ownedExit  = portfolioExitHigh[0]
  const ownedTrap  = portfolioTrapsHigh[0]
  const coachHeadline = ownedExit
    ? `Revisa ${ownedExit.ticker} — tienes esta posición y Cerebro detecta deterioro.`
    : ownedTrap
    ? `${ownedTrap.ticker} puede ser una trampa — y está en tu cartera.`
    : highRiskCount > 0
    ? 'Yo hoy empezaría por proteger la cartera.'
    : topEntry
    ? `Yo hoy miraría ${topEntry.ticker} primero.`
    : topBounces.length > 0
    ? 'Hoy veo más vigilancia que compra inmediata.'
    : 'Hoy no forzaría ninguna operación.'
  const coachSubline = ownedExit
    ? `El Exit Monitor tiene señal HIGH en ${ownedExit.ticker}. Antes de buscar entradas nuevas, vale la pena revisar esta posición.`
    : ownedTrap
    ? `${ownedTrap.ticker} tiene puntuación de trampa ${ownedTrap.trap_score}/10. Puede estar barata sin estar limpia.`
    : highRiskCount > 0
    ? 'Hay señales de riesgo que pueden ahorrar más dinero que una buena entrada. Primero limpio lo delicado, luego busco oportunidades.'
    : topEntry
    ? 'Hay al menos una idea con suficiente claridad para abrir análisis. La decisión final sigue siendo tamaño, precio y encaje con tu cartera.'
    : topBounces.length > 0
    ? 'Hay posibles movimientos tácticos, pero Cerebro no está gritando compra. Mejor mirar niveles y esperar confirmación.'
    : 'El sistema no encuentra una prioridad urgente. En días así, la ventaja está en no inventarse señales.'

  const tabs = [
    { id: 'briefing' as const,    label: 'Briefing',        icon: Newspaper,         count: undefined,          highlight: !!briefingData?.narrative },
    { id: 'myportfolio' as const, label: 'Mi cartera',      icon: Wallet,            count: portfolioRiskCount || (portfolioPositions.length ? undefined : undefined), highlight: portfolioRiskCount > 0 },
    { id: 'entry' as const,       label: 'Señales',         icon: Zap,               count: (entryData?.strong_buy ?? 0) + (entryData?.buy ?? 0), highlight: (entryData?.strong_buy ?? 0) > 0 },
    { id: 'bounces' as const,     label: 'Rebotes',         icon: Repeat2,           count: topBounces.length,  highlight: topBounces.length > 0 },
    { id: 'convergence' as const, label: 'Convergencias',   icon: Crosshair,         count: convergence?.triple_or_more, highlight: (convergence?.triple_or_more ?? 0) > 0 },
    { id: 'agents' as const,      label: 'Agentes IA',      icon: Bot,               count: (exitData?.high_count ?? 0) + (trapsData?.high_count ?? 0) + (squeezeData?.high_count ?? 0) + (decayData?.high_count ?? 0), highlight: (exitData?.high_count ?? 0) + (trapsData?.high_count ?? 0) + (squeezeData?.high_count ?? 0) + (decayData?.high_count ?? 0) > 0 },
    { id: 'alerts' as const,      label: 'Alertas',         icon: Bell,              count: alerts.filter(a => a.severity === 'HIGH').length || undefined, highlight: alerts.some(a => a.severity === 'HIGH') },
    { id: 'calibration' as const, label: 'Calibración',     icon: SlidersHorizontal, count: calibration?.total_recommendations },
    { id: 'thesis' as const,      label: 'Thesis Drift',    icon: GitBranch,          count: undefined,                            highlight: false },
    { id: 'contrarian' as const,  label: 'Contrarian',      icon: Target,             count: undefined,                            highlight: false },
    { id: 'novedades' as const,   label: 'Novedades',       icon: Bell,               count: undefined,                            highlight: false },
  ]


  return (
    <>
      <StaleDataBanner module="cerebro" />
      {/* Header — se oculta cuando Cerebro va embebido como pestaña del Dashboard */}
      {!embedded && (
        <div className="mb-7 animate-fade-in-up">
          <h2 className="text-pagina font-extrabold tracking-tight mb-2 gradient-title flex items-center gap-2">
            <Brain size={22} className="text-violet-400" />
            Cerebro — IA Proactiva
          </h2>
          <p className="text-cuerpo text-muted-foreground">
            Te resume lo importante primero. El detalle técnico sigue debajo cuando lo necesites.
          </p>
        </div>
      )}

      <IdeasHoy signals={entrySignals} onVerDetalle={() => scrollToTabs('entry')} />

      <CerebroCoachPanel
        headline={coachHeadline}
        subline={coachSubline}
        actions={coachActions}
        onOpenTab={scrollToTabs}
      />

      {/* Cinco cifras, no cinco tarjetas. Son navegables —cada una lleva a su
          pestaña— y por eso estaban en `<Card>`: para parecer pulsables. Pero
          una cifra pulsable se resuelve con estado de pulsación, no metiéndola
          en un rectángulo; en caja competían entre sí y con el título. */}
      <CifrasClave cifras={[
        { etiqueta: 'En cartera',
          valor: portfolioPositions.length || '—',
          tono: portfolioPositions.length > 0 ? 'neutro' : 'apagado',
          sub: portfolioRiskCount > 0
            ? <span className="text-danger">{portfolioRiskCount} alerta{portfolioRiskCount > 1 ? 's' : ''}</span>
            : portfolioEarnings.length > 0 ? `${portfolioEarnings.length} earnings próx.` : 'sin alertas',
          onClick: () => setActiveTab('myportfolio') },
        { etiqueta: 'Strong Buy hoy',
          valor: entryData?.strong_buy ?? '—',
          tono: (entryData?.strong_buy ?? 0) > 0 ? 'favor' : 'apagado',
          sub: `${entryData?.buy ?? 0} BUY · ${entryData?.monitor ?? 0} Monitor`,
          onClick: () => setActiveTab('entry') },
        { etiqueta: 'Win rate VALUE',
          valor: insights ? insights.baseline_win_rate.toFixed(1) : '—',
          unidad: insights ? '%' : undefined,
          tono: insights?.baseline_win_rate == null ? 'apagado'
            : insights.baseline_win_rate >= 55 ? 'favor'
            : insights.baseline_win_rate >= 45 ? 'aviso' : 'alarma',
          sub: `90d histórico${insights?.poblacion === 'VALUE' ? ' · solo US' : ''}` },
        { etiqueta: 'Convergencias',
          valor: convergence?.total_convergences ?? '—',
          sub: `${convergence?.triple_or_more ?? 0} triples`,
          onClick: () => setActiveTab('convergence') },
        { etiqueta: 'Alertas HIGH',
          valor: alertsData?.high_count ?? '—',
          tono: (alertsData?.high_count ?? 0) > 0 ? 'alarma' : 'apagado',
          sub: `${alertsData?.total ?? 0} total`,
          onClick: () => setActiveTab('alerts') },
      ]} />

      {/* Tabs */}
      <div id="cerebro-tabs-anchor" className="flex gap-1 mb-4 border-b border-border/40 overflow-x-auto">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`underline-tab -mb-px active:scale-[0.98] ${activeTab === tab.id ? 'active' : ''}`}
          >
            <tab.icon size={12} />
            {tab.label}
            {tab.count != null && (
              <span className={`text-micro px-1.5 py-0.5 rounded-full font-bold ${
                tab.highlight ? 'bg-red-500/20 text-red-400' : 'bg-muted/30 text-muted-foreground'
              }`}>{tab.count}</span>
            )}
          </button>
        ))}
      </div>

      {/* ── TAB: Briefing ─────────────────────────────────────────────────────── */}
      {activeTab === 'briefing' && (
        <div key="briefing" className="space-y-4 animate-fade-in-up">
          {briefingData?.narrative ? (
            <>
              <AiNarrativeCard narrative={briefingData.narrative} label={`Briefing diario · ${briefingData.generated_at} · Régimen ${briefingData.regime}`} />
              {portfolioEarnings.length > 0 && (
                <Card className="glass">
                  <CardContent className="p-3">
                    <div className="flex items-center gap-2 mb-2">
                      <CalendarDays size={12} className="text-amber-400" />
                      <span className="etiqueta-seccion text-amber-400">Earnings en tu cartera · próx. 14 días</span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {portfolioEarnings.map(e => (
                        <span key={e.ticker} className="inline-flex items-center gap-1.5 text-mini font-bold px-2.5 py-1 rounded-lg bg-amber-500/15 text-amber-300 border border-amber-500/30">
                          {e.ticker}
                          <span className="font-normal text-amber-400">{e.days_to_earnings === 0 ? 'HOY' : e.days_to_earnings === 1 ? 'MAÑANA' : `en ${e.days_to_earnings}d`}</span>
                          {e.implied_move_pct != null && <span className="font-normal text-muted-foreground">±{e.implied_move_pct.toFixed(1)}%</span>}
                        </span>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </>
          ) : (
            <Card className="glass border-border/30">
              <CardContent className="p-4">
                <div className="flex items-center gap-2 mb-3">
                  <Newspaper size={16} className="text-muted-foreground" />
                  <span className="etiqueta-seccion">Resumen automático</span>
                  <span className="ml-auto text-micro text-muted-foreground">Briefing IA no generado aún</span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-mini">
                  <div className="rounded-lg bg-muted/10 border border-border/20 p-2.5">
                    <div className="etiqueta-seccion mb-1">Régimen</div>
                    <div className="font-bold text-foreground/80">{briefingData?.regime ?? insights?.market_regimes?.[0]?.label ?? '—'}</div>
                  </div>
                  <div className="rounded-lg bg-emerald-500/5 border border-emerald-500/15 p-2.5">
                    <div className="etiqueta-seccion mb-1">Entradas hoy</div>
                    <div className="font-bold text-emerald-400">{(entryData?.strong_buy ?? 0) + (entryData?.buy ?? 0)} accionables</div>
                  </div>
                  <div className="rounded-lg bg-red-500/5 border border-red-500/15 p-2.5">
                    <div className="etiqueta-seccion mb-1">Alertas HIGH</div>
                    <div className="font-bold text-red-400">{alertsData?.high_count ?? 0}</div>
                  </div>
                  <div className="rounded-lg bg-cyan-500/5 border border-cyan-500/15 p-2.5">
                    <div className="etiqueta-seccion mb-1">Convergencias</div>
                    <div className="font-bold text-cyan-400">{convergence?.triple_or_more ?? 0} triples</div>
                  </div>
                  {portfolioRiskCount > 0 && (
                    <div className="rounded-lg bg-violet-500/5 border border-violet-500/20 p-2.5 col-span-2">
                      <div className="etiqueta-seccion mb-1">Tu cartera</div>
                      <div className="font-bold text-violet-400">{portfolioRiskCount} alerta{portfolioRiskCount > 1 ? 's' : ''} en posiciones propias</div>
                    </div>
                  )}
                  {portfolioEarnings.length > 0 && (
                    <div className="rounded-lg bg-amber-500/5 border border-amber-500/20 p-2.5 col-span-2 sm:col-span-3">
                      <div className="etiqueta-seccion mb-1.5">Earnings en tu cartera (próx. 14d)</div>
                      <div className="flex flex-wrap gap-2">
                        {portfolioEarnings.map(e => (
                          <span key={e.ticker} className="inline-flex items-center gap-1.5 text-mini font-bold px-2 py-0.5 rounded-lg bg-amber-500/15 text-amber-300 border border-amber-500/30">
                            {e.ticker}
                            <span className="font-normal text-amber-400">{e.days_to_earnings === 0 ? 'HOY' : e.days_to_earnings === 1 ? 'MAÑANA' : `en ${e.days_to_earnings}d`}</span>
                            {e.implied_move_pct != null && <span className="font-normal text-muted-foreground">±{e.implied_move_pct.toFixed(1)}%</span>}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {briefingData?.sections && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {/* Top entries */}
              {briefingSections.top_entries.length > 0 && (
                <Card className="glass hover:border-border/60 animate-fade-in-up" style={{ animationDelay: '60ms' }}>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <Zap size={16} className="text-emerald-400" />
                      <span className="etiqueta-seccion">Entradas hoy</span>
                      <span className="ml-auto text-micro bg-emerald-500/15 text-emerald-400 px-1.5 py-0.5 rounded border border-emerald-500/30 font-bold">
                        {briefingSections.strong_buy_count} SB · {briefingSections.buy_count} BUY
                      </span>
                    </div>
                    <div className="space-y-1.5">
                      {briefingSections.top_entries.map(([ticker, score]) => (
                        <div key={ticker} className="flex items-center gap-2">
                          <TickerLogo ticker={ticker} size="xs" className="shrink-0" />
                          <Link to={`/search?q=${ticker}`} className="font-mono font-bold text-primary text-apoyo hover:underline w-12">{ticker}</Link>
                          <div className="flex-1 h-1.5 rounded-full barra-pista overflow-hidden">
                            <div className="h-full rounded-full bg-emerald-500" style={{ width: `${score}%` }} />
                          </div>
                          <span className="tabular-nums text-mini text-muted-foreground w-6 text-right">{score}</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Smart money */}
              {briefingSections.smart_money.length > 0 && (
                <Card className="glass hover:border-border/60 animate-fade-in-up" style={{ animationDelay: '120ms' }}>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <Building2 size={16} className="text-purple-400" />
                      <span className="etiqueta-seccion">Smart Money</span>
                    </div>
                    <div className="space-y-1.5">
                      {briefingSections.smart_money.map(([ticker, nHF, nInsiders]) => (
                        <div key={ticker} className="flex items-center gap-2">
                          <TickerLogo ticker={ticker} size="xs" className="shrink-0" />
                          <Link to={`/search?q=${ticker}`} className="font-mono font-bold text-primary text-apoyo hover:underline">{ticker}</Link>
                          <span className="ml-auto text-micro text-purple-400">
                            {nHF > 0 ? `${nHF} HF` : `${nInsiders ?? 0} insiders`}
                          </span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Macro stress */}
              {briefingSections.macro_stress.length > 0 && (
                <Card className="glass hover:border-border/60 animate-fade-in-up" style={{ animationDelay: '150ms' }}>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <Activity size={16} className="text-orange-300" />
                      <span className="etiqueta-seccion">Macro Stress</span>
                    </div>
                    <div className="space-y-2">
                      {briefingSections.macro_stress.map((item) => (
                        <div key={item.market} className="rounded-lg border border-orange-500/15 bg-orange-500/8 px-3 py-2">
                          <div className="flex items-center gap-2">
                            <span className="text-apoyo font-bold text-foreground">{item.market}</span>
                            <span className="ml-auto text-micro font-bold text-orange-300">{item.score.toFixed(0)}</span>
                          </div>
                          <div className="mt-0.5 text-micro text-muted-foreground">{item.regime}</div>
                          {item.exposed.length > 0 && (
                            <div className="mt-2 flex flex-wrap gap-1">
                              {item.exposed.map((ticker) => (
                                <span key={ticker} className="rounded-full border border-orange-500/20 bg-muted/50 px-1.5 py-0.5 text-micro font-bold text-orange-200">
                                  {ticker}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Exits + traps */}
              {(briefingSections.exit_warnings.length > 0 || briefingSections.traps_warning.length > 0) && (
                <Card className="glass hover:border-border/60 animate-fade-in-up" style={{ animationDelay: '180ms' }}>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <ShieldAlert size={16} className="text-red-400" />
                      <span className="etiqueta-seccion">Vigilar / Salir</span>
                    </div>
                    <div className="space-y-2">
                      {briefingSections.exit_warnings.map(([ticker, reason, aiFinding, entryScore, currentScore]: [string, string, string, number, number]) => (
                        <div key={`exit-${ticker}`} className="rounded-lg border border-red-500/15 bg-red-500/5 px-3 py-2">
                          <div className="flex items-center gap-2 mb-1">
                            <TickerLogo ticker={ticker} size="xs" className="shrink-0" />
                            <Link to={`/search?q=${ticker}`} className="font-mono font-bold text-red-400 text-apoyo hover:underline">{ticker}</Link>
                            {entryScore != null && currentScore != null && (
                              <span className="ml-auto text-micro text-red-400 font-mono">score {Math.round(entryScore)} → {Math.round(currentScore)}</span>
                            )}
                          </div>
                          <p className="text-micro text-muted-foreground leading-tight">{reason}</p>
                          {aiFinding && <p className="mt-1 text-micro text-red-300 leading-tight italic">{aiFinding}</p>}
                        </div>
                      ))}
                      {briefingSections.traps_warning.map(([ticker, score]) => (
                        <div key={`trap-${ticker}`} className="flex items-center gap-2">
                          <TickerLogo ticker={ticker} size="xs" className="shrink-0" />
                          <Link to={`/search?q=${ticker}`} className="font-mono font-bold text-amber-400 text-apoyo hover:underline">{ticker}</Link>
                          <span className="ml-auto text-micro text-amber-400">trampa {score}/10</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Convergences */}
              {briefingSections.top_convergences.length > 0 && (
                <Card className="glass hover:border-border/60 animate-fade-in-up" style={{ animationDelay: '240ms' }}>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <Crosshair size={16} className="text-cyan-400" />
                      <span className="etiqueta-seccion">Convergencias</span>
                    </div>
                    <div className="space-y-1.5">
                      {briefingSections.top_convergences.map(([ticker, score]) => (
                        <div key={ticker} className="flex items-center gap-2">
                          <TickerLogo ticker={ticker} size="xs" className="shrink-0" />
                          <Link to={`/search?q=${ticker}`} className="font-mono font-bold text-primary text-apoyo hover:underline">{ticker}</Link>
                          <span className="ml-auto text-micro text-cyan-400">conv {score}</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Portfolio earnings */}
              {portfolioEarnings.length > 0 && (
                <Card className="glass hover:border-border/60 animate-fade-in-up" style={{ animationDelay: '270ms' }}>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <Bell size={16} className="text-violet-400" />
                      <span className="etiqueta-seccion">Earnings en tu cartera</span>
                      <span className="ml-auto text-micro bg-violet-500/15 text-violet-400 px-1.5 py-0.5 rounded border border-violet-500/30 font-bold">
                        {portfolioEarnings.length} próximos
                      </span>
                    </div>
                    <div className="space-y-2">
                      {portfolioEarnings.map(e => (
                        <div key={e.ticker} className="flex items-center gap-2">
                          <TickerLogo ticker={e.ticker} size="xs" className="shrink-0" />
                          <Link to={`/search?q=${e.ticker}`} className="font-mono font-bold text-primary text-apoyo hover:underline w-12 shrink-0">{e.ticker}</Link>
                          <span className="text-micro text-muted-foreground truncate flex-1">{e.company}</span>
                          <span className={`text-micro font-bold tabular-nums shrink-0 ${e.days_to_earnings === 0 ? 'text-red-400' : e.days_to_earnings != null && e.days_to_earnings <= 3 ? 'text-amber-400' : 'text-violet-400'}`}>
                            {e.days_to_earnings === 0 ? 'HOY' : `${e.days_to_earnings}d`}
                          </span>
                          {e.earnings_catalyst && (
                            <span className="text-micro px-1 py-0.5 rounded bg-emerald-500/15 text-emerald-400 border border-emerald-500/20 font-bold shrink-0">CAT</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Alerts */}
              {briefingSections.high_alerts.length > 0 && (
                <Card className="glass hover:border-border/60 animate-fade-in-up" style={{ animationDelay: '300ms' }}>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <Bell size={16} className="text-amber-400" />
                      <span className="etiqueta-seccion">Alertas HIGH</span>
                    </div>
                    <div className="space-y-1.5">
                      {briefingSections.high_alerts.map(([ticker, type]) => (
                        <div key={`alert-${ticker}-${type}`} className="flex items-center gap-2">
                          <TickerLogo ticker={ticker} size="xs" className="shrink-0" />
                          <Link to={`/search?q=${ticker}`} className="font-mono font-bold text-primary text-apoyo hover:underline">{ticker}</Link>
                          <span className="ml-auto text-micro text-amber-400">{type}</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── TAB: Mi Cartera ──────────────────────────────────────────────────── */}
      {activeTab === 'myportfolio' && (
        <div className="space-y-4 animate-fade-in-up">
          {!user ? (
            <Card className="glass"><CardContent className="py-12 text-center text-muted-foreground">Inicia sesión para ver tu cartera.</CardContent></Card>
          ) : portfolioPositions.length === 0 ? (
            <Card className="glass"><CardContent className="py-12 text-center text-muted-foreground">No hay posiciones guardadas. Añádelas en <Link to="/my-portfolio" className="text-primary hover:underline">Mi cartera →</Link></CardContent></Card>
          ) : (
            <>
              {/* Risk alerts for owned positions */}
              {portfolioRiskCount > 0 && (
                <div className="space-y-2">
                  <div className="etiqueta-seccion text-red-400">Alertas en tus posiciones</div>
                  {portfolioExitHigh.map(e => (
                    <div key={e.ticker} className="flex items-start gap-3 p-3 rounded-xl border border-red-500/30 bg-red-500/5">
                      <TickerLogo ticker={e.ticker} size="sm" className="shrink-0 mt-0.5" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <Link to={`/search?q=${e.ticker}`} className="font-mono font-bold text-primary text-cuerpo hover:underline">{e.ticker}</Link>
                          <span className="text-micro font-bold px-1 py-0.5 rounded border bg-red-500/15 text-red-400 border-red-500/30">EXIT HIGH</span>
                          {e.current_score != null && <span className="text-micro text-muted-foreground ml-auto">Score {e.entry_score.toFixed(0)} → {e.current_score.toFixed(0)}</span>}
                        </div>
                        <p className="text-mini text-muted-foreground">{e.reasons.slice(0, 2).join(' · ')}</p>
                      </div>
                    </div>
                  ))}
                  {portfolioTrapsHigh.map(t => (
                    <div key={t.ticker} className="flex items-start gap-3 p-3 rounded-xl border border-amber-500/30 bg-amber-500/5">
                      <TickerLogo ticker={t.ticker} size="sm" className="shrink-0 mt-0.5" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <Link to={`/search?q=${t.ticker}`} className="font-mono font-bold text-primary text-cuerpo hover:underline">{t.ticker}</Link>
                          <span className="text-micro font-bold px-1 py-0.5 rounded border bg-amber-500/15 text-amber-400 border-amber-500/30">TRAMPA HIGH</span>
                          <span className="text-micro text-amber-400 ml-auto">{t.trap_score}/10</span>
                        </div>
                        <div className="flex flex-wrap gap-1 mt-1">{t.flags.slice(0, 3).map((f, i) => <span key={i} className="text-micro text-muted-foreground bg-muted/10 border border-border/20 px-1.5 py-0.5 rounded">{f}</span>)}</div>
                      </div>
                    </div>
                  ))}
                  {portfolioDecayHigh.map(d => (
                    <div key={d.ticker} className="flex items-start gap-3 p-3 rounded-xl border border-orange-500/25 bg-orange-500/5">
                      <TickerLogo ticker={d.ticker} size="sm" className="shrink-0 mt-0.5" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <Link to={`/search?q=${d.ticker}`} className="font-mono font-bold text-primary text-cuerpo hover:underline">{d.ticker}</Link>
                          <span className="text-micro font-bold px-1 py-0.5 rounded border bg-orange-500/15 text-orange-400 border-orange-500/25">DETERIORO</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Earnings upcoming */}
              {portfolioEarnings.length > 0 && (
                <div className="space-y-2">
                  <div className="etiqueta-seccion text-violet-400">Earnings próximos (≤14d)</div>
                  {portfolioEarnings.map(e => (
                    <div key={e.ticker} className="flex items-center gap-3 p-3 rounded-xl border border-violet-500/20 bg-violet-500/5">
                      <TickerLogo ticker={e.ticker} size="sm" className="shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <Link to={`/search?q=${e.ticker}`} className="font-mono font-bold text-primary text-cuerpo hover:underline">{e.ticker}</Link>
                          <span className="text-micro text-muted-foreground truncate">{e.company}</span>
                        </div>
                        {e.implied_move_pct != null && <div className="text-micro text-muted-foreground">Movimiento implícito: ±{e.implied_move_pct.toFixed(1)}%</div>}
                      </div>
                      <div className="text-right shrink-0">
                        <div className={`text-cuerpo font-black tabular-nums ${e.days_to_earnings === 0 ? 'text-red-400' : e.days_to_earnings != null && e.days_to_earnings <= 3 ? 'text-amber-400' : 'text-violet-400'}`}>
                          {e.days_to_earnings === 0 ? 'HOY' : `${e.days_to_earnings}d`}
                        </div>
                        {e.earnings_catalyst && <div className="text-micro text-emerald-400 font-bold">CATALIZADOR</div>}
                        {e.earnings_warning && <div className="text-micro text-amber-400 font-bold">RIESGO</div>}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Positions P&L grid */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="etiqueta-seccion">Tus posiciones</div>
                  <Link to="/my-portfolio" className="text-mini text-primary hover:underline">Ver análisis completo →</Link>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {portfolioPositions.map(pos => {
                    const live = livePrices[pos.ticker]
                    const pnlPct = live != null ? ((live - pos.avg_price) / pos.avg_price) * 100 : null
                    const hasExit  = pSet.has(pos.ticker.toUpperCase()) && (exitData?.exits ?? []).some(e => e.ticker.toUpperCase() === pos.ticker.toUpperCase())
                    const hasTrap  = pSet.has(pos.ticker.toUpperCase()) && (trapsData?.traps ?? []).some(t => t.ticker.toUpperCase() === pos.ticker.toUpperCase())
                    const hasEarnings = portfolioEarnings.some(e => e.ticker.toUpperCase() === pos.ticker.toUpperCase())
                    return (
                      <div key={pos.ticker} className={`flex items-center gap-3 p-3 rounded-xl border transition-colors ${hasExit ? 'border-red-500/25 bg-red-500/5' : hasTrap ? 'border-amber-500/20 bg-amber-500/5' : 'border-border/30 bg-muted/5 hover:border-border/50'}`}>
                        <TickerLogo ticker={pos.ticker} size="sm" className="shrink-0" />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1.5">
                            <Link to={`/search?q=${pos.ticker}`} className="font-mono font-bold text-primary text-cuerpo hover:underline">{pos.ticker}</Link>
                            {hasExit  && <span className="text-micro font-bold px-1 py-0 rounded border bg-red-500/15 text-red-400 border-red-500/25">EXIT</span>}
                            {hasTrap  && <span className="text-micro font-bold px-1 py-0 rounded border bg-amber-500/15 text-amber-400 border-amber-500/25">TRAMPA</span>}
                            {hasEarnings && <span className="text-micro font-bold px-1 py-0 rounded border bg-violet-500/15 text-violet-400 border-violet-500/25">EARN</span>}
                          </div>
                          <div className="text-micro text-muted-foreground">
                            {pos.shares} acc · entrada {pos.currency === 'USD' ? '$' : '£'}{pos.avg_price.toFixed(2)}
                          </div>
                        </div>
                        <div className="text-right shrink-0">
                          {live != null ? (
                            <>
                              <div className="text-apoyo font-bold text-foreground tabular-nums">{pos.currency === 'USD' ? '$' : '£'}{live.toFixed(2)}</div>
                              <div className={`text-micro font-bold tabular-nums ${pnlPct != null && pnlPct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                {pnlPct != null ? `${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(1)}%` : '—'}
                              </div>
                            </>
                          ) : (
                            <div className="text-micro text-muted-foreground">sin precio</div>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* ── TAB: Señales de Entrada ──────────────────────────────────────────── */}
      {activeTab === 'entry' && (
        <div className="space-y-4 animate-fade-in-up">
          {entryData?.narrative && (
            <AiNarrativeCard narrative={entryData.narrative} label="Análisis de entradas de hoy" />
          )}

          {/* Filter buttons */}
          <div className="flex gap-2 flex-wrap">
            {(['ACTIONABLE', 'STRONG_BUY', 'BUY', 'MONITOR'] as const).map(f => {
              const counts: Record<string, number | undefined> = {
                ACTIONABLE: (entryData?.strong_buy ?? 0) + (entryData?.buy ?? 0),
                STRONG_BUY: entryData?.strong_buy,
                BUY: entryData?.buy,
                MONITOR: entryData?.monitor,
              }
              const labels: Record<string, string> = { ACTIONABLE: 'Accionables', STRONG_BUY: 'Strong Buy', BUY: 'Buy', MONITOR: 'Monitor' }
              return (
                <button
                  key={f}
                  onClick={() => setEntryFilter(f)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-mini font-semibold border transition-colors active:scale-[0.98] ${
                    entryFilter === f
                      ? 'bg-primary/15 text-primary border-primary/30'
                      : 'bg-muted/10 text-muted-foreground border-border/30 hover:text-foreground'
                  }`}
                >
                  {labels[f]}
                  <span className="text-micro opacity-70">{counts[f] ?? 0}</span>
                </button>
              )
            })}
          </div>

          {loadingE ? (
            <div className="space-y-3">{['a','b','c'].map(k => <Card key={k} className="glass h-32 animate-pulse" />)}</div>
          ) : filteredEntry.length === 0 ? (
            <Card className="glass">
              <CardContent className="py-12 text-center text-muted-foreground">
                {entryFilter === 'ACTIONABLE'
                  ? 'No hay señales de entrada claras hoy. Revisa mañana.'
                  : `No hay señales ${entryFilter.replace('_', ' ')} hoy.`}
              </CardContent>
            </Card>
          ) : (
            filteredEntry.map((sig, i) => (
              <div
                key={sig.ticker}
                data-row-idx={i}
                className={`animate-fade-in-up rounded-xl transition-shadow ${focusedIdx === i ? 'ring-2 ring-primary/50' : ''}`}
                style={{ animationDelay: `${i * 60}ms` }}
                onClick={() => setFocusedIdx(i)}
              >
                <EntrySignalCard sig={sig} />
              </div>
            ))
          )}
        </div>
      )}

      {/* ── TAB: Rebotes ───────────────────────────────────────────────────────── */}
      {activeTab === 'bounces' && (
        <div className="space-y-4 animate-fade-in-up">
          <div className="flex items-center justify-between">
            <p className="text-mini text-muted-foreground">
              Setups de rebote — oversold con RSI bajo y soporte claro · <Link to="/mean-reversion" className="text-primary hover:underline">Ver tabla completa →</Link>
            </p>
            <span className="text-mini text-muted-foreground">{topBounces.length} setups de calidad</span>
          </div>

          {topBounces.length === 0 ? (
            <Card className="glass">
              <CardContent className="py-12 text-center text-muted-foreground">
                Sin rebotes de calidad detectados hoy
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {topBounces.map((d, i) => {
                const rr = d.risk_reward != null ? Number(d.risk_reward) : null
                const rrColor = rr == null ? 'text-muted-foreground' : rr >= 3 ? 'text-emerald-400' : rr >= 2 ? 'text-cyan-400' : rr >= 1 ? 'text-amber-400' : 'text-red-400'
                const strategyShort = (d.strategy || '').includes('Flag') ? 'Bull Flag' : 'Oversold'
                const isDaily = d.reversion_score >= 80
                return (
                  <Card
                    key={d.ticker}
                    className="glass border border-border/30 hover:border-primary/30 transition-colors cursor-pointer active:scale-[0.98] animate-fade-in-up"
                    style={{ animationDelay: `${i * 60}ms` }}
                  >
                    <CardContent className="p-4">
                      {/* Header */}
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <TickerLogo ticker={d.ticker} size="sm" />
                          <div>
                            <Link to={`/search?q=${d.ticker}`} className="font-mono font-bold text-foreground hover:text-primary transition-colors">
                              {d.ticker}
                            </Link>
                            {d.company_name && (
                              <div className="text-micro text-muted-foreground truncate max-w-[120px]">{d.company_name}</div>
                            )}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className={`text-micro font-bold px-1.5 py-0.5 rounded border ${
                            isDaily
                              ? 'bg-violet-500/10 border-violet-500/25 text-violet-400'
                              : 'bg-blue-500/10 border-blue-500/25 text-blue-400'
                          }`}>{isDaily ? 'DIARIO' : 'SEMANAL'}</div>
                          <div className="text-micro text-muted-foreground mt-0.5">{strategyShort}</div>
                        </div>
                      </div>

                      {/* Price grid */}
                      <div className="grid grid-cols-3 gap-1.5 mb-3">
                        <div className="rounded-lg bg-muted/15 p-2 text-center">
                          <div className="text-micro text-muted-foreground mb-0.5">Entrada</div>
                          <div className="text-mini font-bold leading-none">{d.entry_zone?.split(' ')[0] ?? '—'}</div>
                        </div>
                        <div className="rounded-lg bg-emerald-500/8 border border-emerald-500/15 p-2 text-center">
                          <div className="text-micro text-muted-foreground mb-0.5">Target</div>
                          <div className="text-mini font-bold text-emerald-400 leading-none">{precio(d.target, d.ticker)}</div>
                        </div>
                        <div className="rounded-lg bg-red-500/6 border border-red-500/10 p-2 text-center">
                          <div className="text-micro text-muted-foreground mb-0.5">Stop</div>
                          <div className="text-mini font-bold text-red-400 leading-none">{precio(d.stop_loss, d.ticker)}</div>
                        </div>
                      </div>

                      {/* Metrics row */}
                      <div className="flex items-center justify-between text-mini">
                        <div className="flex items-center gap-3">
                          {d.rsi != null && (
                            <span className={`font-semibold ${d.rsi < 25 ? 'text-red-400' : d.rsi < 35 ? 'text-amber-400' : 'text-muted-foreground'}`}>
                              RSI {d.rsi.toFixed(0)}
                            </span>
                          )}
                          {d.drawdown_pct != null && (
                            <span className="text-muted-foreground">↓{Math.abs(d.drawdown_pct).toFixed(0)}%</span>
                          )}
                        </div>
                        {rr != null && (
                          <span className={`font-black ${rrColor}`}>R:R {rr.toFixed(1)}x</span>
                        )}
                      </div>

                      {/* AI + win rate row */}
                      {(d.ai_confirmation || d.historical_win_rate != null) && (
                        <div className="flex items-center justify-between mt-2 pt-2 border-t border-border/15">
                          <div className="flex items-center gap-1.5">
                            {d.ai_confirmation && (
                              <span className={`text-micro font-black px-1.5 py-0.5 rounded border leading-none ${
                                d.ai_confirmation === 'YES' ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/20'
                                : d.ai_confirmation === 'CAUTION' ? 'bg-amber-500/15 text-amber-400 border-amber-500/20'
                                : 'bg-red-500/15 text-red-400 border-red-500/20'
                              }`} title={d.ai_reason ?? ''}>
                                {d.ai_confirmation === 'YES' ? <Check size={12} strokeWidth={2.5} className="inline -mt-px" /> : d.ai_confirmation === 'CAUTION' ? <TriangleAlert size={12} strokeWidth={2.5} className="inline -mt-px" /> : <X size={12} strokeWidth={2.5} className="inline -mt-px" />} IA
                                {d.ai_confidence != null ? ` ${d.ai_confidence}%` : ''}
                              </span>
                            )}
                            {d.ai_reason && (
                              <span className="text-micro text-muted-foreground truncate max-w-[110px]">{d.ai_reason}</span>
                            )}
                          </div>
                          {d.historical_win_rate != null && (
                            <span className="text-micro text-muted-foreground tabular-nums">{d.historical_win_rate.toFixed(0)}% hist</span>
                          )}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* ── TAB: Convergencias ─────────────────────────────────────────────────── */}
      {activeTab === 'convergence' && (
        <div className="space-y-4 animate-fade-in-up">
          {signals.length === 0 ? (
            <Card className="glass"><CardContent className="py-12 text-center text-muted-foreground">Sin convergencias detectadas hoy</CardContent></Card>
          ) : (() => {
            const tripleSignals = signals.filter(s => s.strategy_count >= 3)
            const displayedSignals = showAllConvergences ? signals : tripleSignals
            return (
            <>
              <div className="flex items-center justify-between">
                <p className="text-mini text-muted-foreground">
                  {showAllConvergences ? `${signals.length} convergencias totales` : `${tripleSignals.length} convergencias triples (≥3 estrategias)`}
                </p>
                {!showAllConvergences && signals.length > tripleSignals.length ? (
                  <button onClick={() => setShowAllConvergences(true)} className="filter-btn">Ver todas ({signals.length})</button>
                ) : showAllConvergences ? (
                  <button onClick={() => setShowAllConvergences(false)} className="filter-btn active">Solo triples ({tripleSignals.length})</button>
                ) : null}
              </div>
              {displayedSignals.length === 0 && (
                <Card className="glass"><CardContent className="py-12 text-center text-muted-foreground">Sin convergencias triples hoy</CardContent></Card>
              )}
            {displayedSignals.map((sig, i) => (
              <Card key={sig.ticker} className={`glass border hover:border-border/60 animate-fade-in-up ${sig.strategy_count >= 3 ? 'border-amber-500/30' : 'border-border/40'}`} style={{ animationDelay: `${i * 60}ms` }}>
                <CardContent className="p-4">
                  <div className="flex items-start gap-3">
                    <TickerLogo ticker={sig.ticker} size="sm" className="mt-0.5 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <Link to={`/search?q=${sig.ticker}`} className="font-mono font-bold text-primary text-cuerpo hover:underline">
                          {sig.ticker}
                        </Link>
                        {sig.strategy_count >= 3 && (
                          <span className="text-micro font-bold px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30">TRIPLE</span>
                        )}
                        {sig.strategies.map(s => strategyBadge(s))}
                        {sig.conviction_grade && <Badge variant={sig.conviction_grade === 'A' ? 'green' : sig.conviction_grade === 'B' ? 'blue' : 'yellow'} className="text-micro">{sig.conviction_grade}</Badge>}
                      </div>
                      <div className="text-mini text-muted-foreground mb-2">{sig.company_name} · {sig.sector}</div>
                      <div className="flex flex-wrap gap-3 text-mini mb-2">
                        {sig.value_score != null && <span>Score: <strong className="text-foreground">{sig.value_score.toFixed(0)}</strong></span>}
                        {sig.analyst_upside_pct != null && <span>Upside: <strong className={colorUpside(sig.analyst_upside_pct)}>{sig.analyst_upside_pct >= 0 ? '+' : ''}{sig.analyst_upside_pct.toFixed(1)}%</strong></span>}
                        {sig.fcf_yield_pct != null && <span>FCF: <strong className={sig.fcf_yield_pct >= 5 ? 'text-emerald-400' : 'text-foreground'}>{sig.fcf_yield_pct.toFixed(1)}%</strong></span>}
                        <span className="ml-auto text-muted-foreground">Conv. score: {sig.convergence_score}</span>
                      </div>
                      {sig.analysis && (
                        <p className="text-mini text-foreground/70 leading-relaxed border-l-2 border-violet-500/40 pl-2">
                          {sig.analysis}
                        </p>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
            }
            </>
            )
          })()}
        </div>
      )}

      {/* ── TAB: Alertas ──────────────────────────────────────────────────────── */}
      {activeTab === 'alerts' && (
        <AlertsTab
          alerts={alerts}
          showAll={showAllAlerts}
          onToggleAll={() => setShowAllAlerts(v => !v)}
        />
      )}

      {/* ── TAB: Calibración ─────────────────────────────────────────────────── */}
      {activeTab === 'calibration' && (
        <div className="space-y-4 animate-fade-in-up">
          {calibration?.narrative && (
            <AiNarrativeCard narrative={calibration.narrative} label="Recomendaciones de auto-mejora" />
          )}
          {(calibration?.recommendations ?? []).length === 0 ? (
            <Card className="glass"><CardContent className="py-12 text-center text-muted-foreground">
              Se necesitan más señales completadas para generar recomendaciones.
            </CardContent></Card>
          ) : (
            <Card className="glass">
              <CardContent className="p-4">
                <div className="space-y-3">
                  {(calibration?.recommendations ?? []).map((rec, i) => (
                    <div key={i} className={`flex items-start gap-3 p-3 rounded-lg border ${
                      rec.type === 'BOOST' ? 'bg-emerald-500/5 border-emerald-500/20' :
                      rec.type === 'REDUCE' ? 'bg-red-500/5 border-red-500/20' :
                      'bg-amber-500/5 border-amber-500/20'
                    }`}>
                      <span className={`text-micro font-bold px-1.5 py-0.5 rounded border shrink-0 mt-0.5 ${
                        rec.type === 'BOOST' ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' :
                        rec.type === 'REDUCE' ? 'bg-red-500/15 text-red-400 border-red-500/30' :
                        'bg-amber-500/15 text-amber-400 border-amber-500/30'
                      }`}>{rec.type}</span>
                      <div>
                        <div className="text-mini font-semibold text-foreground/80 mb-0.5">{rec.factor}</div>
                        <p className="text-mini text-muted-foreground leading-relaxed">{rec.insight}</p>
                        <span className="text-micro text-muted-foreground">n={rec.n} señales</span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
          {loadingCal && <Loading />}
        </div>
      )}

      {/* ── TAB: Agentes IA ───────────────────────────────────────────────────── */}
      {activeTab === 'agents' && (
        <div className="space-y-6 animate-fade-in-up">

          {/* Exit Monitor */}
          <section>
            <div className="flex items-center gap-2 mb-3">
              <TrendingDown size={16} className="text-red-400" />
              <h3 className="text-cuerpo font-bold text-foreground/80">Exit Monitor</h3>
              {exitData && <span className="text-micro text-red-400 bg-red-500/10 border border-red-500/20 px-1.5 py-0.5 rounded font-bold">{exitData.high_count} HIGH · {exitData.total} total</span>}
            </div>
            {exitData?.narrative && <AiNarrativeCard narrative={exitData.narrative} label="" />}
            <div className="space-y-2 mt-2">
              {[...(exitData?.exits ?? [])].sort((a, b) => {
                const aOwned = pSet.has(a.ticker.toUpperCase()) ? -1 : 0
                const bOwned = pSet.has(b.ticker.toUpperCase()) ? -1 : 0
                return aOwned - bOwned
              }).slice(0, 8).map(e => {
                const owned = pSet.has(e.ticker.toUpperCase())
                return (
                <div key={e.ticker} className={`flex items-start gap-3 p-3 rounded-xl border ${owned ? 'border-red-500/40 bg-red-500/8 ring-1 ring-red-500/20' : e.severity === 'HIGH' ? 'border-red-500/25 bg-red-500/5' : 'border-amber-500/20 bg-amber-500/5'}`}>
                  <TickerLogo ticker={e.ticker} size="sm" className="shrink-0 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                      <Link to={`/search?q=${e.ticker}`} className="font-mono font-bold text-primary text-apoyo hover:underline">{e.ticker}</Link>
                      <span className={`text-micro font-bold px-1 py-0.5 rounded border ${e.severity === 'HIGH' ? 'bg-red-500/15 text-red-400 border-red-500/30' : 'bg-amber-500/15 text-amber-400 border-amber-500/30'}`}>{e.severity}</span>
                      {owned && <span className="text-micro font-bold px-1.5 py-0.5 rounded border bg-violet-500/20 text-violet-300 border-violet-500/40">EN CARTERA</span>}
                      {(e as any).ai_validation && (
                        <span className={`text-micro font-bold px-1.5 py-0.5 rounded border ${
                          (e as any).ai_validation.verdict === 'FALSE_POSITIVE' ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' :
                          (e as any).ai_validation.verdict === 'TRUE_POSITIVE'  ? 'bg-red-500/15 text-red-400 border-red-500/30' :
                          'bg-muted/20 text-muted-foreground border-border/30'
                        }`}>
                          <Sparkles size={12} strokeWidth={2.25} className="inline -mt-px mr-1" />{(e as any).ai_validation.verdict === 'FALSE_POSITIVE' ? 'FALSO POSITIVO' : (e as any).ai_validation.verdict === 'TRUE_POSITIVE' ? 'CONFIRMADO' : 'INCIERTO'} {(e as any).ai_validation.confidence}%
                        </span>
                      )}
                      {e.current_score != null && <span className="text-micro text-muted-foreground ml-auto">Score {e.entry_score.toFixed(0)} → {e.current_score.toFixed(0)}</span>}
                    </div>
                    <p className="text-mini text-muted-foreground leading-relaxed">{e.reasons.join(' · ')}</p>
                    {(e as any).ai_validation?.summary && (
                      <p className="text-micro text-muted-foreground mt-1 italic">{(e as any).ai_validation.summary}</p>
                    )}
                  </div>
                </div>
                )
              })}
              {!exitData?.exits?.length && <EmptyState compact title="Sin señales de salida activas" />}
            </div>
          </section>

          {/* Value Trap Detector */}
          <section>
            <div className="flex items-center gap-2 mb-3">
              <AlertOctagon size={16} className="text-amber-400" />
              <h3 className="text-cuerpo font-bold text-foreground/80">Value Trap Detector</h3>
              {trapsData && <span className="text-micro text-amber-400 bg-amber-500/10 border border-amber-500/20 px-1.5 py-0.5 rounded font-bold">{trapsData.high_count} HIGH · {trapsData.total} total</span>}
            </div>
            {trapsData?.narrative && <AiNarrativeCard narrative={trapsData.narrative} label="" />}
            <div className="space-y-2 mt-2">
              {[...(trapsData?.traps ?? [])].sort((a, b) => (pSet.has(a.ticker.toUpperCase()) ? -1 : 1) - (pSet.has(b.ticker.toUpperCase()) ? -1 : 1)).slice(0, 8).map(t => {
                const owned = pSet.has(t.ticker.toUpperCase())
                return (
                <div key={t.ticker} className={`p-3 rounded-xl border ${owned ? 'border-amber-500/40 bg-amber-500/8 ring-1 ring-amber-500/20' : t.severity === 'HIGH' ? 'border-red-500/25 bg-red-500/5' : 'border-amber-500/20 bg-amber-500/5'}`}>
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <TickerLogo ticker={t.ticker} size="sm" className="shrink-0" />
                    <Link to={`/search?q=${t.ticker}`} className="font-mono font-bold text-primary text-apoyo hover:underline">{t.ticker}</Link>
                    <span className="text-micro text-muted-foreground">{t.company_name}</span>
                    {owned && <span className="text-micro font-bold px-1.5 py-0.5 rounded border bg-violet-500/20 text-violet-300 border-violet-500/40">EN CARTERA</span>}
                    <span className="ml-auto text-micro text-amber-400">trampa {t.trap_score}/10</span>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {t.flags.map((f, i) => <span key={i} className="text-micro text-muted-foreground bg-muted/10 border border-border/20 px-1.5 py-0.5 rounded">{f}</span>)}
                  </div>
                </div>
                )
              })}
              {!trapsData?.traps?.length && <EmptyState compact title="Sin value traps detectadas" />}
            </div>
          </section>

          {/* Smart Money */}
          <section>
            <div className="flex items-center gap-2 mb-3">
              <Building2 size={16} className="text-purple-400" />
              <h3 className="text-cuerpo font-bold text-foreground/80">Smart Money Convergence</h3>
              {smData && <span className="text-micro text-purple-400 bg-purple-500/10 border border-purple-500/20 px-1.5 py-0.5 rounded font-bold">{smData.total} señales</span>}
            </div>
            {smData?.narrative && <AiNarrativeCard narrative={smData.narrative} label="" />}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2">
              {(smData?.signals ?? []).slice(0, 8).map(s => (
                <div key={s.ticker} className="flex items-center gap-3 p-3 rounded-xl border border-purple-500/20 bg-purple-500/5">
                  <TickerLogo ticker={s.ticker} size="sm" className="shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <Link to={`/search?q=${s.ticker}`} className="font-mono font-bold text-primary text-apoyo hover:underline">{s.ticker}</Link>
                      {s.in_value && <span className="text-micro bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 px-1 py-0 rounded font-bold">VALUE</span>}
                    </div>
                    <div className="text-micro text-muted-foreground">{s.n_hedge_funds} HF · {s.n_insiders} insiders · conv {s.convergence_score}</div>
                  </div>
                </div>
              ))}
              {!smData?.signals?.length && <div className="col-span-2"><EmptyState compact title="Sin convergencias HF+insiders" /></div>}
            </div>
          </section>

          {/* Insider Clusters */}
          <section>
            <div className="flex items-center gap-2 mb-3">
              <Users size={16} className="text-teal-400" />
              <h3 className="text-cuerpo font-bold text-foreground/80">Insider Sector Clusters</h3>
              {clustersData && <span className="text-micro text-teal-400 bg-teal-500/10 border border-teal-500/20 px-1.5 py-0.5 rounded font-bold">{clustersData.total} clusters</span>}
            </div>
            {clustersData?.narrative && <AiNarrativeCard narrative={clustersData.narrative} label="" />}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2">
              {(clustersData?.clusters ?? []).map(c => (
                <div key={c.sector} className={`p-3 rounded-xl border ${c.signal === 'STRONG' ? 'border-teal-500/30 bg-teal-500/5' : 'border-border/30 bg-muted/5'}`}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-mini font-bold text-foreground/80">{c.sector}</span>
                    <span className={`text-micro font-bold px-1.5 py-0.5 rounded border ${c.signal === 'STRONG' ? 'bg-teal-500/20 text-teal-400 border-teal-500/30' : 'bg-muted/20 text-muted-foreground border-border/30'}`}>{c.signal}</span>
                  </div>
                  <div className="text-micro text-muted-foreground mb-1">{c.ticker_count} empresas · {c.total_purchases} compras · score {c.cluster_score}</div>
                  <div className="flex flex-wrap gap-1">
                    {c.tickers.slice(0, 6).map(t => (
                      <Link key={t} to={`/search?q=${t}`} className="text-micro font-mono text-primary hover:underline bg-muted/15 border border-border/20 px-1 py-0.5 rounded">{t}</Link>
                    ))}
                  </div>
                </div>
              ))}
              {!clustersData?.clusters?.length && <div className="col-span-2"><EmptyState compact title="Sin clusters sectoriales de insiders" /></div>}
            </div>
          </section>

          {/* Dividend Safety */}
          <section>
            <div className="flex items-center gap-2 mb-3">
              <Wallet size={16} className="text-emerald-400" />
              <h3 className="text-cuerpo font-bold text-foreground/80">Dividend Safety Monitor</h3>
              {divData && <span className="text-micro text-red-400 bg-red-500/10 border border-red-500/20 px-1.5 py-0.5 rounded font-bold">{divData.at_risk} AT RISK · {divData.total} total</span>}
            </div>
            {divData?.narrative && <AiNarrativeCard narrative={divData.narrative} label="" />}
            <div className="space-y-2 mt-2">
              {(divData?.dividends ?? []).slice(0, 8).map(d => {
                const ratingStyle = d.rating === 'AT_RISK' ? 'border-red-500/25 bg-red-500/5' : d.rating === 'WATCH' ? 'border-amber-500/20 bg-amber-500/5' : 'border-emerald-500/20 bg-emerald-500/5'
                const ratingBadge = d.rating === 'AT_RISK' ? 'bg-red-500/15 text-red-400 border-red-500/30' : d.rating === 'WATCH' ? 'bg-amber-500/15 text-amber-400 border-amber-500/30' : 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                return (
                  <div key={d.ticker} className={`flex items-start gap-3 p-3 rounded-xl border ${ratingStyle}`}>
                    <TickerLogo ticker={d.ticker} size="sm" className="shrink-0 mt-0.5" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <Link to={`/search?q=${d.ticker}`} className="font-mono font-bold text-primary text-apoyo hover:underline">{d.ticker}</Link>
                        <span className={`text-micro font-bold px-1 py-0.5 rounded border ${ratingBadge}`}>{d.rating}</span>
                        <span className="text-micro text-emerald-400 ml-1">yield {d.div_yield.toFixed(1)}%</span>
                        {d.payout_ratio != null && <span className="text-micro text-muted-foreground">payout {d.payout_ratio.toFixed(0)}%</span>}
                        <span className="text-micro text-muted-foreground ml-auto">safety {d.safety_score}</span>
                      </div>
                      {d.risk_flags.length > 0 && <p className="text-mini text-muted-foreground">{d.risk_flags[0]}</p>}
                    </div>
                  </div>
                )
              })}
              {!divData?.dividends?.length && <EmptyState compact title="Sin tickers con dividendo en VALUE" />}
            </div>
          </section>

          {/* Piotroski Momentum */}
          <section>
            <div className="flex items-center gap-2 mb-3">
              <BarChart2 size={16} className="text-blue-400" />
              <h3 className="text-cuerpo font-bold text-foreground/80">Piotroski Momentum</h3>
              {piotrData && <span className="text-micro text-blue-400 bg-blue-500/10 border border-blue-500/20 px-1.5 py-0.5 rounded font-bold">{piotrData.improving} mejorando · {piotrData.total} analizados</span>}
            </div>
            {piotrData?.narrative && <AiNarrativeCard narrative={piotrData.narrative} label="" />}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2">
              {(piotrData?.candidates ?? []).slice(0, 10).map(c => {
                const trendColor = c.trend === 'IMPROVING' ? 'text-emerald-400' : c.trend === 'SLIGHT_UP' ? 'text-blue-400' : c.trend === 'DETERIORATING' ? 'text-red-400' : c.trend === 'SLIGHT_DOWN' ? 'text-amber-400' : 'text-muted-foreground'
                const trendIcon = c.trend === 'IMPROVING' || c.trend === 'SLIGHT_UP' ? <TrendingUp size={12} /> : c.trend === 'DETERIORATING' || c.trend === 'SLIGHT_DOWN' ? <TrendingDown size={12} /> : <Minus size={12} />
                return (
                  <div key={c.ticker} className="flex items-center gap-3 p-3 rounded-xl border border-border/30 bg-muted/5">
                    <TickerLogo ticker={c.ticker} size="sm" className="shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <Link to={`/search?q=${c.ticker}`} className="font-mono font-bold text-primary text-apoyo hover:underline">{c.ticker}</Link>
                        <span className={`flex items-center gap-0.5 text-micro font-semibold ${trendColor}`}>{trendIcon} {c.trend.replace('_', ' ')}</span>
                      </div>
                      <div className="text-micro text-muted-foreground">
                        F-score: {c.piotroski_prev != null ? `${c.piotroski_prev} → ` : ''}<strong className={c.piotroski_current >= 7 ? 'text-emerald-400' : c.piotroski_current <= 3 ? 'text-red-400' : 'text-foreground'}>{c.piotroski_current}/9</strong>
                        {c.delta !== 0 && <span className={c.delta > 0 ? ' text-emerald-400' : ' text-red-400'}> ({c.delta > 0 ? '+' : ''}{c.delta})</span>}
                      </div>
                    </div>
                  </div>
                )
              })}
              {!piotrData?.candidates?.length && <div className="col-span-2"><EmptyState compact title="Sin datos Piotroski destacables" /></div>}
            </div>
          </section>

          {/* Portfolio Stress Test */}
          <section>
            <div className="flex items-center gap-2 mb-3">
              <Activity size={16} className="text-pink-400" />
              <h3 className="text-cuerpo font-bold text-foreground/80">Portfolio Stress Test</h3>
              {stressData && <span className="text-micro text-muted-foreground bg-muted/15 border border-border/30 px-1.5 py-0.5 rounded font-bold">{stressData.total_positions} posiciones · {stressData.risks.length} riesgos</span>}
            </div>
            {stressData?.narrative && <AiNarrativeCard narrative={stressData.narrative} label="" />}
            <div className="space-y-2 mt-2">
              {(stressData?.risks ?? []).map((r, i) => (
                <div key={i} className={`p-3 rounded-xl border ${r.severity === 'HIGH' ? 'border-red-500/25 bg-red-500/5' : r.severity === 'MEDIUM' ? 'border-amber-500/20 bg-amber-500/5' : 'border-border/30 bg-muted/5'}`}>
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className={`text-micro font-bold px-1 py-0.5 rounded border ${r.severity === 'HIGH' ? 'bg-red-500/15 text-red-400 border-red-500/30' : r.severity === 'MEDIUM' ? 'bg-amber-500/15 text-amber-400 border-amber-500/30' : 'bg-muted/15 text-muted-foreground border-border/30'}`}>{r.severity}</span>
                    <span className="text-micro font-semibold text-foreground/70">{r.type.replace(/_/g, ' ')}</span>
                  </div>
                  <p className="text-mini text-muted-foreground">{r.message}</p>
                </div>
              ))}
              {stressData && (stressData.risks ?? []).length === 0 && (
                <div className="p-4 rounded-xl border border-emerald-500/20 bg-emerald-500/5 text-center text-cuerpo text-emerald-400">
                  Sin riesgos de concentración detectados — cartera bien diversificada
                </div>
              )}
            </div>
            {stressData?.sector_breakdown && stressData.sector_breakdown.length > 0 && (
              <Card className="glass mt-3">
                <CardContent className="p-4">
                  <div className="etiqueta-seccion mb-3">Distribución sectorial (últimas 60 días)</div>
                  <div className="space-y-2">
                    {stressData.sector_breakdown.map(s => (
                      <div key={s.sector} className="flex items-center gap-2">
                        <span className="text-mini text-muted-foreground w-36 truncate">{s.sector}</span>
                        <div className="flex-1 h-1.5 rounded-full barra-pista overflow-hidden">
                          <div className="h-full rounded-full bg-primary/50" style={{ width: `${s.pct}%` }} />
                        </div>
                        <span className="text-micro text-muted-foreground w-10 text-right tabular-nums">{s.pct}%</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </section>

          {/* Short Squeeze Detector */}
          <section>
            <div className="flex items-center gap-2 mb-3">
              <Zap size={16} className="text-cyan-400" />
              <h3 className="text-cuerpo font-bold text-foreground/80">Short Squeeze Detector</h3>
              {squeezeData && <span className="text-micro text-cyan-400 bg-cyan-500/10 border border-cyan-500/20 px-1.5 py-0.5 rounded font-bold">{squeezeData.high_count} HIGH · {squeezeData.total} total</span>}
            </div>
            {squeezeData?.narrative && <AiNarrativeCard narrative={squeezeData.narrative} label="" />}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2">
              {((squeezeData as { setups?: ShortSqueezeSetup[] } | null)?.setups ?? []).slice(0, 8).map((s: ShortSqueezeSetup) => (
                <div key={s.ticker} className={`p-3 rounded-xl border ${s.severity === 'HIGH' ? 'border-cyan-500/30 bg-cyan-500/5' : 'border-border/30 bg-muted/5'}`}>
                  <div className="flex items-center gap-2 mb-1">
                    <TickerLogo ticker={s.ticker} size="sm" className="shrink-0" />
                    <Link to={`/search?q=${s.ticker}`} className="font-mono font-bold text-primary text-apoyo hover:underline">{s.ticker}</Link>
                    <span className={`text-micro font-bold px-1 py-0.5 rounded border ${s.severity === 'HIGH' ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40' : 'bg-muted/20 text-muted-foreground border-border/30'}`}>{s.severity}</span>
                    <span className="text-micro text-muted-foreground ml-auto">squeeze {s.squeeze_score}/10</span>
                  </div>
                  <div className="text-micro text-muted-foreground mb-1">
                    {s.short_pct_float.toFixed(1)}% short float
                    {s.insider_buying && <span className="ml-1.5 text-teal-400">· insiders comprando</span>}
                    {s.hf_present && <span className="ml-1.5 text-purple-400">· HF presente</span>}
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {s.flags.map((f, i) => <span key={i} className="text-micro text-muted-foreground bg-muted/10 border border-border/20 px-1.5 py-0.5 rounded">{f}</span>)}
                  </div>
                </div>
              ))}
              {!(squeezeData as { setups?: ShortSqueezeSetup[] } | null)?.setups?.length && (
                <div className="col-span-2"><EmptyState compact title="Sin short squeeze setups detectados" /></div>
              )}
            </div>
          </section>

          {/* Quality Decay Monitor */}
          <section>
            <div className="flex items-center gap-2 mb-3">
              <TrendingDown size={16} className="text-orange-400" />
              <h3 className="text-cuerpo font-bold text-foreground/80">Quality Decay Monitor</h3>
              {decayData && <span className="text-micro text-orange-400 bg-orange-500/10 border border-orange-500/20 px-1.5 py-0.5 rounded font-bold">{decayData.high_count} HIGH · {decayData.total} total</span>}
            </div>
            {decayData?.narrative && <AiNarrativeCard narrative={decayData.narrative} label="" />}
            <div className="space-y-2 mt-2">
              {((decayData as { decays?: QualityDecay[] } | null)?.decays ?? []).slice(0, 8).map((d: QualityDecay) => (
                <div key={d.ticker} className={`p-3 rounded-xl border ${d.severity === 'HIGH' ? 'border-orange-500/25 bg-orange-500/5' : 'border-amber-500/15 bg-amber-500/5'}`}>
                  <div className="flex items-center gap-2 mb-1">
                    <TickerLogo ticker={d.ticker} size="sm" className="shrink-0" />
                    <Link to={`/search?q=${d.ticker}`} className="font-mono font-bold text-primary text-apoyo hover:underline">{d.ticker}</Link>
                    <span className="text-micro text-muted-foreground">{d.company_name}</span>
                    <span className={`text-micro font-bold px-1 py-0.5 rounded border ml-auto ${d.severity === 'HIGH' ? 'bg-orange-500/20 text-orange-400 border-orange-500/30' : 'bg-amber-500/15 text-amber-400 border-amber-500/25'}`}>{d.severity}</span>
                    <span className="text-micro text-muted-foreground">decay {d.decay_score}/10</span>
                  </div>
                  {d.margin_prev != null && d.margin_curr != null && (
                    <div className="text-micro text-muted-foreground mb-1">
                      Margen: <span className="text-red-400">{d.margin_prev.toFixed(1)}% → {d.margin_curr.toFixed(1)}%</span>
                      {d.fcf_prev != null && d.fcf_curr != null && (
                        <span className="ml-2">FCF: <span className="text-red-400">{d.fcf_prev.toFixed(0)}M → {d.fcf_curr.toFixed(0)}M</span></span>
                      )}
                    </div>
                  )}
                  <div className="flex flex-wrap gap-1">
                    {d.flags.map((f, i) => <span key={i} className="text-micro text-muted-foreground bg-muted/10 border border-border/20 px-1.5 py-0.5 rounded">{f}</span>)}
                  </div>
                </div>
              ))}
              {!(decayData as { decays?: QualityDecay[] } | null)?.decays?.length && (
                <EmptyState compact title="Sin señales de deterioro detectadas" />
              )}
            </div>
          </section>

        </div>
      )}

      {/* ── TAB: Thesis Drift ──────────────────────────────────────────────────── */}
      {activeTab === 'thesis' && (
        <Suspense fallback={<Loading />}>
          <ThesisDriftTab />
        </Suspense>
      )}

      {/* ── TAB: Contrarian Discovery ─────────────────────────────────────────── */}
      {activeTab === 'contrarian' && (
        <Suspense fallback={<Loading />}>
          <ContrarianDiscovery />
        </Suspense>
      )}

      {activeTab === 'novedades' && (
        <div className="px-1 py-2">
          <ScoreAlerts />
        </div>
      )}
    </>
  )
}
