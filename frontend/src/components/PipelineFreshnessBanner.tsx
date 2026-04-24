import { Activity, AlertTriangle, CheckCircle2 } from 'lucide-react'
import { usePipelineStatus, usePipelineHealth } from './StaleDataBanner'

function hoursAgo(iso: string): number {
  return (Date.now() - new Date(iso).getTime()) / (1000 * 60 * 60)
}

function timeAgoLabel(iso: string): string {
  const h = hoursAgo(iso)
  if (h < 1) return `hace ${Math.max(1, Math.floor(h * 60))}min`
  if (h < 24) return `hace ${Math.floor(h)}h`
  const d = Math.floor(h / 24)
  return d === 1 ? 'ayer' : `hace ${d}d`
}

export default function PipelineFreshnessBanner({ className = '' }: { className?: string }) {
  const pipelineInfo = usePipelineStatus()
  const health = usePipelineHealth()

  if (!pipelineInfo && !health) return null

  const lastRun = pipelineInfo?.status?.last_run ?? health?.generated_at
  if (!lastRun) return null

  const ok = health?.ok_count ?? null
  const total = health?.total ?? null
  const allOk = ok != null && total != null && ok === total
  const degraded = ok != null && total != null && ok < total && ok >= total - 2
  const broken = ok != null && total != null && ok < total - 2

  const pipelineStale = pipelineInfo?.stale ?? false
  const showWarn = pipelineStale || broken
  const showAmber = !showWarn && degraded

  const tone = showWarn
    ? 'bg-red-500/8 border-red-500/25 text-red-300'
    : showAmber
      ? 'bg-amber-500/8 border-amber-500/25 text-amber-300'
      : 'bg-emerald-500/8 border-emerald-500/20 text-emerald-300'

  const Icon = showWarn ? AlertTriangle : (allOk ? CheckCircle2 : Activity)
  const iconTone = showWarn ? 'text-red-400' : showAmber ? 'text-amber-400' : 'text-emerald-400'

  const failing = health
    ? Object.entries(health.modules)
        .filter(([, m]) => m.status !== 'ok')
        .map(([name]) => name)
    : []

  return (
    <div
      className={`inline-flex flex-wrap items-center gap-2 text-[0.72rem] font-medium px-3 py-1.5 rounded-lg border ${tone} ${className}`}
      title={failing.length ? `Módulos con problemas: ${failing.join(', ')}` : 'Todos los módulos OK'}
    >
      <Icon size={13} className={iconTone} />
      <span className="font-semibold">Pipeline</span>
      <span className="opacity-40">·</span>
      <span className="opacity-80">{timeAgoLabel(lastRun)}</span>
      {ok != null && total != null && (
        <>
          <span className="opacity-40">·</span>
          <span className={`font-mono ${allOk ? 'opacity-80' : 'font-semibold'}`}>
            {ok}/{total} módulos OK
          </span>
        </>
      )}
    </div>
  )
}
