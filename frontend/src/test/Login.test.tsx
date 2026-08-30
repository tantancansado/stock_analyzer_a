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
      signUp: vi.fn().mockResolvedValue({ error: null, needsConfirmation: true }),
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

    expect(screen.getByRole('button', { name: 'Entrar' })).toHaveTextContent('Entrar')
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

  describe('crear cuenta', () => {
    it('cambia a modo signup y llama a signUp, no a signIn', async () => {
      const signIn = vi.fn()
      const signUp = vi.fn().mockResolvedValue({ error: null, needsConfirmation: true })
      useAuthMock.mockReturnValue({ user: null, loading: false, signIn, signUp })

      const user = userEvent.setup()
      renderLogin()

      await user.click(screen.getByRole('button', { name: 'Cambiar a crear cuenta' }))
      await user.type(screen.getByPlaceholderText('tu@email.com'), 'nuevo@example.com')
      await user.type(screen.getByPlaceholderText('••••••••'), 'secret123')
      await user.click(screen.getByRole('button', { name: 'Crear cuenta' }))

      await waitFor(() => {
        expect(signUp).toHaveBeenCalledWith('nuevo@example.com', 'secret123')
      })
      expect(signIn).not.toHaveBeenCalled()
    })

    it('con confirmación de email pendiente, avisa y vuelve a modo entrar', async () => {
      const signUp = vi.fn().mockResolvedValue({ error: null, needsConfirmation: true })
      useAuthMock.mockReturnValue({ user: null, loading: false, signIn: vi.fn(), signUp })

      const user = userEvent.setup()
      renderLogin()

      await user.click(screen.getByRole('button', { name: 'Cambiar a crear cuenta' }))
      await user.type(screen.getByPlaceholderText('tu@email.com'), 'nuevo@example.com')
      await user.type(screen.getByPlaceholderText('••••••••'), 'secret123')
      await user.click(screen.getByRole('button', { name: 'Crear cuenta' }))

      expect(await screen.findByText(/Revisa tu correo/)).toBeInTheDocument()
      // Vuelve a modo "Entrar": el botón de submit vuelve a decir "Entrar"
      expect(screen.getByRole('button', { name: 'Entrar' })).toBeInTheDocument()
    })

    it('muestra el error si el email ya existe o Supabase lo rechaza', async () => {
      const signUp = vi.fn().mockResolvedValue({ error: 'User already registered', needsConfirmation: false })
      useAuthMock.mockReturnValue({ user: null, loading: false, signIn: vi.fn(), signUp })

      const user = userEvent.setup()
      renderLogin()

      await user.click(screen.getByRole('button', { name: 'Cambiar a crear cuenta' }))
      await user.type(screen.getByPlaceholderText('tu@email.com'), 'ya@example.com')
      await user.type(screen.getByPlaceholderText('••••••••'), 'secret123')
      await user.click(screen.getByRole('button', { name: 'Crear cuenta' }))

      expect(await screen.findByText('User already registered')).toBeInTheDocument()
    })
  })
})
