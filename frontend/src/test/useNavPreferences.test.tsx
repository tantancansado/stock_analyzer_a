import { describe, it, expect, beforeEach, vi } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { useNavPreferences, visibleCategories } from '../hooks/useNavPreferences'
import { NAV_CATEGORIES, type NavCategory } from '../lib/nav'

const KEY = 'sa-nav-hidden-v1'

beforeEach(() => localStorage.clear())

describe('useNavPreferences', () => {
  it('arranca con el menú entero', () => {
    const { result } = renderHook(() => useNavPreferences())
    expect(result.current.hidden).toEqual([])
  })

  it('oculta y vuelve a mostrar', () => {
    const { result } = renderHook(() => useNavPreferences())
    act(() => result.current.toggle('/bounce'))
    expect(result.current.isHidden('/bounce')).toBe(true)
    act(() => result.current.toggle('/bounce'))
    expect(result.current.isHidden('/bounce')).toBe(false)
  })

  it('persiste entre montajes', () => {
    const primero = renderHook(() => useNavPreferences())
    act(() => primero.result.current.toggle('/bounce'))
    const segundo = renderHook(() => useNavPreferences())
    expect(segundo.result.current.hidden).toContain('/bounce')
  })

  it('restablece', () => {
    const { result } = renderHook(() => useNavPreferences())
    act(() => { result.current.toggle('/bounce'); result.current.toggle('/options') })
    expect(result.current.hidden).toHaveLength(2)
    act(() => result.current.reset())
    expect(result.current.hidden).toEqual([])
  })

  it('mantiene sincronizadas dos instancias en la misma pestaña', () => {
    // El sidebar y el modal montan el hook por separado: si no se hablan, se
    // apaga una sección en el modal y el menú de detrás no se entera.
    const sidebar = renderHook(() => useNavPreferences())
    const modal   = renderHook(() => useNavPreferences())
    act(() => modal.result.current.toggle('/bounce'))
    expect(sidebar.result.current.isHidden('/bounce')).toBe(true)
  })

  it('guarda lo OCULTO, no lo visible', () => {
    // Importa: así una sección nueva aparece sola al añadirla al código, en
    // vez de nacer invisible para quien ya tuviera preferencias guardadas.
    const { result } = renderHook(() => useNavPreferences())
    act(() => result.current.toggle('/bounce'))
    expect(JSON.parse(localStorage.getItem(KEY)!)).toEqual(['/bounce'])
  })

  it('sobrevive a un localStorage corrupto', () => {
    localStorage.setItem(KEY, '{no es json')
    const { result } = renderHook(() => useNavPreferences())
    expect(result.current.hidden).toEqual([])
  })

  it('descarta basura que no sean rutas', () => {
    localStorage.setItem(KEY, JSON.stringify(['/bounce', 42, null, { a: 1 }]))
    const { result } = renderHook(() => useNavPreferences())
    expect(result.current.hidden).toEqual(['/bounce'])
  })

  it('no revienta si el almacenamiento está bloqueado', () => {
    // Modo privado / cookies bloqueadas: setItem lanza.
    const spy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('QuotaExceededError')
    })
    const { result } = renderHook(() => useNavPreferences())
    expect(() => act(() => result.current.toggle('/bounce'))).not.toThrow()
    expect(result.current.isHidden('/bounce')).toBe(true)   // vale para esta sesión
    spy.mockRestore()
  })
})

describe('visibleCategories', () => {
  const admin = (c: NavCategory[]) => c.flatMap(x => x.items).filter(i => i.adminOnly)

  it('sin nada oculto devuelve el menú completo', () => {
    const vis = visibleCategories([], true)
    expect(vis.flatMap(c => c.items)).toHaveLength(NAV_CATEGORIES.flatMap(c => c.items).length)
  })

  it('quita lo oculto', () => {
    const vis = visibleCategories(['/bounce'], true)
    expect(vis.flatMap(c => c.items).map(i => i.path)).not.toContain('/bounce')
  })

  it('una categoría que se queda vacía desaparece entera', () => {
    // Un título de categoría flotando sobre un hueco es peor que no tenerla.
    const objetivo = NAV_CATEGORIES[0]
    const vis = visibleCategories(objetivo.items.map(i => i.path), true)
    expect(vis.map(c => c.name)).not.toContain(objetivo.name)
  })

  it('esconde lo de admin a quien no lo es', () => {
    expect(admin(visibleCategories([], false))).toHaveLength(0)
    expect(admin(visibleCategories([], true)).length).toBeGreaterThan(0)
  })

  it('una ruta oculta que ya no existe no rompe nada', () => {
    const vis = visibleCategories(['/seccion-que-se-borro'], true)
    expect(vis.flatMap(c => c.items)).toHaveLength(NAV_CATEGORIES.flatMap(c => c.items).length)
  })
})
