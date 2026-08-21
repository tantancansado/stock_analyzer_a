/**
 * Línea de payoff del LEAPS: strike, precio actual, break-even y (si hay
 * target de analistas) el precio objetivo, todos en una misma recta de precio.
 *
 * Antes esto eran 6 números en un grid (Delta, Leverage, Break-even, B/E move,
 * Acción, target...) que había que leer y componer mentalmente para saber una
 * cosa: "¿cuánto tiene que subir la acción para que esto no pierda, y cuánto
 * me queda de colchón ya ganado?". La línea lo responde de un vistazo — es la
 * misma lectura que un gráfico de opciones de un bróker, pero con solo los
 * cuatro puntos que importan para un deep-ITM comprado (no vendido, sin
 * segunda pata).
 *
 * Los números siguen todos en el grid de Metric de abajo — esto no los
 * sustituye, les da un mapa antes de leerlos.
 */

type Props = {
  strike: number
  spot: number
  breakeven: number
  target?: number | null
  className?: string
}

const fmt = (n: number) =>
  n >= 1000 ? n.toLocaleString('es-ES', { maximumFractionDigits: 0 })
            : n.toLocaleString('es-ES', { maximumFractionDigits: 2 })

export default function LeapsPayoffLine({ strike, spot, breakeven, target, className = '' }: Readonly<Props>) {
  if (!strike || !spot || !breakeven) return null

  const puntos = [
    { v: strike, etiqueta: 'Strike' },
    { v: spot, etiqueta: 'Hoy' },
    { v: breakeven, etiqueta: 'Empate' },
    ...(target != null && target > 0 ? [{ v: target, etiqueta: 'Target' }] : []),
  ]
  const lo = Math.min(...puntos.map(p => p.v))
  const hi = Math.max(...puntos.map(p => p.v))
  const aire = (hi - lo) * 0.12 || 1
  const escalaMin = lo - aire
  const escalaMax = hi + aire
  const pos = (v: number) => ((v - escalaMin) / (escalaMax - escalaMin)) * 100

  const posStrike = pos(strike)
  const posBreakeven = pos(breakeven)
  const posSpot = pos(spot)
  const posTarget = target != null ? pos(target) : null

  return (
    <div className={`w-full ${className}`}>
      <div className="relative h-2 rounded-full bg-red-500/15">
        {/* Desde el strike (donde arranca el valor intrínseco) hasta el
            break-even: es la zona ya cubierta por el precio actual, en verde
            si spot > breakeven, en ámbar si aún no ha llegado */}
        <div
          className="absolute inset-y-0 rounded-full bg-emerald-500/25"
          style={{ left: `${Math.min(posStrike, posBreakeven)}%`, width: `${Math.abs(posBreakeven - posStrike)}%` }}
        />
        {/* Zona de pérdida: desde break-even hacia arriba no hay pérdida, así
            que se marca la franja INVERSA — de escalaMin hasta break-even es
            "por debajo de esto, pierdes al vencimiento" */}
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-red-500/20"
          style={{ width: `${posBreakeven}%` }}
        />
        {target != null && (
          <div
            className="absolute top-1/2 h-3.5 w-[2px] -translate-y-1/2 -translate-x-1/2 rounded-full bg-violet-400"
            style={{ left: `${posTarget}%` }}
            title={`Target analistas: ${fmt(target)}`}
          />
        )}
        <div
          className="absolute top-1/2 h-3 w-[2px] -translate-y-1/2 -translate-x-1/2 rounded-full bg-amber-400"
          style={{ left: `${posBreakeven}%` }}
          title={`Break-even: ${fmt(breakeven)}`}
        />
        <div
          className="absolute top-1/2 h-3 w-[2px] -translate-y-1/2 -translate-x-1/2 rounded-full bg-muted-foreground/50"
          style={{ left: `${posStrike}%` }}
          title={`Strike: ${fmt(strike)}`}
        />
        {/* Precio actual: el marcador sólido, el que se encuentra primero */}
        <div
          className="absolute top-1/2 h-4 w-[3px] -translate-y-1/2 -translate-x-1/2 rounded-full bg-foreground shadow-[0_0_0_2px_hsl(var(--background))]"
          style={{ left: `${posSpot}%` }}
          title={`Precio actual: ${fmt(spot)}`}
        />
      </div>

      <div className="mt-1.5 flex flex-wrap items-baseline gap-x-3 gap-y-0.5 text-[0.58rem] tabular-nums">
        <span className="inline-flex items-center gap-1">
          <span className="h-2 w-[2px] rounded-full bg-muted-foreground/50" />
          <span className="text-muted-foreground/70">Strike</span>
          <span className="font-semibold text-foreground/80">{fmt(strike)}</span>
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="h-2 w-[2px] rounded-full bg-foreground" />
          <span className="text-muted-foreground/70">Hoy</span>
          <span className="font-semibold text-foreground/80">{fmt(spot)}</span>
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="h-2 w-[2px] rounded-full bg-amber-400" />
          <span className="text-muted-foreground/70">Empate</span>
          <span className="font-semibold text-foreground/80">{fmt(breakeven)}</span>
        </span>
        {target != null && target > 0 && (
          <span className="inline-flex items-center gap-1">
            <span className="h-2 w-[2px] rounded-full bg-violet-400" />
            <span className="text-muted-foreground/70">Target</span>
            <span className="font-semibold text-foreground/80">{fmt(target)}</span>
          </span>
        )}
        <span className={`ml-auto font-semibold ${spot >= breakeven ? 'text-emerald-400' : 'text-amber-400'}`}>
          {spot >= breakeven
            ? `+${(((spot - breakeven) / breakeven) * 100).toFixed(1)}% de colchón ya ganado`
            : `necesita +${(((breakeven - spot) / spot) * 100).toFixed(1)}% para empatar`}
        </span>
      </div>
    </div>
  )
}
