import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'

/**
 * Los iconos son de una familia (lucide), no emoji del sistema.
 *
 * El sistema pinta los emoji a todo color y con su propio estilo, así que
 * junto a texto en versalitas y a otros iconos se ve que están pegados y no
 * diseñados. Llegó a haber ~130 repartidos por 32 ficheros: 🐋 para smart
 * money en una página y ◆ en otra, 🟢🟡⚪ repitiendo el color que ya tenía la
 * pastilla, ⭐💀🚀 como tipos de evento.
 *
 * Las banderas de país SÍ se permiten: no hay equivalente de línea y son
 * convención. Las flechas y símbolos tipográficos (← ↑ ✓ ✗ ⌘ ★) también: se
 * pintan con la fuente y el color del texto, no como ilustración.
 */

const RAIZ = join(__dirname, '..')

// Pictogramas a color. Excluye el bloque de indicadores regionales (banderas),
// las flechas (2190-21FF) y los símbolos técnicos tipográficos.
const PICTOGRAMA = /[\u{1F300}-\u{1F5FF}\u{1F900}-\u{1FAFF}\u{1F600}-\u{1F64F}\u{1F680}-\u{1F6FF}\u{2600}-\u{26FF}\u{2B00}-\u{2BFF}\u{1F100}-\u{1F1E5}]/u

const PERMITIDOS = new Set([
  'pages/MacroRadar.tsx',   // banderas de país de los índices
])

function ficheros(dir: string): string[] {
  return readdirSync(dir).flatMap(nombre => {
    const ruta = join(dir, nombre)
    if (statSync(ruta).isDirectory()) return nombre === 'test' ? [] : ficheros(ruta)
    return /\.tsx?$/.test(nombre) ? [ruta] : []
  })
}

/** Quita comentarios de bloque y de línea: ahí un emoji es documentación. */
function sinComentarios(src: string): string {
  return src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '')
}

describe('iconografía', () => {
  it('no hay emoji pictográficos en el código que se renderiza', () => {
    const infractores: string[] = []
    for (const ruta of ficheros(RAIZ)) {
      const rel = relative(RAIZ, ruta).replace(/\\/g, '/')
      if (PERMITIDOS.has(rel)) continue
      const lineas = sinComentarios(readFileSync(ruta, 'utf-8')).split('\n')
      lineas.forEach((linea, i) => {
        const m = PICTOGRAMA.exec(linea)
        if (m) infractores.push(`${rel}:${i + 1}  ${m[0]}  ${linea.trim().slice(0, 70)}`)
      })
    }
    expect(infractores, `Usa un icono de lucide-react en su lugar:\n${infractores.join('\n')}`).toEqual([])
  })

  it('no se usan colores de paleta ajena, que no cambian con el tema', () => {
    // slate/zinc/gray/neutral/stone son tonos FIJOS: en modo claro se quedan
    // igual de oscuros. Los tokens (bg-muted, border-border,
    // text-muted-foreground) sí responden al tema.
    const PALETA = /\b(?:text|bg|border|from|to|via|ring|fill|stroke)-(?:slate|zinc|gray|neutral|stone)-\d{2,3}\b/
    const infractores: string[] = []
    for (const ruta of ficheros(RAIZ)) {
      const rel = relative(RAIZ, ruta).replace(/\\/g, '/')
      const lineas = sinComentarios(readFileSync(ruta, 'utf-8')).split('\n')
      lineas.forEach((linea, i) => {
        const m = PALETA.exec(linea)
        if (m) infractores.push(`${rel}:${i + 1}  ${m[0]}`)
      })
    }
    expect(infractores, `Usa un token del tema:\n${infractores.join('\n')}`).toEqual([])
  })
})
