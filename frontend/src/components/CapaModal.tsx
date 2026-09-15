import { useRef, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { FocusScope, useDialog, useOverlay, usePreventScroll } from 'react-aria'

/**
 * La capa compartida de todo lo que se superpone a la página.
 *
 * Los cinco modales de la app se montaron cada uno por su cuenta y ninguno
 * atrapaba el foco: con el tabulador se salía del modal por detrás y se seguía
 * recorriendo la página que hay debajo —invisible tras el fondo oscuro— sin
 * forma de saber dónde estás. Tres no declaraban `role="dialog"` ni
 * `aria-modal`, así que un lector de pantalla ni anunciaba que se hubiera
 * abierto nada, y tres tampoco bloqueaban el scroll: al deslizar en el móvil se
 * movía la lista de debajo.
 *
 * Esto NO reescribe ningún modal. Envuelve el marcado que ya tienen y le añade
 * las cuatro cosas que faltaban, delegándolas en React Aria (Adobe) en lugar de
 * escribirlas a mano cinco veces:
 *
 *   FocusScope contain      el tabulador da la vuelta dentro del modal
 *   FocusScope restoreFocus al cerrar, el foco vuelve a quien lo abrió
 *   usePreventScroll        bloquea el scroll del fondo, iOS incluido, y lleva
 *                           su propio contador para los modales anidados
 *   useOverlay              Escape y pulsación fuera, con la semántica correcta
 *                           (no cierra si el gesto EMPIEZA dentro y termina
 *                           fuera, que es lo que hacía el `onClick` del fondo)
 *
 * El `className` posiciona el contenedor, que es lo único que cambia entre
 * ellos: hoja inferior en móvil para las tesis, centrado al 20% para la paleta.
 */

interface Props {
  readonly onClose: () => void
  readonly children: ReactNode
  /** Qué es este diálogo, para quien no ve la pantalla. */
  readonly etiqueta?: string
  /** id del encabezado que ya lo titula, si lo hay. Tiene prioridad sobre `etiqueta`. */
  readonly etiquetadoPor?: string
  /** Posicionamiento del contenedor. */
  readonly className?: string
  /** Clases del fondo, o `null` si el modal ya pinta el suyo (p. ej. animado). */
  readonly claseFondo?: string | null
  /** Un panel de ajustes no debería robar el foco como lo hace un diálogo modal. */
  readonly sinAutoFoco?: boolean
}

export default function CapaModal({
  onClose,
  children,
  etiqueta,
  etiquetadoPor,
  className = 'fixed inset-0 z-[500] flex items-center justify-center p-4',
  claseFondo = 'fixed inset-0 z-[500] bg-black/70 backdrop-blur-md animate-fade-in',
  sinAutoFoco = false,
}: Props) {
  const ref = useRef<HTMLDivElement>(null)

  usePreventScroll()

  const { overlayProps } = useOverlay(
    { onClose, isOpen: true, isDismissable: true, shouldCloseOnBlur: false },
    ref,
  )
  const { dialogProps } = useDialog(
    { 'aria-label': etiquetadoPor ? undefined : etiqueta, 'aria-labelledby': etiquetadoPor },
    ref,
  )

  return createPortal(
    <>
      {/* El fondo va FUERA del FocusScope: es decorativo y no debe recibir foco.
          Cerrar al pulsarlo lo gestiona `useOverlay`, no un onClick aquí.
          `null` = el modal ya trae el suyo, normalmente porque lo anima. */}
      {claseFondo !== null && <div className={claseFondo} aria-hidden="true" />}

      <FocusScope contain restoreFocus autoFocus={!sinAutoFoco}>
        <div
          {...overlayProps}
          {...dialogProps}
          ref={ref}
          aria-modal="true"
          className={className}
        >
          {children}
        </div>
      </FocusScope>
    </>,
    document.body,
  )
}
