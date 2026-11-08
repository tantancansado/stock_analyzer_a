import { Ruler } from 'lucide-react'
import { fetchPesosValue, type PesoIdea } from '../api/client'
import { useApi } from '../hooks/useApi'
import TickerLogo from '../components/TickerLogo'
import EmptyState from '../components/EmptyState'
import PageHeader from '@/components/PageHeader'
import PageShell from '@/components/PageShell'
import CifrasClave from '../components/CifrasClave'

/**
 * Cuánto poner en cada idea de Value US (position_sizer.py).
 *
 * Era un Kelly sobre todo el tracker que daba casi el mismo número a todas, con
 * stops técnicos y sobre la lista vieja de cinco dimensiones. Ahora: una posición
 * completa por idea en Prioridad, menos si se mueve mucho, y dos como mucho por
 * ciclo. Sin dinero nuevo para Observar.
 */

const pct = (x: number) => `${x.toLocaleString('es-ES', { maximumFractionDigits: 1 })} %`

export default function PositionSizing() {
  const { data, loading, error } = useApi<PesoIdea[]>(() => fetchPesosValue().then(d => ({ data: d })), [])

  // La cabecera se pinta también mientras carga o si falla. Ver PageShell.
  const cabecera = {
    title: 'Peso en cartera',
    subtitle: 'Cuánto poner en cada idea de Value US',
  } as const
  if (loading || error) return <PageShell {...cabecera} loading={loading} error={error} />

  const filas = data ?? []
  const prioridad = filas.filter(f => f.value_grupo === 'PRIORIDAD')
  const conPeso = prioridad.filter(f => (f.peso_objetivo_pct ?? 0) > 0)
  const porCiclo = prioridad.filter(f => f.peso_objetivo_pct === 0)
  const total = conPeso.reduce((t, f) => t + (f.peso_objetivo_pct ?? 0), 0)

  return (
    <>
      <PageHeader {...cabecera} />

      <p className="text-cuerpo text-muted-foreground leading-relaxed mb-5 max-w-3xl">
        Cada idea en Prioridad vale una posición completa, el 5 % de la cartera, porque medido no
        se puede saber cuál de dos Prioridades ganará más. Lo que sí se ajusta es el riesgo: la que
        se mueve el doble que la media pesa la mitad, y de las que se mueven igual (el mismo ciclo)
        entran dos como mucho, las más baratas. Observar no recibe dinero nuevo.
      </p>

      {prioridad.length === 0 ? (
        <div className="glass rounded-2xl">
          <EmptyState
            icon={<Ruler size={32} strokeWidth={1.5} />}
            title="Hoy no hay ideas en Prioridad"
            subtitle="Sin Prioridad no hay a qué dar peso: el dinero se queda en la base de la cartera"
          />
        </div>
      ) : (
        <>
          <CifrasClave cifras={[
            { etiqueta: 'Ideas con peso', valor: conPeso.length, sub: 'en Prioridad' },
            { etiqueta: 'Entre todas', valor: total.toLocaleString('es-ES', { maximumFractionDigits: 1 }), unidad: '%', sub: 'de la cartera' },
            { etiqueta: 'Fuera por ciclo', valor: porCiclo.length, sub: 'ya hay dos que se mueven igual' },
          ]} />

          <ul className="glass rounded-2xl divide-y divide-border/30">
            {prioridad.map(f => (
              <li key={f.ticker} className="flex items-start gap-3 px-4 py-3">
                <TickerLogo ticker={f.ticker} size="sm" className="mt-0.5 shrink-0" />
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="font-mono font-bold text-cuerpo text-foreground">{f.ticker}</span>
                    <span className="font-bold text-cuerpo tabular-nums text-foreground">
                      {f.peso_objetivo_pct == null ? '—' : f.peso_objetivo_pct > 0 ? pct(f.peso_objetivo_pct) : 'Nada'}
                    </span>
                  </div>
                  <p className="text-mini text-muted-foreground leading-relaxed mt-0.5">{f.peso_motivo}</p>
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
    </>
  )
}
