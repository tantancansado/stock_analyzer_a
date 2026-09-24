/**
 * Una sola física para toda la app.
 *
 * El panel de «Personalizar menú» se escribió con un muelle único y una
 * entrada escalonada, y es lo que hace que se lea como una lista que llega y
 * no como un bloque que aparece de golpe. El resto de la interfaz se movía
 * con cuatro vocabularios distintos —`animate-in zoom-in-95`, `modal-enter`,
 * `animate-fade-in-up`, y nada— así que cada superficie tenía su propio
 * carácter y ninguna salía al cerrarse: desaparecían de golpe.
 *
 * Aquí vive ese vocabulario, y es deliberadamente corto. Un muelle, un
 * escalonado, una pulsación. Cuando hay una sola física, el movimiento deja
 * de notarse como animación y pasa a notarse como peso: es lo que separa una
 * interfaz que se mueve de una que parece estar hecha de algo.
 *
 * TODO lo de aquí se apaga con `useReducedMotion()` en el punto de uso. No es
 * opcional: para quien tiene sensibilidad vestibular, una interfaz que se
 * desliza no es bonita, es mareo.
 */

/** El muelle. Firme y corto: llega, se asienta y no rebota. */
export const MUELLE = { type: 'spring', stiffness: 420, damping: 34, mass: 0.8 } as const

/**
 * El mismo muelle con menos masa, para lo que sigue al dedo.
 *
 * Un indicador que se desliza entre pestañas tiene que llegar antes que el
 * panel que lo contiene, o se lee como retardo en vez de como respuesta.
 */
export const MUELLE_LIGERO = { type: 'spring', stiffness: 420, damping: 34, mass: 0.7 } as const

/** El fondo oscuro: solo opacidad, y rápido. Aquí un muelle sobra. */
export const FONDO = { duration: 0.18 } as const

/**
 * Cuánto se retrasa cada fila de una lista que entra.
 *
 * 22 ms, y se corta a los 12: más allá el retardo se nota como lentitud, no
 * como ritmo. Una lista de cuarenta filas escalonada entera tarda casi un
 * segundo en terminar de aparecer, y para entonces ya has empezado a leer.
 */
export const PASO_ESCALON = 0.022
export const MAX_ESCALONES = 12

export function escalonado(indice: number) {
  return { ...MUELLE, delay: Math.min(indice, MAX_ESCALONES) * PASO_ESCALON }
}

/** Lo que hace un elemento pulsable al hundirse. Casi nada, a propósito. */
export const PULSACION = { scale: 0.985 } as const

/**
 * Entrada y salida de un panel que se superpone.
 *
 * En móvil el panel sube desde abajo (hoja inferior) y en escritorio aparece
 * centrado: el mismo desplazamiento en `y` sirve para los dos, porque 28px es
 * poco para leerse como «sube desde el borde» y suficiente para que el panel
 * tenga una dirección de llegada.
 *
 * Sale menos de lo que entra (20 contra 28) y a una escala más cercana a 1:
 * cerrar tiene que sentirse más corto que abrir, o la interfaz se nota lenta.
 */
export const PANEL = {
  initial: { opacity: 0, y: 28, scale: 0.98 },
  animate: { opacity: 1, y: 0, scale: 1 },
  exit: { opacity: 0, y: 20, scale: 0.985 },
} as const

/** Entrada de una fila dentro de un panel, antes del escalonado. */
export const FILA = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
} as const
