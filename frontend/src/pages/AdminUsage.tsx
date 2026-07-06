import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { apiClient } from '@/api/client'
import Loading, { ErrorState } from '@/components/Loading'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Users, Briefcase, BookOpen, TrendingUp } from 'lucide-react'
import PageHeader from '@/components/PageHeader'

const ADMIN_USER_ID = '3da8acd3-0b70-43c7-9684-6da77fbc6cfa'

interface RegisteredUser {
  user_id: string
  email: string
  created_at: string
  last_sign_in: string | null
  confirmed: boolean
  positions: number
  tickers: string[]
  last_portfolio_activity: string
  journal_entries: number
}

interface TopTicker {
  ticker: string
  count: number
}

interface AdminData {
  registered_users: RegisteredUser[]
  total_users: number
  total_positions: number
  total_journal_entries: number
  top_tickers: TopTicker[]
}

function StatCard({ icon: Icon, label, value, color }: {
  icon: typeof Users
  label: string
  value: number | string
  color: string
}) {
  return (
    <Card className="glass">
      <CardContent className="p-5 flex items-center gap-4">
        <div className="p-3 rounded-lg" style={{ background: `${color}22` }}>
          <Icon size={20} style={{ color }} />
        </div>
        <div>
          <div className="text-2xl font-bold text-foreground font-mono">{value}</div>
          <div className="text-xs text-foreground/50 mt-0.5">{label}</div>
        </div>
      </CardContent>
    </Card>
  )
}

function ActivityBar({ value, max }: { value: number; max: number }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full" style={{ background: 'rgba(255,255,255,0.08)' }}>
        <div className="h-1.5 rounded-full transition-all" style={{ width: `${pct}%`, background: '#22d3ee' }} />
      </div>
      <span className="text-xs font-mono text-foreground/60 w-4 text-right">{value}</span>
    </div>
  )
}

function fmtDate(iso: string | null | undefined) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric' })
}

function fmtDatetime(iso: string | null | undefined) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('es-ES', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
}

export default function AdminUsage() {
  const { user, loading: authLoading } = useAuth()
  const navigate = useNavigate()
  const [data, setData] = useState<AdminData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (authLoading) return
    if (!user || user.id !== ADMIN_USER_ID) {
      navigate('/dashboard', { replace: true })
      return
    }
    apiClient.get<AdminData>('/api/admin/usage')
      .then(r => setData(r.data))
      .catch(e => setError(e?.response?.data?.error ?? e.message))
      .finally(() => setLoading(false))
  }, [user, authLoading, navigate])

  if (authLoading || loading) return <Loading />
  if (error) return <ErrorState message={error} />
  if (!data) return null

  const maxPositions = Math.max(...data.registered_users.map(u => u.positions), 1)
  const maxJournal = Math.max(...data.registered_users.map(u => u.journal_entries), 1)
  const maxTopTicker = Math.max(...data.top_tickers.map(t => t.count), 1)

  const activeUsers = data.registered_users.filter(u => u.positions > 0 || u.journal_entries > 0)
  const confirmedUsers = data.registered_users.filter(u => u.confirmed)

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-8">
      <PageHeader title="Admin · Uso de la app" subtitle="Solo visible para el owner" />

      {/* KPI cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon={Users}     label="Usuarios registrados" value={data.total_users}           color="#22d3ee" />
        <StatCard icon={Users}     label="Confirmados"          value={confirmedUsers.length}       color="#a78bfa" />
        <StatCard icon={Briefcase} label="Posiciones totales"   value={data.total_positions}        color="#34d399" />
        <StatCard icon={BookOpen}  label="Entradas de journal"  value={data.total_journal_entries}  color="#f59e0b" />
      </div>

      {/* Usuarios con actividad */}
      <Card className="glass">
        <CardContent className="p-6">
          <h2 className="text-sm font-semibold text-foreground/70 uppercase tracking-wider mb-4">
            Usuarios con actividad ({activeUsers.length})
          </h2>
          {activeUsers.length === 0 ? (
            <p className="text-foreground/40 text-sm">Ningún usuario ha usado Mi Cartera todavía.</p>
          ) : (
            <div className="space-y-4">
              {activeUsers.map(u => (
                <div key={u.user_id} className="border-b border-white/5 pb-4 last:border-0 last:pb-0">
                  <div className="flex flex-wrap items-center gap-2 mb-2">
                    <span className="text-sm text-foreground font-medium">{u.email ?? u.user_id.slice(0, 16) + '…'}</span>
                    {u.confirmed
                      ? <Badge variant="outline" className="text-emerald-400 border-emerald-400/30 text-xs">confirmado</Badge>
                      : <Badge variant="outline" className="text-amber-400 border-amber-400/30 text-xs">sin confirmar</Badge>}
                    {u.user_id === ADMIN_USER_ID && (
                      <Badge variant="outline" className="text-cyan-400 border-cyan-400/30 text-xs">owner</Badge>
                    )}
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-x-6 gap-y-1 text-xs text-foreground/50 mb-2">
                    <span>Registro: <span className="text-foreground/70">{fmtDate(u.created_at)}</span></span>
                    <span>Último login: <span className="text-foreground/70">{fmtDate(u.last_sign_in)}</span></span>
                    <span>Última actividad cartera: <span className="text-foreground/70">{fmtDatetime(u.last_portfolio_activity)}</span></span>
                    <span>Entradas journal: <span className="text-foreground/70">{u.journal_entries}</span></span>
                  </div>
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2 text-xs text-foreground/40">
                      <span className="w-16">Posiciones</span>
                      <div className="flex-1"><ActivityBar value={u.positions} max={maxPositions} /></div>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-foreground/40">
                      <span className="w-16">Journal</span>
                      <div className="flex-1"><ActivityBar value={u.journal_entries} max={maxJournal} /></div>
                    </div>
                  </div>
                  {u.tickers.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {u.tickers.map(t => (
                        <span key={t} className="px-1.5 py-0.5 rounded text-xs font-mono"
                          style={{ background: 'rgba(34,211,238,0.1)', color: '#22d3ee' }}>{t}</span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Todos los usuarios registrados */}
      <Card className="glass">
        <CardContent className="p-6">
          <h2 className="text-sm font-semibold text-foreground/70 uppercase tracking-wider mb-4">
            Todos los usuarios ({data.total_users})
          </h2>
          <div className="table-x-wrap">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 text-left">
                  <th className="pb-2 text-xs text-foreground/40 font-medium">Email</th>
                  <th className="pb-2 text-xs text-foreground/40 font-medium text-center">Estado</th>
                  <th className="pb-2 text-xs text-foreground/40 font-medium text-right">Registro</th>
                  <th className="pb-2 text-xs text-foreground/40 font-medium text-right">Último login</th>
                  <th className="pb-2 text-xs text-foreground/40 font-medium text-right">Posiciones</th>
                </tr>
              </thead>
              <tbody>
                {data.registered_users.map(u => (
                  <tr key={u.user_id} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                    <td className="py-2.5 text-foreground/80 font-mono text-xs">
                      {u.email ?? u.user_id.slice(0, 20) + '…'}
                      {u.user_id === ADMIN_USER_ID && (
                        <span className="ml-1.5 text-cyan-400 text-xs">(owner)</span>
                      )}
                    </td>
                    <td className="py-2.5 text-center">
                      {u.confirmed
                        ? <span className="text-emerald-400 text-xs">✓</span>
                        : <span className="text-amber-400 text-xs">○</span>}
                    </td>
                    <td className="py-2.5 text-right text-foreground/50 text-xs">{fmtDate(u.created_at)}</td>
                    <td className="py-2.5 text-right text-foreground/50 text-xs">{fmtDate(u.last_sign_in)}</td>
                    <td className="py-2.5 text-right font-mono text-foreground/70">{u.positions}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Top tickers */}
      {data.top_tickers.length > 0 && (
        <Card className="glass">
          <CardContent className="p-6">
            <h2 className="text-sm font-semibold text-foreground/70 uppercase tracking-wider mb-4 flex items-center gap-2">
              <TrendingUp size={14} className="text-foreground/40" />
              Tickers más añadidos entre todos los usuarios
            </h2>
            <div className="space-y-2">
              {data.top_tickers.map(t => (
                <div key={t.ticker} className="flex items-center gap-3">
                  <span className="font-mono text-sm text-foreground w-16">{t.ticker}</span>
                  <div className="flex-1">
                    <div className="h-2 rounded-full" style={{ background: 'rgba(255,255,255,0.06)' }}>
                      <div
                        className="h-2 rounded-full transition-all"
                        style={{
                          width: `${Math.min((t.count / maxTopTicker) * 100, 100)}%`,
                          background: 'linear-gradient(90deg, #22d3ee, #6366f1)',
                        }}
                      />
                    </div>
                  </div>
                  <span className="text-xs font-mono text-foreground/50 w-6 text-right">{t.count}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
