import { useEffect, useState } from 'react'

/** Punto de corte: por debajo, una tabla de 14 columnas no es legible. */
const MOVIL_MAX = 639  // igual que el `sm` de Tailwind (min-width: 640px)

/**
 * ¿Estamos en un viewport de móvil?
 *
 * Se usa para RENDERIZAR algo distinto, no para ocultar con CSS: las listas de
 * VALUE/ENTRY pasan a tarjetas en móvil, y duplicar el marcado (tabla oculta +
 * tarjetas ocultas) significaría montar dos árboles de decenas de filas cada
 * uno, con sus modales y sus tooltips, para tirar la mitad.
 *
 * Inicializa leyendo el ancho real —no `false`— para no pintar la tabla en el
 * primer frame y saltar a tarjetas justo después.
 */
export function useIsMobile(): boolean {
  const [esMovil, setEsMovil] = useState(
    () => typeof window !== 'undefined' && window.matchMedia(`(max-width: ${MOVIL_MAX}px)`).matches
  )

  useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${MOVIL_MAX}px)`)
    const alCambiar = (e: MediaQueryListEvent) => setEsMovil(e.matches)
    mq.addEventListener('change', alCambiar)
    setEsMovil(mq.matches)
    return () => mq.removeEventListener('change', alCambiar)
  }, [])

  return esMovil
}

export default useIsMobile
