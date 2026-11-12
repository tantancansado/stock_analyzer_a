import { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import { AnimatePresence } from 'motion/react'
import { TriangleAlert, Gem } from 'lucide-react'
import { precio } from '../lib/moneda'
import { Link, useSearchParams } from 'react-router-dom'
import { fetchValueOpportunities, fetchMarketRegime, fetchThesis, fetchMacroRadar, type ValueOpportunity } from '../api/client'
import StaleDataBanner from '../components/StaleDataBanner'
import { useApi } from '../hooks/useApi'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import CsvDownload from '../components/CsvDownload'
import PaginationBar from '../components/PaginationBar'
import InfoTooltip from '../components/InfoTooltip'
import ThesisModal from '../components/ThesisModal'
import TickerLogo from '../components/TickerLogo'
import OwnedBadge from '../components/OwnedBadge'
import ValuationBar from '../components/ValuationBar'
import OeAiBadge from '../components/OeAiBadge'
import PageHeader from '../components/PageHeader'
import AvisoDatosViejos from '@/components/AvisoDatosViejos'
import RendimientoReal from '../components/RendimientoReal'
import { LogoCandleBull } from '../components/BrandLogos'
import { ValueDecisionBadge } from '../components/ValueDecision'
import { getValueDecision } from '@/lib/valueDecision'
import PageShell from '@/components/PageShell'
import { nlRegimen, nlRegimenTono } from '@/lib/nl'
import CifrasClave from '../components/CifrasClave'

/** Nuestro potencial: la valoración triangulada (DCF y P/E propios con el
 *  consenso), que es lo que decide la lista. El objetivo de los analistas solo,
 *  donde no hay otro. Era el del analista: INTU salía a +19 % con nuestros
 *  modelos viéndole +150 %. */
function potencial(d: ValueOpportunity): number | null {
  return d.upside_triangulated_pct ?? d.analyst_upside_pct ?? null
}

// Value US decide con UNA regla (value_bands.nota_value) y cada fila dice su grupo,
// por qué en una línea, nuestro potencial y el precio. Nada más: el 12-nov la vista
// «avanzada» enseñaba al lado de tres de Prioridad ESPERA, EXIT, TRAP, un grado D,
// «HARD REJECT», un R:R con stop del 8 % y un P(win) que ya no se publica, y la clara
// repetía en cada fila el mismo párrafo fijo. El usuario: «sigo sin ver si está para
// entrar o no» y «hay demasiada info». Una sola vista; el resto vive en la ficha.
const GRUPO_FILTROS: { clave: string; etiqueta: string }[] = [
  { clave: 'ALL',       etiqueta: 'Todas' },
  { clave: 'PRIORIDAD', etiqueta: 'Prioridad' },
  { clave: 'OBSERVAR',  etiqueta: 'Observar' },
]

const MACRO_AVISO: Record<string, { bg: string; text: string; msg: string }> = {
  STRESS: { bg: 'border-yellow-500/30 bg-yellow-500/8', text: 'text-yellow-400', msg: 'Estrés moderado en el mercado.' },
  ALERT:  { bg: 'border-orange-500/30 bg-orange-500/8', text: 'text-orange-400', msg: 'Alerta macro elevada.' },
  CRISIS: { bg: 'border-red-500/40 bg-red-500/10',     text: 'text-red-400',    msg: 'Posible régimen de crisis.' },
}

const PAGE_SIZE = 50

// «Más datos»: los números para quien los quiera, sin los veredictos de reglas
// anteriores. Es una preferencia de pantalla de este navegador, nada más.
const CLAVE_MAS_DATOS = 'sa-value-mas-datos'
function leerMasDatos(): boolean {
  try { return localStorage.getItem(CLAVE_MAS_DATOS) === '1' } catch { return false }
}

const pct = (v: number | null | undefined, decimales = 1) =>
  v == null ? '—' : `${v.toLocaleString('es-ES', { maximumFractionDigits: decimales, minimumFractionDigits: decimales })} %`
const dias = (d: ValueOpportunity) =>
  d.days_to_earnings == null || d.days_to_earnings < 0 ? '—' : `${d.days_to_earnings} d`
const divBB = (d: ValueOpportunity) =>
  [d.dividend_yield_pct != null && d.dividend_yield_pct > 0 ? pct(d.dividend_yield_pct) : null,
   d.buyback_active ? 'recompra' : null].filter(Boolean).join(' + ') || '—'

export default function ValueUS() {
  const { data, loading, error } = useApi(() => fetchValueOpportunities(), [])
  const { data: regime } = useApi(() => fetchMarketRegime(), [])
  const { data: macroRaw } = useApi(() => fetchMacroRadar(), [])
  const [expandedRow, setExpandedRow] = useState<ValueOpportunity | null>(null)
  const [thesisText, setThesisText] = useState<string>('')
  const [searchParams, setSearchParams] = useSearchParams()
  const filterGrupo = searchParams.get('grupo') ?? 'ALL'
  const [page, setPage] = useState(1)
  const [focusedIdx, setFocusedIdx] = useState(-1)
  const [masDatos, setMasDatos] = useState(leerMasDatos)
  const alternarDatos = () => setMasDatos(v => {
    try { localStorage.setItem(CLAVE_MAS_DATOS, v ? '0' : '1') } catch { /* sin almacenamiento: solo esta visita */ }
    return !v
  })

  function setFilterGrupo(v: string) {
    setSearchParams(p => {
      const next = new URLSearchParams(p)
      if (v === 'ALL') next.delete('grupo')
      else next.set('grupo', v)
      return next
    }, { replace: true })
  }

  const currentThesisTicker = useRef<string | null>(null)
  // pagedRef must be declared before early returns (React Rules of Hooks)
  const pagedRef = useRef<ValueOpportunity[]>([])

  const toggleThesis = useCallback(async (ticker: string, row: ValueOpportunity) => {
    currentThesisTicker.current = ticker
    setExpandedRow(row)
    setThesisText('Cargando tesis...')
    const fallback = () => {
      const parts: string[] = []
      if (row.ai_reasoning) parts.push(row.ai_reasoning)
      if (row.conviction_reasons) parts.push(row.conviction_reasons.split(/\s*\|\|?\s*/).slice(0, 3).map(r => `• ${r}`).join('\n'))
      return parts.length > 0
        ? `${parts.join('\n\n')}\n\n_Tesis narrativa aún no generada. Mostrando el razonamiento de la IA._`
        : 'Sin tesis disponible'
    }
    try {
      const res = await fetchThesis(ticker)
      if (currentThesisTicker.current !== ticker) return
      setThesisText(res.data.thesis ?? fallback())
    } catch { if (currentThesisTicker.current === ticker) setThesisText(fallback()) }
  }, [])

  useEffect(() => { setPage(1); setFocusedIdx(-1) }, [filterGrupo])
  useEffect(() => { window.scrollTo({ top: 0, behavior: 'smooth' }) }, [page])

  // Teclado: j/k/flechas para moverse, Enter abre la ficha, Esc suelta.
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const tag = (document.activeElement as HTMLElement)?.tagName
      if (tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA') return
      if (e.key === 'Escape') { setFocusedIdx(-1); return }
      if (e.key === 'j' || e.key === 'ArrowDown' || e.key === 'k' || e.key === 'ArrowUp') {
        e.preventDefault()
        const paso = e.key === 'j' || e.key === 'ArrowDown' ? 1 : -1
        setFocusedIdx(i => {
          const n = Math.min(Math.max(i + paso, 0), pagedRef.current.length - 1)
          setTimeout(() => document.querySelector(`[data-row-idx="${n}"]`)?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }), 0)
          return n
        })
      } else if (e.key === 'Enter') {
        setFocusedIdx(i => {
          if (i >= 0 && pagedRef.current[i]) toggleThesis(pagedRef.current[i].ticker, pagedRef.current[i])
          return i
        })
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [toggleThesis])

  const rows = data?.data ?? []
  // La nota ya ordena: PRIORIDAD arriba y, dentro de cada grupo, lo más barata.
  const sorted = useMemo(
    () => rows
      .filter(r => filterGrupo === 'ALL' || r.value_grupo === filterGrupo)
      .sort((a, b) => (b.value_score ?? 0) - (a.value_score ?? 0)),
    [rows, filterGrupo],
  )

  // Concentración DE VERDAD: un sector que se lleve al menos un cuarto de la lista.
  const concentrated = useMemo(() => {
    const counts: Record<string, number> = {}
    rows.forEach(d => { const s = d.sector || 'Unknown'; counts[s] = (counts[s] || 0) + 1 })
    const minimo = Math.max(3, Math.ceil(rows.length * 0.25))
    return Object.entries(counts).filter(([, c]) => c >= minimo).sort((a, b) => b[1] - a[1])
  }, [rows])

  // Cabecera también mientras carga o si la API falla. Ver PageShell.
  if (loading || error) return <PageShell title="VALUE US" loading={loading} error={error} />

  const totalPages = Math.ceil(sorted.length / PAGE_SIZE)
  const paged = sorted.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)
  pagedRef.current = paged

  const usRegime = regime?.us as Record<string, string> | undefined
  // "UNKNOWN" no es un régimen, es la ausencia de dato: no se pinta.
  const regimeCrudo = usRegime?.regime || usRegime?.market_regime || ''
  const regimeLabel = nlRegimen(regimeCrudo)
  const regimeRec = usRegime?.recommendation || ''
  const macro = macroRaw as { regime?: { name: string }; composite_score?: number; max_score?: number } | null
  const aviso = macro?.regime?.name ? MACRO_AVISO[macro.regime.name] : undefined

  const fmtPotencial = (d: ValueOpportunity) => {
    const v = potencial(d)
    if (v == null) return <span className="text-muted-foreground">—</span>
    return <span className={v >= 0 ? 'text-emerald-400' : 'text-red-400'}>{v >= 0 ? '+' : ''}{v.toFixed(0)}%</span>
  }
  const abrir = (i: number, d: ValueOpportunity) => { setFocusedIdx(i); toggleThesis(d.ticker, d) }

  return (
    <>
      <StaleDataBanner module="value_us" />
      <PageHeader
        title="Value US"
        subtitle={<>
          {regimeLabel && (
            <Badge variant={nlRegimenTono(regimeCrudo)} className="mr-2 align-middle text-mini">
              {regimeLabel}
            </Badge>
          )}
          Prioridad: barata frente a su propia historia y creciendo. Es la que se compra.
          {regimeRec && <> · <strong className="text-foreground">{regimeRec}</strong></>}
        </>}
      >
        <CsvDownload dataset="value-us" label="CSV" />
        <LogoCandleBull size={44} className="ml-1 opacity-80 hidden sm:block" />
      </PageHeader>

      <AvisoDatosViejos clave="value" />

      {/* Lo primero tras la cabecera: si esta lista bate al índice o no. */}
      <RendimientoReal fuente="alpha_us" />

      {aviso && macro && (
        <div className={`mb-5 flex items-start gap-3 px-4 py-3 rounded-lg border ${aviso.bg}`}>
          <TriangleAlert size={16} strokeWidth={2} className={`shrink-0 mt-0.5 ${aviso.text}`} />
          <p className={`text-mini ${aviso.text}`}>
            Macro: {aviso.msg} ({macro.composite_score?.toFixed(1)}/{macro.max_score})
          </p>
          <Link to="/macro-radar" className={`ml-auto shrink-0 text-micro font-semibold ${aviso.text} hover:underline`}>
            Ver detalle →
          </Link>
        </div>
      )}

      <CifrasClave cifras={rows.some(r => r.value_grupo) ? [
        { etiqueta: 'Prioridad', valor: rows.filter(r => r.value_grupo === 'PRIORIDAD').length,
          sub: 'barata frente a su historia y creciendo', tono: 'favor' },
        { etiqueta: 'Observar', valor: rows.filter(r => r.value_grupo === 'OBSERVAR').length,
          sub: 'pasan la puerta, les falta algo' },
      ] : [
        { etiqueta: 'Publicadas', valor: rows.length, sub: 'con los datos verificados' },
      ]} />

      {concentrated.length > 0 && (
        <p className="mb-5 flex items-center gap-2 text-apoyo text-warn">
          <TriangleAlert size={12} strokeWidth={2.25} className="shrink-0" />
          Concentración sectorial: {concentrated.map(([s, c]) => `${s} (${c})`).join(', ')}
        </p>
      )}

      <div className="mb-3 flex flex-wrap items-center gap-2 border-b border-border/60 pb-3">
        {GRUPO_FILTROS.map(({ clave, etiqueta }) => (
          <button
            key={clave}
            type="button"
            onClick={() => setFilterGrupo(clave)}
            className={`filter-btn ${filterGrupo === clave ? 'active' : ''}`}
          >{etiqueta}</button>
        ))}
        <span className="ml-auto filter-label !normal-case !tracking-normal">
          {sorted.length !== rows.length ? `${sorted.length} / ${rows.length}` : `${rows.length} ideas`}
        </span>
        <button
          type="button"
          aria-pressed={masDatos}
          onClick={alternarDatos}
          className={`filter-btn ${masDatos ? 'active' : ''}`}
        >{masDatos ? 'Menos datos' : 'Más datos'}</button>
      </div>

      {/* Móvil */}
      <div className="sm:hidden space-y-2.5 mb-2">
        {paged.map((d, i) => {
          const decision = getValueDecision({ row: d })
          const pot = potencial(d)
          return (
            <div
              key={d.ticker}
              data-fila-value={d.ticker}
              onClick={() => abrir(i, d)}
              className={`glass rounded-2xl p-4 cursor-pointer active:scale-[0.98] transition-transform border entra-escalonada ${decision.panelClass}`}
              style={{ '--i': Math.min(i, 12) } as React.CSSProperties}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3 min-w-0">
                  <TickerLogo ticker={d.ticker} size="md" className="mt-0.5 shrink-0" />
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono font-extrabold text-titulo leading-tight">{d.ticker}</span>
                      <ValueDecisionBadge decision={decision} />
                      <OwnedBadge ticker={d.ticker} />
                    </div>
                    <span className="text-mini text-muted-foreground truncate max-w-[210px] block mt-0.5">{d.company_name}</span>
                  </div>
                </div>
                <div className="text-right shrink-0">
                  {pot != null && (
                    <div className={`text-cuerpo font-bold ${pot >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {pot >= 0 ? '+' : ''}{pot.toFixed(0)}%
                    </div>
                  )}
                  <div className="text-micro text-muted-foreground mt-0.5">{precio(d.current_price, d.ticker)}</div>
                </div>
              </div>
              <p className="mt-3 text-apoyo font-semibold text-foreground">{decision.headline}</p>
              {masDatos && (
                <p className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-mini text-muted-foreground tabular-nums">
                  <span>Nota {d.value_score?.toFixed(0) ?? '—'}</span>
                  <span>Caja libre {pct(d.fcf_yield_pct)}</span>
                  <span>Analistas {d.analyst_upside_pct != null ? `${d.analyst_upside_pct >= 0 ? '+' : ''}${d.analyst_upside_pct.toFixed(0)} %` : '—'}</span>
                  <span>Resultados {dias(d)}</span>
                  <span>{divBB(d)}</span>
                  {d.sector && <span>{d.sector}</span>}
                </p>
              )}
              <ValuationBar
                className="mt-2.5"
                precio={d.current_price}
                pctDesdeMax={d.pct_from_52w_high}
                pctDesdeMin={d.pct_from_52w_low}
                objetivoAnalista={d.target_price_analyst}
                objetivoDcf={d.target_price_dcf}
                objetivoPe={d.target_price_pe}
              />
            </div>
          )
        })}
      </div>

      {/* Escritorio */}
      <div className="hidden sm:block">
        <Card className="glass animate-fade-in-up overflow-clip">
          <div className="table-x-wrap">
          <Table>
            <TableHeader>
              <TableRow className="border-border/50 hover:bg-transparent">
                <TableHead>Empresa</TableHead>
                <TableHead>Decisión</TableHead>
                <TableHead className="min-w-[320px]">Por qué</TableHead>
                <TableHead className="whitespace-nowrap">
                  Potencial
                  <InfoTooltip text="Lo que le ven nuestras valoraciones (DCF y P/E propios) junto al consenso de analistas. El detalle de cada una está en la ficha." align="right" />
                </TableHead>
                <TableHead>Precio</TableHead>
                {masDatos && (
                  <>
                    <TableHead className="whitespace-nowrap">
                      Nota
                      <InfoTooltip text="Prioridad 80-100, Observar 40-60. Dentro de cada grupo, más alta = más barata frente a su historia y por caja libre." align="right" />
                    </TableHead>
                    <TableHead className="whitespace-nowrap">Caja libre</TableHead>
                    <TableHead className="whitespace-nowrap">Analistas</TableHead>
                    <TableHead className="whitespace-nowrap">Div. / recompra</TableHead>
                    <TableHead className="whitespace-nowrap">Resultados</TableHead>
                    <TableHead>Sector</TableHead>
                  </>
                )}
              </TableRow>
            </TableHeader>
            <TableBody>
              {paged.map((d, i) => {
                const decision = getValueDecision({ row: d })
                return (
                  <TableRow
                    key={d.ticker}
                    data-row-idx={i}
                    data-fila-value={d.ticker}
                    style={{ '--i': Math.min(i, 12) } as React.CSSProperties}
                    className={`entra-escalonada cursor-pointer transition-colors ${i === focusedIdx ? 'ring-1 ring-inset ring-primary/40 bg-primary/5' : ''}`}
                    onClick={() => abrir(i, d)}
                  >
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <TickerLogo ticker={d.ticker} size="sm" />
                        <div className="min-w-0">
                          <div className="flex items-center gap-1.5">
                            <span className="font-mono font-bold text-primary text-cuerpo">{d.ticker}</span>
                            <OwnedBadge ticker={d.ticker} />
                            {d.oe_ai_verdict?.toUpperCase().startsWith('UNRELIABLE') && (
                              <OeAiBadge verdict={d.oe_ai_verdict} adjustment={d.oe_ai_adjustment} />
                            )}
                          </div>
                          <div className="max-w-[180px] truncate text-mini text-muted-foreground">{d.company_name}</div>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell><ValueDecisionBadge decision={decision} /></TableCell>
                    <TableCell className="min-w-[320px] max-w-[560px] whitespace-normal text-apoyo text-foreground">
                      {decision.headline}
                    </TableCell>
                    <TableCell className="tabular-nums font-semibold">{fmtPotencial(d)}</TableCell>
                    <TableCell className="tabular-nums">{precio(d.current_price, d.ticker)}</TableCell>
                    {masDatos && (
                      <>
                        <TableCell className="tabular-nums text-muted-foreground">{d.value_score?.toFixed(0) ?? '—'}</TableCell>
                        <TableCell className="tabular-nums text-muted-foreground">{pct(d.fcf_yield_pct)}</TableCell>
                        <TableCell className="tabular-nums text-muted-foreground whitespace-nowrap">
                          {precio(d.target_price_analyst, d.ticker, null, 0)}
                          {d.analyst_upside_pct != null && ` (${d.analyst_upside_pct >= 0 ? '+' : ''}${d.analyst_upside_pct.toFixed(0)} %)`}
                        </TableCell>
                        <TableCell className="tabular-nums text-muted-foreground whitespace-nowrap">{divBB(d)}</TableCell>
                        <TableCell className="tabular-nums text-muted-foreground">{dias(d)}</TableCell>
                        <TableCell className="max-w-[140px] truncate text-muted-foreground text-mini">{d.sector ?? '—'}</TableCell>
                      </>
                    )}
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
          </div>
          {sorted.length === 0 && (
            <CardContent className="py-16 text-center">
              <Gem size={32} strokeWidth={1.5} className="mx-auto mb-4 opacity-20" />
              {/* Vacío por el gate NO es lo mismo que vacío por el filtro de grupo. */}
              <p className="font-medium text-muted-foreground">
                {rows.length === 0 ? 'Hoy no hay ninguna idea verificada' : 'Ninguna en este grupo'}
              </p>
              {rows.length === 0 && (
                <p className="mt-2 text-mini text-muted-foreground max-w-md mx-auto leading-relaxed">
                  El filtro de calidad no dio por buena ninguna: o los candidatos de hoy
                  no pasaron la revisión de datos, o no pudo ejecutarse.
                </p>
              )}
            </CardContent>
          )}
        </Card>
      </div>

      <PaginationBar page={page} totalPages={totalPages} onPage={setPage} />

      {/* AnimatePresence aquí, no dentro del modal: el modal se DESMONTA al
          cerrarse, y una animación de salida necesita que alguien retrase ese
          desmontaje. */}
      <AnimatePresence>
        {expandedRow && (
          <ThesisModal
            row={expandedRow}
            thesisText={thesisText}
            onClose={() => setExpandedRow(null)}
          />
        )}
      </AnimatePresence>
    </>
  )
}
