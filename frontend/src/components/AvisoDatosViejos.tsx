import { useEffect, useState } from 'react'
import { History } from 'lucide-react'
import { fetchFrescura, type Frescura } from '../api/client'

/** El dato es correcto, pero lo calculó una versión anterior del modelo.
 *
 * No es lo mismo que el banner de pipeline parado: ahí el problema es que no
 * hay datos nuevos. Aquí los hay, corrieron bien, y el modelo cambió después.
 * El 18-sep-2026 eso significaba ver MSFT «un 45% cara» cuando con el ancla
 * arreglada sale un 27% barata, y dos rebotes con esperanza negativa que el
 * filtro nuevo ya descarta.
 *
 * Avisa; no oculta nada. Un dato de ayer sigue siendo el mejor que hay hasta
 * que el pipeline vuelva a correr, y esconderlo dejaría la página en blanco
 * sin motivo. */

let _cache: Frescura | null | undefined = undefined

export function useFrescura(clave: string) {
  const [f, setF] = useState<Frescura | null | undefined>(_cache)
  useEffect(() => {
    if (_cache !== undefined) return
    fetchFrescura().then(r => { _cache = r; setF(r) })
  }, [])
  const m = f?.modelos?.[clave]
  return m?.desfasado ? m : null
}

export default function AvisoDatosViejos({ clave }: { clave: string }) {
  const m = useFrescura(clave)
  if (!m) return null

  const cuando = m.modulos_mas_nuevos[0]?.cambiado_el
  const fecha = cuando
    ? new Date(cuando).toLocaleDateString('es-ES', {
        day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
      })
    : null

  return (
    <div className="glass rounded-md border border-amber-500/30 px-3 py-2 mb-4 flex items-start gap-2 text-[0.72rem] text-amber-300">
      <History size={16} strokeWidth={2} className="shrink-0 mt-px" />
      <span>
        <strong>Calculado con el modelo anterior.</strong>{' '}
        Estos números salieron del pipeline y son correctos para el código que
        había entonces, pero {m.modulos_mas_nuevos.length === 1 ? 'el modelo cambió' : 'los modelos cambiaron'}
        {fecha ? ` el ${fecha}` : ''} y todavía no se han vuelto a generar.
        Se actualizan solos en la próxima ejecución.
      </span>
    </div>
  )
}
