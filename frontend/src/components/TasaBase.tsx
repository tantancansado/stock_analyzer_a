import { History, LifeBuoy, TriangleAlert } from 'lucide-react'

/**
 * Qué hizo ESTE valor las otras veces que estuvo ASÍ.
 *
 * El resto de la ficha describe un ESTADO —score, márgenes, en qué fase está—.
 * Esto es lo único que dice qué pasó DESPUÉS, y era justo lo que faltaba: el
 * usuario acababa preguntándolo a mano cada vez.
 *
 * Se pinta como frase, no como número suelto y de colores, por dos motivos. Uno,
 * porque lo que importa es la FORMA del reparto («o para aquí o se desploma»,
 * «cayó otro 4% de mediana») y eso no cabe en una cifra. Y dos, porque un número
 * con un color al lado se lee como un veredicto, y esto no lo es: es una tasa
 * base, no una predicción.
 */
export interface TasaBaseProps {
  frase?: string | null
  n?: number | null
  bimodal?: boolean | null
  /** Soporte real, con fecha e historial (soportes.py). */
  soporte?: string | null
  soporteAntiguo?: boolean | null
  /** Sin tarjeta, para meterla debajo de otra cosa. */
  plano?: boolean
}

export default function TasaBase({ frase, n, bimodal, soporte, soporteAntiguo, plano }: TasaBaseProps) {
  if (!frase) return null

  const pocaMuestra = n != null && n < 5
  const cuerpo = (
    <>
      <div className="flex items-center gap-1.5 mb-1.5">
        {bimodal
          ? <TriangleAlert size={12} className="text-amber-400 shrink-0" />
          : <History size={12} className="text-muted-foreground shrink-0" />}
        <span className="etiqueta-seccion">Las veces anteriores</span>
        {n != null && (
          <span className={`text-micro font-bold tabular-nums ${pocaMuestra ? 'text-amber-400' : 'text-muted-foreground'}`}>
            n={n}
          </span>
        )}
      </div>
      <p className="text-mini text-muted-foreground leading-relaxed">{frase}</p>
      {bimodal && (
        <p className="text-micro text-amber-400 mt-1.5 leading-relaxed">
          Sin casos intermedios: una orden a medio camino queda donde
          históricamente no ha pasado nada.
        </p>
      )}
      {soporte && (
        <div className="mt-2.5 pt-2.5 border-t border-border/20 flex items-start gap-1.5">
          <LifeBuoy size={12} className={`mt-0.5 shrink-0 ${soporteAntiguo ? 'text-amber-400' : 'text-muted-foreground'}`} />
          <p className="text-mini text-muted-foreground leading-relaxed">{soporte}</p>
        </div>
      )}
    </>
  )

  if (plano) return <div>{cuerpo}</div>
  return (
    <div className={`rounded-xl border px-3.5 py-3 ${
      bimodal ? 'border-amber-500/25 bg-amber-500/5' : 'border-border/20 bg-muted/5'
    }`}>
      {cuerpo}
    </div>
  )
}
