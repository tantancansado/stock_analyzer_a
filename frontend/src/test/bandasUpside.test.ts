import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

import {
  UPSIDE_GOLDEN_MAX, UPSIDE_HARD_REJECT, UPSIDE_MIN,
  bandaUpside, colorUpside, enZonaDorada,
} from '../lib/bandasUpside'

const RAIZ = join(__dirname, '..', '..', '..')

describe('bandasUpside', () => {
  it('no se desincroniza de value_bands.py', () => {
    // Es la razón de existir del fichero: CLAUDE.md dice que la banda vive en
    // un solo sitio, y un espejo sin vigilancia es otra copia más.
    const py = readFileSync(join(RAIZ, 'value_bands.py'), 'utf8')
    const num = (nombre: string) => {
      const m = py.match(new RegExp(`^${nombre}\\s*=\\s*([\\d.]+)`, 'm'))
      if (!m) throw new Error(`${nombre} no está en value_bands.py`)
      return Number(m[1])
    }
    expect(UPSIDE_MIN).toBe(num('UPSIDE_MIN'))
    expect(UPSIDE_GOLDEN_MAX).toBe(num('UPSIDE_GOLDEN_MAX'))
    expect(UPSIDE_HARD_REJECT).toBe(num('UPSIDE_HARD_REJECT'))
  })

  it('clasifica cada tramo', () => {
    expect(bandaUpside(null)).toBe('sin-dato')
    expect(bandaUpside(5)).toBe('flojo')
    expect(bandaUpside(10)).toBe('dorada')
    expect(bandaUpside(24.9)).toBe('dorada')
    // 25 era 'transicion' hasta el 17-sep-2026. Medido sobre las señales con
    // 90 días cerrados, [25,30) acierta el 62% y [10,25) el 61%: la misma
    // banda. Se unificaron y el estado 'transicion' desapareció.
    expect(bandaUpside(25)).toBe('dorada')
    expect(bandaUpside(29.9)).toBe('dorada')
    expect(bandaUpside(30)).toBe('trampa')
    expect(bandaUpside(30)).toBe('trampa')
    expect(bandaUpside(120)).toBe('trampa')
  })

  it('un upside alto no es verde', () => {
    // El fallo que se repetía en media app: pintar verde a partir de un suelo,
    // sin techo, premiando justo la franja que peor rinde.
    // El techo está en 30, no en 25: 27 sí es verde desde el 17-sep-2026.
    // Lo que el test protege es que EXISTA un techo, no dónde está.
    expect(colorUpside(18)).toBe('text-emerald-400')
    expect(colorUpside(27)).toBe('text-emerald-400')
    expect(colorUpside(35)).not.toBe('text-emerald-400')
    expect(colorUpside(35)).toBe('text-red-400')
    expect(enZonaDorada(35)).toBe(false)
  })
})

describe('nadie escribe la banda a mano', () => {
  it('no quedan copias inline del [10, 25) ni del ≥30', async () => {
    // Es la regla de CLAUDE.md llevada al frontend. Seis pantallas escribían su
    // propia versión y no todas coincidían: unas usaban la banda entera y otras
    // solo el suelo, pintando de verde cualquier upside por encima de 10 —o sea
    // premiando también la franja pegada al HARD REJECT.
    const { glob } = await import('node:fs/promises')
    // Un identificador que contenga "upside", una comparación, y uno de los
    // tres números de la banda. Verificado contra los seis casos reales que se
    // corrigieron y contra los que NO deben saltar (`>= UPSIDE_HARD_REJECT`,
    // `colorUpside(upside)`, `enZonaDorada(...)`).
    const inline = /[A-Za-z_.]*upside\w*[^\n;]{0,40}?(?:>=|<=|>|<|===?|!==?)\s*(?:10|25|30)\b/i
    const culpables: string[] = []
    for await (const f of glob(join(__dirname, '..', '**/*.{ts,tsx}'))) {
      if (f.includes('/test/') || f.endsWith('bandasUpside.ts')) continue
      const src = readFileSync(f, 'utf8')
      src.split('\n').forEach((l, i) => {
        const codigo = l.replace(/\/\/.*$/, '')
        if (inline.test(codigo) && !codigo.includes('UPSIDE_')) {
          culpables.push(`${f.split('/src/')[1]}:${i + 1}`)
        }
      })
    }
    expect(culpables, 'importa la banda de lib/bandasUpside en vez de escribirla').toEqual([])
  })
})
