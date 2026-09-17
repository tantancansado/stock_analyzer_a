import { useEffect, useState } from 'react'

import { fetchPortfolioTracker, type AlphaStat, type PortfolioSummary } from '../api/client'

/**
 * Cómo le ha ido de verdad a esta lista, contra comprar el índice.
 *
 * El dato existía y estaba bien calculado (`summary.json` → `alpha`), pero se
 * pintaba SOLO en la página de Cartera. En Value US, que es donde se decide
 * la compra, se veía el score de cada pick y nada sobre si la estrategia bate
 * al índice o no.
 *
 * El 17-sep-2026 el resumen decía «61,5% de aciertos, +3,15% de media» —que
 * suena bien— mientras el índice hacía +5,27% en el mismo periodo. Acertar la
 * dirección y quedarse por debajo del índice son compatibles, y el segundo
 * dato es el que dice si merece la pena el trabajo.
 */
export default function RendimientoReal({ fuente = 'alpha_us' }: { fuente?: 'alpha_us' | 'alpha_eu' }) {
  const [pf, setPf] = useState<PortfolioSummary | null>(null)

  useEffect(() => {
    let vivo = true
    fetchPortfolioTracker()
      .then(r => { if (vivo) setPf((r as { data?: PortfolioSummary })?.data ?? (r as PortfolioSummary)) })
      .catch(() => { /* sin tracker no se pinta nada: es un añadido, no un bloqueo */ })
    return () => { vivo = false }
  }, [])

  const grupo = pf?.[fuente] ?? pf?.alpha
  const a: AlphaStat | undefined = grupo?.['90d']
  // Menos de cinco señales cerradas no dice nada, y publicar un porcentaje sin
  // su n es el error que más veces se ha repetido en esta app.
  if (!a || (a.count ?? 0) < 5 || a.avg_alpha == null) return null

  const gana = a.avg_alpha > 0
  const color = gana ? 'text-emerald-400' : 'text-red-400'

  return (
    <div className="glass rounded-md px-3 py-2 mb-4 text-mini flex flex-wrap items-center gap-x-4 gap-y-1">
      <span className="text-muted-foreground">Cómo le ha ido a esta lista, a 90 días:</span>
      <span>
        señales <strong className="text-foreground">{a.avg_signal_return?.toFixed(1)}%</strong>
        {' · '}índice <strong className="text-foreground">{a.avg_benchmark_return?.toFixed(1)}%</strong>
      </span>
      <span className={color}>
        <strong>{gana ? '+' : ''}{a.avg_alpha.toFixed(2)}%</strong> contra el índice
      </span>
      {a.positive_alpha_rate != null && (
        <span className="text-muted-foreground">
          lo baten {a.positive_alpha_rate.toFixed(0)}% de las señales
        </span>
      )}
      <span className="text-muted-foreground">n={a.count}</span>
    </div>
  )
}
