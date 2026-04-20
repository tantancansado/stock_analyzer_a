import { render, screen, fireEvent, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
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

  it('closes the shortcuts modal on backdrop click and Escape', async () => {
    const onClose = vi.fn()
    const { container } = render(<ShortcutsModal open onClose={onClose} />)

    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledTimes(1)

    fireEvent.click(container.firstChild as HTMLElement)
    expect(onClose).toHaveBeenCalledTimes(2)
  })
})
