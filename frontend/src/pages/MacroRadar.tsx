import { fetchMacroRadar } from '../api/client'
import { useApi } from '../hooks/useApi'
import Loading, { ErrorState } from '../components/Loading'
import { Card, CardContent } from '@/components/ui/card'

interface SignalData {
  label: string
  description: string
  score: number
  current?: number | null
  percentile?: number
  change_5d?: number
  change_20d?: number
  pct_from_200?: number
  interpretation: string
}

interface MacroData {
  timestamp: string
  date: string
  regime: { name: string; color: string; description: string }
  composite_score: number
  composite_pct: number
  max_score: number
  signals: Record<string, SignalData>
  signal_order: string[]
  ai_narrative?: string | null
  errors?: string[]
}

const SIGNAL_ICONS: Record<string, string> = {
  vix:         '⚡',
  yield_curve: '📈',
  credit:      '💳',
  copper_gold: '🔩',
  gold_spy:    '🥇',
  oil:         '🛢',
  defense:     '🛡',
  dollar:      '💵',
  yen:         '🇯🇵',
  breadth:     '📊',
}

function scoreToColor(score: number): string {
  if (score >= 1.5)  return 'text-emerald-400'
  if (score >= 0.5)  return 'text-green-400'
  if (score >= -0.5) return 'text-yellow-400'
  if (score >= -1.5) return 'text-orange-400'
  return 'text-red-400'
}

function scoreToBg(score: number): string {
  if (score >= 1.5)  return 'bg-emerald-500/10 border-emerald-500/20'
  if (score >= 0.5)  return 'bg-green-500/10 border-green-500/20'
  if (score >= -0.5) return 'bg-yellow-500/10 border-yellow-500/20'
  if (score >= -1.5) return 'bg-orange-500/10 border-orange-500/20'
  return 'bg-red-500/10 border-red-500/20'
}

function scoreToLabel(score: number): string {
  if (score >= 1.5)  return 'Positivo'
  if (score >= 0.5)  return 'Neutro+'
  if (score >= -0.5) return 'Neutro'
  if (score >= -1.5) return 'Precaución'
  return 'Alerta'
}

function regimeBadgeVariant(name: string): string {
  const map: Record<string, string> = {
    CALM:   'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    WATCH:  'bg-lime-500/15 text-lime-400 border-lime-500/30',
    STRESS: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30',
    ALERT:  'bg-orange-500/15 text-orange-400 border-orange-500/30',
    CRISIS: 'bg-red-500/15 text-red-400 border-red-500/30',
  }
  return map[name] ?? 'bg-muted/20 text-muted-foreground border-border'
}

function ScoreGauge({ score, max }: { score: number; max: number }) {
  // score range: -max to +max → normalize to 0-100
  const pct = ((score + max) / (2 * max)) * 100
  const color = score >= 4 ? '#10b981' : score >= 0 ? '#84cc16' : score >= -4 ? '#f59e0b' : score >= -8 ? '#f97316' : '#ef4444'
  return (
    <div className="relative w-full">
      <div className="flex justify-between text-[0.65rem] text-muted-foreground mb-1">
        <span>Crisis</span>
        <span>Neutro</span>
        <span>Calma</span>
      </div>
      <div className="h-2 w-full rounded-full bg-muted/30 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <div className="flex justify-between text-[0.65rem] text-muted-foreground mt-1">
        <span>{-max}</span>
        <span className="font-bold" style={{ color }}>{score.toFixed(1)}</span>
        <span>+{max}</span>
      </div>
    </div>
  )
}

function SignalCard({ id, signal }: { id: string; signal: SignalData }) {
  const icon = SIGNAL_ICONS[id] ?? '📌'
  const score = signal.score ?? 0

  return (
    <Card className={`glass border ${scoreToBg(score)} transition-all`}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="flex items-center gap-2">
            <span className="text-lg">{icon}</span>
            <span className="text-xs font-semibold text-foreground leading-tight">{signal.label}</span>
          </div>
          <div className={`text-xs font-bold px-1.5 py-0.5 rounded ${scoreToColor(score)}`}>
            {score >= 0 ? '+' : ''}{score.toFixed(1)}
          </div>
        </div>

        {/* Score bar */}
        <div className="mb-2">
          <div className="h-1.5 w-full rounded-full bg-muted/30 overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-700"
              style={{
                width: `${((score + 2) / 4) * 100}%`,
                backgroundColor: score >= 1 ? '#10b981' : score >= 0 ? '#84cc16' : score >= -1 ? '#f97316' : '#ef4444',
              }}
            />
          </div>
        </div>

        <p className="text-[0.7rem] text-muted-foreground leading-snug mb-1.5">
          {signal.interpretation || '—'}
        </p>

        <div className="flex items-center justify-between">
          {signal.percentile != null && (
            <span className="text-[0.62rem] text-muted-foreground/70">
              p{signal.percentile.toFixed(0)} vs 1yr
            </span>
          )}
          <span className={`text-[0.65rem] font-medium ${scoreToColor(score)}`}>
            {scoreToLabel(score)}
          </span>
        </div>

        {signal.change_5d != null && (
          <div className="mt-1 text-[0.62rem] text-muted-foreground/60">
            5d: <span className={signal.change_5d >= 0 ? 'text-green-400' : 'text-red-400'}>
              {signal.change_5d >= 0 ? '+' : ''}{signal.change_5d.toFixed(1)}%
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default function MacroRadar() {
  const { data, loading, error } = useApi<MacroData>(() => fetchMacroRadar(), [])

  if (loading) return <Loading />
  if (error) return <ErrorState message={error} />
  if (!data || !data.regime) return <ErrorState message="Sin datos de radar macro" />

  const { regime, composite_score, max_score, signals, signal_order, ai_narrative, date, errors } = data

  const orderedSignals = (signal_order || Object.keys(signals)).filter(k => signals[k])

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground mb-1">Macro Radar</h1>
          <p className="text-sm text-muted-foreground">
            Sistema de alerta temprana — detecta cambios de régimen antes de que ocurran
          </p>
        </div>
        <div className="text-right flex flex-col items-end gap-2">
          <span
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-sm font-bold ${regimeBadgeVariant(regime.name)}`}
          >
            <span className="w-2 h-2 rounded-full animate-pulse" style={{ backgroundColor: regime.color }} />
            {regime.name}
          </span>
          <span className="text-xs text-muted-foreground">{date}</span>
        </div>
      </div>

      {/* Regime card + gauge */}
      <Card className="glass border border-border/50">
        <CardContent className="p-5 flex flex-col md:flex-row gap-6">
          <div className="flex-1 space-y-3">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: regime.color }} />
              <span className="text-base font-bold text-foreground">{regime.name}</span>
            </div>
            <p className="text-sm text-muted-foreground">{regime.description}</p>
            {ai_narrative && (
              <div className="mt-3 p-3 rounded-lg bg-muted/20 border border-border/30">
                <p className="text-xs font-semibold text-primary mb-1">Análisis IA</p>
                <p className="text-sm text-foreground/90 leading-relaxed">{ai_narrative}</p>
              </div>
            )}
          </div>
          <div className="md:w-64 flex flex-col justify-center gap-2">
            <p className="text-xs text-muted-foreground font-medium">Puntuación compuesta</p>
            <ScoreGauge score={composite_score} max={max_score} />
            <div className="grid grid-cols-3 gap-1 mt-1">
              {[
                { label: 'Positivas', count: orderedSignals.filter(k => signals[k]?.score > 0).length, color: 'text-green-400' },
                { label: 'Neutras',   count: orderedSignals.filter(k => signals[k]?.score === 0).length, color: 'text-yellow-400' },
                { label: 'Negativas', count: orderedSignals.filter(k => signals[k]?.score < 0).length, color: 'text-red-400' },
              ].map(s => (
                <div key={s.label} className="text-center">
                  <div className={`text-lg font-bold ${s.color}`}>{s.count}</div>
                  <div className="text-[0.62rem] text-muted-foreground">{s.label}</div>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Signal grid */}
      <div>
        <h2 className="text-sm font-semibold text-muted-foreground mb-3 uppercase tracking-wider">
          Señales ({orderedSignals.length})
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
          {orderedSignals.map(key => (
            <SignalCard key={key} id={key} signal={signals[key]} />
          ))}
        </div>
      </div>

      {/* Data errors */}
      {errors && errors.length > 0 && (
        <div className="text-xs text-muted-foreground/60 text-right">
          Señales sin datos: {errors.join(', ')}
        </div>
      )}

      {/* Legend */}
      <Card className="glass border border-border/30">
        <CardContent className="p-4">
          <p className="text-xs font-semibold text-muted-foreground mb-2 uppercase tracking-wider">Guía de regímenes</p>
          <div className="flex flex-wrap gap-3">
            {[
              { name: 'CALM',   color: '#10b981', desc: 'Favorable' },
              { name: 'WATCH',  color: '#84cc16', desc: 'Vigilancia' },
              { name: 'STRESS', color: '#f59e0b', desc: 'Estrés moderado' },
              { name: 'ALERT',  color: '#f97316', desc: 'Alerta elevada' },
              { name: 'CRISIS', color: '#ef4444', desc: 'Capital protection' },
            ].map(r => (
              <div key={r.name} className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: r.color }} />
                <span className="text-xs font-bold" style={{ color: r.color }}>{r.name}</span>
                <span className="text-xs text-muted-foreground">— {r.desc}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
