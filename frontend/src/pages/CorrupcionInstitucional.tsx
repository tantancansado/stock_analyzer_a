import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import { apiClient } from '../api/client'
import Loading, { ErrorState } from '../components/Loading'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { ExternalLink, AlertTriangle, TrendingUp, TrendingDown, FileText, Scroll, Building2 } from 'lucide-react'
import { cn } from '@/lib/utils'

// ─── Types ────────────────────────────────────────────────────────────────────

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
  analysis?: {
    reasoning?: string
    expected_move_pct?: number | null
    companies?: string[]
  }
}

interface PoliticalSignal {
  id: string
  source_type: 'CONGRESS_TRADE' | 'GOVERNMENT_CONTRACT' | 'EXECUTIVE_ORDER'
  title: string
  link?: string
  scanned_at: string
  tickers: string[]
  signal_type: string
  signal_strength: string
  reasoning?: string
  // Congress trade fields
  politician?: string
  party?: string
  chamber?: string
  transaction_type?: string
  amount?: string
  amount_mid?: number
  transaction_date?: string
  disclosure_date?: string
  asset_description?: string
  // Contract fields
  recipient?: string
  agency?: string
  sector?: string
  description?: string
  amount_raw?: number
  // EO fields
  eo_number?: string
  abstract?: string
  agencies?: string[]
  signing_date?: string
}

// ─── Constants ────────────────────────────────────────────────────────────────

const TABS = [
  { id: 'trump',     label: 'Trump',          icon: AlertTriangle, color: 'text-red-400',    desc: 'Truth Social & noticias' },
  { id: 'congress',  label: 'Congreso',        icon: Building2,     color: 'text-orange-400', desc: 'Trades de senadores y representantes' },
  { id: 'contracts', label: 'Contratos gov.',  icon: FileText,      color: 'text-yellow-400', desc: 'USASpending.gov — $10M+' },
  { id: 'eo',        label: 'Executive Orders', icon: Scroll,       color: 'text-purple-400', desc: 'Federal Register' },
] as const

type TabId = typeof TABS[number]['id']

const SIGNAL_TYPE_LABELS: Record<string, string> = {
  CONTRACT_AWARD:    'Contrato gov.',
  BUY_SIGNAL:        'Recomendación directa',
  CONGRESS_BUY:      'Compra política',
  CONGRESS_SELL:     'Venta política',
  EXECUTIVE_ORDER:   'Executive Order',
  REGULATORY_CHANGE: 'Cambio regulatorio',
  TARIFF:            'Arancel',
  TRADE_DEAL:        'Acuerdo comercial',
  NEUTRAL:           'Neutral',
}

const STRENGTH_STYLE: Record<string, string> = {
  HIGH:   'bg-red-500/15 text-red-400 border-red-500/30',
  MEDIUM: 'bg-orange-500/15 text-orange-400 border-orange-500/30',
  LOW:    'bg-yellow-500/15 text-yellow-400 border-yellow-500/30',
}

const PARTY_COLOR: Record<string, string> = {
  R: 'text-red-400', Republican: 'text-red-400',
  D: 'text-blue-400', Democrat: 'text-blue-400',
  I: 'text-purple-400', Independent: 'text-purple-400',
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function fmtDate(raw?: string) {
  if (!raw) return '—'
  try {
    return new Date(raw).toLocaleDateString('es-ES', {
      day: '2-digit', month: 'short', year: 'numeric',
    })
  } catch { return raw.slice(0, 10) }
}

function TickerChip({ ticker }: { ticker: string }) {
  return (
    <span className="font-mono font-semibold text-foreground bg-muted/50 px-1.5 py-0.5 rounded text-xs">
      {ticker}
    </span>
  )
}

function StrengthBadge({ strength }: { strength: string }) {
  return (
    <span className={cn('text-[0.68rem] font-semibold px-1.5 py-0.5 rounded border', STRENGTH_STYLE[strength] ?? STRENGTH_STYLE.LOW)}>
      {strength}
    </span>
  )
}

// ─── Card variants ────────────────────────────────────────────────────────────

function TrumpCard({ signal }: { signal: TrumpSignal }) {
  return (
    <Card className="glass border-border/30 hover:border-border/60 transition-colors">
      <CardContent className="p-4 space-y-2">
        <div className="flex items-start gap-2">
          <a href={signal.link} target="_blank" rel="noopener noreferrer"
            className="text-sm font-medium leading-snug hover:text-primary transition-colors line-clamp-2 flex-1">
            {signal.title}
          </a>
          {signal.link && (
            <a href={signal.link} target="_blank" rel="noopener noreferrer"
              className="shrink-0 mt-0.5 text-muted-foreground/40 hover:text-muted-foreground transition-colors">
              <ExternalLink size={12} />
            </a>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-1.5 text-xs">
          {signal.tickers.map(t => <TickerChip key={t} ticker={t} />)}
          <Badge variant="outline" className="text-[0.68rem] py-0 px-1.5 border-border/40 gap-1">
            <FileText size={11} />
            {SIGNAL_TYPE_LABELS[signal.signal_type] ?? signal.signal_type}
          </Badge>
          <StrengthBadge strength={signal.signal_strength} />
          {signal.analysis?.expected_move_pct != null && (
            <span className="text-emerald-400 font-medium">+{signal.analysis.expected_move_pct}% est.</span>
          )}
          <span className="ml-auto text-muted-foreground/40 text-[0.68rem]">{fmtDate(signal.published || signal.scanned_at)}</span>
        </div>
        <div className="text-[0.7rem] text-muted-foreground/40 truncate">{signal.source}</div>
      </CardContent>
    </Card>
  )
}

function CongressCard({ signal }: { signal: PoliticalSignal }) {
  const isBuy = signal.signal_type === 'CONGRESS_BUY'
  const partyKey = signal.party?.charAt(0) ?? ''
  const partyColor = PARTY_COLOR[partyKey] ?? PARTY_COLOR[signal.party ?? ''] ?? 'text-muted-foreground'

  return (
    <Card className="glass border-border/30 hover:border-border/60 transition-colors">
      <CardContent className="p-4 space-y-2">
        <div className="flex items-start gap-3">
          <div className={cn('mt-0.5 shrink-0', isBuy ? 'text-emerald-400' : 'text-red-400')}>
            {isBuy ? <TrendingUp size={16} strokeWidth={1.75} /> : <TrendingDown size={16} strokeWidth={1.75} />}
          </div>
          <div className="flex-1 min-w-0 space-y-1.5">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-semibold text-sm">{signal.politician}</span>
              {signal.party && (
                <span className={cn('text-xs font-medium', partyColor)}>
                  {signal.party} · {signal.chamber}
                </span>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-1.5 text-xs">
              {signal.tickers.map(t => <TickerChip key={t} ticker={t} />)}
              <span className={cn('font-semibold text-xs', isBuy ? 'text-emerald-400' : 'text-red-400')}>
                {isBuy ? 'COMPRA' : 'VENTA'}
              </span>
              {signal.amount && (
                <span className="text-muted-foreground bg-muted/30 px-1.5 py-0.5 rounded">{signal.amount}</span>
              )}
              <StrengthBadge strength={signal.signal_strength} />
              <span className="ml-auto text-muted-foreground/40 text-[0.68rem]">{fmtDate(signal.transaction_date)}</span>
            </div>
            {signal.asset_description && (
              <div className="text-[0.7rem] text-muted-foreground/50 truncate">{signal.asset_description}</div>
            )}
          </div>
        </div>
        {signal.link && (
          <a href={signal.link} target="_blank" rel="noopener noreferrer"
            className="flex items-center gap-1 text-[0.7rem] text-muted-foreground/40 hover:text-muted-foreground transition-colors w-fit">
            <ExternalLink size={11} /> Ver declaración oficial
          </a>
        )}
      </CardContent>
    </Card>
  )
}

function ContractCard({ signal }: { signal: PoliticalSignal }) {
  return (
    <Card className="glass border-border/30 hover:border-border/60 transition-colors">
      <CardContent className="p-4 space-y-2">
        <div className="flex items-start gap-2">
          <div className="flex-1 min-w-0 space-y-1.5">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-semibold text-sm">{signal.recipient}</span>
              {signal.amount && (
                <span className="text-emerald-400 font-bold text-sm">{signal.amount}</span>
              )}
            </div>
            <div className="text-xs text-muted-foreground">{signal.agency}</div>
            <div className="flex flex-wrap items-center gap-1.5 text-xs">
              {signal.tickers.map(t => <TickerChip key={t} ticker={t} />)}
              {signal.sector && (
                <Badge variant="outline" className="text-[0.68rem] py-0 px-1.5 border-border/40">{signal.sector}</Badge>
              )}
              <StrengthBadge strength={signal.signal_strength} />
              <span className="ml-auto text-muted-foreground/40 text-[0.68rem]">{fmtDate(signal.scanned_at)}</span>
            </div>
            {signal.description && (
              <div className="text-[0.7rem] text-muted-foreground/50 line-clamp-2">{signal.description}</div>
            )}
          </div>
          {signal.link && (
            <a href={signal.link} target="_blank" rel="noopener noreferrer"
              className="shrink-0 text-muted-foreground/40 hover:text-muted-foreground transition-colors mt-0.5">
              <ExternalLink size={12} />
            </a>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

function EoCard({ signal }: { signal: PoliticalSignal }) {
  return (
    <Card className="glass border-border/30 hover:border-border/60 transition-colors">
      <CardContent className="p-4 space-y-2">
        <div className="flex items-start gap-2">
          <div className="flex-1 min-w-0 space-y-1.5">
            <a href={signal.link} target="_blank" rel="noopener noreferrer"
              className="text-sm font-medium leading-snug hover:text-primary transition-colors line-clamp-2 block">
              {signal.title}
            </a>
            <div className="flex flex-wrap items-center gap-1.5 text-xs">
              {signal.tickers.slice(0, 6).map(t => <TickerChip key={t} ticker={t} />)}
              <StrengthBadge strength={signal.signal_strength} />
              <span className="ml-auto text-muted-foreground/40 text-[0.68rem]">{fmtDate(signal.signing_date || signal.scanned_at)}</span>
            </div>
            {signal.abstract && (
              <div className="text-[0.7rem] text-muted-foreground/50 line-clamp-2">{signal.abstract}</div>
            )}
            {signal.agencies && signal.agencies.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {signal.agencies.slice(0, 3).map(a => (
                  <span key={a} className="text-[0.65rem] text-muted-foreground/50 bg-muted/20 px-1.5 py-0.5 rounded">{a}</span>
                ))}
              </div>
            )}
          </div>
          {signal.link && (
            <a href={signal.link} target="_blank" rel="noopener noreferrer"
              className="shrink-0 text-muted-foreground/40 hover:text-muted-foreground transition-colors mt-0.5">
              <ExternalLink size={12} />
            </a>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function CorrupcionInstitucional() {
  const [activeTab, setActiveTab] = useState<TabId>('trump')
  const [filterType, setFilterType] = useState<string>('ALL')

  const { data: trumpData, loading: trumpLoading, error: trumpError } =
    useApi(() => apiClient.get<TrumpSignal[]>('/api/trump-signals?limit=100').then(r => r.data), [])

  const { data: politicalData, loading: polLoading, error: polError } =
    useApi(() => apiClient.get<PoliticalSignal[]>('/api/political-signals?limit=200').then(r => r.data), [])

  const trumpSignals = trumpData ?? []
  const politicalSignals = politicalData ?? []

  const congressSignals = politicalSignals.filter(s => s.source_type === 'CONGRESS_TRADE')
  const contractSignals = politicalSignals.filter(s => s.source_type === 'GOVERNMENT_CONTRACT')
  const eoSignals       = politicalSignals.filter(s => s.source_type === 'EXECUTIVE_ORDER')

  const counts: Record<TabId, number> = {
    trump:     trumpSignals.length,
    congress:  congressSignals.length,
    contracts: contractSignals.length,
    eo:        eoSignals.length,
  }

  // Trump tab type filter
  const trumpTypes = ['ALL', ...Array.from(new Set(trumpSignals.map(s => s.signal_type)))]
  const filteredTrump = filterType === 'ALL' ? trumpSignals : trumpSignals.filter(s => s.signal_type === filterType)

  const isLoading = trumpLoading || polLoading
  const hasError  = trumpError || polError

  return (
    <div className="space-y-6 p-4 md:p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="space-y-1">
        <div className="flex items-center gap-2.5">
          <AlertTriangle size={20} className="text-red-400" strokeWidth={1.75} />
          <h1 className="text-xl font-bold tracking-tight">Corrupción Institucional</h1>
        </div>
        <p className="text-sm text-muted-foreground">
          Señales de mercado derivadas de contratos gubernamentales, trades del Congreso y Executive Orders.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-muted/20 rounded-lg border border-border/30 flex-wrap">
        {TABS.map(tab => {
          const Icon = tab.icon
          const count = counts[tab.id]
          return (
            <button
              key={tab.id}
              onClick={() => { setActiveTab(tab.id); setFilterType('ALL') }}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all flex-1 justify-center',
                activeTab === tab.id
                  ? 'bg-background text-foreground shadow-sm border border-border/40'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              <Icon size={13} className={activeTab === tab.id ? tab.color : ''} />
              <span className="hidden sm:inline">{tab.label}</span>
              {count > 0 && (
                <span className={cn('text-[0.65rem] font-bold px-1 py-0.5 rounded', activeTab === tab.id ? 'bg-muted' : 'bg-muted/50')}>
                  {count}
                </span>
              )}
            </button>
          )
        })}
      </div>

      {isLoading && <Loading />}
      {!isLoading && hasError && <ErrorState message="No se pudieron cargar las señales" />}

      {/* Trump tab */}
      {!isLoading && activeTab === 'trump' && (
        <div className="space-y-3">
          {trumpTypes.length > 2 && (
            <div className="flex flex-wrap gap-2">
              {trumpTypes.map(t => (
                <button key={t} onClick={() => setFilterType(t)}
                  className={cn('px-3 py-1 rounded-full text-xs font-medium border transition-all',
                    filterType === t
                      ? 'bg-red-500/15 text-red-400 border-red-500/30'
                      : 'border-border/40 text-muted-foreground hover:text-foreground'
                  )}>
                  {t === 'ALL' ? 'Todos' : (SIGNAL_TYPE_LABELS[t] ?? t)}
                </button>
              ))}
            </div>
          )}
          {filteredTrump.length === 0
            ? <Empty text="No hay señales Trump registradas todavía." />
            : filteredTrump.map(s => <TrumpCard key={s.id} signal={s} />)
          }
        </div>
      )}

      {/* Congress tab */}
      {!isLoading && activeTab === 'congress' && (
        <div className="space-y-3">
          <SectionNote text="Trades de senadores y representantes (STOCK Act). Lag máximo 45 días respecto a la operación real." />
          {congressSignals.length === 0
            ? <Empty text="No hay trades del Congreso registrados todavía. El scanner se ejecuta diariamente." />
            : congressSignals.map(s => <CongressCard key={s.id} signal={s} />)
          }
        </div>
      )}

      {/* Contracts tab */}
      {!isLoading && activeTab === 'contracts' && (
        <div className="space-y-3">
          <SectionNote text="Contratos gubernamentales >$10M adjudicados en los últimos 3 días (USASpending.gov)." />
          {contractSignals.length === 0
            ? <Empty text="No hay contratos registrados todavía. El scanner se ejecuta diariamente." />
            : contractSignals.map(s => <ContractCard key={s.id} signal={s} />)
          }
        </div>
      )}

      {/* Executive Orders tab */}
      {!isLoading && activeTab === 'eo' && (
        <div className="space-y-3">
          <SectionNote text="Executive Orders publicadas en el Federal Register con impacto potencial en sectores cotizados." />
          {eoSignals.length === 0
            ? <Empty text="No hay Executive Orders registradas todavía. El scanner se ejecuta diariamente." />
            : eoSignals.map(s => <EoCard key={s.id} signal={s} />)
          }
        </div>
      )}
    </div>
  )
}

function SectionNote({ text }: { text: string }) {
  return (
    <p className="text-xs text-muted-foreground/60 italic border-l-2 border-border/30 pl-3">{text}</p>
  )
}

function Empty({ text }: { text: string }) {
  return (
    <div className="text-center py-14 text-muted-foreground text-sm">{text}</div>
  )
}
