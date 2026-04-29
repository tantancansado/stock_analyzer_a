import type { ValueOpportunity } from '../api/client'

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
  if (row.profitability_penalty != null && row.profitability_penalty !== 0) {
    items.push({ label: 'Rent. baja', value: -Math.abs(row.profitability_penalty), positive: false })
  }

  return items.sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
}

export default function ScoreBreakdown({ row }: ScoreBreakdownProps) {
  const items = buildContributions(row)
  if (items.length === 0) return null

  const positives = items.filter(i => i.positive)
  const negatives = items.filter(i => !i.positive)

  return (
    <div>
      <h4 className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground mb-2">
        Breakdown del Score
      </h4>
      <div className="flex flex-wrap gap-1.5">
        {items.map((item, i) => (
          <span
            key={i}
            className={`inline-flex items-center gap-1 text-[0.65rem] font-medium px-2 py-0.5 rounded-full border ${
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
        <div className="mt-2 flex items-center gap-3 text-[0.6rem] text-muted-foreground">
          <span className="text-emerald-400">
            Positivo: +{positives.reduce((s, i) => s + i.value, 0).toFixed(1)}pts
          </span>
          <span className="text-red-400">
            Negativo: {negatives.reduce((s, i) => s + i.value, 0).toFixed(1)}pts
          </span>
          {row.days_in_list != null && row.days_in_list > 0 && (
            <span className="text-amber-400/70">
              {row.days_in_list}d en lista
            </span>
          )}
        </div>
      )}
    </div>
  )
}
