import { usePersonalPortfolio } from '@/context/PersonalPortfolioContext'

interface Props {
  ticker: string
  showShares?: boolean
  className?: string
}

/**
 * Shows a small "En cartera" badge when the user owns this ticker.
 * Optionally shows the number of shares.
 */
export default function OwnedBadge({ ticker, showShares = false, className = '' }: Props) {
  const { getPosition } = usePersonalPortfolio()
  const pos = getPosition(ticker)
  if (!pos) return null

  return (
    <span
      className={`inline-flex items-center gap-1 text-[0.58rem] font-bold px-1.5 py-0.5 rounded-full
        bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 uppercase tracking-wide
        whitespace-nowrap ${className}`}
      title={`En tu cartera: ${pos.shares} acc · coste ${pos.currency === 'EUR' ? '€' : '$'}${pos.avg_price.toFixed(2)}`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" />
      {showShares ? `${pos.shares} acc` : 'En cartera'}
    </span>
  )
}
