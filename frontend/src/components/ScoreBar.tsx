import { useState, useEffect } from 'react'

interface Props {
  score: number | null | undefined
  max?: number
}

function getColor(score: number): string {
  if (score >= 70) return '#10b981'
  if (score >= 55) return '#3b82f6'
  if (score >= 40) return '#f59e0b'
  return '#ef4444'
}

export default function ScoreBar({ score, max = 100 }: Props) {
  const [animPct, setAnimPct] = useState(0)
  const targetPct = score == null ? 0 : Math.min((score / max) * 100, 100)

  // Animate mask from 100% → (100 - target)% whenever score changes
  useEffect(() => {
    if (score == null) return
    setAnimPct(0)
    // Double-RAF: first frame paints mask=100% (hidden), second triggers the CSS transition
    const id1 = requestAnimationFrame(() => {
      const id2 = requestAnimationFrame(() => setAnimPct(targetPct))
      return () => cancelAnimationFrame(id2)
    })
    return () => cancelAnimationFrame(id1)
  }, [score]) // eslint-disable-line react-hooks/exhaustive-deps

  if (score == null) return <span className="text-muted-foreground">—</span>

  const color = getColor(score)

  return (
    <span className="score-bar">
      <span
        style={{
          fontWeight: 700,
          color,
          fontSize: '0.84rem',
          minWidth: 36,
          fontVariantNumeric: 'tabular-nums',
          letterSpacing: '-0.01em',
        }}
      >
        {score.toFixed(1)}
      </span>
      {/* Track has full red→amber→green gradient; mask covers the unfilled right portion */}
      <span className="score-track">
        <span
          className="score-mask"
          style={{ width: `${100 - animPct}%` }}
        />
      </span>
    </span>
  )
}
