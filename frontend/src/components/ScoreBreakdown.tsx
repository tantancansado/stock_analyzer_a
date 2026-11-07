import type { ValueOpportunity } from '../api/client'
import { precio } from '../lib/moneda'

interface ScoreBreakdownProps {
  row: ValueOpportunity
}

interface Contribution {
  label: string
  value: number
  positive: boolean
}

function buildContributions(row: ValueOpportunity): Contribution[] {
  const items: Contribution[] = []

  const add = (label: string, val: number | null | undefined) => {
    if (val == null || val === 0) return
    items.push({ label, value: val, positive: val > 0 })
  }

  add('FCF Yield', row.fcf_bonus)
  add('Piotroski', row.piotroski_bonus)
  add('R:R ratio', row.rr_bonus)
  add('Insiders', row.insider_bonus)
  add('Institucional', row.institutional_bonus)
  add('Opciones', row.options_bonus)
  add('Media móvil', row.mr_bonus)
  add('Sector rot.', row.sector_bonus)
  add('Dividendo', row.dividend_bonus)
  add('Buyback', row.buyback_bonus)
  add('Rev. analistas', row.revision_bonus)
  add('Hedge Funds', row.hf_bonus)
  add('Cerebro IA', row.cerebro_score_adj)
  add('Owner Earn.', row.oe_ai_adjustment)
  // IV bonus: derive from iv_ratio
  if (row.iv_ratio != null) {
    let ivAdj = 0
    if (row.iv_ratio < 0.8)        ivAdj =  3
    else if (row.iv_ratio >= 2)    ivAdj = -5
    else if (row.iv_ratio >= 1.3)  ivAdj = -3
    if (ivAdj !== 0) items.push({ label: 'IV/HV', value: ivAdj, positive: ivAdj > 0 })
  }
  if (row.profitability_penalty != null && row.profitability_penalty !== 0) {
    items.push({ label: 'Rent. baja', value: -Math.abs(row.profitability_penalty), positive: false })
  }

  return items.sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
}

const num = (v: number, d = 1) => v.toLocaleString('es-ES', { minimumFractionDigits: d, maximumFractionDigits: d })
const signo = (v: number, d = 0) => `${v > 0 ? '+' : ''}${num(v, d)}`

/** Value US: la nota no es una suma, así que aquí se dice de qué sale. */
function ComoSaleLaNota({ row }: ScoreBreakdownProps) {
  const filas: { etiqueta: string; valor: string; nota?: string }[] = []
  if (row.per_z != null && row.per_norm != null && row.per_mediana_10a != null) {
    filas.push({ etiqueta: 'PER contra su historia', valor: `${signo(row.per_z, 1)}σ`, nota: `${num(row.per_norm)} frente a ${num(row.per_mediana_10a)} de mediana en 10 años` })
  } else if (row.per_sin_dato_motivo) {
    filas.push({ etiqueta: 'PER contra su historia', valor: 'Sin dato', nota: row.per_sin_dato_motivo })
  }
  if (row.precio_per_menos_1s != null) {
    filas.push({ etiqueta: 'Precio a −1σ', valor: precio(row.precio_per_menos_1s, row.ticker), nota: row.precio_per_media != null ? `a su mediana: ${precio(row.precio_per_media, row.ticker)}` : undefined })
  }
  if (row.ventas_anual_pct != null) {
    filas.push({ etiqueta: 'Ventas último año', valor: `${signo(row.ventas_anual_pct)} %`, nota: row.rev_growth_yoy != null ? `último trimestre: ${signo(row.rev_growth_yoy)} %` : undefined })
  }
  if (row.fcf_yield_pct != null) filas.push({ etiqueta: 'FCF yield', valor: `${num(row.fcf_yield_pct)} %` })
  if (row.revision_13s_pct != null) {
    filas.push({ etiqueta: 'Consenso de BPA en 13 semanas', valor: `${signo(row.revision_13s_pct, 1)} %` })
  }
  if (row.bpa_sobre_tendencia_pct != null && row.bpa_sobre_tendencia_pct > 25) {
    filas.push({ etiqueta: 'Beneficio sobre su tendencia', valor: `${signo(row.bpa_sobre_tendencia_pct)} %`, nota: 'Puede estar en pico de ciclo: un PER bajo engaña más' })
  }
  return (
    <div>
      <h4 className="etiqueta-seccion mb-2">Cómo sale la nota</h4>
      {row.value_falta && <p className="mb-2 text-apoyo text-foreground">Le falta: {row.value_falta}.</p>}
      <dl className="space-y-1.5">
        {filas.map(f => (
          <div key={f.etiqueta} className="flex flex-wrap items-baseline justify-between gap-x-3 text-apoyo">
            <dt className="text-muted-foreground">{f.etiqueta}</dt>
            <dd className="font-semibold tabular-nums text-foreground">
              {f.valor}
              {f.nota && <span className="ml-2 font-normal text-micro text-muted-foreground">{f.nota}</span>}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

export default function ScoreBreakdown({ row }: ScoreBreakdownProps) {
  if (row.value_grupo) return <ComoSaleLaNota row={row} />
  const items = buildContributions(row)
  if (items.length === 0) return null

  const positives = items.filter(i => i.positive)
  const negatives = items.filter(i => !i.positive)

  return (
    <div>
      <h4 className="etiqueta-seccion mb-2">
        Breakdown del Score
      </h4>
      <div className="flex flex-wrap gap-1.5">
        {items.map((item, i) => (
          <span
            key={i}
            className={`inline-flex items-center gap-1 text-micro font-medium px-2 py-0.5 rounded-full border ${
              item.positive
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/25'
                : 'bg-red-500/10 text-red-400 border-red-500/25'
            }`}
          >
            <span>{item.positive ? '+' : ''}{item.value.toFixed(1)}</span>
            <span className="opacity-70">{item.label}</span>
          </span>
        ))}
      </div>
      {(positives.length > 0 || negatives.length > 0) && (
        <div className="mt-2 flex items-center gap-3 text-micro text-muted-foreground">
          <span className="text-emerald-400">
            Positivo: +{positives.reduce((s, i) => s + i.value, 0).toFixed(1)}pts
          </span>
          <span className="text-red-400">
            Negativo: {negatives.reduce((s, i) => s + i.value, 0).toFixed(1)}pts
          </span>
          {row.days_in_list != null && row.days_in_list > 0 && (
            <span className="text-amber-400">
              {row.days_in_list}d en lista
            </span>
          )}
        </div>
      )}
    </div>
  )
}
