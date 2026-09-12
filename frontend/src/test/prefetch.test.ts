import { describe, it, expect, vi } from 'vitest'
import { prefetchRuta } from '../lib/prefetch'
import { NAV_CATEGORIES } from '../lib/nav'
import prefetchSource from '../lib/prefetch?raw'

describe('prefetch de rutas', () => {
  it('cubre todas las entradas del menú', () => {
    // El mapa de prefetch.ts se mantiene a mano y puede desincronizarse de
    // App.tsx. Que falte una ruta no rompe nada (simplemente no se precarga),
    // así que sin este test el fallo sería invisible.
    const sinCubrir = NAV_CATEGORIES
      .flatMap(c => c.items)
      .map(i => i.path)
      .filter(p => !prefetchSource.includes(`'${p}':`))
    expect(sinCubrir).toEqual([])
  })

  it('no revienta con una ruta desconocida', () => {
    expect(() => prefetchRuta('/no-existe')).not.toThrow()
  })

  it('no vuelve a pedir lo que ya pidió', async () => {
    // Sin esta guarda, pasar el ratón varias veces por el mismo enlace
    // dispararía una importación por cada pasada.
    const espia = vi.spyOn(console, 'error').mockImplementation(() => {})
    prefetchRuta('/leaps')
    prefetchRuta('/leaps')
    prefetchRuta('/leaps')
    await new Promise(r => setTimeout(r, 0))
    expect(espia).not.toHaveBeenCalled()
    espia.mockRestore()
  })

  it('usa literales en los import(), no rutas construidas', () => {
    // Vite solo reconoce (y reutiliza el chunk de) un import() con literal.
    // Con una ruta armada en tiempo de ejecución crearía un módulo aparte y
    // el prefetch descargaría el doble en vez de adelantar trabajo.
    expect(prefetchSource).not.toMatch(/import\(\s*[`'"][^`'"]*\$\{/)
    expect(prefetchSource).toMatch(/import\('\.\.\/pages\/Leaps'\)/)
  })
})
