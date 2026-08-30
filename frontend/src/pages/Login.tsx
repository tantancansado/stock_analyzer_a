import { useState, type FormEvent } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export default function Login() {
  const { user, loading, signIn, signUp } = useAuth()
  const [mode, setMode] = useState<'signin' | 'signup'>('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [info, setInfo] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  // Already logged in
  if (!loading && user) return <Navigate to="/dashboard" replace />

  function switchMode(next: 'signin' | 'signup') {
    setMode(next)
    setError(null)
    setInfo(null)
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setInfo(null)
    setSubmitting(true)
    if (mode === 'signup') {
      const { error, needsConfirmation } = await signUp(email, password)
      if (error) {
        setError(error)
      } else if (needsConfirmation) {
        // Crear la cuenta no garantiza acceso — ALLOWED_EMAILS lo decide en
        // el backend en cada llamada, no aquí. Si el email no está en la
        // lista, verá la app vacía con el aviso claro (ver api/client.ts).
        setInfo('Cuenta creada. Revisa tu correo para confirmarla antes de entrar.')
        setMode('signin')
      } else {
        // Sin confirmación de email activada en Supabase: la sesión ya está
        // abierta, onAuthStateChange lo recoge solo y el Navigate de arriba
        // redirige en el siguiente render.
      }
    } else {
      const { error } = await signIn(email, password)
      if (error) setError(error)
    }
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
            {/* Crear cuenta no da acceso por sí solo — solo saca un login de
                Supabase válido. Quien lo use decide si accede o no ALLOWED_EMAILS
                en el backend, en cada llamada a la API. */}
            <div className="flex rounded-md border border-border/50 p-0.5 mb-5 text-xs font-semibold">
              {/* aria-label distinto del texto visible: si no, su nombre
                  accesible ("Entrar"/"Crear cuenta") choca con el del botón
                  de submit de más abajo, que dice lo mismo según el modo */}
              <button
                type="button"
                aria-label="Cambiar a iniciar sesión"
                onClick={() => switchMode('signin')}
                className={`flex-1 py-1.5 rounded-[5px] transition-colors ${mode === 'signin' ? 'bg-primary/15 text-primary' : 'text-muted-foreground/60'}`}
              >
                Entrar
              </button>
              <button
                type="button"
                aria-label="Cambiar a crear cuenta"
                onClick={() => switchMode('signup')}
                className={`flex-1 py-1.5 rounded-[5px] transition-colors ${mode === 'signup' ? 'bg-primary/15 text-primary' : 'text-muted-foreground/60'}`}
              >
                Crear cuenta
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="login-email" className="text-[0.7rem] font-bold uppercase tracking-wider text-muted-foreground/70 block mb-1.5">
                  Email
                </label>
                <input
                  id="login-email"
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
                <label htmlFor="login-password" className="text-[0.7rem] font-bold uppercase tracking-wider text-muted-foreground/70 block mb-1.5">
                  Contraseña
                </label>
                <input
                  id="login-password"
                  type="password"
                  required
                  minLength={mode === 'signup' ? 6 : undefined}
                  autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
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

              {info && (
                <p className="text-[0.75rem] text-emerald-400 bg-emerald-400/10 border border-emerald-400/20 rounded px-3 py-2">
                  {info}
                </p>
              )}

              <Button type="submit" disabled={submitting} className="w-full mt-2">
                {submitting
                  ? (mode === 'signup' ? 'Creando cuenta…' : 'Entrando…')
                  : (mode === 'signup' ? 'Crear cuenta' : 'Entrar')}
              </Button>
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
