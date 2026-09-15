import { render, screen, fireEvent, act, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi, afterEach } from 'vitest'
import { ToastProvider, useToast } from '@/components/Toast'
import ShortcutsModal from '@/components/ShortcutsModal'

function ToastHarness() {
  const { toast } = useToast()
  return (
    <div>
      <button onClick={() => toast('ok', 'success')}>success</button>
      <button onClick={() => toast('info', 'info')}>info</button>
      <button onClick={() => toast('error', 'error')}>error</button>
      <button onClick={() => {
        toast('one', 'info')
        toast('two', 'info')
        toast('three', 'info')
        toast('four', 'info')
      }}>many</button>
    </div>
  )
}

describe('Toast and ShortcutsModal', () => {
  // Un test de este fichero llama a `vi.useFakeTimers()` y nunca los devolvía,
  // así que todo lo que venía después corría con el reloj parado: cualquier
  // `waitFor` se agotaba y los efectos que programan trabajo —como el foco
  // inicial de un modal— no llegaban a ejecutarse. No daba síntoma hasta que
  // alguien escribía un test que dependiera del tiempo real.
  afterEach(() => { vi.useRealTimers() })

  it('renders toast messages through the provider', async () => {
    const user = userEvent.setup()
    render(
      <ToastProvider>
        <ToastHarness />
      </ToastProvider>,
    )

    await user.click(screen.getByRole('button', { name: 'success' }))
    expect(screen.getByText('ok')).toBeInTheDocument()
  })

  it('keeps only the latest three toasts', async () => {
    const user = userEvent.setup()
    render(
      <ToastProvider>
        <ToastHarness />
      </ToastProvider>,
    )

    await user.click(screen.getByRole('button', { name: 'many' }))

    expect(screen.queryByText('one')).not.toBeInTheDocument()
    expect(screen.getByText('two')).toBeInTheDocument()
    expect(screen.getByText('three')).toBeInTheDocument()
    expect(screen.getByText('four')).toBeInTheDocument()
  })

  it('auto-removes toast messages after their timeout', async () => {
    vi.useFakeTimers()
    render(
      <ToastProvider>
        <ToastHarness />
      </ToastProvider>,
    )

    fireEvent.click(screen.getByRole('button', { name: 'info' }))
    expect(screen.getAllByText('info').length).toBeGreaterThan(1)

    act(() => {
      vi.advanceTimersByTime(3000)
    })

    expect(screen.getAllByText('info')).toHaveLength(1)
  })

  it('renders no modal when closed', () => {
    const { container } = render(<ShortcutsModal open={false} onClose={vi.fn()} />)
    expect(container.firstChild).toBeNull()
  })

  it('cierra con Escape y pulsando fuera', async () => {
    // Antes esto disparaba `keyDown` sobre `document`, que era como estaba
    // escrito el modal: un listener global. Ahora la tecla la recoge el propio
    // diálogo (React Aria), así que hay que pulsarla como la pulsa una persona
    // —sobre lo que tiene el foco—. Y el foco SIEMPRE está dentro, porque
    // `CapaModal` lo atrapa y lo lleva ahí al abrir; si algún día dejara de
    // hacerlo, este test se cae, que es justo lo que interesa.
    const onClose = vi.fn()
    render(<ShortcutsModal open onClose={onClose} />)

    // El foco lo coloca un efecto, no el render, así que hay que esperarlo.
    await waitFor(() =>
      expect(screen.getByRole('dialog')).toContainElement(document.activeElement as HTMLElement))

    fireEvent.keyDown(document.activeElement as HTMLElement, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledTimes(1)

    // Pulsar fuera. Con `fireEvent` no basta: React Aria mira dónde EMPIEZA y
    // dónde acaba el gesto —para que arrastrar desde dentro hacia fuera no
    // cierre por accidente— y eso necesita la secuencia entera de puntero, que
    // es lo que emite `userEvent`.
    await userEvent.setup({ document }).click(document.body)
    expect(onClose).toHaveBeenCalledTimes(2)
  })
})
