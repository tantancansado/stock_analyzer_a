import { cn } from '@/lib/utils'

/**
 * Las cifras clave de una página.
 *
 * Treinta y un ficheros pintaban esto a mano y ninguno igual que otro: cuatro
 * tarjetas `.glass` con etiqueta en versalitas espaciadas, número en
 * `text-cifra font-extrabold` y una línea de apoyo. Por eso la app no se sentía
 * diseñada — cada página se inventaba su versión de lo mismo.
 *
 * Tres decisiones, y ninguna es de gusto:
 *
 * 1. NO van en tarjeta. En una interfaz densa la caja no agrupa: agrupa el
 *    aire. Cuatro cifras dentro de cuatro cajas iguales, encima de otra caja
 *    con contadores y otra con un aviso, son cuatro rectángulos compitiendo
 *    entre sí y ninguno gana. La regla que se sigue aquí: si necesitas un
 *    borde, probablemente lo que necesitas es más espacio.
 *
 * 2. La etiqueta va en frase, no en VERSALITAS ESPACIADAS. Las versalitas con
 *    `tracking-widest` son idioma de panel de control de los 2010: gritan sin
 *    jerarquizar, y a 11px además se leen peor.
 *
 * 3. La unidad pesa MENOS que el valor. «45.1/100» con el «/100» en el mismo
 *    peso que el número compite con él; en gris y regular, el ojo lee primero
 *    la cifra y luego la escala. Es de las pocas cosas que separan una interfaz
 *    financiera creíble de una que parece una maqueta.
 *
 * Y las cifras van tabulares (`tabular-nums`) para que al cambiar de valor no
 * bailen de sitio.
 */

export type TonoCifra = 'favor' | 'aviso' | 'alarma' | 'neutro'

const TONO: Record<TonoCifra, string> = {
  favor:  'text-success',
  aviso:  'text-warn',
  alarma: 'text-danger',
  neutro: 'text-foreground',
}

export interface Cifra {
  readonly etiqueta: string
  readonly valor: React.ReactNode
  /** «%», «/100», «pts»… Se pinta más ligero y en gris, detrás del valor. */
  readonly unidad?: string
  /** Una línea de contexto debajo. */
  readonly sub?: React.ReactNode
  readonly tono?: TonoCifra
}

export default function CifrasClave({
  cifras, cargando = false, className = '',
}: {
  readonly cifras: readonly Cifra[]
  /** Esqueleto mientras llega el dato, con la MISMA maqueta: sin esto la
      página salta de sitio al cargar. */
  readonly cargando?: boolean
  readonly className?: string
}) {
  if (cifras.length === 0) return null

  return (
    <div
      className={cn(
        // Separador de pelo entre columnas en vez de cuatro cajas. En móvil
        // van de dos en dos: cuatro en fila a 390px deja 90px por cifra y el
        // número se parte.
        'grid grid-cols-2 gap-x-6 gap-y-6 sm:flex sm:flex-wrap sm:gap-x-10 mb-7',
        className,
      )}
    >
      {cifras.map(({ etiqueta, valor, unidad, sub, tono }, i) => (
        <div
          key={etiqueta}
          className={cn(
            'min-w-0',
            // La línea divisoria solo entre columnas, y solo donde hay sitio.
            i > 0 && 'sm:border-l sm:border-border/60 sm:pl-10',
          )}
        >
          <div className="text-mini font-medium text-muted-foreground mb-1.5">{etiqueta}</div>
          {cargando ? (
            <div className="h-[1.875rem] w-16 rounded-md bg-muted animate-pulse" />
          ) : (
          <div className="flex items-baseline gap-1">
            <span className={cn(
              'text-cifra font-semibold tracking-tight tabular-nums leading-none',
              TONO[tono ?? 'neutro'],
            )}>
              {valor}
            </span>
            {unidad && (
              <span className="text-titulo font-normal text-muted-foreground leading-none">{unidad}</span>
            )}
          </div>
          )}
          {sub && <div className="text-mini text-muted-foreground mt-1.5">{sub}</div>}
        </div>
      ))}
    </div>
  )
}
