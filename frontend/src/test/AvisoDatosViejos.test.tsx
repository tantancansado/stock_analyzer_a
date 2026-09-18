/**
 * El dato es correcto y aun así puede estar mal: lo calculó el modelo de ayer.
 *
 * El 18-sep-2026 el pipeline corrió a las 06:01 y el filtro de rebotes entró
 * a las 08:08. Entre las dos cosas, la app publicó dos setups con esperanza
 * negativa que el filtro nuevo ya descarta, y una ficha de MSFT que decía «un
 * 45% cara» cuando con el ancla arreglada sale un 27% barata. Nada de eso es
 * el pipeline parado —de eso ya avisa StaleDataBanner—: es el pipeline
 * funcionando con la versión anterior del modelo.
 */
import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const fetchFrescuraMock = vi.fn()
vi.mock('../api/client', () => ({
  fetchFrescura: () => fetchFrescuraMock(),
}))

async function montar(clave: string) {
  vi.resetModules()
  const mod = await import('@/components/AvisoDatosViejos')
  const Aviso = mod.default
  return render(<Aviso clave={clave} />)
}

const DESFASADO = {
  generated_at: '2026-09-18T14:00:00Z',
  hay_desfase: true,
  desfasados: ['rebotes'],
  modelos: {
    rebotes: {
      etiqueta: 'rebotes',
      fichero: 'bounce_setups_broad.json',
      datos_del: '2026-09-18T06:01:33Z',
      desfasado: true,
      modulos_mas_nuevos: [
        { modulo: 'bounce_scanner_broad.py', cambiado_el: '2026-09-18T08:08:00Z' },
      ],
    },
    value: {
      etiqueta: 'oportunidades VALUE',
      fichero: 'value_opportunities.csv',
      datos_del: '2026-09-18T05:44:29Z',
      desfasado: false,
      modulos_mas_nuevos: [],
    },
    leaps: {
      etiqueta: 'LEAPS',
      fichero: 'leaps_opportunities.json',
      datos_del: null,
      desfasado: null,
      modulos_mas_nuevos: [],
    },
  },
}

describe('AvisoDatosViejos', () => {
  beforeEach(() => {
    fetchFrescuraMock.mockReset()
    fetchFrescuraMock.mockResolvedValue(DESFASADO)
  })

  it('avisa cuando el modelo cambió después de generarse el dato', async () => {
    await montar('rebotes')
    await waitFor(() =>
      expect(screen.getByText(/Calculado con el modelo anterior/)).toBeInTheDocument())
  })

  it('dice que se arregla solo, para que no parezca un fallo que atender', async () => {
    await montar('rebotes')
    await waitFor(() =>
      expect(screen.getByText(/próxima ejecución/)).toBeInTheDocument())
  })

  it('no dice nada cuando el dato es del código actual', async () => {
    const { container } = await montar('value')
    await waitFor(() => expect(fetchFrescuraMock).toHaveBeenCalled())
    expect(container).toBeEmptyDOMElement()
  })

  it('«no lo sé» no se pinta como aviso', async () => {
    // desfasado: null. Avisar sin saberlo sería ruido; callarlo y darlo por
    // bueno sería mentir. Aquí no se pinta, y el JSON lo deja registrado.
    const { container } = await montar('leaps')
    await waitFor(() => expect(fetchFrescuraMock).toHaveBeenCalled())
    expect(container).toBeEmptyDOMElement()
  })

  it('una clave desconocida no rompe la página', async () => {
    const { container } = await montar('seccion-que-no-existe')
    await waitFor(() => expect(fetchFrescuraMock).toHaveBeenCalled())
    expect(container).toBeEmptyDOMElement()
  })

  it('si el fichero no está, la página sigue igual', async () => {
    fetchFrescuraMock.mockResolvedValue(null)
    const { container } = await montar('rebotes')
    await waitFor(() => expect(fetchFrescuraMock).toHaveBeenCalled())
    expect(container).toBeEmptyDOMElement()
  })
})
