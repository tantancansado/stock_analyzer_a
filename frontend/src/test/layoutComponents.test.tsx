import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import PageHeader from '@/components/PageHeader'
import PaginationBar from '@/components/PaginationBar'
import InfoTooltip from '@/components/InfoTooltip'

describe('layout components', () => {
  beforeEach(() => {
    window.scrollTo = vi.fn()
  })

  it('renders the page header with subtitle and actions', () => {
    render(
      <PageHeader title="Dashboard" subtitle="Resumen diario">
        <button>Accion</button>
      </PageHeader>,
    )

    expect(screen.getByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
    expect(screen.getByText('Resumen diario')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Accion' })).toBeInTheDocument()
  })

  it('hides pagination when there is only one page', () => {
    const { container } = render(<PaginationBar page={1} totalPages={1} onPage={vi.fn()} />)
    expect(container.firstChild).toBeNull()
  })

  it('changes page and scrolls to the top', async () => {
    const user = userEvent.setup()
    const onPage = vi.fn()
    render(<PaginationBar page={3} totalPages={10} onPage={onPage} />)

    await user.click(screen.getByRole('button', { name: '4' }))

    expect(onPage).toHaveBeenCalledWith(4)
    expect(window.scrollTo).toHaveBeenCalledWith({ top: 0, behavior: 'smooth' })
    expect(screen.getByText('…')).toBeInTheDocument()
  })

  it('renders the tooltip badge and panel text', () => {
    render(<InfoTooltip text="Explicacion breve" side="bottom" align="right" />)

    expect(screen.getByText('?')).toBeInTheDocument()
    expect(screen.getByText('Explicacion breve')).toBeInTheDocument()
  })
})
