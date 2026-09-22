import { useApi } from '../hooks/useApi'
import { fetchCalibration, type CalibrationBucket, type CalibrationRegime, type CalibrationSector, type CalibrationStats } from '../api/client'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import PageHeader from '../components/PageHeader'
import PageShell from '@/components/PageShell'
import { nlRegimen } from '@/lib/nl'

function WinBar({ value, max = 80 }: { value: number | null | undefined; max?: number }) {
  const v = value ?? 0
  const pct = Math.min((v / max) * 100, 100)
  const color = v >= 50 ? 'var(--success)' : v >= 35 ? 'var(--warn)' : 'var(--danger)'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 rounded-full" style={{ background: 'rgba(255,255,255,0.08)' }}>
        <div className="h-2 rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-mini w-10 text-right" style={{ color }}>{v.toFixed(1)}%</span>
    </div>
  )
}

function ReturnBadge({ value }: { value: number | null | undefined }) {
  const v = value ?? 0
  const color = v > 0 ? 'var(--success)' : v > -3 ? 'var(--warn)' : 'var(--danger)'
  return <span style={{ color }} className="text-mini font-mono">{v > 0 ? '+' : ''}{v.toFixed(2)}%</span>
}

function ScoreBucketsTable({ buckets }: { buckets: CalibrationBucket[] }) {
  return (
    <div className="table-x-wrap">
      <table className="w-full text-cuerpo">
        <thead>
          <tr className="border-b border-foreground/10 text-left">
            <th className="pb-2 text-mini text-muted-foreground font-medium">Score</th>
            <th className="pb-2 text-mini text-muted-foreground font-medium text-right">Señales</th>
            <th className="pb-2 text-mini text-muted-foreground font-medium pl-4">Win Rate 14d</th>
            <th className="pb-2 text-mini text-muted-foreground font-medium text-right">Retorno Medio</th>
            <th className="pb-2 text-mini text-muted-foreground font-medium text-right">Mediana</th>
          </tr>
        </thead>
        <tbody>
          {buckets.map(b => (
            <tr key={b.range} className="border-b border-foreground/5 hover:bg-foreground/5 transition-colors">
              <td className="py-2.5 font-mono font-medium text-foreground">{b.range}</td>
              <td className="py-2.5 text-right text-muted-foreground">{b.count}</td>
              <td className="py-2.5 pl-4 min-w-[160px]">
                <WinBar value={b.win_rate} />
              </td>
              <td className="py-2.5 text-right">
                <ReturnBadge value={b.avg_return} />
              </td>
              <td className="py-2.5 text-right">
                <ReturnBadge value={b.median_return} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function RegimeTable({ rows }: { rows: CalibrationRegime[] }) {
  return (
    <div className="table-x-wrap">
      <table className="w-full text-cuerpo">
        <thead>
          <tr className="border-b border-foreground/10 text-left">
            <th className="pb-2 text-mini text-muted-foreground font-medium">Régimen</th>
            <th className="pb-2 text-mini text-muted-foreground font-medium text-right">Señales</th>
            <th className="pb-2 text-mini text-muted-foreground font-medium pl-4">Win Rate 14d</th>
            <th className="pb-2 text-mini text-muted-foreground font-medium text-right">Retorno Medio</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.regime} className="border-b border-foreground/5 hover:bg-foreground/5 transition-colors">
              {/* `nlRegimen`, igual que la tarjeta de «Régimen más favorable»
                  ocho líneas más arriba: la misma página enseñaba «Alcista
                  confirmada» en un sitio y «CONFIRMED_UPTREND» en el otro. Y
                  el SNAKE_CASE en inglés era, además, la columna que empujaba
                  la tabla fuera de una pantalla de 390px. */}
              <td className="py-2.5 font-medium text-foreground">
                {nlRegimen(r.regime) || r.regime}
              </td>
              <td className="py-2.5 text-right text-muted-foreground">{r.count}</td>
              <td className="py-2.5 pl-4 min-w-[160px]">
                <WinBar value={r.win_rate} />
              </td>
              <td className="py-2.5 text-right">
                <ReturnBadge value={r.avg_return} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function SectorTable({ rows }: { rows: CalibrationSector[] }) {
  return (
    <div className="table-x-wrap">
      <table className="w-full text-cuerpo">
        <thead>
          <tr className="border-b border-foreground/10 text-left">
            <th className="pb-2 text-mini text-muted-foreground font-medium">Sector</th>
            <th className="pb-2 text-mini text-muted-foreground font-medium text-right">Señales</th>
            <th className="pb-2 text-mini text-muted-foreground font-medium pl-4">Win Rate 14d</th>
            <th className="pb-2 text-mini text-muted-foreground font-medium text-right">Retorno Medio</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.sector} className="border-b border-foreground/5 hover:bg-foreground/5 transition-colors">
              <td className="py-2.5 text-foreground/90">{r.sector}</td>
              <td className="py-2.5 text-right text-muted-foreground">{r.count}</td>
              <td className="py-2.5 pl-4 min-w-[160px]">
                <WinBar value={r.win_rate} />
              </td>
              <td className="py-2.5 text-right">
                <ReturnBadge value={r.avg_return} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ScoreInsight({ buckets }: { buckets: CalibrationBucket[] }) {
  if (buckets.length < 2) return null
  const sorted = [...buckets].sort((a, b) => b.win_rate - a.win_rate)
  const best = sorted[0]
  const worst = sorted[sorted.length - 1]
  const hasMonotone = buckets.every((b, i) =>
    i === 0 || b.win_rate >= buckets[i - 1].win_rate
  )
  return (
    <div className="mt-4 p-3 rounded-lg text-mini text-foreground/70" style={{ background: 'rgba(255,255,255,0.04)' }}>
      {/* En JSX, no en una plantilla de texto: React escapa las cadenas, así
          que el `<b>` se leía literal en pantalla —«Mejor bucket: <b>70-75</b>
          (100% win rate)»— en vez de poner el rango en negrita. */}
      {hasMonotone
        ? 'El score es monotónico: a mayor score, mayor win rate.'
        : <>Mejor bucket: <b>{best.range}</b> ({best.win_rate}% win rate) · Peor:{' '}
            {worst.range} ({worst.win_rate}%)</>
      }
      {' '}El sistema es más fiable con score {'>'}={buckets.find(b => b.win_rate >= 35)?.range?.split('-')[0] || 65}pts.
    </div>
  )
}

export default function Calibration() {
  const { data, loading, error } = useApi(fetchCalibration)

  // Cabecera también mientras carga o si la API falla: si no, la pantalla
  // de error no dice en qué sección estás. Ver PageShell.
  if (loading || error || !data) return (
    <PageShell
      title="Calibración del Sistema"
      loading={loading}
      error={loading ? null : 'No hay datos de calibración aún. Se generan al final del pipeline diario.'}
    />
  )

  // Se elige por el LÍMITE INFERIOR del intervalo, no por el win rate bruto, y
  // solo entre los que tienen muestra suficiente.
  //
  // Ordenando por win rate a secas, "Mejor rango de score" era 70-75 pts con
  // un 100%… sobre CATORCE señales. Eso no es el mejor rango, es el que tuvo
  // más suerte: destacar el máximo de una muestra pequeña es exactamente cómo
  // se encuentra ruido, y este repo ya se dio un susto así (un tramo de n=8
  // que parecía perfecto estuvo a punto de convertirse en un filtro nuevo).
  //
  // El límite inferior responde a "¿cuál es el peor caso razonable?", que es
  // lo que hay que saber antes de fiarse de un tramo.
  const MUESTRA_MINIMA = 30
  const mejorPor = <T extends CalibrationStats>(filas: T[] | undefined): T | undefined =>
    [...(filas || [])]
      .filter(f => f.count >= MUESTRA_MINIMA && f.ci_low != null)
      .sort((a, b) => (b.ci_low ?? 0) - (a.ci_low ?? 0))[0]

  const bestScore = mejorPor(data.score_buckets)
  const bestSector = mejorPor(data.sector_calibration)
  const bestRegime = mejorPor(data.regime_analysis)

  return (
    <div className="p-4 md:p-6 space-y-6 max-w-5xl mx-auto">
      <PageHeader
        title="Calibración del Sistema"
        subtitle={`¿Cuándo predice bien el sistema? Análisis sobre ${data.total_completed.toLocaleString()} señales completadas.`}
      />

      {/* Summary KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {bestScore && (
          <Card className="glass border-foreground/10 min-w-0">
            <CardContent className="p-4">
              <div className="text-mini text-muted-foreground mb-1">Mejor rango de score</div>
              <div className="text-seccion font-semibold text-foreground">{bestScore.range} pts</div>
              <Badge variant="outline" className="mt-1 text-mini" style={{ color: 'var(--success)', borderColor: '#10b98144' }}>
                {bestScore.win_rate}% win rate
              </Badge>
              <div className="mt-1 text-micro text-muted-foreground tabular-nums">
                IC 95%: {bestScore.ci_low}–{bestScore.ci_high}% · {bestScore.count} señales
              </div>
            </CardContent>
          </Card>
        )}
        {bestSector && (
          <Card className="glass border-foreground/10 min-w-0">
            <CardContent className="p-4">
              <div className="text-mini text-muted-foreground mb-1">Sector más fiable</div>
              <div className="text-seccion font-semibold text-foreground truncate">{bestSector.sector}</div>
              <Badge variant="outline" className="mt-1 text-mini" style={{ color: 'var(--success)', borderColor: '#10b98144' }}>
                {bestSector.win_rate}% win rate
              </Badge>
              <div className="mt-1 text-micro text-muted-foreground tabular-nums">
                IC 95%: {bestSector.ci_low}–{bestSector.ci_high}% · {bestSector.count} señales
              </div>
            </CardContent>
          </Card>
        )}
        {bestRegime && (
          <Card className="glass border-foreground/10 min-w-0">
            <CardContent className="p-4">
              <div className="text-mini text-muted-foreground mb-1">Régimen más favorable</div>
              <div className="text-seccion font-semibold text-foreground">{nlRegimen(bestRegime.regime) || bestRegime.regime}</div>
              <Badge variant="outline" className="mt-1 text-mini" style={{ color: 'var(--success)', borderColor: '#10b98144' }}>
                {bestRegime.win_rate}% win rate
              </Badge>
              <div className="mt-1 text-micro text-muted-foreground tabular-nums">
                IC 95%: {bestRegime.ci_low}–{bestRegime.ci_high}% · {bestRegime.count} señales
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {!bestScore && !bestSector && !bestRegime && (
        <p className="text-mini text-muted-foreground">
          Todavía no hay ningún tramo con {MUESTRA_MINIMA} señales completadas, así que
          no se destaca ninguno como «el mejor»: con menos muestra, el que encabeza la
          lista suele ser el que tuvo más suerte. El detalle completo está en las
          tablas de abajo.
        </p>
      )}

      {/* Score Calibration */}
      {data.score_buckets?.length > 0 && (
        <Card className="glass border-foreground/10 min-w-0">
          <CardContent className="p-5">
            <h2 className="text-cuerpo font-semibold text-foreground mb-4">Calibración por Score VALUE</h2>
            <ScoreBucketsTable buckets={data.score_buckets} />
            <ScoreInsight buckets={data.score_buckets} />
          </CardContent>
        </Card>
      )}

      {/* Regime + Sector side by side */}
      {/* `min-w-0` en las tarjetas: un grid item vale `min-width: auto`, así
          que NO se encoge por debajo de su contenido. Las dos tablas medían
          517px dentro de una pantalla de 390 y el Card se estiraba con ellas,
          de modo que `.table-x-wrap` —que sí tiene overflow-x: auto en
          móvil— nunca llegaba a ser más estrecho que su tabla y no había
          scroll que hacer. La columna del win rate quedaba fuera y sin forma
          de alcanzarla. */}
      <div className="grid md:grid-cols-2 gap-4">
        {data.regime_analysis?.length > 0 && (
          <Card className="glass border-foreground/10 min-w-0">
            <CardContent className="p-5">
              <h2 className="text-cuerpo font-semibold text-foreground mb-4">Por Régimen de Mercado</h2>
              <RegimeTable rows={data.regime_analysis} />
            </CardContent>
          </Card>
        )}
        {data.fcf_yield_buckets?.length > 0 && (
          <Card className="glass border-foreground/10 min-w-0">
            <CardContent className="p-5">
              <h2 className="text-cuerpo font-semibold text-foreground mb-4">Por FCF Yield</h2>
              <ScoreBucketsTable buckets={data.fcf_yield_buckets} />
            </CardContent>
          </Card>
        )}
      </div>

      {/* Sector Calibration */}
      {data.sector_calibration?.length > 0 && (
        <Card className="glass border-foreground/10 min-w-0">
          <CardContent className="p-5">
            <h2 className="text-cuerpo font-semibold text-foreground mb-4">Calibración por Sector</h2>
            <SectorTable rows={data.sector_calibration} />
          </CardContent>
        </Card>
      )}

      <p className="text-mini text-muted-foreground text-right">
        Actualizado: {new Date(data.generated_at).toLocaleString('es-ES')}
      </p>
    </div>
  )
}
