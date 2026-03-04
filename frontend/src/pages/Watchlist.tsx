import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Star, Trash2, StickyNote, ChevronRight } from 'lucide-react'
import { useWatchlist, type WatchlistEntry } from '../hooks/useWatchlist'
import GradeBadge from '../components/GradeBadge'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'

function fmt(n: number | undefined | null, dec = 1) {
  if (n == null) return '—'
  return n.toFixed(dec)
}

function NoteEditor({ entry, onSave }: { entry: WatchlistEntry; onSave: (note: string) => void }) {
  const [editing, setEditing] = useState(false)
  const [val, setVal] = useState(entry.note ?? '')

  if (!editing) {
    return (
      <button
        onClick={() => setEditing(true)}
        className="text-[0.65rem] text-muted-foreground/50 hover:text-foreground transition-colors flex items-center gap-1"
        title={entry.note || 'Añadir nota'}
      >
        <StickyNote size={11} />
        {entry.note ? <span className="truncate max-w-[100px]">{entry.note}</span> : <span>nota</span>}
      </button>
    )
  }

  return (
    <div className="flex items-center gap-1" onClick={e => e.stopPropagation()}>
      <input
        autoFocus
        value={val}
        onChange={e => setVal(e.target.value)}
        onKeyDown={e => {
          if (e.key === 'Enter') { onSave(val); setEditing(false) }
          if (e.key === 'Escape') { setVal(entry.note ?? ''); setEditing(false) }
        }}
        className="text-[0.7rem] px-1.5 py-0.5 rounded border border-border/50 bg-transparent text-foreground w-28 focus:outline-none focus:border-primary/50"
        placeholder="Nota..."
      />
      <button
        onClick={() => { onSave(val); setEditing(false) }}
        className="text-[0.65rem] text-primary hover:text-primary/80 transition-colors"
      >
        OK
      </button>
    </div>
  )
}

export default function Watchlist() {
  const { entries, remove, updateNote } = useWatchlist()
  const [sortKey, setSortKey] = useState<keyof WatchlistEntry>('added_at')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')

  const onSort = (key: keyof WatchlistEntry) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(key); setSortDir('desc') }
  }

  const thCls = (key: keyof WatchlistEntry) =>
    `cursor-pointer select-none whitespace-nowrap transition-colors hover:text-foreground ${sortKey === key ? 'text-primary' : ''}`

  const sorted = [...entries].sort((a, b) => {
    const av = a[sortKey] ?? ''
    const bv = b[sortKey] ?? ''
    if (typeof av === 'string' && typeof bv === 'string') {
      return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av)
    }
    const an = Number(av); const bn = Number(bv)
    if (an < bn) return sortDir === 'asc' ? -1 : 1
    if (an > bn) return sortDir === 'asc' ? 1 : -1
    return 0
  })

  return (
    <>
      <div className="mb-7 animate-fade-in-up flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-extrabold tracking-tight mb-2 flex items-center gap-2">
            <Star size={20} className="text-amber-400" strokeWidth={1.75} />
            <span className="gradient-title">Watchlist</span>
          </h2>
          <p className="text-sm text-muted-foreground">
            Tickers guardados · {entries.length} {entries.length === 1 ? 'ticker' : 'tickers'} · Guardado localmente
          </p>
        </div>
      </div>

      {entries.length === 0 ? (
        <Card className="glass">
          <CardContent className="py-16 text-center">
            <Star size={40} strokeWidth={1.25} className="text-muted-foreground/20 mx-auto mb-4" />
            <p className="font-medium text-muted-foreground mb-2">Tu watchlist está vacía</p>
            <p className="text-xs text-muted-foreground/60 mb-5">
              Añade tickers desde VALUE US, VALUE EU o Buscar Ticker pulsando la estrella ★
            </p>
            <div className="flex gap-2 justify-center flex-wrap">
              {[
                { to: '/value',    label: 'VALUE US' },
                { to: '/value-eu', label: 'VALUE EU' },
                { to: '/search',   label: 'Buscar Ticker' },
              ].map(l => (
                <Link
                  key={l.to}
                  to={l.to}
                  className="flex items-center gap-1 text-xs px-3 py-1.5 rounded border border-border/50 text-muted-foreground hover:text-foreground hover:border-primary/50 transition-colors"
                >
                  {l.label} <ChevronRight size={11} />
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card className="glass overflow-hidden animate-fade-in-up">
          <Table>
            <TableHeader>
              <TableRow className="border-border/50 hover:bg-transparent">
                <TableHead className={thCls('ticker')} onClick={() => onSort('ticker')}>Ticker</TableHead>
                <TableHead className={thCls('company_name')} onClick={() => onSort('company_name')}>Empresa</TableHead>
                <TableHead className={thCls('sector')} onClick={() => onSort('sector')}>Sector</TableHead>
                <TableHead className={thCls('current_price')} onClick={() => onSort('current_price')}>Precio</TableHead>
                <TableHead className={thCls('value_score')} onClick={() => onSort('value_score')}>Score</TableHead>
                <TableHead>Grade</TableHead>
                <TableHead className={thCls('analyst_upside_pct')} onClick={() => onSort('analyst_upside_pct')}>Upside</TableHead>
                <TableHead className={thCls('fcf_yield_pct')} onClick={() => onSort('fcf_yield_pct')}>FCF%</TableHead>
                <TableHead className={thCls('added_at')} onClick={() => onSort('added_at')}>Añadido</TableHead>
                <TableHead>Nota</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sorted.map(e => (
                <TableRow key={e.ticker}>
                  <TableCell className="font-mono font-bold text-amber-400 text-[0.8rem] tracking-wide">
                    <Link to={`/search?q=${e.ticker}`} className="hover:underline">{e.ticker}</Link>
                  </TableCell>
                  <TableCell className="text-[0.76rem] text-muted-foreground max-w-[140px] truncate">
                    {e.company_name || '—'}
                  </TableCell>
                  <TableCell className="text-[0.75rem] text-muted-foreground">{e.sector || '—'}</TableCell>
                  <TableCell className="tabular-nums text-[0.8rem]">
                    {e.current_price != null ? `$${e.current_price.toFixed(2)}` : '—'}
                  </TableCell>
                  <TableCell className="tabular-nums text-[0.8rem] text-primary font-semibold">
                    {e.value_score != null ? fmt(e.value_score, 0) : '—'}
                  </TableCell>
                  <TableCell>
                    <GradeBadge grade={e.conviction_grade} />
                  </TableCell>
                  <TableCell className={`tabular-nums text-[0.8rem] font-semibold ${e.analyst_upside_pct != null && e.analyst_upside_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {e.analyst_upside_pct != null ? `${e.analyst_upside_pct >= 0 ? '+' : ''}${e.analyst_upside_pct.toFixed(1)}%` : '—'}
                  </TableCell>
                  <TableCell className={`tabular-nums text-[0.8rem] ${e.fcf_yield_pct != null && e.fcf_yield_pct >= 5 ? 'text-emerald-400' : ''}`}>
                    {e.fcf_yield_pct != null ? `${e.fcf_yield_pct.toFixed(1)}%` : '—'}
                  </TableCell>
                  <TableCell className="text-[0.72rem] text-muted-foreground tabular-nums">
                    {new Date(e.added_at).toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit' })}
                  </TableCell>
                  <TableCell>
                    <NoteEditor entry={e} onSave={note => updateNote(e.ticker, note)} />
                  </TableCell>
                  <TableCell>
                    <button
                      onClick={() => remove(e.ticker)}
                      className="text-muted-foreground/40 hover:text-red-400 transition-colors"
                      title="Eliminar de watchlist"
                    >
                      <Trash2 size={13} />
                    </button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
    </>
  )
}
