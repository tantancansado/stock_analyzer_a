import { describe, expect, it, vi } from 'vitest'
import Calendar from '@/pages/Calendar'
import EntrySetups from '@/pages/EntrySetups'
import MyPortfolio from '@/pages/MyPortfolio'
import Macro from '@/pages/Macro'

describe('page wrappers', () => {
  // Europa y Global se apagan y encienden con un interruptor (lib/mercados.ts): los dos
  // estados tienen que funcionar, porque volver a encenderlo debe ser cambiar una línea.
  it('configures the Value tabs con Europa y Global encendidos', async () => {
    vi.resetModules()
    vi.doMock('@/lib/mercados', () => ({ EUROPA_Y_GLOBAL: true }))
    const { default: ValueEncendido } = await import('@/pages/Value')
    const element = ValueEncendido()
    vi.doUnmock('@/lib/mercados')

    expect(element.props.paramKey).toBe('region')
    expect(element.props.defaultTab).toBe('us')
    expect(element.props.tabs.map((tab: { id: string }) => tab.id)).toEqual(['us', 'eu', 'global'])
  })

  it('con Europa y Global apagados, Value es Value US sin pestañas', async () => {
    vi.resetModules()
    vi.doMock('@/lib/mercados', () => ({ EUROPA_Y_GLOBAL: false }))
    const { default: ValueApagado } = await import('@/pages/Value')
    const element = ValueApagado()
    vi.doUnmock('@/lib/mercados')

    expect(element.props.tabs).toBeUndefined()
    expect(element.props.children).toBeTruthy()
  })

  it('configures the Calendar tabs', () => {
    const element = Calendar()

    expect(element.props.tabs.map((tab: { id: string }) => tab.id)).toEqual(['earnings', 'catalysts'])
  })

  it('configures the EntrySetups tabs', () => {
    const element = EntrySetups()

    // EntrySetups wraps a freshness banner + PageTabs in a div, so dig out the
    // PageTabs child rather than reading props.tabs off the root element.
    const children = element.props.children as { props?: { tabs?: { id: string }[] } }[]
    const pageTabs = children.find(c => Array.isArray(c?.props?.tabs))
    expect(pageTabs?.props?.tabs?.map(tab => tab.id)).toEqual(['catalyst', 'mean-reversion', 'momentum', 'broad-bounce'])
  })

  it('configures the MyPortfolio tabs', () => {
    const element = MyPortfolio()

    // Sin «Estrategias IA» desde el 12-nov-2026: daba recortes, recompras y stops por
    // niveles de precio, contra la regla de venta.
    expect(element.props.tabs.map((tab: { id: string }) => tab.id)).toEqual(['positions', 'signals'])
  })

  it('configures the Macro tabs', () => {
    const element = Macro()

    expect(element.props.tabs.map((tab: { id: string }) => tab.id)).toEqual(['radar', 'countries', 'stress'])
  })
})
