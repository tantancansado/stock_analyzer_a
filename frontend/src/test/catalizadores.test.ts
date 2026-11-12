import { describe, expect, it } from 'vitest'

import { CATALYSTS, SETUPS } from '@/pages/CatalystScreener'

describe('combinaciones de catalizadores', () => {
  // Hasta el 12-nov dos combinaciones pedían `rr_strong`, renombrado hacía meses:
  // se descartaba en silencio y filtraban con dos condiciones diciendo tres.
  it('cada catalizador que pide una combinación existe', () => {
    const ids = new Set(CATALYSTS.map(c => c.id))
    for (const s of SETUPS) {
      for (const id of s.catalysts) expect(ids.has(id), `${s.id} pide ${id}`).toBe(true)
    }
  })

  it('el nombre que se lee primero no lleva jerga', () => {
    for (const s of SETUPS) expect(s.label).not.toMatch(/R:R|Piotroski|EPS|BPA|VALUE|≥/)
  })
})
