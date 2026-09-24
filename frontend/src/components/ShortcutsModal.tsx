import { X, Keyboard } from 'lucide-react'
import { motion, useReducedMotion } from 'motion/react'
import { FILA, escalonado } from '@/lib/movimiento'
import CapaModal from './CapaModal'
import PanelAnimado, { FondoAnimado } from './PanelAnimado'

interface Props {
  open: boolean
  onClose: () => void
}

const SHORTCUTS: { keys: string[]; desc: string }[] = [
  { keys: ['⌘', 'K'],       desc: 'Abrir buscador / paleta de comandos' },
  { keys: ['?'],             desc: 'Mostrar atajos de teclado' },
  { keys: ['Esc'],           desc: 'Cerrar modal / paleta' },
  { keys: ['↑', '↓'],       desc: 'Navegar resultados en la paleta' },
  { keys: ['Enter'],         desc: 'Ir a la selección / buscar ticker' },
]

export default function ShortcutsModal({ open, onClose }: Readonly<Props>) {
  const quieto = useReducedMotion()

  // La presencia la lleva App.tsx, que es quien monta y desmonta este modal.
  // Aquí NO se anida otro AnimatePresence: con dos, cuál manda la salida
  // depende de cómo propague el contexto de presencia, y eso es justo el tipo
  // de detalle que funciona hoy y se rompe en la siguiente versión.
  if (!open) return null

  return (
        <CapaModal
          onClose={onClose}
          etiqueta="Atajos de teclado"
          className="fixed inset-0 z-[200] flex items-center justify-center p-4"
          claseFondo={null}
        >
          <FondoAnimado onClose={onClose} className="absolute inset-0 cursor-default bg-black/60 backdrop-blur-sm" />

          <PanelAnimado className="relative z-10 w-full max-w-sm liquid-glass rounded-2xl shadow-2xl p-5">
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Keyboard size={16} className="text-primary" />
                <span className="text-cuerpo font-bold text-foreground">Atajos de teclado</span>
              </div>
              <button
                onClick={onClose}
                className="p-1 rounded-lg text-muted-foreground hover:text-foreground hover:bg-foreground/10 transition-colors"
              >
                <X size={16} />
              </button>
            </div>

            {/* La lista entra escalonada, como la de «Personalizar menú»: son
                cinco filas cortas y el ritmo es justo lo que las hace leerse
                como una lista en vez de como un bloque. */}
            <ul className="space-y-2">
              {SHORTCUTS.map((s, i) => (
                <motion.li
                  key={s.desc}
                  className="flex items-center justify-between gap-4"
                  initial={quieto ? false : FILA.initial}
                  animate={FILA.animate}
                  transition={quieto ? { duration: 0 } : escalonado(i)}
                >
                  <span className="text-mini text-muted-foreground">{s.desc}</span>
                  <div className="flex items-center gap-1 shrink-0">
                    {s.keys.map(k => (
                      <kbd
                        key={k}
                        className="inline-flex items-center justify-center min-w-[22px] h-[22px] px-1.5 rounded-md bg-foreground/8 border border-border/50 text-micro font-semibold text-foreground/80 font-mono"
                      >
                        {k}
                      </kbd>
                    ))}
                  </div>
                </motion.li>
              ))}
            </ul>

            <p className="mt-4 text-micro text-muted-foreground text-center">
              Pulsa <kbd className="inline px-1 py-0.5 rounded bg-foreground/8 border border-border/40 text-micro">?</kbd> en cualquier momento para abrir este panel
            </p>
          </PanelAnimado>
        </CapaModal>
  )
}
