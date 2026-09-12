import { useEffect, useMemo } from 'react'
import { X, RotateCcw, SlidersHorizontal } from 'lucide-react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { NAV_CATEGORIES, type NavLinkItem } from '@/lib/nav'
import { useNavPreferences } from '@/hooks/useNavPreferences'

// Los colores van en línea con variables CSS y NO con los alias de shadcn
// (text-foreground, text-muted-foreground, bg-accent, border-border...):
// en este proyecto falta el bloque @theme inline de Tailwind v4 y esas
// utilidades no llegan a generar CSS. `.text-primary` existe, pero escrita
// a mano en index.css y solo bajo `.dark` — usarla dejaba el modal sin
// color en modo claro. Las variables sí resuelven en los tres temas.

interface Props {
  readonly open: boolean
  readonly onClose: () => void
  readonly canSeeAdmin: boolean
}

/** Muelle único para todo el panel: una sola física, toda la interfaz se mueve igual. */
const MUELLE = { type: 'spring', stiffness: 420, damping: 34, mass: 0.8 } as const

// El estado va SIEMPRE en el color de la app, nunca en el de la sección. Con
// el color propio de cada una salía un arcoíris —y, peor, switches ROJOS en
// Macro, Dividend traps y Corrupción: en cualquier interfaz un control rojo
// significa peligro, no "activado"—. La identidad de la sección ya vive en su
// icono; el interruptor solo dice encendido o apagado.
function Interruptor({ on }: { readonly on: boolean }) {
  const quieto = useReducedMotion()
  return (
    <span
      aria-hidden
      className="relative inline-flex h-[22px] w-[38px] shrink-0 items-center rounded-full px-[3px] transition-colors duration-300"
      style={{
        background: on ? 'hsl(var(--primary))' : 'hsl(var(--muted-foreground) / 0.22)',
      }}
    >
      <motion.span
        className="block h-4 w-4 rounded-full bg-white shadow-sm"
        animate={{ x: on ? 16 : 0 }}
        transition={quieto ? { duration: 0 } : MUELLE}
      />
    </span>
  )
}

function Fila({
  item, visible, onToggle, index,
}: {
  readonly item: NavLinkItem
  readonly visible: boolean
  readonly onToggle: () => void
  readonly index: number
}) {
  const quieto = useReducedMotion()
  const Icono = item.icon
  return (
    <motion.button
      type="button"
      onClick={onToggle}
      aria-pressed={visible}
      // La entrada escalonada es lo que hace que la lista se lea como una
      // lista y no como un bloque que aparece de golpe. Se corta a los 12
      // primeros: más allá el retardo se nota como lentitud, no como ritmo.
      initial={quieto ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={quieto ? { duration: 0 } : { ...MUELLE, delay: Math.min(index, 12) * 0.022 }}
      whileTap={quieto ? undefined : { scale: 0.985 }}
      className="nav-custom-row flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-colors"
    >
      <span
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg transition-all duration-300"
        style={{
          background: visible ? `color-mix(in srgb, ${item.color} 14%, transparent)` : 'transparent',
          color: visible ? item.color : 'hsl(var(--muted-foreground) / 0.55)',
        }}
      >
        <Icono size={16} strokeWidth={1.75} />
      </span>
      <span
        className="min-w-0 flex-1 truncate text-[0.92rem] font-medium transition-colors duration-300"
        style={{ color: visible ? 'hsl(var(--foreground))' : 'hsl(var(--muted-foreground) / 0.6)' }}
      >
        {item.label}
      </span>
      <Interruptor on={visible} />
    </motion.button>
  )
}

export default function NavCustomizer({ open, onClose, canSeeAdmin }: Props) {
  const { hidden, toggle, reset, isHidden } = useNavPreferences()
  const quieto = useReducedMotion()

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  const categorias = useMemo(
    () => NAV_CATEGORIES
      .map(c => ({ ...c, items: c.items.filter(i => !i.adminOnly || canSeeAdmin) }))
      .filter(c => c.items.length > 0),
    [canSeeAdmin],
  )

  const total = categorias.reduce((n, c) => n + c.items.length, 0)
  const visibles = total - categorias.reduce(
    (n, c) => n + c.items.filter(i => isHidden(i.path)).length, 0)

  let indice = 0

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[200] flex items-end justify-center sm:items-center sm:p-4">
          <motion.button
            type="button"
            aria-label="Cerrar"
            onClick={onClose}
            className="absolute inset-0 cursor-default bg-black/55 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: quieto ? 0 : 0.18 }}
          />

          <motion.div
            className="liquid-glass nav-custom-panel relative z-10 flex max-h-[88vh] w-full flex-col rounded-t-2xl shadow-2xl sm:max-h-[78vh] sm:max-w-md sm:rounded-2xl"
            initial={quieto ? { opacity: 0 } : { opacity: 0, y: 28, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={quieto ? { opacity: 0 } : { opacity: 0, y: 20, scale: 0.985 }}
            transition={quieto ? { duration: 0 } : MUELLE}
          >
            {/* Asa: en móvil el panel sube desde abajo y el asa dice que se puede cerrar */}
            <div className="flex justify-center pt-2.5 sm:hidden">
              <span className="h-1 w-9 rounded-full" style={{ background: `hsl(var(--muted-foreground) / 0.28)` }} />
            </div>

            <header className="flex items-start justify-between gap-3 px-5 pb-3 pt-3.5">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <SlidersHorizontal size={16} strokeWidth={1.75} style={{ color: 'hsl(var(--primary))' }} />
                  <h2 className="text-[0.98rem] font-bold" style={{ color: 'hsl(var(--foreground))' }}>Tu menú</h2>
                </div>
                <p className="mt-0.5 text-[0.78rem]" style={{ color: `hsl(var(--muted-foreground) / 0.78)` }}>
                  Elige qué secciones quieres ver. Se guarda solo.
                </p>
              </div>
              <button
                type="button"
                onClick={onClose}
                aria-label="Cerrar"
                className="nav-custom-row -mr-1 shrink-0 rounded-lg p-1.5 transition-colors" style={{ color: `hsl(var(--muted-foreground) / 0.8)` }}
              >
                <X size={16} strokeWidth={1.75} />
              </button>
            </header>

            {/* Contador + progreso: el número cambia con el mismo muelle que todo lo demás */}
            <div className="px-5 pb-3">
              <div className="mb-1.5 flex items-baseline gap-1.5 text-[0.78rem]" style={{ color: `hsl(var(--muted-foreground) / 0.82)` }}>
                <motion.span
                  key={visibles}
                  className="font-bold tabular-nums" style={{ color: 'hsl(var(--foreground))' }}
                  initial={quieto ? false : { opacity: 0, y: -5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={quieto ? { duration: 0 } : MUELLE}
                >
                  {visibles}
                </motion.span>
                <span>de {total} secciones visibles</span>
              </div>
              {/* Colores en línea, no por clase: varios alias de shadcn no
                  llegan a generar CSS en este proyecto (falta @theme inline),
                  y la barra salía invisible. Las variables sí resuelven. */}
              <div
                className="h-1 w-full overflow-hidden rounded-full"
                style={{ background: 'hsl(var(--muted-foreground) / 0.18)' }}
              >
                <motion.div
                  className="h-full rounded-full"
                  style={{ background: 'hsl(var(--primary))' }}
                  animate={{ width: `${total ? (visibles / total) * 100 : 0}%` }}
                  transition={quieto ? { duration: 0 } : MUELLE}
                />
              </div>
            </div>

            {/* El scroll va AQUÍ dentro y no en .liquid-glass, que fija overflow
                clip para sus pseudo-elementos y lo pisaría. */}
            <div
              className="custom-scrollbar min-h-0 flex-1 overflow-y-auto px-2.5 pb-2"
              style={{
                // Máscara, no degradado de color: el panel es translúcido y un
                // degradado a un color opaco se vería como una banda sucia.
                maskImage: 'linear-gradient(to bottom, transparent 0, #000 14px, #000 calc(100% - 14px), transparent 100%)',
                WebkitMaskImage: 'linear-gradient(to bottom, transparent 0, #000 14px, #000 calc(100% - 14px), transparent 100%)',
              }}
            >
              {categorias.map(cat => (
                <section key={cat.name} className="mb-1.5">
                  <h3 className="px-3 pb-1 pt-2.5 text-[0.68rem] font-bold uppercase tracking-[0.14em]" style={{ color: `hsl(var(--muted-foreground) / 0.6)` }}>
                    {cat.name}
                  </h3>
                  {cat.items.map(item => (
                    <Fila
                      key={item.path}
                      item={item}
                      visible={!isHidden(item.path)}
                      onToggle={() => toggle(item.path)}
                      index={indice++}
                    />
                  ))}
                </section>
              ))}
            </div>

            <AnimatePresence initial={false}>
              {hidden.length > 0 && (
                <motion.footer
                  className="shrink-0 overflow-hidden border-t" style={{ borderColor: 'hsl(var(--border) / 0.45)' }}
                  initial={quieto ? false : { height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={quieto ? { opacity: 0 } : { height: 0, opacity: 0 }}
                  transition={quieto ? { duration: 0 } : MUELLE}
                >
                  <button
                    type="button"
                    onClick={reset}
                    className="nav-custom-row flex w-full items-center justify-center gap-2 px-5 py-3 text-[0.85rem] font-medium transition-colors" style={{ color: `hsl(var(--muted-foreground) / 0.85)` }}
                  >
                    <RotateCcw size={12} strokeWidth={1.75} />
                    Mostrar las {hidden.length} ocultas
                  </button>
                </motion.footer>
              )}
            </AnimatePresence>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}
