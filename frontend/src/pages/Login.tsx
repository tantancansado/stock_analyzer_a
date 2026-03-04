import { useState, type FormEvent } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { Card, CardContent } from '@/components/ui/card'

export default function Login() {
  const { user, loading, signIn } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  // Already logged in
  if (!loading && user) return <Navigate to="/dashboard" replace />

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    const { error } = await signIn(email, password)
    if (error) setError(error)
    setSubmitting(false)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background relative overflow-hidden">
      {/* Background orbs */}
      <div className="bg-orbs" aria-hidden="true">
        <div className="orb orb-1" />
        <div className="orb orb-2" />
        <div className="orb orb-3" />
      </div>

      <div className="w-full max-w-sm px-4 relative z-10">
        {/* Logo / title */}
        <div className="text-center mb-8">
          <div className="text-3xl font-extrabold tracking-tight gradient-title mb-1">
            Stock Analyzer
          </div>
          <p className="text-sm text-muted-foreground">Sistema de análisis VALUE + MOMENTUM</p>
        </div>

        <Card className="glass">
          <CardContent className="p-6">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="text-[0.7rem] font-bold uppercase tracking-wider text-muted-foreground/70 block mb-1.5">
                  Email
                </label>
                <input
                  type="email"
                  required
                  autoComplete="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  className="w-full text-sm px-3 py-2 rounded-md border border-border/50 bg-transparent text-foreground focus:outline-none focus:border-primary/60 transition-colors"
                  placeholder="tu@email.com"
                />
              </div>

              <div>
                <label className="text-[0.7rem] font-bold uppercase tracking-wider text-muted-foreground/70 block mb-1.5">
                  Contraseña
                </label>
                <input
                  type="password"
                  required
                  autoComplete="current-password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  className="w-full text-sm px-3 py-2 rounded-md border border-border/50 bg-transparent text-foreground focus:outline-none focus:border-primary/60 transition-colors"
                  placeholder="••••••••"
                />
              </div>

              {error && (
                <p className="text-[0.75rem] text-red-400 bg-red-400/10 border border-red-400/20 rounded px-3 py-2">
                  {error}
                </p>
              )}

              <button
                type="submit"
                disabled={submitting}
                className="w-full py-2 rounded-md bg-primary text-primary-foreground text-sm font-semibold transition-opacity hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed mt-2"
              >
                {submitting ? 'Entrando…' : 'Entrar'}
              </button>
            </form>
          </CardContent>
        </Card>

        <p className="text-center text-[0.65rem] text-muted-foreground/40 mt-4">
          Acceso privado · Solo usuarios autorizados
        </p>
      </div>
    </div>
  )
}
