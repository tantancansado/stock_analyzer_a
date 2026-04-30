import { useEffect, useState } from 'react'
import { TrendingUp, TrendingDown, Plus, LogOut, Loader2 } from 'lucide-react'
import { fetchScoreAlerts } from '../api/client'
import type { ScoreAlert, ScoreAlertsData } from '../api/client'

const TYPE_CONFIG: Record<string, { label: string; icon: React.ElementType; bg: string; text: string; border: string }> = {
  SCORE_UP:   { label: 'Subida',       icon: TrendingUp,   bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/25' },
  NEW_ENTRY:  { label: 'Nueva entrada', icon: Plus,         bg: 'bg-cyan-500/10',    text: 'text-cyan-400',    border: 'border-cyan-500/25' },
  SCORE_DOWN: { label: 'Bajada',        icon: TrendingDown, bg: 'bg-red-500/10',     text: 'text-red-400',     border: 'border-red-500/25' },
  EXITED:     { label: 'Salida',        icon: LogOut,       bg: 'bg-amber-500/10',   text: 'text-amber-400',   border: 'border-amber-500/25' },
}

function AlertRow({ alert }: { alert: ScoreAlert }) {
  const cfg = TYPE_CONFIG[alert.type] ?? TYPE_CONFIG.SCORE_DOWN
  const Icon = cfg.icon
  const deltaStr = alert.delta != null
    ? `${alert.delta > 0 ? '+' : ''}${alert.delta.toFixed(1)}pts`
    : alert.score_today != null
    ? `${alert.score_today.toFixed(1)}pts`
    : alert.score_prev != null
    ? `prev ${alert.score_prev.toFixed(1)}pts`
    : ''

  return (
    <div className={`flex items-center gap-3 px-3 py-2 rounded-lg border ${cfg.bg} ${cfg.border}`}>
      <Icon size={13} className={cfg.text} />
      <span className={`font-mono font-bold text-sm w-16 shrink-0 ${cfg.text}`}>{alert.ticker}</span>
      <span className="text-xs text-foreground/60 flex-1 truncate">{alert.company_name}</span>
      <span className="text-[0.65rem] text-muted-foreground/50 hidden sm:block">{alert.sector}</span>
      {alert.grade && (
        <span className="text-[0.6rem] font-bold px-1.5 py-0.5 rounded bg-muted/30 border border-border/30 text-muted-foreground/60">
          {alert.grade}
        </span>
      )}
      <span className={`text-xs font-bold tabular-nums shrink-0 ${cfg.text}`}>{deltaStr}</span>
    </div>
  )
}

function SummaryPill({ label, count, color }: { label: string; count: number; color: string }) {
  if (count === 0) return null
  return (
    <span className={`text-[0.65rem] font-bold px-2 py-0.5 rounded-full border ${color}`}>
      {count} {label}
    </span>
  )
}

export default function ScoreAlerts() {
  const [data, setData] = useState<ScoreAlertsData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let alive = true
    fetchScoreAlerts()
      .then(d => { if (alive) setData(d) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [])

  if (loading) {
    return (
      <div className="flex items-center gap-2 py-8 justify-center text-sm text-muted-foreground">
        <Loader2 size={14} className="animate-spin" /> Cargando novedades...
      </div>
    )
  }

  if (!data || data.alerts.length === 0) {
    return (
      <p className="text-sm text-muted-foreground/60 text-center py-8">
        Sin cambios significativos desde ayer.
      </p>
    )
  }

  const groups: Record<string, ScoreAlert[]> = {}
  for (const a of data.alerts) {
    ;(groups[a.type] ??= []).push(a)
  }
  const order = ['SCORE_UP', 'NEW_ENTRY', 'SCORE_DOWN', 'EXITED']

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground/50">
          Novedades vs {data.generated_at}
        </span>
        <SummaryPill label="↑" count={data.counts.score_up}   color="bg-emerald-500/10 text-emerald-400 border-emerald-500/25" />
        <SummaryPill label="nueva" count={data.counts.new_entries} color="bg-cyan-500/10 text-cyan-400 border-cyan-500/25" />
        <SummaryPill label="↓" count={data.counts.score_down} color="bg-red-500/10 text-red-400 border-red-500/25" />
        <SummaryPill label="salida" count={data.counts.exited}  color="bg-amber-500/10 text-amber-400 border-amber-500/25" />
      </div>

      {order.map(type => {
        const rows = groups[type]
        if (!rows?.length) return null
        const cfg = TYPE_CONFIG[type]
        return (
          <div key={type}>
            <h4 className={`text-[0.6rem] font-bold uppercase tracking-widest mb-1.5 ${cfg.text}`}>
              {cfg.label}
            </h4>
            <div className="space-y-1">
              {rows.map((a, i) => <AlertRow key={i} alert={a} />)}
            </div>
          </div>
        )
      })}
    </div>
  )
}
