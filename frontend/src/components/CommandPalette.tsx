import { useEffect, useRef, useState, useCallback } from 'react'
import { Command } from 'cmdk'
import { useNavigate } from 'react-router-dom'
import { Search, ArrowRight } from 'lucide-react'
import { NAV_LINKS } from '@/lib/nav'

interface Props {
  open: boolean
  onClose: () => void
}

export default function CommandPalette({ open, onClose }: Props) {
  const [query, setQuery]       = useState('')
  const navigate                = useNavigate()
  const inputRef                = useRef<HTMLInputElement>(null)

  // Focus input when opened
  useEffect(() => {
    if (open) {
      setQuery('')
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [open])

  // ESC key
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  const go = useCallback((path: string) => {
    navigate(path)
    onClose()
  }, [navigate, onClose])

  // Filter nav links by query
  const filtered = NAV_LINKS.filter(item => {
    if (!query) return true
    const q = query.toLowerCase()
    return (
      item.label.toLowerCase().includes(q) ||
      item.path.toLowerCase().includes(q) ||
      (item.keywords ?? []).some(k => k.toLowerCase().includes(q))
    )
  })

  if (!open) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-[200] bg-black/60 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Palette */}
      <div className="fixed inset-x-0 top-[15vh] z-[201] mx-auto w-full max-w-lg px-4">
        <Command
          className="cmd-palette glass rounded-2xl border border-border/80 shadow-2xl overflow-hidden"
          shouldFilter={false}
        >
          {/* Search input */}
          <div className="flex items-center gap-3 px-4 py-3.5 border-b border-border/50">
            <Search size={15} className="text-muted-foreground flex-shrink-0" strokeWidth={1.75} />
            <Command.Input
              ref={inputRef}
              value={query}
              onValueChange={setQuery}
              placeholder="Navegar, buscar ticker…"
              className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground/60 outline-none"
            />
            {query && (
              <button
                onClick={() => setQuery('')}
                className="text-muted-foreground/50 hover:text-muted-foreground text-xs px-1.5 py-0.5 rounded border border-border/40 transition-colors"
              >
                esc
              </button>
            )}
            {!query && (
              <kbd className="hidden sm:flex items-center gap-0.5 text-[0.6rem] text-muted-foreground/40 font-mono">
                <span className="text-xs">⌘</span>K
              </kbd>
            )}
          </div>

          <Command.List className="max-h-[400px] overflow-y-auto p-2">
            {filtered.length === 0 && (
              <Command.Empty className="py-10 text-center text-sm text-muted-foreground">
                Sin resultados para "<span className="text-foreground">{query}</span>"
              </Command.Empty>
            )}

            {filtered.length > 0 && (
              <Command.Group heading="Navegación" className="cmd-group">
                {filtered.map(item => (
                  <Command.Item
                    key={item.path}
                    value={item.path}
                    onSelect={() => go(item.path)}
                    className="cmd-item flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer text-sm transition-all"
                  >
                    <span
                      className="flex items-center justify-center w-6 h-6 rounded-md flex-shrink-0"
                      style={{ background: `${item.color}1a`, color: item.color }}
                    >
                      <item.icon size={13} strokeWidth={1.75} />
                    </span>
                    <span className="flex-1 text-foreground font-medium">{item.label}</span>
                    <ArrowRight size={12} className="text-muted-foreground/30 flex-shrink-0" />
                  </Command.Item>
                ))}
              </Command.Group>
            )}
          </Command.List>

          {/* Footer */}
          <div className="flex items-center gap-4 px-4 py-2.5 border-t border-border/40 text-[0.6rem] text-muted-foreground/50 font-mono">
            <span><kbd className="mr-0.5">↑↓</kbd> navegar</span>
            <span><kbd className="mr-0.5">↵</kbd> abrir</span>
            <span><kbd className="mr-0.5">esc</kbd> cerrar</span>
          </div>
        </Command>
      </div>
    </>
  )
}
