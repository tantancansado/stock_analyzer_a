import type { ReactNode } from 'react'
import { motion, useReducedMotion } from 'motion/react'
import { FONDO, MUELLE, PANEL } from '@/lib/movimiento'

/**
 * El panel de un modal y su fondo, con la física de la app.
 *
 * Existe para que los cinco modales no vuelvan a tener cinco animaciones. Los
 * tenía: `animate-in zoom-in-95` en la paleta, `modal-enter` en las tesis,
 * `animate-fade-in-up` en los atajos, un muelle propio en «Personalizar
 * menú»... y ninguno de los cuatro primeros salía al cerrarse, porque una
 * clase CSS de entrada no sabe nada de la salida.
 *
 * No sustituye a `CapaModal`, que es quien pone el foco atrapado, el scroll
 * bloqueado y la semántica de diálogo. Va DENTRO: CapaModal coloca, esto se
 * mueve.
 */

/** El fondo oscuro. Pulsarlo cierra — lo gestiona `useOverlay` de CapaModal,
 *  pero se mantiene el botón para quien navega con teclado y para el táctil. */
export function FondoAnimado({
  onClose, className = 'absolute inset-0 cursor-default bg-black/55 backdrop-blur-sm',
}: {
  readonly onClose: () => void
  readonly className?: string
}) {
  const quieto = useReducedMotion()
  return (
    <motion.button
      type="button"
      aria-label="Cerrar"
      onClick={onClose}
      className={className}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={quieto ? { duration: 0 } : FONDO}
    />
  )
}

export default function PanelAnimado({
  children, className, id,
}: {
  readonly children: ReactNode
  readonly className?: string
  readonly id?: string
}) {
  const quieto = useReducedMotion()
  return (
    <motion.div
      id={id}
      className={className}
      // Con movimiento reducido solo se funde: el desplazamiento y la escala
      // son justo lo que marea, y la opacidad no.
      initial={quieto ? { opacity: 0 } : PANEL.initial}
      animate={PANEL.animate}
      exit={quieto ? { opacity: 0 } : PANEL.exit}
      transition={quieto ? { duration: 0 } : MUELLE}
    >
      {children}
    </motion.div>
  )
}
