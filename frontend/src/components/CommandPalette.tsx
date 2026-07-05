import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search } from 'lucide-react'
import { cn } from '@/lib/utils'
import { NAV_CATEGORIES } from '@/lib/nav'

// El palette se alimenta de la MISMA fuente que el menú (nav.ts). Antes tenía
// 9 items hardcodeados de 40+ páginas, algunos con paths obsoletos (p.ej.
// /portfolio-tracker, que no existe): navegar con Cmd+K a media app fallaba.
// Ahora cubre todo y no se puede desincronizar.
const NAVIGATION = NAV_CATEGORIES.flatMap(cat =>
  cat.items
    .filter(it => !it.adminOnly)
    .map(it => ({
      id: it.path,
      title: it.label,
      icon: <it.icon size={16} />,
      path: it.path,
      keywords: it.keywords ?? [],
    })),
)

export default function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const navigate = useNavigate()
  const inputRef = useRef<HTMLInputElement>(null)

  // Toggle via props logic handled in App.tsx (App captures Cmd+K and sets open)
  // We just need to handle Escape to close
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }
    document.addEventListener('keydown', down)
    return () => document.removeEventListener('keydown', down)
  }, [onClose])

  // Auto focus input when opened
  useEffect(() => {
    if (open) {
      setQuery('')
      setSelectedIndex(0)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [open])

  // Filter items
  const q = query.trim().toLowerCase()
  const navItems = q
    ? NAVIGATION.filter(
        n =>
          n.title.toLowerCase().includes(q) ||
          n.id.includes(q) ||
          ('keywords' in n && (n.keywords as string[]).some(kw => kw.includes(q))),
      )
    : NAVIGATION
  const isTickerSearch = q.length >= 1 && q.length <= 5 && /^[a-z]+$/i.test(q)
  
  const totalItems = navItems.length + (isTickerSearch ? 1 : 0)

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!open) return
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedIndex((i) => (i + 1) % totalItems)
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedIndex((i) => (i - 1 + totalItems) % totalItems)
      } else if (e.key === 'Enter') {
        e.preventDefault()
        if (totalItems === 0) return
        
        // Handle selection
        if (isTickerSearch && selectedIndex === 0) {
          navigate(`/search?q=${q.toUpperCase()}`)
          onClose()
        } else {
          const navIdx = isTickerSearch ? selectedIndex - 1 : selectedIndex
          if (navIdx >= 0 && navIdx < navItems.length) {
            navigate(navItems[navIdx].path)
            onClose()
          }
        }
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [open, selectedIndex, totalItems, isTickerSearch, q, navigate, navItems, onClose])

  // Reset index on query change
  useEffect(() => { setSelectedIndex(0) }, [query])

  if (!open) return null

  return (
    <>
      <div 
        className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm animate-in fade-in duration-200"
        onClick={onClose}
      />
      <div className="fixed left-[50%] top-[20%] z-50 w-full max-w-lg translate-x-[-50%] rounded-xl border border-primary/20 bg-background/80 shadow-2xl backdrop-blur-xl animate-in zoom-in-95 duration-200 overflow-hidden">
        <div className="flex items-center border-b border-primary/20 px-3">
          <Search className="mr-2 h-4 w-4 shrink-0 text-primary opacity-50" />
          <input
            ref={inputRef}
            className="flex h-12 w-full rounded-md bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50"
            placeholder="Escribe un comando o busca un ticker..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <kbd className="pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground opacity-100">
            ESC
          </kbd>
        </div>
        
        <div className="max-h-[300px] overflow-y-auto p-2 scrollbar-none">
          {totalItems === 0 && (
            <div className="py-6 text-center text-sm text-muted-foreground">
              Sin resultados para <span className="font-mono">{query}</span>
            </div>
          )}

          {isTickerSearch && (
            <div className="mb-2">
              <div className="px-2 py-1.5 text-[0.65rem] font-semibold uppercase text-muted-foreground">Analizar Ticker</div>
              <div
                role="option"
                aria-selected={selectedIndex === 0}
                tabIndex={0}
                className={cn(
                  "flex items-center gap-2 rounded-sm px-2 py-2.5 text-sm transition-colors cursor-pointer",
                  selectedIndex === 0 ? "bg-primary/20 text-primary" : "text-foreground hover:bg-white/5"
                )}
                onClick={() => { navigate(`/search?q=${q.toUpperCase()}`); onClose() }}
              >
                <Search size={16} className="text-primary/70" />
                <span>Analizar <strong className="font-mono text-primary">{q.toUpperCase()}</strong></span>
              </div>
            </div>
          )}

          {navItems.length > 0 && (
            <div>
              <div className="px-2 py-1.5 text-[0.65rem] font-semibold uppercase text-muted-foreground">Navegación</div>
              {navItems.map((item, i) => {
                const idx = isTickerSearch ? i + 1 : i
                return (
                  <div
                    key={item.id}
                    className={cn(
                      "flex items-center gap-2 rounded-sm px-2 py-2 text-sm transition-colors cursor-pointer mb-0.5",
                      selectedIndex === idx ? "bg-primary/20 text-primary shadow-[inset_0_0_10px_rgba(0,255,255,0.1)]" : "text-foreground hover:bg-white/5"
                    )}
                    onClick={() => { navigate(item.path); onClose() }}
                  >
                    <div className={selectedIndex === idx ? "text-primary" : "text-muted-foreground"}>
                      {item.icon}
                    </div>
                    {item.title}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </>
  )
}
