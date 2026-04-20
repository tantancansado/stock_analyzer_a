import { describe, expect, it } from 'vitest'
import Value from '@/pages/Value'
import Calendar from '@/pages/Calendar'
import EntrySetups from '@/pages/EntrySetups'
import MyPortfolio from '@/pages/MyPortfolio'
import Macro from '@/pages/Macro'

describe('page wrappers', () => {
  it('configures the Value tabs', () => {
    const element = Value()

    expect(element.props.paramKey).toBe('region')
    expect(element.props.defaultTab).toBe('us')
    expect(element.props.tabs.map((tab: { id: string }) => tab.id)).toEqual(['us', 'eu', 'global'])
  })

  it('configures the Calendar tabs', () => {
    const element = Calendar()

    expect(element.props.tabs.map((tab: { id: string }) => tab.id)).toEqual(['earnings', 'catalysts'])
  })

  it('configures the EntrySetups tabs', () => {
    const element = EntrySetups()

    expect(element.props.tabs.map((tab: { id: string }) => tab.id)).toEqual(['mean-reversion', 'momentum'])
  })

  it('configures the MyPortfolio tabs', () => {
    const element = MyPortfolio()

    expect(element.props.tabs.map((tab: { id: string }) => tab.id)).toEqual(['positions', 'signals'])
  })

  it('configures the Macro tabs', () => {
    const element = Macro()

    expect(element.props.tabs.map((tab: { id: string }) => tab.id)).toEqual(['radar', 'countries'])
  })
})
