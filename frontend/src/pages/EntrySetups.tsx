import { lazy } from 'react'
import PageTabs from '../components/PageTabs'
import BroadBounceView from './BroadBounceView'
import CatalystScreener from './CatalystScreener'
import { usePipelineHealth } from '../components/StaleDataBanner'
import { CheckCircle2, AlertTriangle, AlertCircle, ChevronDown } from 'lucide-react'

const MeanReversion = lazy(() => import('./MeanReversion'))
const Momentum      = lazy(() => import('./Momentum'))

const MODULES = [
  { id: 'catalysts',      label: 'Catalizadores' },
  { id: 'mean_reversion', label: 'Mean Reversion' },
  { id: 'technical',      label: 'Momentum VCP' },
  { id: 'bounce_broad',   label: 'Universo Ampliado' },
] as const

const ACTIONS_URL = 'https://github.com/tantancansado/stock_analyzer_a/actions/workflows/daily-analysis.yml'

function EntrySetupsFreshness() {
  const health = usePipelineHealth()
  if (!health) return null

  const today = new Date().toISOString().slice(0, 10)
  const pipelineRanToday = health.pipeline_date === today

  const statuses = MODULES.map(m => {
    const mod = health.modules[m.id]
    const isOk = mod?.status === 'ok'
    const isToday = mod?.date === today
    return { ...m, mod, isOk, isToday, daysAgo: mod?.days_ago ?? null }
  })

  const allOk    = statuses.every(s => s.isOk && s.isToday)
  const anyStale = statuses.some(s => !s.isOk || !s.isToday)
  const noneRan  = !pipelineRanToday && statuses.every(s => !s.isOk)

  if (allOk) {
    return (
      <div className="inline-flex items-center gap-2 text-[0.7rem] font-medium mb-4 px-3 py-1.5 rounded-lg border bg-emerald-500/8 border-emerald-500/20 text-emerald-400/80">
        <CheckCircle2 size={16} className="text-emerald-400" />
        <span className="font-semibold text-emerald-400">Todos los módulos actualizados hoy</span>
      </div>
    )
  }

  const nStale = statuses.filter(s => !s.isOk || !s.isToday).length

  // Las pastillas de módulo van en flex-wrap: a 390px se apilan en cuatro
  // filas y el aviso se comía 177px ANTES del primer setup — un tercio de la
  // pantalla para una advertencia. El titular dice lo que hay que saber y el
  // detalle (qué módulo concreto) queda a un toque, que es donde importa: al
  // decidir si fiarse de una sección.
  return (
    <details className={`group rounded-xl border px-4 py-3 mb-4 ${noneRan ? 'bg-red-500/8 border-red-500/25' : 'bg-amber-500/8 border-amber-500/25'}`}>
      <summary className="flex cursor-pointer list-none items-center gap-3 marker:hidden">
        {noneRan
          ? <AlertCircle size={16} className="text-red-400 shrink-0" />
          : <AlertTriangle size={16} className="text-amber-400 shrink-0" />}
        <span className={`min-w-0 flex-1 text-xs font-bold ${noneRan ? 'text-red-400' : 'text-amber-400'}`}>
          {noneRan
            ? 'Pipeline no ejecutado hoy — datos desactualizados'
            : `${nStale} de ${statuses.length} módulos sin actualizar hoy`}
        </span>
        {anyStale && (
          <a href={ACTIONS_URL} target="_blank" rel="noopener noreferrer"
            onClick={e => e.stopPropagation()}
            className="shrink-0 text-[0.65rem] font-bold px-2.5 py-1 rounded-lg border bg-amber-500/10 border-amber-500/25 text-amber-400 hover:bg-amber-500/20 transition-colors">
            Ver pipeline →
          </a>
        )}
        <ChevronDown size={12} className="shrink-0 text-muted-foreground transition-transform group-open:rotate-180" />
      </summary>
      <div className="mt-3">
        <div className="flex flex-wrap gap-2">
          {statuses.map(s => (
            <div key={s.id} className={`flex items-center gap-1.5 px-2 py-1 rounded-lg border text-[0.68rem] font-medium ${
              s.isOk && s.isToday
                ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                : s.isOk
                ? 'bg-amber-500/10 border-amber-500/20 text-amber-400'
                : 'bg-red-500/10 border-red-500/20 text-red-400'
            }`}>
              {s.isOk && s.isToday
                ? <CheckCircle2 size={12} />
                : <AlertTriangle size={12} />}
              {s.label}
              {s.daysAgo != null && !s.isToday && (
                <span className="opacity-60">{s.daysAgo === 0 ? 'hoy' : `${s.daysAgo}d`}</span>
              )}
            </div>
          ))}
        </div>
      </div>
    </details>
  )
}

export default function EntrySetups() {
  return (
    <div>
      <EntrySetupsFreshness />
      <PageTabs
        tabs={[
          { id: 'catalyst',       icon: '⚡', label: 'Catalizadores',     content: <CatalystScreener /> },
          { id: 'mean-reversion', icon: '↩', label: 'Mean Reversion',     content: <MeanReversion /> },
          { id: 'momentum',       icon: '↑', label: 'Momentum VCP',       content: <Momentum /> },
          { id: 'broad-bounce',   icon: '🔍', label: 'Universo ampliado', content: <BroadBounceView /> },
        ]}
      />
    </div>
  )
}
