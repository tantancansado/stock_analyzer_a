import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider, useAuth } from '@/context/AuthContext'

const getSessionMock = vi.fn()
const onAuthStateChangeMock = vi.fn()
const signInWithPasswordMock = vi.fn()
const signOutMock = vi.fn()
const unsubscribeMock = vi.fn()

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: () => getSessionMock(),
      onAuthStateChange: (...args: unknown[]) => onAuthStateChangeMock(...args),
      signInWithPassword: (...args: unknown[]) => signInWithPasswordMock(...args),
      signOut: () => signOutMock(),
    },
  },
}))

function Harness() {
  const { user, loading, signIn, signOut } = useAuth()

  return (
    <div>
      <output data-testid="user">{user?.id ?? 'none'}</output>
      <output data-testid="loading">{String(loading)}</output>
      <button onClick={() => signIn('ana@example.com', 'secret')}>sign-in</button>
      <button onClick={() => signOut()}>sign-out</button>
    </div>
  )
}

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getSessionMock.mockResolvedValue({ data: { session: null } })
    onAuthStateChangeMock.mockImplementation((_cb: (event: string, session: { user?: { id: string } } | null) => void) => {
      return { data: { subscription: { unsubscribe: unsubscribeMock } } }
    })
    signInWithPasswordMock.mockResolvedValue({ error: null })
    signOutMock.mockResolvedValue(undefined)
  })

  it('loads the initial session and clears loading', async () => {
    getSessionMock.mockResolvedValue({ data: { session: { user: { id: 'user-1' } } } })

    render(
      <AuthProvider>
        <Harness />
      </AuthProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    expect(screen.getByTestId('user')).toHaveTextContent('user-1')
  })

  it('updates the user when auth state changes', async () => {
    let authHandler: ((event: string, session: { user?: { id: string } } | null) => void) | undefined
    onAuthStateChangeMock.mockImplementation((cb) => {
      authHandler = cb
      return { data: { subscription: { unsubscribe: unsubscribeMock } } }
    })

    render(
      <AuthProvider>
        <Harness />
      </AuthProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    authHandler?.('SIGNED_IN', { user: { id: 'user-2' } })

    await waitFor(() => {
      expect(screen.getByTestId('user')).toHaveTextContent('user-2')
    })
  })

  it('calls supabase signInWithPassword and signOut', async () => {
    const user = userEvent.setup()
    render(
      <AuthProvider>
        <Harness />
      </AuthProvider>,
    )

    await user.click(screen.getByRole('button', { name: 'sign-in' }))
    await user.click(screen.getByRole('button', { name: 'sign-out' }))

    expect(signInWithPasswordMock).toHaveBeenCalledWith({ email: 'ana@example.com', password: 'secret' })
    expect(signOutMock).toHaveBeenCalled()
  })

  it('returns the error message from failed sign-in attempts', async () => {
    signInWithPasswordMock.mockResolvedValue({ error: { message: 'Credenciales inválidas' } })

    let result: { error: string | null } | undefined
    function CaptureHarness() {
      const { signIn } = useAuth()
      return (
        <button
          onClick={async () => {
            result = await signIn('ana@example.com', 'bad')
          }}
        >
          capture
        </button>
      )
    }

    const user = userEvent.setup()
    render(
      <AuthProvider>
        <CaptureHarness />
      </AuthProvider>,
    )

    await user.click(screen.getByRole('button', { name: 'capture' }))

    await waitFor(() => {
      expect(result).toEqual({ error: 'Credenciales inválidas' })
    })
  })
})
