import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { ComponentProps } from 'react'
import PageTabs from '@/components/PageTabs'

vi.mock('motion/react', async () => {
  const React = await import('react')

  const MockDiv = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
    ({ children, ...props }, ref) => <div ref={ref} {...props}>{children}</div>,
  )

  const MockSpan = React.forwardRef<HTMLSpanElement, React.HTMLAttributes<HTMLSpanElement>>(
    ({ children, ...props }, ref) => <span ref={ref} {...props}>{children}</span>,
  )

  return {
    AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    motion: {
      div: MockDiv,
      span: MockSpan,
    },
    useReducedMotion: () => false,
  }
})

function LocationProbe() {
  const location = useLocation()
  return <output data-testid="location">{location.pathname}{location.search}</output>
}

type TabsProps = ComponentProps<typeof PageTabs>

function renderPageTabs(
  props: Partial<TabsProps> = {},
  initialEntries: string[] = ['/analysis'],
) {
  const tabs: TabsProps['tabs'] = [
    { id: 'overview', icon: 'O', label: 'Overview', content: <div>Overview content</div> },
    { id: 'signals', icon: 'S', label: 'Signals', content: <div>Signals content</div> },
    { id: 'notes', icon: 'N', label: 'Notes', content: <div>Notes content</div> },
  ]

  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Routes>
        <Route
          path="*"
          element={
            <>
              <PageTabs tabs={tabs} defaultTab="overview" {...props} />
              <LocationProbe />
            </>
          }
        />
      </Routes>
    </MemoryRouter>,
  )
}

describe('PageTabs', () => {
  it('uses the default tab when no query param is present', () => {
    renderPageTabs()

    expect(screen.getByText('Overview content')).toBeInTheDocument()
    expect(screen.getByTestId('location')).toHaveTextContent('/analysis')
  })

  it('respects a valid query param on first render', () => {
    renderPageTabs({}, ['/analysis?tab=signals'])

    expect(screen.getByText('Signals content')).toBeInTheDocument()
    expect(screen.queryByText('Overview content')).not.toBeInTheDocument()
  })

  it('falls back to the default tab when the query param is invalid', () => {
    renderPageTabs({}, ['/analysis?tab=missing'])

    expect(screen.getByText('Overview content')).toBeInTheDocument()
  })

  it('updates the search param and visible content when another tab is clicked', async () => {
    const user = userEvent.setup()
    renderPageTabs({}, ['/analysis?tab=overview'])

    await user.click(screen.getByRole('button', { name: /signals/i }))

    expect(screen.getByText('Signals content')).toBeInTheDocument()
    expect(screen.getByTestId('location')).toHaveTextContent('/analysis?tab=signals')
  })

  it('supports a custom query param key', async () => {
    const user = userEvent.setup()
    renderPageTabs({ paramKey: 'view' }, ['/analysis?view=notes'])

    expect(screen.getByText('Notes content')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /overview/i }))

    expect(screen.getByTestId('location')).toHaveTextContent('/analysis?view=overview')
    expect(screen.getByText('Overview content')).toBeInTheDocument()
  })
})
