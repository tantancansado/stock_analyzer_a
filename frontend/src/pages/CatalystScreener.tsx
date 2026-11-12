import { useMemo, useState } from 'react'
import type { LucideIcon } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { fetchValueOpportunities, type ValueOpportunity } from '../api/client'
import Loading from '../components/Loading'
import { useNavigate } from 'react-router-dom'
import { ValueDecisionBadge } from '../components/ValueDecision'
import { getValueDecision } from '../lib/valueDecision'
import { BotonMasDatos, useMasDatos } from '../components/MasDatos'
import TickerLogo from '../components/TickerLogo'
import InfoTooltip from '../components/InfoTooltip'
import { Card } from '@/components/ui/card'
import EmptyState from '../components/EmptyState'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { ArrowUpCircle, BarChart3, CalendarDays, Coins, Flame, Gem, RefreshCw, SearchX, Target, TrendingUp, Trophy, Zap } from 'lucide-react'

// ── Catalyst definitions ──────────────────────────────────────────────────────

interface Catalyst {
  id: string
  icon: LucideIcon
  label: string
  /** Lo que se lee en la vista sencilla, sin jerga. */
  llano: (d: ValueOpportunity) => string
  description: string
  color: string        // tailwind color key (emerald, amber, violet, blue, cyan, rose)
  match: (d: ValueOpportunity) => boolean
}

export const CATALYSTS: Catalyst[] = [
  {
    id: 'earnings_catalyst',
    icon: CalendarDays,
    label: 'Earnings próximo',
    llano: d => `resultados en ${d.days_to_earnings} días`,
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
    icon: TrendingUp,
    label: 'EPS acelerando',
    llano: () => 'beneficio acelerando',
    description: 'Beneficio por acción creciendo más rápido que el trimestre anterior — señal de momentum fundamental.',
    color: 'emerald',
    match: d => d.eps_accelerating === true,
  },
  {
    id: 'analyst_upgrade',
    icon: ArrowUpCircle,
    label: 'Upgrade reciente',
    llano: () => 'un analista ha mejorado su recomendación',
    description: 'Analista ha subido recomendación en los últimos 14 días — catalizador externo de visibilidad.',
    color: 'blue',
    match: d => (d.upgrade_days_14d ?? 99) < 14 && (d.upgrade_days_14d ?? 99) >= 0,
  },
  {
    id: 'target_raised',
    icon: Target,
    label: 'Precio objetivo subido',
    llano: d => `los analistas suben su objetivo un ${Math.round(d.target_change_7d_pct ?? 0)}\u00A0%`,
    description: 'Precio objetivo de consenso subido ≥3% en los últimos 7 días — revisión al alza de estimaciones.',
    color: 'cyan',
    match: d => (d.target_change_7d_pct ?? 0) >= 3,
  },
  {
    id: 'buyback',
    icon: RefreshCw,
    label: 'Recompra activa',
    llano: () => 'recompra acciones',
    description: 'La empresa está recomprando acciones propias — señal de que directivos creen que cotizan barato.',
    color: 'violet',
    match: d => d.buyback_active === true,
  },
  {
    id: 'fcf_strong',
    icon: Coins,
    label: 'FCF ≥5%',
    llano: d => `genera caja: ${(d.fcf_yield_pct ?? 0).toFixed(1).replace('.', ',')}\u00A0% al año sobre lo que vale`,
    description: 'FCF Yield ≥5% — la empresa genera cash real respecto a su valor de mercado. Buen colchón.',
    color: 'emerald',
    match: d => (d.fcf_yield_pct ?? 0) >= 5,
  },
  {
    id: 'piotroski',
    icon: Trophy,
    label: 'Piotroski F≥7',
    llano: () => 'cuentas sanas',
    description: 'F-Score ≥7 sobre 9 — salud financiera excelente según los 9 criterios de Piotroski.',
    color: 'emerald',
    match: d => (d.piotroski_score ?? 0) >= 7,
  },
]

// ── Predefined combo setups ───────────────────────────────────────────────────

interface Setup {
  id: string
  label: string
  subtitle: string
  catalysts: string[]   // IDs of required catalysts
  badge: string
  badgeIcon: LucideIcon
  badgeColor: string
}

// Dos combinaciones pedían `rr_strong`, que se renombró a `upside_dorado`: el
// `find(...)!` daba undefined, el `filter(Boolean)` lo quitaba y filtraban con dos
// condiciones diciendo tres («+ R:R≥3»). Ahora cada una dice lo que filtra, y un
// test comprueba que todo id existe. La banda del analista ya no puntúa en Value US.
export const SETUPS: Setup[] = [
  {
    id: 'pre_earnings_value',
    label: 'Resultados pronto y beneficio acelerando',
    subtitle: 'Resultados en 8-30 días + BPA acelerando',
    catalysts: ['earnings_catalyst', 'eps_accel'],
    badge: 'Timing',
    badgeIcon: Flame,
    badgeColor: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  },
  {
    id: 'analyst_conviction',
    label: 'Los analistas la están mejorando',
    subtitle: 'Mejora de recomendación (14 d) + objetivo subido ≥3 % (7 d) + caja libre ≥5 %',
    catalysts: ['analyst_upgrade', 'target_raised', 'fcf_strong'],
    badge: 'Externo',
    badgeIcon: BarChart3,
    badgeColor: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
  },
  {
    id: 'quality_compounding',
    label: 'Calidad que recompra acciones',
    subtitle: 'Caja libre ≥5 % + recompra activa + Piotroski ≥7',
    catalysts: ['fcf_strong', 'buyback', 'piotroski'],
    badge: 'Calidad',
    badgeIcon: Gem,
    badgeColor: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  },
  {
    id: 'triple_confluence',
    label: 'Beneficio acelerando y recompras',
    subtitle: 'BPA acelerando + recompra activa',
    catalysts: ['eps_accel', 'buyback'],
    badge: 'Alto',
    badgeIcon: Zap,
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
      className={`inline-flex items-center gap-1 text-micro font-bold px-1.5 py-0.5 rounded border tracking-wide ${cls}`}
      title={c.description}
    >
      <c.icon size={12} strokeWidth={2} className="shrink-0" />
      {c.label}
    </span>
  )
}

// ── Main component ─────────────────────────────────────────────────────────────

/** Vista sencilla (12-nov-2026): qué empresas de la lista cumplen la combinación, su
 *  grupo de Value y sus catalizadores en una línea. La avanzada añade los números. */
export default function CatalystScreener() {
  const navigate = useNavigate()
  const { data: usData, loading } = useApi(() => fetchValueOpportunities(), [])
  const [activeSetup, setActiveSetup] = useState<string>(SETUPS[0].id)
  const [avanzada, alternar] = useMasDatos('catalizadores')

  const allRows = useMemo(() => usData?.data ?? [], [usData])
  const setup = SETUPS.find(s => s.id === activeSetup) ?? SETUPS[0]
  const activeCatalysts = setup.catalysts.map(id => CATALYSTS.find(c => c.id === id)).filter((c): c is Catalyst => !!c)

  const results = useMemo(() =>
    allRows
      .filter(d => activeCatalysts.every(c => c.match(d)))
      .sort((a, b) => (b.value_score ?? 0) - (a.value_score ?? 0)),
    [allRows, activeCatalysts]
  )

  const setupCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const s of SETUPS) {
      const cats = s.catalysts.map(id => CATALYSTS.find(c => c.id === id)).filter((c): c is Catalyst => !!c)
      counts[s.id] = allRows.filter(d => cats.every(c => c.match(d))).length
    }
    return counts
  }, [allRows])

  const abrir = (t: string) => navigate(`/search?q=${encodeURIComponent(t)}`)

  return (
    <div className="space-y-5">
      <h1 className="sr-only">Catalizadores</h1>

      <p className="text-apoyo text-muted-foreground">
        Empresas de la lista de Value con algo que puede moverlas pronto. Elige qué buscar:
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
        {SETUPS.map(s => {
          const count = setupCounts[s.id] ?? 0
          const active = s.id === activeSetup
          return (
            <button
              key={s.id}
              onClick={() => setActiveSetup(s.id)}
              aria-pressed={active}
              className={`text-left px-3 py-2.5 rounded-xl border transition-all flex items-center justify-between gap-3 ${
                active ? 'border-primary/50 bg-primary/10' : 'border-border/40 bg-card/50 hover:border-border/70'
              }`}
            >
              <span className="min-w-0">
                <span className={`block text-apoyo font-semibold leading-tight ${active ? 'text-foreground' : 'text-muted-foreground'}`}>{s.label}</span>
                {avanzada && <span className="block text-micro text-muted-foreground mt-0.5">{s.subtitle}</span>}
              </span>
              <span className={`text-seccion font-bold tabular-nums shrink-0 ${count === 0 ? 'text-muted-foreground' : active ? 'text-primary' : 'text-foreground'}`}>{count}</span>
            </button>
          )
        })}
      </div>

      <div className="flex justify-end">
        <BotonMasDatos activo={avanzada} onClick={alternar} />
      </div>

      {loading ? <Loading /> : results.length === 0 ? (
        <Card>
          <EmptyState
            compact
            icon={<SearchX size={32} strokeWidth={1.5} />}
            title="Hoy ninguna empresa lo cumple"
            subtitle="Prueba otra opción o vuelve mañana"
          />
        </Card>
      ) : !avanzada ? (
        <div className="space-y-2">
          {results.map(d => {
            const decision = getValueDecision({ row: d })
            const pot = d.upside_triangulated_pct ?? d.analyst_upside_pct
            const porque = CATALYSTS.filter(c => c.match(d)).map(c => c.llano(d)).join(' · ')
            return (
              <button
                key={d.ticker}
                type="button"
                data-fila-catalizador={d.ticker}
                onClick={() => abrir(d.ticker)}
                className="w-full text-left flex items-start gap-3 rounded-xl px-3 py-3 glass border border-border/30 hover:border-border/60 transition-colors"
              >
                <TickerLogo ticker={d.ticker} size="sm" className="mt-0.5 shrink-0" />
                <span className="min-w-0 flex-1">
                  <span className="flex flex-wrap items-center gap-2">
                    <span className="font-mono font-bold text-primary">{d.ticker}</span>
                    {d.value_grupo && <ValueDecisionBadge decision={decision} />}
                    <span className="text-mini text-muted-foreground truncate">{d.company_name}</span>
                  </span>
                  <span className="block text-apoyo text-foreground/90 mt-1">{porque.charAt(0).toUpperCase() + porque.slice(1)}.</span>
                </span>
                {pot != null && (
                  <span className={`shrink-0 text-cuerpo font-bold tabular-nums ${pot >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {pot >= 0 ? '+' : ''}{pot.toFixed(0)}%
                  </span>
                )}
              </button>
            )
          })}
        </div>
      ) : (
        <div className="rounded-xl border border-border/40 overflow-clip">
          <div className="table-x-wrap">
          <Table>
            <TableHeader>
              <TableRow className="border-border/40">
                <TableHead>Ticker</TableHead>
                <TableHead>Grupo</TableHead>
                <TableHead>Catalizadores</TableHead>
                <TableHead>Nota</TableHead>
                <TableHead>
                  Potencial
                  <InfoTooltip text="Nuestras valoraciones (DCF y P/E propios) junto al consenso" />
                </TableHead>
                <TableHead>Caja libre</TableHead>
                <TableHead>Resultados</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {results.map(d => {
                const pot = d.upside_triangulated_pct ?? d.analyst_upside_pct
                return (
                  <TableRow key={d.ticker} data-fila-catalizador={d.ticker} className="border-border/30 cursor-pointer" onClick={() => abrir(d.ticker)}>
                    <TableCell className="font-mono font-bold text-primary text-apoyo">
                      <div className="flex items-center gap-2">
                        <TickerLogo ticker={d.ticker} size="sm" />
                        <span>{d.ticker}<span className="block font-sans font-normal text-mini text-muted-foreground max-w-[160px] truncate">{d.company_name}</span></span>
                      </div>
                    </TableCell>
                    <TableCell>{d.value_grupo && <ValueDecisionBadge decision={getValueDecision({ row: d })} />}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {CATALYSTS.filter(c => c.match(d)).map(c => <CatalystTag key={c.id} c={c} />)}
                      </div>
                    </TableCell>
                    <TableCell className="tabular-nums text-muted-foreground">{d.value_score?.toFixed(0) ?? '—'}</TableCell>
                    <TableCell className="tabular-nums">
                      {pot != null ? <span className={pot >= 0 ? 'text-emerald-400' : 'text-red-400'}>{pot >= 0 ? '+' : ''}{pot.toFixed(0)}%</span> : '—'}
                    </TableCell>
                    <TableCell className="tabular-nums text-muted-foreground">{d.fcf_yield_pct != null ? `${d.fcf_yield_pct.toFixed(1)}%` : '—'}</TableCell>
                    <TableCell className="tabular-nums text-muted-foreground">{d.days_to_earnings != null && d.days_to_earnings >= 0 ? `${d.days_to_earnings} d` : '—'}</TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
          </div>
        </div>
      )}
    </div>
  )
}
