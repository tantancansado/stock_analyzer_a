import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

/**
 * Invariantes del CSS que ningún build comprueba.
 *
 * El caso que motivó esto: al quitar un bloque de overrides quedó un selector
 * colgando delante de un comentario —
 *
 *     [data-theme="noir"] [class*="rounded"],
 *     ／* comentario *／
 *     [data-theme="noir"] .glow-border::before { background: gris }
 *
 * El comentario no separa nada, así que la lista de selectores continuaba y la
 * regla se aplicaba a CADA elemento redondeado del tema. Tailwind compiló sin
 * una queja y habría llegado a producción.
 */

const HOJAS = ['index.css', 'nothing-theme.css'].map(f => ({
  nombre: f,
  css: readFileSync(join(__dirname, '..', f), 'utf-8'),
}))

/** Quita comentarios para poder razonar sobre la estructura. */
const sinComentarios = (css: string) => css.replace(/\/\*[\s\S]*?\*\//g, '')

describe.each(HOJAS)('$nombre', ({ css }) => {
  it('las llaves cuadran', () => {
    const limpio = sinComentarios(css)
    expect(limpio.split('{').length).toBe(limpio.split('}').length)
  })

  it('ningún selector se queda colgando antes de una llave', () => {
    // `foo, {` significa que algo se borró de la lista de selectores.
    const colgantes = [...sinComentarios(css).matchAll(/,\s*\{/g)]
    expect(colgantes, 'hay una coma justo antes de {').toHaveLength(0)
  })

  it('ninguna regla empieza por coma', () => {
    const colgantes = [...sinComentarios(css).matchAll(/\}\s*,/g)]
    expect(colgantes).toHaveLength(0)
  })
})

describe('deuda de temas', () => {
  // Estos números solo pueden BAJAR. Si un cambio los sube, es que se ha
  // vuelto a perseguir una clase de Tailwind en vez de declarar un token.
  //                    !important  [class*=]
  //   punto de partida      35          76     index.css
  //                        112           ?     nothing-theme.css
  const TECHO = {
    'index.css':        { important: 21, atributo: 75 },
    'nothing-theme.css': { important: 96, atributo: 16 },
  } as const

  it.each(HOJAS)('$nombre no acumula más !important ni selectores por atributo', ({ nombre, css }) => {
    const techo = TECHO[nombre as keyof typeof TECHO]
    const important = (css.match(/!important/g) ?? []).length
    const atributo = (css.match(/\[class\*=/g) ?? []).length
    expect(important, `!important subió a ${important}`).toBeLessThanOrEqual(techo.important)
    expect(atributo, `selectores [class*=] subieron a ${atributo}`).toBeLessThanOrEqual(techo.atributo)
  })
})
