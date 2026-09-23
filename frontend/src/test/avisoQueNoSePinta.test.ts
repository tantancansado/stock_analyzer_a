import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'

/**
 * Un aviso que se abre y se cierra sin pintar nada.
 *
 * En la tabla de VALUE US el marcador de «tus modelos propios no respaldan el
 * target del analista» era esto:
 *
 *     <span className={...} title={`Los modelos propios...`}>
 *
 *     </span>
 *
 * Todo correcto menos el contenido: dentro solo había espacios. El `title`
 * existía, el color existía, la condición se cumplía en 27 de los 45 picks
 * publicados — y en pantalla no aparecía nada. Probablemente quedó así al
 * quitar los emoji de la app sin poner el icono de lucide en su sitio.
 *
 * Es el fallo silencioso de siempre, pero en el frontend: no rompe el build,
 * no sale en consola, no lo cambia ningún test de datos. Solo se ve mirando.
 */

const RAIZ = join(__dirname, '..')

const ETIQUETAS = new Set(['span', 'div', 'button', 'p', 'a', 'td', 'th', 'li',
                           'h1', 'h2', 'h3', 'strong', 'em', 'label'])

function ficheros(dir: string): string[] {
  return readdirSync(dir).flatMap(nombre => {
    const ruta = join(dir, nombre)
    if (statSync(ruta).isDirectory()) return nombre === 'test' ? [] : ficheros(ruta)
    return /\.tsx$/.test(nombre) ? [ruta] : []
  })
}

describe('avisos visibles', () => {
  it('ningún elemento se abre y se cierra sin contenido', () => {
    const infractores: string[] = []

    for (const ruta of ficheros(RAIZ)) {
      const lineas = readFileSync(ruta, 'utf8').split('\n')
      for (let i = 0; i < lineas.length; i++) {
        const cierre = lineas[i].trim().match(/^<\/([a-z][a-z0-9]*)>$/)
        if (!cierre || !ETIQUETAS.has(cierre[1])) continue

        // Retrocede saltando líneas en blanco. Si justo antes está el `>` que
        // cierra una etiqueta de apertura multilínea, entre ambas no hay nada.
        let j = i - 1
        let blancos = 0
        while (j >= 0 && lineas[j].trim() === '') { blancos++; j-- }
        if (!blancos || j < 0) continue
        if (lineas[j].trim() === '>') {
          infractores.push(`${relative(RAIZ, ruta)}:${i + 1} <${cierre[1]}>`)
        }
      }
    }

    expect(infractores, `Estos elementos no pintan nada:\n  ${infractores.join('\n  ')}`)
      .toEqual([])
  })
})
