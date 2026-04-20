import { useSearchParams } from 'react-router-dom'
import { Suspense, type ReactNode } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import Loading from './Loading'

export interface PageTab {
  id: string
  icon: string
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
      <div className="page-tabs-shell flex gap-1 mb-5 p-1 rounded-xl bg-white/5 border border-border/30 w-fit">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setTab(tab.id)}
            className={`page-tab relative flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeId === tab.id
                ? 'text-primary border border-primary/30 shadow-sm'
                : 'text-muted-foreground hover:text-foreground hover:bg-white/5'
            }`}
          >
            {activeId === tab.id && (
              <motion.span
                layoutId={`page-tab-indicator-${paramKey}`}
                className="page-tab-indicator absolute inset-0 rounded-lg bg-primary/15"
                transition={{ type: 'spring', stiffness: 420, damping: 34, mass: 0.7 }}
              />
            )}
            <span className="relative z-10 text-base leading-none">{tab.icon}</span>
            <span className="relative z-10">{tab.label}</span>
          </button>
        ))}
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
