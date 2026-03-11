import { useEffect, useState } from 'react'
import { AreaChart, Area, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { fetchPriceHistory, type PricePoint } from '@/api/client'
import { Loader2 } from 'lucide-react'

interface Props {
  ticker: string
  /** Pre-loaded data — skips the fetch if provided */
  data?: PricePoint[]
  height?: number
  /** Hides axes and tooltip — compact sparkline mode */
  mini?: boolean
}

export default function PriceChart({ ticker, data: external, height = 200, mini = false }: Props) {
  const [data,    setData]    = useState<PricePoint[]>(external ?? [])
  const [loading, setLoading] = useState(!external)

  useEffect(() => {
    if (external) { setData(external); return }
    setLoading(true)
    fetchPriceHistory(ticker)
      .then(r => setData(r.data.prices ?? []))
      .catch(() => setData([]))
      .finally(() => setLoading(false))
  }, [ticker, external])

  if (loading) {
    return (
      <div style={{ height }} className="flex items-center justify-center">
        <Loader2 size={14} className="animate-spin text-muted-foreground/50" />
      </div>
    )
  }

  if (!data.length) return null

  const first  = data[0]?.close ?? 0
  const last   = data[data.length - 1]?.close ?? 0
  const isUp   = last >= first
  const color  = isUp ? '#10b981' : '#ef4444'
  const gradId = `pg-${ticker.replace(/[^a-zA-Z0-9]/g, '')}`

  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 4, right: mini ? 0 : 8, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor={color} stopOpacity={0.18} />
              <stop offset="95%" stopColor={color} stopOpacity={0}    />
            </linearGradient>
          </defs>
          {!mini && (
            <XAxis
              dataKey="date"
              tick={{ fontSize: 10, fill: '#64748b' }}
              tickFormatter={d => d.slice(5)}
              interval="preserveStartEnd"
              axisLine={false}
              tickLine={false}
            />
          )}
          {!mini && (
            <YAxis
              domain={['auto', 'auto']}
              tick={{ fontSize: 10, fill: '#64748b' }}
              tickFormatter={v => `$${v}`}
              width={50}
              axisLine={false}
              tickLine={false}
            />
          )}
          {!mini && (
            <Tooltip
              contentStyle={{
                background: 'rgba(15,17,23,0.95)',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: '8px',
                fontSize: '12px',
                padding: '8px 12px',
              }}
              labelStyle={{ color: '#94a3b8', marginBottom: '2px' }}
              formatter={(v) => [`$${Number(v ?? 0).toFixed(2)}`, 'Precio']}
              labelFormatter={l => l as string}
            />
          )}
          <Area
            type="monotone"
            dataKey="close"
            stroke={color}
            strokeWidth={mini ? 1.5 : 2}
            fill={`url(#${gradId})`}
            dot={false}
            activeDot={mini ? false : { r: 3, strokeWidth: 0, fill: color }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
