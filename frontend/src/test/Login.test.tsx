import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Login from '@/pages/Login'

const useAuthMock = vi.fn()

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => useAuthMock(),
}))

function renderLogin() {
  render(
    <MemoryRouter initialEntries={['/login']}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/dashboard" element={<div>Dashboard page</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('Login', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthMock.mockReturnValue({
      user: null,
      loading: false,
      signIn: vi.fn().mockResolvedValue({ error: null }),
    })
  })

  it('redirects authenticated users to the dashboard', async () => {
    useAuthMock.mockReturnValue({
      user: { id: 'user-1' },
      loading: false,
      signIn: vi.fn(),
    })

    renderLogin()

    expect(await screen.findByText('Dashboard page')).toBeInTheDocument()
  })

  it('submits credentials and clears the loading state on success', async () => {
    const signIn = vi.fn().mockResolvedValue({ error: null })
    useAuthMock.mockReturnValue({ user: null, loading: false, signIn })

    const user = userEvent.setup()
    renderLogin()

    await user.type(screen.getByPlaceholderText('tu@email.com'), 'ana@example.com')
    await user.type(screen.getByPlaceholderText('••••••••'), 'secret')
    await user.click(screen.getByRole('button', { name: 'Entrar' }))

    await waitFor(() => {
      expect(signIn).toHaveBeenCalledWith('ana@example.com', 'secret')
    })

    expect(screen.getByRole('button')).toHaveTextContent('Entrar')
  })

  it('shows an error when sign-in fails', async () => {
    const signIn = vi.fn().mockResolvedValue({ error: 'Acceso denegado' })
    useAuthMock.mockReturnValue({ user: null, loading: false, signIn })

    const user = userEvent.setup()
    renderLogin()

    await user.type(screen.getByPlaceholderText('tu@email.com'), 'ana@example.com')
    await user.type(screen.getByPlaceholderText('••••••••'), 'bad')
    await user.click(screen.getByRole('button', { name: 'Entrar' }))

    expect(await screen.findByText('Acceso denegado')).toBeInTheDocument()
  })
})
