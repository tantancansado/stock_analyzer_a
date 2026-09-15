import { useEffect, useState } from 'react'
import { CloudOff } from 'lucide-react'
import { NOMBRE_FUENTE, fuentesFallidas, suscribirse, type FuenteDatos } from '@/lib/estadoDatos'

/**
 * «No he podido comprobarlo» no es lo mismo que «no hay nada».
 *
 * Cuando falla la carga de un caché compartido, la lista se pinta sin señales
 * —idéntico a un día tranquilo de verdad—. Este aviso separa las dos cosas, que
 * es lo único que hace falta para no leer un cero falso como si fuera real.
 *
 * Va una sola vez en la cabecera de la app, no por página: el caché es
 * compartido, así que el fallo afecta a todas.
 */
export default function AvisoDatos({ className = '' }: { readonly className?: string }) {
  const [fallidas, setFallidas] = useState<FuenteDatos[]>(fuentesFallidas)

  useEffect(() => suscribirse(setFallidas), [])

  if (fallidas.length === 0) return null

  const nombres = fallidas.map(f => NOMBRE_FUENTE[f])
  const lista = nombres.length === 1
    ? nombres[0]
    : `${nombres.slice(0, -1).join(', ')} y ${nombres.at(-1)}`

  return (
    <div
      role="status"
      className={`rounded-xl border px-4 py-3 mb-5 flex items-start gap-3 bg-amber-500/8 border-amber-500/30 ${className}`}
    >
      <CloudOff size={16} className="text-amber-400 shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <div className="text-cuerpo font-bold text-amber-400 mb-0.5">
          No he podido cargar {lista}
        </div>
        <div className="text-mini text-muted-foreground">
          Lo que ves abajo está incompleto. Que no aparezca una señal no
          significa que no la haya — significa que no se ha podido comprobar.
          Recarga para reintentarlo.
        </div>
      </div>
    </div>
  )
}
