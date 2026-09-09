import { CheckCircle2, Eye, PauseCircle, ShieldAlert, SlidersHorizontal } from 'lucide-react'
import type { ValueOpportunity } from '@/api/client'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import type { ValueDecision } from '@/lib/valueDecision'

/** El orden es el de la decisión: lo accionable primero, lo descartado al
 *  final. Los cuatro tienen que estar o los contadores no suman lo publicado. */
const CONTADORES = [
  { clave: 'ready' as const, etiqueta: 'para revisar',    tono: 'text-emerald-400' },
  { clave: 'watch' as const, etiqueta: 'en vigilancia',   tono: 'text-sky-400' },
  { clave: 'wait'  as const, etiqueta: 'sin señal clara', tono: 'text-muted-foreground' },
  { clave: 'avoid' as const, etiqueta: 'mejor evitar',    tono: 'text-red-400' },
]

export function ValueDecisionBadge({ decision, className }: { decision: ValueDecision; className?: string }) {
  const Icon =
    decision.kind === 'ready' ? CheckCircle2 :
    decision.kind === 'watch' ? Eye :
    decision.kind === 'avoid' ? ShieldAlert :
    PauseCircle

  return (
    <span className={cn('inline-flex items-center gap-1.5 rounded-full border px-2 py-1 text-[0.68rem] font-bold', decision.badgeClass, className)}>
      <Icon size={12} strokeWidth={1.8} />
      {decision.label}
    </span>
  )
}

export function ValueModeToggle({
  clearMode,
  onChange,
}: {
  clearMode: boolean
  onChange: (enabled: boolean) => void
}) {
  return (
    <button
      type="button"
      aria-pressed={clearMode}
      onClick={() => onChange(!clearMode)}
      className={cn(
        'inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs font-semibold transition-colors',
        clearMode
          ? 'border-primary/40 bg-primary/10 text-primary'
          : 'border-border/50 text-muted-foreground hover:border-border/80 hover:text-foreground'
      )}
      title={clearMode ? 'Cambiar a vista avanzada' : 'Cambiar a vista clara'}
    >
      <SlidersHorizontal size={13} strokeWidth={1.8} />
      {clearMode ? 'Vista clara' : 'Vista avanzada'}
    </button>
  )
}

export function ValueClarityPanel({
  rows,
  totalPublicadas,
  onResetFilters,
  getDecision,
}: {
  rows: ValueOpportunity[]
  /** Ideas publicadas hoy ANTES de aplicar filtros de la pantalla. */
  totalPublicadas: number
  onResetFilters: () => void
  getDecision: (row: ValueOpportunity) => ValueDecision
}) {
  const evaluated = rows.map(row => ({ row, decision: getDecision(row) }))
  // Los cuatro tipos que devuelve getValueDecision. `wait` no tenía contador:
  // con 4 ideas publicadas (1 watch + 3 wait) el resumen decía "1" y parecía
  // que el sistema no había encontrado casi nada. Los contadores tienen que
  // sumar lo que hay en pantalla o están mintiendo.
  const grupos = {
    ready: evaluated.filter(i => i.decision.kind === 'ready'),
    watch: evaluated.filter(i => i.decision.kind === 'watch'),
    wait:  evaluated.filter(i => i.decision.kind === 'wait'),
    avoid: evaluated.filter(i => i.decision.kind === 'avoid'),
  }
  const sinNada = evaluated.length === 0

  return (
    // Tira compacta, no panel hero. Antes esto medía ~850px en móvil y su
    // tarjeta grande repetía el MISMO pick que encabeza la lista de abajo:
    // veías EQIX dos veces, una en formato hero de media pantalla y otra tres
    // dedos más abajo. Los contadores son lo único que la lista no puede
    // decirte de un vistazo, así que es lo único que se queda.
    <Card className="glass mb-4 overflow-clip">
      <CardContent className="p-3 sm:p-4">
        {sinNada ? (
          // Dos situaciones muy distintas que antes decían lo mismo: que el
          // pipeline no publicara nada (legítimo — el gate solo saca lo que
          // la IA verifica) o que tus filtros lo escondan. El 9-sep-2026 el
          // suelo de score por defecto (55) dejaba esta pantalla en "no hay
          // ideas" con 4 picks publicados: parecía que no había encontrado nada.
          <div className="text-sm">
            {totalPublicadas > 0 ? (
              <>
                <p className="text-foreground">
                  Tus filtros están escondiendo {totalPublicadas === 1 ? 'la única idea' : `las ${totalPublicadas} ideas`} de hoy.
                </p>
                <button
                  type="button"
                  onClick={onResetFilters}
                  className="mt-2 font-semibold text-primary underline underline-offset-2"
                >
                  Quitar filtros
                </button>
              </>
            ) : (
              <p className="text-muted-foreground">
                Hoy no ha pasado ninguna idea el filtro de calidad. No es un fallo:
                el sistema prefiere no enseñarte nada antes que enseñarte algo sin verificar.
              </p>
            )}
          </div>
        ) : (
          // Solo los contadores. Los botones de vista viven en el panel
          // "Vista recomendada activa" que va justo debajo, con más contexto
          // — tenerlos también aquí era el mismo par de controles dos veces
          // seguidas.
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
            {CONTADORES.map(({ clave, etiqueta, tono }) => (
              <div key={clave} className="flex items-baseline gap-1.5">
                <span className={`text-lg font-extrabold tabular-nums ${tono}`}>{grupos[clave].length}</span>
                <span className="text-[0.68rem] font-medium text-muted-foreground">{etiqueta}</span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
