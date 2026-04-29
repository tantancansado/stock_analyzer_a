import { useMemo, useState } from 'react'
import { useApi } from '../hooks/useApi'
import { fetchValueOpportunities, fetchEUValueOpportunities, type ValueOpportunity } from '../api/client'
import Loading from '../components/Loading'
import ScoreBar from '../components/ScoreBar'
import GradeBadge from '../components/GradeBadge'
import TickerLogo from '../components/TickerLogo'
import InfoTooltip from '../components/InfoTooltip'
import { Card } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

// ── Catalyst definitions ──────────────────────────────────────────────────────

interface Catalyst {
  id: string
  icon: string
  label: string
  description: string
  color: string        // tailwind color key (emerald, amber, violet, blue, cyan, rose)
  match: (d: ValueOpportunity) => boolean
}

const CATALYSTS: Catalyst[] = [
  {
    id: 'earnings_catalyst',
    icon: '📅',
    label: 'Earnings próximo',
    description: 'Resultados en 8-30 días — ventana de expansión de múltiplo si EPS supera expectativas. No en los próximos 7d (riesgo de gap).',
    color: 'amber',
    match: d =>
      d.days_to_earnings != null &&
      d.days_to_earnings >= 8 &&
      d.days_to_earnings <= 30 &&
      !d.earnings_warning,
  },
  {
    id: 'eps_accel',
    icon: '📈',
    label: 'EPS acelerando',
    description: 'Beneficio por acción creciendo más rápido que el trimestre anterior — señal de momentum fundamental.',
    color: 'emerald',
    match: d => d.eps_accelerating === true,
  },
  {
    id: 'analyst_upgrade',
    icon: '⬆️',
    label: 'Upgrade reciente',
    description: 'Analista ha subido recomendación en los últimos 14 días — catalizador externo de visibilidad.',
    color: 'blue',
    match: d => (d.upgrade_days_14d ?? 99) < 14 && (d.upgrade_days_14d ?? 99) >= 0,
  },
  {
    id: 'target_raised',
    icon: '🎯',
    label: 'Precio objetivo subido',
    description: 'Precio objetivo de consenso subido ≥3% en los últimos 7 días — revisión al alza de estimaciones.',
    color: 'cyan',
    match: d => (d.target_change_7d_pct ?? 0) >= 3,
  },
  {
    id: 'buyback',
    icon: '🔁',
    label: 'Recompra activa',
    description: 'La empresa está recomprando acciones propias — señal de que directivos creen que cotizan barato.',
    color: 'violet',
    match: d => d.buyback_active === true,
  },
  {
    id: 'fcf_strong',
    icon: '💰',
    label: 'FCF ≥5%',
    description: 'FCF Yield ≥5% — la empresa genera cash real respecto a su valor de mercado. Buen colchón.',
    color: 'emerald',
    match: d => (d.fcf_yield_pct ?? 0) >= 5,
  },
  {
    id: 'piotroski',
    icon: '🏆',
    label: 'Piotroski F≥7',
    description: 'F-Score ≥7 sobre 9 — salud financiera excelente según los 9 criterios de Piotroski.',
    color: 'emerald',
    match: d => (d.piotroski_score ?? 0) >= 7,
  },
  {
    id: 'rr_strong',
    icon: '⚖️',
    label: 'R:R ≥3',
    description: 'Risk:Reward ≥3 con stop loss del 8% — upside de analistas justifica ampliamente el riesgo.',
    color: 'amber',
    match: d => (d.risk_reward_ratio ?? 0) >= 3,
  },
]

// ── Predefined combo setups ───────────────────────────────────────────────────

interface Setup {
  id: string
  label: string
  subtitle: string
  catalysts: string[]   // IDs of required catalysts
  badge: string
  badgeColor: string
}

const SETUPS: Setup[] = [
  {
    id: 'pre_earnings_value',
    label: 'Pre-Earnings VALUE',
    subtitle: 'Earnings en 8-30d + EPS acelerando + R:R≥3',
    catalysts: ['earnings_catalyst', 'eps_accel', 'rr_strong'],
    badge: '🔥 Timing',
    badgeColor: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  },
  {
    id: 'analyst_conviction',
    label: 'Convicción Analistas',
    subtitle: 'Upgrade reciente + precio objetivo subido + FCF≥5%',
    catalysts: ['analyst_upgrade', 'target_raised', 'fcf_strong'],
    badge: '📊 Externo',
    badgeColor: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
  },
  {
    id: 'quality_compounding',
    label: 'Compounder de Calidad',
    subtitle: 'FCF≥5% + Recompra activa + Piotroski F≥7',
    catalysts: ['fcf_strong', 'buyback', 'piotroski'],
    badge: '💎 Calidad',
    badgeColor: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  },
  {
    id: 'triple_confluence',
    label: 'Triple Confluencia',
    subtitle: 'EPS acelerando + Recompra + R:R≥3',
    catalysts: ['eps_accel', 'buyback', 'rr_strong'],
    badge: '⚡ Alto',
    badgeColor: 'bg-violet-500/15 text-violet-400 border-violet-500/30',
  },
]

// ── Color helpers ─────────────────────────────────────────────────────────────

const COLOR_MAP: Record<string, string> = {
  emerald: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  amber:   'bg-amber-500/15 text-amber-400 border-amber-500/30',
  blue:    'bg-blue-500/15 text-blue-400 border-blue-500/30',
  cyan:    'bg-cyan-500/15 text-cyan-400 border-cyan-500/30',
  violet:  'bg-violet-500/15 text-violet-400 border-violet-500/30',
  rose:    'bg-rose-500/15 text-rose-400 border-rose-500/30',
}

function CatalystTag({ c }: { c: Catalyst }) {
  const cls = COLOR_MAP[c.color] ?? 'bg-muted/20 text-muted-foreground border-border/30'
  return (
    <span
      className={`inline-flex items-center gap-1 text-[0.6rem] font-bold px-1.5 py-0.5 rounded border tracking-wide ${cls}`}
      title={c.description}
    >
      {c.icon} {c.label}
    </span>
  )
}

// ── Main component ─────────────────────────────────────────────────────────────

export default function CatalystScreener() {
  const { data: usData, loading: usLoading } = useApi(() => fetchValueOpportunities(), [])
  const { data: euData, loading: euLoading } = useApi(() => fetchEUValueOpportunities(), [])
  const [activeSetup, setActiveSetup] = useState<string>(SETUPS[0].id)

  const allRows = useMemo(() => {
    const us = usData?.data ?? []
    const eu = euData?.data ?? []
    const combined = [...us, ...eu]
    // dedupe by ticker, keep highest value_score
    const map = new Map<string, ValueOpportunity>()
    for (const d of combined) {
      const t = d.ticker?.toUpperCase() ?? ''
      const prev = map.get(t)
      if (!prev || (d.value_score ?? 0) > (prev.value_score ?? 0)) map.set(t, d)
    }
    return Array.from(map.values())
  }, [usData, euData])

  const setup = SETUPS.find(s => s.id === activeSetup) ?? SETUPS[0]

  // Resolve catalyst objects for the active setup
  const activeCatalysts = setup.catalysts.map(id => CATALYSTS.find(c => c.id === id)!).filter(Boolean)

  // Filter rows: must match ALL catalysts in the setup
  const results = useMemo(() =>
    allRows
      .filter(d => activeCatalysts.every(c => c.match(d)))
      .sort((a, b) => (b.value_score ?? 0) - (a.value_score ?? 0)),
    [allRows, activeCatalysts]
  )

  // Per-catalyst counts (from all rows, for the badges on setup cards)
  const catalystCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const c of CATALYSTS) counts[c.id] = allRows.filter(c.match).length
    return counts
  }, [allRows])

  const setupCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const s of SETUPS) {
      const cats = s.catalysts.map(id => CATALYSTS.find(c => c.id === id)!).filter(Boolean)
      counts[s.id] = allRows.filter(d => cats.every(c => c.match(d))).length
    }
    return counts
  }, [allRows])

  const loading = usLoading && euLoading

  return (
    <div className="space-y-6">

      {/* Setup selector cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {SETUPS.map(s => {
          const count = setupCounts[s.id] ?? 0
          const active = s.id === activeSetup
          return (
            <button
              key={s.id}
              onClick={() => setActiveSetup(s.id)}
              className={`text-left p-3 rounded-xl border transition-all ${
                active
                  ? 'border-primary/50 bg-primary/8 shadow-sm shadow-primary/10'
                  : 'border-border/40 bg-card/50 hover:border-border/70 hover:bg-card/80'
              }`}
            >
              <div className="flex items-start justify-between gap-2 mb-1.5">
                <span className={`text-[0.6rem] font-bold px-1.5 py-0.5 rounded border tracking-wide ${s.badgeColor}`}>
                  {s.badge}
                </span>
                <span className={`text-lg font-bold tabular-nums ${count === 0 ? 'text-muted-foreground/30' : active ? 'text-primary' : 'text-foreground'}`}>
                  {count}
                </span>
              </div>
              <p className={`text-[0.78rem] font-semibold leading-tight ${active ? 'text-foreground' : 'text-muted-foreground'}`}>
                {s.label}
              </p>
              <p className="text-[0.65rem] text-muted-foreground/60 mt-0.5 leading-snug">{s.subtitle}</p>
            </button>
          )
        })}
      </div>

      {/* Active setup: catalyst legend */}
      <div className="flex flex-wrap gap-2 items-center">
        <span className="text-[0.72rem] text-muted-foreground/50 font-medium uppercase tracking-wider">Filtros activos:</span>
        {activeCatalysts.map(c => (
          <div key={c.id} className="flex items-center gap-1.5">
            <CatalystTag c={c} />
            <span className="text-[0.65rem] text-muted-foreground/40">
              ({catalystCounts[c.id] ?? 0} tickers)
            </span>
          </div>
        ))}
      </div>

      {/* Results table */}
      {loading ? <Loading /> : results.length === 0 ? (
        <Card className="py-16 text-center">
          <p className="text-4xl mb-3 opacity-20">🔍</p>
          <p className="text-sm text-muted-foreground">Ningún ticker cumple todos los catalizadores ahora mismo</p>
          <p className="text-xs text-muted-foreground/50 mt-1">Prueba otro setup o vuelve cuando el pipeline actualice</p>
        </Card>
      ) : (
        <div className="rounded-xl border border-border/40 overflow-clip">
          <Table>
            <TableHeader>
              <TableRow className="border-border/40">
                <TableHead>Ticker</TableHead>
                <TableHead className="hidden sm:table-cell">Empresa</TableHead>
                <TableHead>Score</TableHead>
                <TableHead className="hidden sm:table-cell">Grade</TableHead>
                <TableHead>Catalizadores</TableHead>
                <TableHead className="hidden md:table-cell">
                  Objetivo
                  <InfoTooltip text="Upside analistas" />
                </TableHead>
                <TableHead className="hidden md:table-cell">
                  FCF%
                  <InfoTooltip text="FCF Yield" />
                </TableHead>
                <TableHead className="hidden lg:table-cell">
                  R:R
                  <InfoTooltip text="Risk:Reward = upside / 8% stop" />
                </TableHead>
                <TableHead className="hidden lg:table-cell">Earn</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {results.map(d => {
                // Which catalysts from the FULL list does this ticker have?
                const matchedCats = CATALYSTS.filter(c => c.match(d))
                return (
                  <TableRow key={d.ticker} className="border-border/30">
                    <TableCell className="font-mono font-bold text-primary text-[0.8rem]">
                      <div className="flex items-center gap-2">
                        <TickerLogo ticker={d.ticker} size="sm" />
                        {d.ticker}
                      </div>
                    </TableCell>
                    <TableCell className="hidden sm:table-cell text-[0.76rem] text-muted-foreground max-w-[160px] truncate">
                      {d.company_name}
                    </TableCell>
                    <TableCell><ScoreBar score={d.value_score} /></TableCell>
                    <TableCell className="hidden sm:table-cell">
                      <GradeBadge grade={d.conviction_grade} score={d.conviction_score} />
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {matchedCats.map(c => <CatalystTag key={c.id} c={c} />)}
                      </div>
                    </TableCell>
                    <TableCell className="hidden md:table-cell tabular-nums text-sm">
                      {d.analyst_upside_pct != null && (
                        <span className={d.analyst_upside_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}>
                          {d.analyst_upside_pct > 0 ? '+' : ''}{d.analyst_upside_pct.toFixed(0)}%
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="hidden md:table-cell tabular-nums text-sm">
                      {d.fcf_yield_pct != null ? (
                        <span className={d.fcf_yield_pct >= 5 ? 'text-emerald-400' : d.fcf_yield_pct >= 3 ? 'text-amber-400' : d.fcf_yield_pct < 0 ? 'text-red-400' : ''}>
                          {d.fcf_yield_pct.toFixed(1)}%
                        </span>
                      ) : '—'}
                    </TableCell>
                    <TableCell className="hidden lg:table-cell tabular-nums text-sm">
                      {d.risk_reward_ratio != null ? (
                        <span className={d.risk_reward_ratio >= 3 ? 'text-emerald-400' : d.risk_reward_ratio >= 2 ? 'text-amber-400' : 'text-red-400'}>
                          {d.risk_reward_ratio.toFixed(1)}x
                        </span>
                      ) : '—'}
                    </TableCell>
                    <TableCell className="hidden lg:table-cell tabular-nums text-[0.76rem]">
                      {d.days_to_earnings != null ? (
                        <span className={
                          d.days_to_earnings <= 7 ? 'text-red-400' :
                          d.days_to_earnings <= 21 ? 'text-amber-400' : 'text-emerald-400'
                        }>
                          {d.days_to_earnings}d
                        </span>
                      ) : '—'}
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}
