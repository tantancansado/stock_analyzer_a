import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import ProtectedRoute from '@/components/ProtectedRoute'

const useAuthMock = vi.fn()

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => useAuthMock(),
}))

vi.mock('@/components/Loading', () => ({
  default: () => <div>Loading screen</div>,
}))

function renderProtectedRoute() {
  return render(
    <MemoryRouter initialEntries={['/dashboard']}>
      <Routes>
        <Route path="/login" element={<div>Login page</div>} />
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<div>Private page</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

describe('ProtectedRoute', () => {
  it('shows the loading state while auth is resolving', () => {
    useAuthMock.mockReturnValue({ user: null, loading: true })
    renderProtectedRoute()

    expect(screen.getByText('Loading screen')).toBeInTheDocument()
  })

  it('redirects unauthenticated users to login', () => {
    useAuthMock.mockReturnValue({ user: null, loading: false })
    renderProtectedRoute()

    expect(screen.getByText('Login page')).toBeInTheDocument()
    expect(screen.queryByText('Private page')).not.toBeInTheDocument()
  })

  it('renders the protected content for authenticated users', () => {
    useAuthMock.mockReturnValue({ user: { id: 'user-1' }, loading: false })
    renderProtectedRoute()

    expect(screen.getByText('Private page')).toBeInTheDocument()
    expect(screen.queryByText('Login page')).not.toBeInTheDocument()
  })
})
