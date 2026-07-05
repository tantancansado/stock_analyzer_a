import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import CommandPalette from '@/components/CommandPalette'

vi.mock('motion/react', async () => {
  const React = await import('react')

  const MockDiv = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
    ({ children, ...props }, ref) => <div ref={ref} {...props}>{children}</div>,
  )

  return {
    AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    motion: {
      div: MockDiv,
    },
    useReducedMotion: () => false,
  }
})

function LocationProbe() {
  const location = useLocation()
  return <output data-testid="location">{location.pathname}{location.search}</output>
}

function renderPalette(onClose = vi.fn()) {
  render(
    <MemoryRouter initialEntries={['/dashboard']}>
      <Routes>
        <Route
          path="*"
          element={
            <>
              <CommandPalette open onClose={onClose} />
              <LocationProbe />
            </>
          }
        />
      </Routes>
    </MemoryRouter>,
  )

  return { onClose }
}

describe('CommandPalette', () => {
  it('navigates to ticker search from the quick action', async () => {
    const user = userEvent.setup()
    const { onClose } = renderPalette()

    await user.type(screen.getByPlaceholderText(/ticker/i), 'aapl')
    await user.click(screen.getByRole('option', { name: /analizar aapl/i }))

    expect(screen.getByTestId('location')).toHaveTextContent('/search?q=AAPL')
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('filters navigation results by keywords', async () => {
    const user = userEvent.setup()
    renderPalette()

    // 'buffett' es keyword de la página de Valoración (owner earnings) en nav.ts
    await user.type(screen.getByPlaceholderText(/ticker/i), 'buffett')

    expect(screen.getByText('Valoración')).toBeInTheDocument()
    expect(screen.queryByText('Centro de mando')).not.toBeInTheDocument()
  })

  it('shows an empty state when there are no matches and no ticker shortcut', async () => {
    const user = userEvent.setup()
    renderPalette()

    await user.type(screen.getByPlaceholderText(/ticker/i), 'zzzzzzz')

    expect(screen.getByText(/Sin resultados para/)).toBeInTheDocument()
  })

  it('closes when escape is pressed', async () => {
    const user = userEvent.setup()
    const { onClose } = renderPalette()

    await user.keyboard('{Escape}')

    expect(onClose).toHaveBeenCalled()
  })
})
