import { describe, it, expect } from 'vitest'
import { readdirSync, readFileSync } from 'node:fs'
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
  // Medido sobre el CSS SIN comentarios, que es lo único que cuenta.
  //
  //                     !important   [class*=]
  //   punto de partida      35          86      index.css
  //                        118          26      nothing-theme.css
  const TECHO = {
    'index.css':         { important: 9, atributo: 42 },
    'nothing-theme.css': { important: 87, atributo: 13 },
  } as const

  it.each(HOJAS)('$nombre no acumula más !important ni selectores por atributo', ({ nombre, css }) => {
    const techo = TECHO[nombre as keyof typeof TECHO]
    // Sobre el CSS sin comentarios: si no, un comentario que EXPLICA por qué se
    // quitó un `!important` cuenta como si lo hubiera añadido. Pasó al escribir
    // la nota de la voz tipográfica.
    const limpio = sinComentarios(css)
    const important = (limpio.match(/!important/g) ?? []).length
    const atributo = (limpio.match(/\[class\*=/g) ?? []).length
    expect(important, `!important subió a ${important}`).toBeLessThanOrEqual(techo.important)
    expect(atributo, `selectores [class*=] subieron a ${atributo}`).toBeLessThanOrEqual(techo.atributo)
  })
})

/**
 * Los tokens de color son COLORES, no tripletes sueltos.
 *
 * Durante mucho tiempo se declararon como `--primary: 239 84% 57%` y cada uso
 * los envolvía: `hsl(var(--primary))`. Funciona mientras todo el que los toca
 * conozca la convención — y deja de funcionar en cuanto alguien no la conoce.
 *
 * Lo destapó el banco de pruebas de HeroUI: su hoja hace
 * `--button-bg: var(--accent)` y recibía «220 13% 92%», que no es un color, así
 * que la declaración se caía entera y el botón salía sin fondo. Nueve nombres
 * chocaban de frente y envenenaban otros 37 derivados, porque
 * `color-mix(in oklab, var(--success) 15%, transparent)` con un triplete dentro
 * también es inválido. 46 de sus 89 tokens rotos, y ni un aviso en el build.
 *
 * Un triplete es una declaración que no se puede validar y un uso que hay que
 * recordar. Un color se valida solo.
 */
describe('tokens de color', () => {
  const TODAS = ['index.css', 'noir-theme.css', 'nothing-theme.css'].map(f => ({
    nombre: f,
    css: sinComentarios(readFileSync(join(__dirname, '..', f), 'utf-8')),
  }))

  it.each(TODAS)('$nombre no declara ningún token como triplete suelto', ({ css }) => {
    const tripletes = [...css.matchAll(/^[ \t]*(--[a-z0-9-]+):[ \t]*[0-9.]+ [0-9.]+% [0-9.]+%[ \t]*;/gm)]
    expect(
      tripletes.map(m => m[1]),
      'un token de color debe valer hsl(...), no «H S% L%»',
    ).toEqual([])
  })

  it.each(TODAS)('$nombre no envuelve tokens en hsl(var(…))', ({ css }) => {
    const envueltos = [...css.matchAll(/hsl\(\s*var\((--[a-z0-9-]+)\)/g)]
    expect(
      envueltos.map(m => m[1]),
      'el token ya es un color: usar var(--x), y color-mix(…) para la opacidad',
    ).toEqual([])
  })

  // El CSS no es el único sitio donde se consumen: hay estilos en línea en los
  // .tsx (gradientes, colores de gráficas) que hacían lo mismo.
  it('ningún .tsx envuelve tokens en hsl(var(…))', () => {
    const raiz = join(__dirname, '..')
    const fuentes: string[] = []
    const recorrer = (dir: string) => {
      for (const e of readdirSync(dir, { withFileTypes: true })) {
        const ruta = join(dir, e.name)
        if (e.isDirectory()) recorrer(ruta)
        else if (/\.tsx?$/.test(e.name)) fuentes.push(ruta)
      }
    }
    recorrer(raiz)

    const culpables = fuentes.flatMap(f => {
      const texto = readFileSync(f, 'utf-8')
        .replace(/\/\*[\s\S]*?\*\//g, '')   // comentarios de bloque
        .replace(/^[ \t]*\/\/.*$/gm, '')     // y de línea: documentan el patrón viejo
      return [...texto.matchAll(/hsl\(\s*var\((--[a-z0-9-]+)\)/g)]
        .map(m => `${f.slice(raiz.length + 1)}: ${m[1]}`)
    })
    expect(culpables, 'el token ya es un color: var(--x) a secas').toEqual([])
  })
})
