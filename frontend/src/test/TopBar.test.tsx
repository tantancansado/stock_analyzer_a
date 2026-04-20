import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import TopBar from '@/components/TopBar'
import type { ComponentProps } from 'react'

const useThemeMock = vi.fn()
const useApiMock = vi.fn()
const useNothingThemeMock = vi.fn()
const fetchPipelineStatusMock = vi.fn()

vi.mock('motion/react', async () => {
  const React = await import('react')
  const MockSpan = React.forwardRef<HTMLSpanElement, React.HTMLAttributes<HTMLSpanElement>>(
    ({ children, ...props }, ref) => <span ref={ref} {...props}>{children}</span>,
  )

  return {
    AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    motion: { span: MockSpan },
    useReducedMotion: () => false,
  }
})

vi.mock('@/context/ThemeContext', () => ({
  useTheme: () => useThemeMock(),
}))

vi.mock('@/hooks/useNothingTheme', () => ({
  useNothingTheme: () => useNothingThemeMock(),
}))

vi.mock('@/hooks/useApi', () => ({
  useApi: (...args: unknown[]) => useApiMock(...args),
}))

vi.mock('@/api/client', () => ({
  fetchCerebroAlerts: vi.fn(),
  fetchPipelineStatus: () => fetchPipelineStatusMock(),
}))

function renderTopBar(path = '/dashboard', props?: Partial<ComponentProps<typeof TopBar>>) {
  const onMenuClick = vi.fn()
  const onOpenCmd = vi.fn()

  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path="*"
          element={<TopBar onMenuClick={props?.onMenuClick ?? onMenuClick} onOpenCmd={props?.onOpenCmd ?? onOpenCmd} />}
        />
      </Routes>
    </MemoryRouter>,
  )

  return { onMenuClick, onOpenCmd }
}

describe('TopBar', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    useThemeMock.mockReturnValue({ theme: 'dark', setTheme: vi.fn() })
    useApiMock.mockReturnValue({ data: { high_count: 3 } })
    useNothingThemeMock.mockReturnValue({ enabled: false, toggle: vi.fn() })
    fetchPipelineStatusMock.mockResolvedValue({
      run_date: new Date().toISOString().slice(0, 10),
      status: 'ok',
      last_run: `${new Date().toISOString().slice(0, 10)}T08:00:00Z`,
    })
  })

  it('shows the route title and opens menu/search actions', async () => {
    const user = userEvent.setup()
    const { onMenuClick, onOpenCmd } = renderTopBar('/owner-earnings')

    expect(screen.getByText('Valoración')).toBeInTheDocument()

    const searchButtons = screen.getAllByRole('button', { name: 'Buscar' })
    await user.click(screen.getByRole('button', { name: 'Menú' }))
    await user.click(searchButtons[0])

    expect(onMenuClick).toHaveBeenCalledOnce()
    expect(onOpenCmd).toHaveBeenCalledOnce()
  })

  it('shows the high alert badge when Cerebro has active alerts', () => {
    renderTopBar('/dashboard')

    expect(screen.getByTitle('Cerebro')).toHaveTextContent('3')
  })

  it('hides the high alert badge when there are no active alerts', () => {
    useApiMock.mockReturnValue({ data: { high_count: 0 } })
    renderTopBar('/dashboard')

    expect(screen.getByTitle('Cerebro')).not.toHaveTextContent('9+')
    expect(screen.getByTitle('Cerebro')).not.toHaveTextContent('0')
  })

  it('shows "Hoy" for a pipeline run from today', async () => {
    const today = new Date().toISOString().slice(0, 10)
    fetchPipelineStatusMock.mockResolvedValue({
      run_date: today,
      status: 'ok',
      last_run: `${today}T08:00:00Z`,
    })

    renderTopBar('/dashboard')

    expect(await screen.findByText('Hoy')).toBeInTheDocument()
  })

  it('shows "Ayer" for a pipeline run from yesterday', async () => {
    const yesterday = new Date(Date.now() - 86_400_000).toISOString().slice(0, 10)
    fetchPipelineStatusMock.mockResolvedValue({
      run_date: yesterday,
      status: 'ok',
      last_run: `${yesterday}T08:00:00Z`,
    })

    renderTopBar('/dashboard')

    expect(await screen.findByText('Ayer')).toBeInTheDocument()
  })

  it('cycles theme from dark to light', async () => {
    const user = userEvent.setup()
    const setTheme = vi.fn()
    useThemeMock.mockReturnValue({ theme: 'dark', setTheme })

    renderTopBar('/dashboard')

    await user.click(screen.getByRole('button', { name: 'Cambiar tema' }))

    expect(setTheme).toHaveBeenCalledWith('light')
  })

  it('cycles theme from light to noir', async () => {
    const user = userEvent.setup()
    const setTheme = vi.fn()
    useThemeMock.mockReturnValue({ theme: 'light', setTheme })

    renderTopBar('/dashboard')

    await user.click(screen.getByRole('button', { name: 'Cambiar tema' }))

    expect(setTheme).toHaveBeenCalledWith('noir')
  })

  it('cycles theme from noir back to dark', async () => {
    const user = userEvent.setup()
    const setTheme = vi.fn()
    useThemeMock.mockReturnValue({ theme: 'noir', setTheme })

    renderTopBar('/dashboard')

    await user.click(screen.getByRole('button', { name: 'Cambiar tema' }))

    expect(setTheme).toHaveBeenCalledWith('dark')
  })

  it('toggles the Nothing theme', async () => {
    const user = userEvent.setup()
    const toggle = vi.fn()
    useNothingThemeMock.mockReturnValue({ enabled: true, toggle })

    renderTopBar('/dashboard')

    await user.click(screen.getByRole('button', { name: 'Toggle Nothing theme' }))

    expect(toggle).toHaveBeenCalledOnce()
  })
})
