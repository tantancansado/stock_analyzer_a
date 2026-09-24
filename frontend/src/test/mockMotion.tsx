import React from 'react'

/**
 * Un `motion/react` de mentira que acepta CUALQUIER etiqueta.
 *
 * Los mocks se escribían a mano y declaraban solo las etiquetas que el
 * componente usaba ese día: `{ motion: { div: MockDiv } }`. En cuanto alguien
 * añadía un `motion.button` —el fondo del modal— el test reventaba con
 * «Element type is invalid», que no dice nada sobre la causa real.
 *
 * Un Proxy devuelve el elemento que le pidan, así que el mock no vuelve a
 * quedarse corto. Y descarta las props de animación antes de llegar al DOM:
 * React avisa por consola de cada `initial`/`whileTap` que le llega, y esos
 * avisos acaban tapando los que sí importan.
 */
const PROPS_DE_MOVIMIENTO = new Set([
  'initial', 'animate', 'exit', 'transition', 'variants', 'layout', 'layoutId',
  'whileTap', 'whileHover', 'whileFocus', 'whileDrag', 'whileInView',
  'drag', 'dragConstraints', 'onAnimationComplete', 'custom',
])

function crear(etiqueta: string) {
  return React.forwardRef<HTMLElement, Record<string, unknown>>((props, ref) => {
    const limpias: Record<string, unknown> = {}
    for (const [k, v] of Object.entries(props)) {
      if (!PROPS_DE_MOVIMIENTO.has(k)) limpias[k] = v
    }
    return React.createElement(etiqueta, { ...limpias, ref })
  })
}

export function mockMotion() {
  const cache = new Map<string, unknown>()
  return {
    AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    motion: new Proxy({} as Record<string, unknown>, {
      get(_t, etiqueta: string) {
        if (!cache.has(etiqueta)) cache.set(etiqueta, crear(etiqueta))
        return cache.get(etiqueta)
      },
    }),
    useReducedMotion: () => false,
  }
}
