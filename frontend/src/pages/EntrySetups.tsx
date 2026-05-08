import { lazy } from 'react'
import PageTabs from '../components/PageTabs'
import BroadBounceView from './BroadBounceView'
import CatalystScreener from './CatalystScreener'
import { usePipelineHealth } from '../components/StaleDataBanner'
import { CheckCircle2, AlertTriangle, AlertCircle } from 'lucide-react'

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
        <CheckCircle2 size={13} className="text-emerald-400" />
        <span className="font-semibold text-emerald-400">Todos los módulos actualizados hoy</span>
      </div>
    )
  }

  return (
    <div className={`rounded-xl border px-4 py-3 mb-4 flex items-start gap-3 ${noneRan ? 'bg-red-500/8 border-red-500/25' : 'bg-amber-500/8 border-amber-500/25'}`}>
      {noneRan
        ? <AlertCircle size={15} className="text-red-400 shrink-0 mt-0.5" />
        : <AlertTriangle size={15} className="text-amber-400 shrink-0 mt-0.5" />}
      <div className="flex-1 min-w-0">
        <div className={`text-xs font-bold mb-2 ${noneRan ? 'text-red-400' : 'text-amber-400'}`}>
          {noneRan ? 'Pipeline no ejecutado hoy — datos desactualizados' : 'Algunos módulos no actualizados hoy'}
        </div>
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
                ? <CheckCircle2 size={10} />
                : <AlertTriangle size={10} />}
              {s.label}
              {s.daysAgo != null && !s.isToday && (
                <span className="opacity-60">{s.daysAgo === 0 ? 'hoy' : `${s.daysAgo}d`}</span>
              )}
            </div>
          ))}
        </div>
      </div>
      {anyStale && (
        <a href={ACTIONS_URL} target="_blank" rel="noopener noreferrer"
          className="shrink-0 text-[0.65rem] font-bold px-2.5 py-1 rounded-lg border bg-amber-500/10 border-amber-500/25 text-amber-400 hover:bg-amber-500/20 transition-colors">
          Ver pipeline →
        </a>
      )}
    </div>
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
