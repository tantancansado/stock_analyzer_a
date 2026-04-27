import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ErrorBoundary from '@/components/ErrorBoundary'

function Boom({ message = 'Kaboom' }: { message?: string }): null {
  throw new Error(message)
}

describe('ErrorBoundary', () => {
  beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    sessionStorage.clear()
  })

  it('renders a retry fallback for regular errors', () => {
    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>,
    )

    expect(screen.getByText('Algo salió mal')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Reintentar' })).toBeInTheDocument()
  })

  it('renders a refresh action for import errors without exposing chunk URLs', () => {
    render(
      <ErrorBoundary>
        <Boom message="Failed to fetch dynamically imported module: https://example.com/assets/BounceTrader-old.js" />
      </ErrorBoundary>,
    )

    expect(screen.getByText('La app necesita actualizarse')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Actualizar ahora' })).toBeInTheDocument()
    expect(screen.queryByText(/BounceTrader-old/)).not.toBeInTheDocument()
  })

  it('clears the import error reload marker after a healthy mount', () => {
    sessionStorage.setItem('sa-import-error-reload', '1')

    render(
      <ErrorBoundary>
        <div>Recovered view</div>
      </ErrorBoundary>,
    )

    expect(sessionStorage.getItem('sa-import-error-reload')).toBeNull()
  })

  it('resets the error state when resetKey changes', () => {
    const { rerender } = render(
      <ErrorBoundary resetKey="/one">
        <Boom />
      </ErrorBoundary>,
    )

    expect(screen.getByText('Algo salió mal')).toBeInTheDocument()

    rerender(
      <ErrorBoundary resetKey="/two">
        <div>Recovered view</div>
      </ErrorBoundary>,
    )

    expect(screen.getByText('Recovered view')).toBeInTheDocument()
  })

  it('clears the error when the user clicks retry', async () => {
    const user = userEvent.setup()
    let shouldThrow = true

    function ToggleBoom() {
      if (shouldThrow) throw new Error('Temporary failure')
      return <div>Recovered view</div>
    }

    const { rerender } = render(
      <ErrorBoundary>
        <ToggleBoom />
      </ErrorBoundary>,
    )

    shouldThrow = false
    await user.click(screen.getByRole('button', { name: 'Reintentar' }))

    rerender(
      <ErrorBoundary>
        <ToggleBoom />
      </ErrorBoundary>,
    )

    expect(screen.getByText('Recovered view')).toBeInTheDocument()
  })
})
