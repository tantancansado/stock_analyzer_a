/**
 * Barra de valoración: dónde está el precio dentro de su rango de 52 semanas
 * y dónde caen los precios objetivo.
 *
 * Es el gráfico que faltaba para la forma de decidir de esta app: se vende a
 * PRECIO OBJETIVO por valoración, no a un % fijo. Los tres objetivos (consenso
 * de analistas, DCF, múltiplo × BPA) ya se calculan y se publican en el CSV,
 * pero solo se veían como números sueltos en una tabla, donde no dicen nada:
 * "objetivo 213,25" no responde ni "¿cuánto queda?" ni "¿está barata ahora?".
 * Puestos sobre el rango real del año, ambas se leen sin pensar.
 *
 * LA ESCALA ES SIEMPRE EL RANGO DE 52 SEMANAS, nunca los objetivos. Dos
 * motivos, y los dos se vieron al probar la primera versión, que estiraba la
 * escala para que cupiera todo:
 *
 *   1. Cada tarjeta salía con una escala distinta, así que la posición del
 *      marcador no significaba lo mismo en dos tarjetas seguidas y la lista
 *      dejaba de ser comparable de un vistazo — que es justo para lo que sirve.
 *   2. Un objetivo roto arrasaba con el dibujo: el DCF de MSFT sale a $94 con
 *      la acción a $484, y esos $94 comprimían el rango real (349-554) contra
 *      el borde derecho hasta hacerlo ilegible.
 *
 * El mínimo y el máximo del año son un hecho de mercado; los objetivos son
 * modelos, y un modelo roto no debe poder romper el gráfico. Lo que se sale se
 * dibuja clavado en el borde con una punta de flecha: "cae fuera, por ese
 * lado" es la lectura correcta y honesta, y no cuesta un píxel más.
 *
 * Los tres objetivos se dibujan juntos a propósito. Cuando coinciden, la tesis
 * es sólida; cuando el DCF dice 94 y el consenso 570, la dispersión ES la
 * información — y un solo número la habría escondido.
 *
 * Sin dato → no se dibuja el marcador. Nunca un objetivo inventado.
 */

type Props = {
  precio: number
  /** Distancia al máximo de 52s en % (negativa: -32.3 = un 32,3% por debajo) */
  pctDesdeMax: number | null | undefined
  /** Distancia al mínimo de 52s en % (positiva: 31.5 = un 31,5% por encima) */
  pctDesdeMin: number | null | undefined
  objetivoAnalista?: number | null
  objetivoDcf?: number | null
  objetivoPe?: number | null
  /** Solo la pista, sin extremos ni leyenda: para filas de lista apretadas */
  compacta?: boolean
  className?: string
}

const COLORES = {
  Consenso: 'hsl(152 70% 45%)',
  DCF: 'hsl(266 70% 62%)',
  'P/E': 'hsl(38 92% 55%)',
} as const

/** Un objetivo que cae fuera del año se clava en el borde correspondiente. */
function fueraDelAnio(pos: number): 'arriba' | 'abajo' | null {
  if (pos > 100) return 'arriba'
  if (pos < 0) return 'abajo'
  return null
}

const fmt = (n: number) =>
  n >= 1000 ? n.toLocaleString('es-ES', { maximumFractionDigits: 0 })
            : n.toLocaleString('es-ES', { maximumFractionDigits: 2 })

export default function ValuationBar({
  precio, pctDesdeMax, pctDesdeMin,
  objetivoAnalista, objetivoDcf, objetivoPe,
  compacta = false, className = '',
}: Readonly<Props>) {
  // El CSV no trae el máximo y el mínimo en dólares, trae la distancia a cada
  // uno. Se reconstruyen desde el precio actual, que sí está siempre.
  if (!precio || precio <= 0) return null
  if (pctDesdeMax == null || pctDesdeMin == null) return null

  const max = precio / (1 + pctDesdeMax / 100)
  const min = precio / (1 + pctDesdeMin / 100)
  if (!Number.isFinite(max) || !Number.isFinite(min) || max <= min) return null

  const objetivos = ([
    ['Consenso', objetivoAnalista],
    ['DCF', objetivoDcf],
    ['P/E', objetivoPe],
  ] as const)
    .filter((o): o is readonly [keyof typeof COLORES, number] =>
      o[1] != null && Number.isFinite(o[1]) && o[1] > 0)
    .map(([etiqueta, valor]) => {
      const bruto = ((valor - min) / (max - min)) * 100
      return {
        etiqueta,
        valor,
        color: COLORES[etiqueta],
        pos: Math.min(100, Math.max(0, bruto)),
        fuera: fueraDelAnio(bruto),
        recorrido: (valor / precio - 1) * 100,
        desplazado: 0,
      }
    })

  // Cuántos van ya clavados en cada borde, para escalonarlos
  const clavados = { arriba: 0, abajo: 0 }
  for (const o of objetivos) {
    if (o.fuera) o.desplazado = clavados[o.fuera]++
  }

  const posPrecio = Math.min(100, Math.max(0, ((precio - min) / (max - min)) * 100))
  const enRango = Math.round(((precio - min) / (max - min)) * 100)

  return (
    <div className={`w-full ${className}`}>
      {/* Pista = el año entero. Izquierda el mínimo, derecha el máximo. */}
      <div className="relative h-1.5 rounded-full bg-primary/20">
        {/* Recorrido desde el mínimo hasta hoy: da el "cuánto ha subido ya" */}
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-primary/40"
          style={{ width: `${posPrecio}%` }}
        />
        {objetivos.map(o => (
          <div
            key={o.etiqueta}
            className="absolute top-1/2 -translate-y-1/2"
            style={{
              left: `${o.pos}%`,
              // Dos objetivos fuera por el mismo lado se clavan en la MISMA
              // coordenada y la de arriba tapa a la de abajo: MCO tiene el
              // consenso en 560 y el DCF en 631, ambos por encima del máximo
              // del año, y solo se veía una flecha. Se escalonan hacia dentro.
              ...(o.fuera && { [o.fuera === 'arriba' ? 'marginLeft' : 'marginRight']: `${o.desplazado * -6}px` }),
            }}
            title={`${o.etiqueta}: ${fmt(o.valor)}${o.fuera ? ' (fuera del rango de 52 semanas)' : ''}`}
          >
            {o.fuera ? (
              // Clavado en el borde: el valor real cae fuera del año
              <span
                className="block h-0 w-0 border-y-[4px] border-y-transparent"
                style={o.fuera === 'arriba'
                  ? { borderLeft: `5px solid ${o.color}`, marginLeft: '-5px' }
                  : { borderRight: `5px solid ${o.color}` }}
              />
            ) : (
              <span
                className="block h-3 w-[2px] -translate-x-1/2 rounded-full"
                style={{ background: o.color }}
              />
            )}
          </div>
        ))}
        {/* Precio actual: el único marcador sólido y con halo, para que sea el
            que el ojo encuentra primero */}
        <div
          className="absolute top-1/2 h-3.5 w-[3px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-foreground shadow-[0_0_0_2px_hsl(var(--background))]"
          style={{ left: `${posPrecio}%` }}
          title={`Precio actual: ${fmt(precio)}`}
        />
      </div>

      {!compacta && (
        <>
          <div className="mt-1 flex items-baseline justify-between gap-2 text-[0.55rem] tabular-nums text-muted-foreground/60">
            <span>{fmt(min)}</span>
            <span className="text-muted-foreground/45">{enRango}% del rango 52s</span>
            <span>{fmt(max)}</span>
          </div>

          {objetivos.length > 0 && (
            <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[0.58rem] tabular-nums">
              {objetivos.map(o => (
                <span key={o.etiqueta} className="inline-flex items-center gap-1">
                  <span className="h-2 w-[2px] rounded-full" style={{ background: o.color }} />
                  <span className="text-muted-foreground/70">{o.etiqueta}</span>
                  <span className="font-semibold text-foreground/80">{fmt(o.valor)}</span>
                  <span className={o.recorrido >= 0 ? 'text-emerald-400/80' : 'text-red-400/80'}>
                    {o.recorrido >= 0 ? '+' : ''}{o.recorrido.toFixed(0)}%
                  </span>
                </span>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
