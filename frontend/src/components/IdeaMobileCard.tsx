import type React from 'react'
import { AlertTriangle, CalendarClock, ChevronRight } from 'lucide-react'
import type { ValueOpportunity } from '@/api/client'
import TickerLogo from './TickerLogo'
import OwnedBadge from './OwnedBadge'
import ValuationBar from './ValuationBar'

/**
 * Una idea (VALUE, catalizadores, LEAPS…) como tarjeta, para móvil.
 *
 * No es la fila de la tabla comprimida: la tabla tiene 14 columnas y en 390px
 * ni cabe ni se entiende. Aquí el orden es el de la decisión —
 * ¿qué es? → ¿puedo entrar? → ¿por qué está barata? → ¿cuánto puedo ganar? —
 * y todo lo que no responde a eso (R:R, P(win), Magic Formula, sector…) se
 * queda en el modal de tesis, a un toque.
 *
 * Regla del proyecto: un dato, un solo dispositivo de énfasis. El veredicto lo
 * lleva el badge; la tarjeta va neutra.
 */

const VEREDICTO = {
  ENTRADA: { texto: 'Listo para entrar', clase: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' },
  VIGILAR: { texto: 'En vigilancia',     clase: 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30' },
  ESPERAR: { texto: 'Aún cayendo',       clase: 'bg-red-500/15 text-red-400 border-red-500/30' },
} as const

const POR_QUE_CAE: Record<string, string> = {
  DETERIORO:   'El negocio está peor',
  CICLICO:     'Parte baja del ciclo',
  EVENTO:      'Shock puntual',
  SENTIMIENTO: 'Sentimiento, no el negocio',
}

function Dato({ etiqueta, valor, tono }: Readonly<{ etiqueta: string; valor: string; tono?: string }>) {
  return (
    <div className="min-w-0">
      <div className="text-[0.55rem] font-bold uppercase tracking-widest text-muted-foreground/50">{etiqueta}</div>
      <div className={`text-sm font-bold tabular-nums truncate ${tono ?? 'text-foreground'}`}>{valor}</div>
    </div>
  )
}

interface Props {
  d: ValueOpportunity
  onOpen: () => void
  /** Fila de badges propia de cada pantalla (catalizadores, tipo de LEAP…). */
  extra?: React.ReactNode
}

export default function IdeaMobileCard({ d, onOpen, extra }: Readonly<Props>) {
  const v = d.entry_readiness ? VEREDICTO[d.entry_readiness] : null
  const upside = d.analyst_upside_pct
  const porQue = d.why_cheap ? POR_QUE_CAE[d.why_cheap] : null
  const earningsCerca = d.days_to_earnings != null && d.days_to_earnings <= 7

  return (
    <button
      onClick={onOpen}
      className="glass w-full rounded-xl border border-border/25 p-3.5 text-left active:bg-white/5"
    >
      <div className="flex items-start gap-2.5">
        <TickerLogo ticker={d.ticker} size="sm" />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="font-mono text-[0.95rem] font-bold tracking-wide text-primary">{d.ticker}</span>
            <OwnedBadge ticker={d.ticker} />
            {v && (
              <span className={`rounded-full border px-2 py-0.5 text-[0.6rem] font-bold uppercase tracking-wide ${v.clase}`}>
                {v.texto}
              </span>
            )}
          </div>
          {d.company_name && (
            <div className="truncate text-[0.72rem] text-muted-foreground">{d.company_name}</div>
          )}
        </div>
        <ChevronRight size={16} className="mt-1 shrink-0 text-muted-foreground/40" />
      </div>

      {porQue && (
        <div className="mt-2.5 text-[0.72rem] text-foreground/70">
          Por qué está barata: <span className="text-foreground/90">{porQue}</span>
        </div>
      )}

      <div className="mt-3 grid grid-cols-3 gap-2">
        <Dato etiqueta="Precio" valor={d.current_price != null ? `$${d.current_price.toFixed(2)}` : '—'} />
        <Dato
          etiqueta="Potencial"
          valor={upside != null ? `${upside > 0 ? '+' : ''}${upside.toFixed(0)}%` : '—'}
          tono={upside == null ? undefined : upside >= 10 ? 'text-emerald-400' : 'text-muted-foreground'}
        />
        <Dato etiqueta="Score" valor={d.value_score != null ? d.value_score.toFixed(0) : '—'} />
      </div>

      {/* "Potencial +21%" no dice si está barata: dice cuánto le falta al
          consenso. La barra pone el precio sobre el rango real del año y
          marca los tres objetivos, que es la pregunta de verdad. */}
      <ValuationBar
        className="mt-3"
        precio={d.current_price}
        pctDesdeMax={d.pct_from_52w_high}
        pctDesdeMin={d.pct_from_52w_low}
        objetivoAnalista={d.target_price_analyst}
        objetivoDcf={d.target_price_dcf}
        objetivoPe={d.target_price_pe}
      />

      {extra && <div className="mt-2.5 flex flex-wrap gap-1">{extra}</div>}

      {(earningsCerca || d.upside_divergence === 'ALTA') && (
        <div className="mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-1">
          {earningsCerca && (
            <span className="inline-flex items-center gap-1 text-[0.65rem] text-amber-400">
              <CalendarClock size={12} />
              Resultados en {d.days_to_earnings}d
            </span>
          )}
          {d.upside_divergence === 'ALTA' && (
            <span className="inline-flex items-center gap-1 text-[0.65rem] text-amber-400">
              <AlertTriangle size={12} />
              Los modelos no confirman el potencial
            </span>
          )}
        </div>
      )}
    </button>
  )
}
