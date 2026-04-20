import { act, render, renderHook, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { useSortedData } from '@/hooks/useSortedData'

interface Row {
  ticker: string
  score: number | null
}

describe('useSortedData', () => {
  it('sorts by the default key and direction', () => {
    const data: Row[] = [
      { ticker: 'MSFT', score: 20 },
      { ticker: 'AAPL', score: 40 },
      { ticker: 'NVDA', score: 10 },
    ]

    const { result } = renderHook(() => useSortedData(data, 'score'))

    expect(result.current.sorted.map(row => row.ticker)).toEqual(['AAPL', 'MSFT', 'NVDA'])
    expect(result.current.sortKey).toBe('score')
    expect(result.current.sortDir).toBe('desc')
  })

  it('toggles direction when sorting the same key twice', () => {
    const data: Row[] = [
      { ticker: 'MSFT', score: 20 },
      { ticker: 'AAPL', score: 40 },
      { ticker: 'NVDA', score: 10 },
    ]

    const { result } = renderHook(() => useSortedData(data, 'score'))

    act(() => {
      result.current.onSort('score')
    })

    expect(result.current.sortDir).toBe('asc')
    expect(result.current.sorted.map(row => row.ticker)).toEqual(['NVDA', 'MSFT', 'AAPL'])
  })

  it('switches key and resets direction to descending', () => {
    const data: Row[] = [
      { ticker: 'MSFT', score: 20 },
      { ticker: 'AAPL', score: 40 },
      { ticker: 'NVDA', score: 10 },
    ]

    const { result } = renderHook(() => useSortedData(data, 'score'))

    act(() => {
      result.current.onSort('ticker')
    })

    expect(result.current.sortKey).toBe('ticker')
    expect(result.current.sortDir).toBe('desc')
    expect(result.current.sorted.map(row => row.ticker)).toEqual(['NVDA', 'MSFT', 'AAPL'])
  })

  it('keeps null numeric values at the end for descending order', () => {
    const data: Row[] = [
      { ticker: 'MSFT', score: 20 },
      { ticker: 'AAPL', score: null },
      { ticker: 'NVDA', score: 10 },
    ]

    const { result } = renderHook(() => useSortedData(data, 'score'))

    expect(result.current.sorted.map(row => row.ticker)).toEqual(['MSFT', 'NVDA', 'AAPL'])
  })

  it('renders a sort icon only for the active key', async () => {
    const user = userEvent.setup()
    const data: Row[] = [
      { ticker: 'MSFT', score: 20 },
      { ticker: 'AAPL', score: 40 },
    ]

    function Harness() {
      const { SortIcon, onSort } = useSortedData(data, 'score')
      return (
        <div>
          <button onClick={() => onSort('score')}>
            Score
            <SortIcon k="score" />
          </button>
          <button>
            Ticker
            <SortIcon k="ticker" />
          </button>
        </div>
      )
    }

    render(<Harness />)

    expect(screen.getAllByRole('button')[0].querySelector('svg')).toBeTruthy()
    expect(screen.getAllByRole('button')[1].querySelector('svg')).toBeFalsy()

    await user.click(screen.getByRole('button', { name: /score/i }))

    expect(screen.getAllByRole('button')[0].querySelector('svg')).toBeTruthy()
  })
})
