import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it } from 'vitest'
import { ThemeProvider, useTheme } from '@/context/ThemeContext'

function ThemeHarness() {
  const { theme, toggle, setTheme } = useTheme()

  return (
    <div>
      <output data-testid="theme">{theme}</output>
      <button onClick={toggle}>toggle</button>
      <button onClick={() => setTheme('noir')}>set-noir</button>
    </div>
  )
}

describe('ThemeContext', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.className = ''
    document.documentElement.removeAttribute('data-theme')
  })

  it('uses dark as the default theme and persists it', () => {
    render(
      <ThemeProvider>
        <ThemeHarness />
      </ThemeProvider>,
    )

    expect(screen.getByTestId('theme')).toHaveTextContent('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(localStorage.getItem('sa-theme')).toBe('dark')
  })

  it('loads the initial theme from localStorage', () => {
    localStorage.setItem('sa-theme', 'light')

    render(
      <ThemeProvider>
        <ThemeHarness />
      </ThemeProvider>,
    )

    expect(screen.getByTestId('theme')).toHaveTextContent('light')
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })

  it('toggles between dark and light', async () => {
    const user = userEvent.setup()
    render(
      <ThemeProvider>
        <ThemeHarness />
      </ThemeProvider>,
    )

    await user.click(screen.getByRole('button', { name: 'toggle' }))

    expect(screen.getByTestId('theme')).toHaveTextContent('light')
    expect(document.documentElement.classList.contains('dark')).toBe(false)
    expect(localStorage.getItem('sa-theme')).toBe('light')

    await user.click(screen.getByRole('button', { name: 'toggle' }))

    expect(screen.getByTestId('theme')).toHaveTextContent('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })

  it('supports setting the noir theme explicitly', async () => {
    const user = userEvent.setup()
    render(
      <ThemeProvider>
        <ThemeHarness />
      </ThemeProvider>,
    )

    await user.click(screen.getByRole('button', { name: 'set-noir' }))

    expect(screen.getByTestId('theme')).toHaveTextContent('noir')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(document.documentElement.getAttribute('data-theme')).toBe('noir')
    expect(localStorage.getItem('sa-theme')).toBe('noir')
  })
})
