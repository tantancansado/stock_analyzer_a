import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import AvisoDatos from '@/components/AvisoDatos'
import { marcarFallo, marcarOk, reiniciarEstadoDatos } from '@/lib/estadoDatos'

/**
 * Lo que se protege aquí es la distinción entre «no hay señal» y «no lo sé».
 *
 * Los cachés compartidos devolvían un vacío al fallar, y un vacío se pinta
 * idéntico a un día sin señales. Para quien decide sobre si entrar o no, un
 * cero por fallo de red leído como un cero real es la lectura contraria.
 */

describe('AvisoDatos', () => {
  beforeEach(() => reiniciarEstadoDatos())

  it('no pinta nada mientras todo carga bien', () => {
    const { container } = render(<AvisoDatos />)
    expect(container).toBeEmptyDOMElement()
  })

  it('aparece cuando una fuente falla, y dice cuál', () => {
    render(<AvisoDatos />)
    act(() => marcarFallo('senales-tecnicas'))

    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.getByText(/No he podido cargar las señales técnicas/)).toBeInTheDocument()
    // El matiz que justifica todo esto.
    expect(screen.getByText(/no significa que no la haya/)).toBeInTheDocument()
  })

  it('enumera varias fuentes en una sola franja', () => {
    render(<AvisoDatos />)
    act(() => { marcarFallo('senales-tecnicas'); marcarFallo('veredictos-entrada') })

    expect(screen.getByText(/las señales técnicas y los veredictos de entrada/)).toBeInTheDocument()
    expect(screen.getAllByRole('status')).toHaveLength(1)
  })

  it('se retira cuando la fuente vuelve a cargar', () => {
    render(<AvisoDatos />)
    act(() => marcarFallo('senales-grafico'))
    expect(screen.queryByRole('status')).toBeInTheDocument()

    act(() => marcarOk('senales-grafico'))
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('deja de escuchar al desmontarse', () => {
    const { unmount } = render(<AvisoDatos />)
    unmount()
    // Si el oyente siguiera vivo, React avisaría de un setState sobre un
    // componente desmontado.
    const aviso = vi.spyOn(console, 'error').mockImplementation(() => {})
    act(() => marcarFallo('confluencia'))
    expect(aviso).not.toHaveBeenCalled()
    aviso.mockRestore()
  })
})

describe('los cachés compartidos avisan cuando fallan', () => {
  beforeEach(() => { vi.resetModules(); reiniciarEstadoDatos() })

  it('useTechnicalData marca el fallo al agotar los reintentos, no antes', async () => {
    vi.doMock('@/api/client', () => ({
      fetchTechnicalSignals: vi.fn().mockRejectedValue(new Error('caída')),
    }))
    const { subscribeToTechnicalData } = await import('@/hooks/useTechnicalData')
    const { fuentesFallidas } = await import('@/lib/estadoDatos')

    // Dos intentos: todavía puede recuperarse, así que no se avisa.
    for (let i = 0; i < 2; i++) {
      subscribeToTechnicalData(vi.fn())
      await new Promise(r => setTimeout(r, 0))
    }
    expect(fuentesFallidas()).not.toContain('senales-tecnicas')

    // Tercero: se agota y entonces sí.
    subscribeToTechnicalData(vi.fn())
    await new Promise(r => setTimeout(r, 0))
    expect(fuentesFallidas()).toContain('senales-tecnicas')
  })
})
