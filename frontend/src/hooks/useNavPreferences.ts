import { useCallback, useEffect, useState } from 'react'
import { NAV_CATEGORIES, type NavCategory } from '@/lib/nav'

const KEY = 'sa-nav-hidden-v1'

/**
 * Qué entradas del menú ha decidido ocultar este usuario.
 *
 * Se guarda lo OCULTO, no lo visible. Así una sección nueva aparece sola en
 * cuanto se añade al código, en vez de nacer invisible para todo el que ya
 * tuviera preferencias guardadas — que es como estas listas se pudren.
 */
function leer(): string[] {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return []
    const v: unknown = JSON.parse(raw)
    return Array.isArray(v) ? v.filter((x): x is string => typeof x === 'string') : []
  } catch {
    return []   // modo privado, almacenamiento bloqueado: menú completo
  }
}

/** Avisa a las demás instancias del hook dentro de esta misma pestaña. */
const EVENTO = 'sa-nav-hidden-change'

export function useNavPreferences() {
  const [hidden, setHidden] = useState<string[]>(leer)

  useEffect(() => {
    const sync = () => setHidden(leer())
    window.addEventListener(EVENTO, sync)
    window.addEventListener('storage', sync)   // otra pestaña
    return () => {
      window.removeEventListener(EVENTO, sync)
      window.removeEventListener('storage', sync)
    }
  }, [])

  const guardar = useCallback((next: string[]) => {
    setHidden(next)
    try {
      localStorage.setItem(KEY, JSON.stringify(next))
    } catch {
      /* sin persistencia; la sesión actual sigue funcionando */
    }
    window.dispatchEvent(new Event(EVENTO))
  }, [])

  const toggle = useCallback((path: string) => {
    const actual = leer()
    guardar(actual.includes(path) ? actual.filter(p => p !== path) : [...actual, path])
  }, [guardar])

  const reset = useCallback(() => guardar([]), [guardar])

  const isHidden = useCallback((path: string) => hidden.includes(path), [hidden])

  return { hidden, toggle, reset, isHidden }
}

/**
 * Las categorías sin lo oculto. Una categoría que se queda sin entradas
 * desaparece entera: dejar su título flotando sobre un hueco es peor que no
 * tenerla.
 */
export function visibleCategories(hidden: string[], canSeeAdmin: boolean): NavCategory[] {
  return NAV_CATEGORIES
    .map(cat => ({
      ...cat,
      items: cat.items.filter(i => (!i.adminOnly || canSeeAdmin) && !hidden.includes(i.path)),
    }))
    .filter(cat => cat.items.length > 0)
}
