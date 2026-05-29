import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import { apiClient } from '../api/client'
import Loading, { ErrorState } from '../components/Loading'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { ExternalLink, AlertTriangle, TrendingUp, FileText } from 'lucide-react'

interface TrumpSignal {
  id: string
  source: string
  title: string
  link: string
  published: string
  scanned_at: string
  tickers: string[]
  signal_type: string
  signal_strength: string
  analysis: {
    has_stock_signal: boolean
    tickers: string[]
    companies: string[]
    signal_type: string
    signal_strength: string
    reasoning: string
    expected_move_pct: number | null
  }
}

const SIGNAL_TYPE_LABELS: Record<string, string> = {
  CONTRACT_AWARD: 'Contrato gubernamental',
  BUY_SIGNAL: 'Recomendación directa',
  TARIFF: 'Arancel / Tarifa',
  POLICY: 'Política pública',
  TWEET: 'Declaración pública',
}

const STRENGTH_COLOR: Record<string, string> = {
  HIGH:   'bg-red-500/15 text-red-400 border-red-500/30',
  MEDIUM: 'bg-orange-500/15 text-orange-400 border-orange-500/30',
  LOW:    'bg-yellow-500/15 text-yellow-400 border-yellow-500/30',
}

function fmtDate(raw: string) {
  try {
    return new Date(raw).toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch { return raw }
}

function SignalTypeIcon({ type }: { type: string }) {
  if (type === 'CONTRACT_AWARD') return <FileText size={13} className="shrink-0" />
  if (type === 'BUY_SIGNAL') return <TrendingUp size={13} className="shrink-0" />
  return <AlertTriangle size={13} className="shrink-0" />
}

export default function CorrupcionInstitucional() {
  const [filterType, setFilterType] = useState<string>('ALL')

  const { data, loading, error } = useApi(
    () => apiClient.get<TrumpSignal[]>('/api/trump-signals?limit=100').then(r => r.data),
    []
  )

  const signals = data ?? []
  const types = ['ALL', ...Array.from(new Set(signals.map(s => s.signal_type)))]

  const filtered = filterType === 'ALL' ? signals : signals.filter(s => s.signal_type === filterType)

  if (loading) return <Loading />
  if (error) return <ErrorState message="No se pudieron cargar las señales" />

  return (
    <div className="space-y-6 p-4 md:p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="space-y-1">
        <div className="flex items-center gap-2.5">
          <AlertTriangle size={20} className="text-red-400" strokeWidth={1.75} />
          <h1 className="text-xl font-bold tracking-tight">Corrupción Institucional</h1>
        </div>
        <p className="text-sm text-muted-foreground">
          Señales de mercado derivadas de contratos, declaraciones y decisiones políticas vinculadas a Trump.
          {signals.length > 0 && <span className="ml-1 text-muted-foreground/60">— {signals.length} señales detectadas</span>}
        </p>
      </div>

      {/* Filter pills */}
      {types.length > 2 && (
        <div className="flex flex-wrap gap-2">
          {types.map(t => (
            <button
              key={t}
              onClick={() => setFilterType(t)}
              className={`px-3 py-1 rounded-full text-xs font-medium border transition-all ${
                filterType === t
                  ? 'bg-red-500/15 text-red-400 border-red-500/30'
                  : 'border-border/40 text-muted-foreground hover:text-foreground hover:border-border'
              }`}
            >
              {t === 'ALL' ? 'Todos' : (SIGNAL_TYPE_LABELS[t] ?? t)}
            </button>
          ))}
        </div>
      )}

      {/* Signals list */}
      {filtered.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground text-sm">
          No hay señales registradas todavía.
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map(signal => (
            <Card key={signal.id} className="glass border-border/30 hover:border-border/60 transition-colors">
              <CardContent className="p-4">
                <div className="flex items-start gap-3">
                  <div className="flex-1 min-w-0 space-y-2">
                    {/* Title + link */}
                    <div className="flex items-start gap-2">
                      <a
                        href={signal.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm font-medium leading-snug hover:text-primary transition-colors line-clamp-2 flex-1"
                      >
                        {signal.title}
                      </a>
                      <a
                        href={signal.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="shrink-0 mt-0.5 text-muted-foreground/50 hover:text-muted-foreground transition-colors"
                        aria-label="Abrir fuente"
                      >
                        <ExternalLink size={13} />
                      </a>
                    </div>

                    {/* Meta row */}
                    <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                      {/* Tickers */}
                      {signal.tickers.map(t => (
                        <span key={t} className="font-mono font-semibold text-foreground bg-muted/40 px-1.5 py-0.5 rounded">
                          {t}
                        </span>
                      ))}

                      {/* Signal type */}
                      <Badge variant="outline" className="gap-1 text-[0.68rem] py-0 px-1.5 border-border/40">
                        <SignalTypeIcon type={signal.signal_type} />
                        {SIGNAL_TYPE_LABELS[signal.signal_type] ?? signal.signal_type}
                      </Badge>

                      {/* Strength */}
                      <span className={`text-[0.68rem] font-semibold px-1.5 py-0.5 rounded border ${STRENGTH_COLOR[signal.signal_strength] ?? STRENGTH_COLOR.LOW}`}>
                        {signal.signal_strength}
                      </span>

                      {/* Expected move */}
                      {signal.analysis?.expected_move_pct != null && (
                        <span className="text-emerald-400 font-medium">
                          +{signal.analysis.expected_move_pct}% est.
                        </span>
                      )}

                      {/* Date */}
                      <span className="ml-auto text-muted-foreground/50">
                        {fmtDate(signal.published || signal.scanned_at)}
                      </span>
                    </div>

                    {/* Source */}
                    <div className="text-[0.7rem] text-muted-foreground/40 truncate">
                      {signal.source}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
