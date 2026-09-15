import { useSearchParams } from 'react-router-dom'
import { Suspense, type ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import Loading from './Loading'

export interface PageTab {
  id: string
  /**
   * Icono de línea, no emoji.
   *
   * Eran emoji (💼 🧠 📊) y se notaba: el sistema los pinta a todo color con
   * su propio estilo, así que cada pestaña tenía una ilustración distinta
   * compitiendo con el texto en vez de una familia de iconos coherente. Es lo
   * primero que delata una interfaz hecha a trozos.
   */
  icon: LucideIcon
  label: string
  content: ReactNode
}

interface Props {
  tabs: PageTab[]
  defaultTab?: string
  paramKey?: string
}

export default function PageTabs({ tabs, defaultTab, paramKey = 'tab' }: Readonly<Props>) {
  const [searchParams, setSearchParams] = useSearchParams()
  const reduceMotion = useReducedMotion()
  const rawParam = searchParams.get(paramKey)
  const validIds = new Set(tabs.map(t => t.id))
  const activeId = (rawParam && validIds.has(rawParam) ? rawParam : null) ?? defaultTab ?? tabs[0]?.id

  const setTab = (id: string) => setSearchParams({ [paramKey]: id }, { replace: true })
  const active = tabs.find(t => t.id === activeId) ?? tabs[0]

  return (
    <div>
      {/* Control segmentado, en voz baja.
          Estaba sobre `liquid-glass` —la piel de los modales— y la pestaña
          activa apilaba CUATRO marcas a la vez: color, borde, sombra y fondo
          teñido. El resultado era que las pestañas gritaban más que el título
          de la página, justo al revés de lo que debe pasar: el título dice
          dónde estás, la pestaña solo acota qué miras dentro.
          Ahora es lo que hace Apple y lo mismo que `.seg-tab`: pista gris
          discreta, pastilla para la activa y UNA sola marca. El color lo lleva
          el texto.

          `max-w-full` + scroll en un div INTERNO: sin esto, en móvil los tabs
          que no caben se cortaban a media palabra ("Momentum VCP" salía como
          "Mome…VC") sin ninguna pista de que hubiera más. */}
      <div className="page-tabs-shell mb-5 p-1 rounded-xl w-fit max-w-full bg-muted/60 border border-border/40">
       <div className="flex gap-1 overflow-x-auto scrollbar-hide">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setTab(tab.id)}
            className={`page-tab relative flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg px-3 py-2 text-apoyo font-medium transition-all sm:gap-2 sm:px-4 sm:text-cuerpo ${
              activeId === tab.id
                ? 'text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            {activeId === tab.id && (
              <motion.span
                layoutId={`page-tab-indicator-${paramKey}`}
                className="page-tab-indicator absolute inset-0 rounded-lg"
                transition={{ type: 'spring', stiffness: 420, damping: 34, mass: 0.7 }}
              />
            )}
            <tab.icon size={16} strokeWidth={1.75} className="relative z-10 shrink-0" />
            <span className="relative z-10">{tab.label}</span>
          </button>
        ))}
       </div>
      </div>

      <Suspense fallback={<Loading />}>
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={active.id}
            initial={reduceMotion ? false : { opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reduceMotion ? { opacity: 1 } : { opacity: 0, y: -6 }}
            transition={{ duration: reduceMotion ? 0 : 0.2, ease: [0.22, 1, 0.36, 1] }}
          >
            {active?.content}
          </motion.div>
        </AnimatePresence>
      </Suspense>
    </div>
  )
}
