import type { ReactNode } from 'react'
import { Info } from 'lucide-react'
import { cn } from '@/lib/utils'

/**
 * Un dato con su rótulo, DENTRO de una tarjeta o una fila.
 *
 * No confundir con `CifrasClave`, que son las cifras de cabecera de una
 * página: aquellas son el titular y van grandes, sin caja y separadas por aire;
 * esta es un dato de apoyo dentro de algo que ya es un objeto (una tarjeta de
 * idea, un modal de tesis, una fila de comparación). Mismo esqueleto —rótulo
 * arriba, valor debajo— y por eso se confundían, pero distinto peso: si una
 * métrica de tarjeta se pinta al tamaño de una cifra de cabecera, la tarjeta
 * pasa a competir con el título de la página.
 *
 * Había 21 repartidas por 12 ficheros, cada una con su tamaño y su peso.
 */

export type TonoMetrica = 'favor' | 'aviso' | 'alarma' | 'neutro' | 'apagado'

const TONO: Record<TonoMetrica, string> = {
  favor:   'text-success',
  aviso:   'text-warn',
  alarma:  'text-danger',
  neutro:  'text-foreground',
  apagado: 'text-muted-foreground',
}

export default function Metrica({
  etiqueta, valor, pista, tono = 'neutro', className,
}: {
  readonly etiqueta: ReactNode
  readonly valor: ReactNode
  /** Texto de ayuda; pinta un icono de información junto al rótulo. */
  readonly pista?: string
  readonly tono?: TonoMetrica
  readonly className?: string
}) {
  return (
    <div className={cn('min-w-0', className)}>
      <div className="etiqueta-seccion mb-0.5 flex items-center gap-1">
        {etiqueta}
        {pista && (
          <span title={pista} className="inline-flex">
            <Info size={12} className="opacity-40 shrink-0" />
          </span>
        )}
      </div>
      {/* `font-semibold` y no `bold`: el dato ya destaca por ir en cifras
          tabulares bajo un rótulo en gris. Añadir peso encima es el segundo
          dispositivo de énfasis para lo mismo. */}
      <div className={cn('text-cuerpo font-semibold tabular-nums leading-none', TONO[tono])}>
        {valor}
      </div>
    </div>
  )
}
