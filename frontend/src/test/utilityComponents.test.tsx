import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import CsvDownload from '@/components/CsvDownload'
import { Progress } from '@/components/ui/progress'
import { Input } from '@/components/ui/input'

const downloadCsvMock = vi.fn()
const fetchPipelineStatusMock = vi.fn()
const fetchPipelineHealthMock = vi.fn()

vi.mock('@/api/client', () => ({
  downloadCsv: (...args: unknown[]) => downloadCsvMock(...args),
  fetchPipelineStatus: () => fetchPipelineStatusMock(),
  fetchPipelineHealth: () => fetchPipelineHealthMock(),
}))

async function loadBannerModule() {
  vi.resetModules()
  return import('@/components/StaleDataBanner')
}

describe('utility components', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('downloads the requested CSV dataset', async () => {
    const user = userEvent.setup()
    render(<CsvDownload dataset="value-us" label="Descargar" />)

    await user.click(screen.getByRole('button', { name: /descargar/i }))

    expect(downloadCsvMock).toHaveBeenCalledWith('value-us')
  })

  it('renders Progress with the expected transform', () => {
    const { container } = render(<Progress value={35} />)
    const bar = container.querySelector('.bg-primary') as HTMLDivElement
    expect(bar.style.transform).toBe('translateX(-65%)')
  })

  it('renders Input with the provided type and value', () => {
    render(<Input type="email" defaultValue="ana@example.com" />)
    const input = screen.getByDisplayValue('ana@example.com')
    expect(input).toHaveAttribute('type', 'email')
  })

  it('shows a green fresh-data badge for an up-to-date module', async () => {
    const today = new Date().toISOString().slice(0, 10)
    fetchPipelineStatusMock.mockResolvedValue({
      run_date: today,
      last_run: new Date().toISOString(),
      status: 'ok',
    })
    fetchPipelineHealthMock.mockResolvedValue({
      generated_at: new Date().toISOString(),
      pipeline_date: today,
      ok_count: 1,
      total: 1,
      modules: {
        cerebro: { status: 'ok', date: today, days_ago: 0 },
      },
    })

    const { default: StaleDataBanner } = await loadBannerModule()
    render(<StaleDataBanner module="cerebro" />)

    expect(await screen.findByText('Datos en vivo')).toBeInTheDocument()
    expect(screen.getByText(/Actualizado hoy/)).toBeInTheDocument()
  })

  it('shows a legacy stale warning when the pipeline is old', async () => {
    const fourDaysAgo = new Date(Date.now() - 4 * 86_400_000).toISOString()
    fetchPipelineStatusMock.mockResolvedValue({
      run_date: fourDaysAgo.slice(0, 10),
      last_run: fourDaysAgo,
      status: 'ok',
    })
    fetchPipelineHealthMock.mockResolvedValue(null)

    const { default: StaleDataBanner } = await loadBannerModule()
    render(<StaleDataBanner dataDate={fourDaysAgo} />)

    await waitFor(() => {
      expect(screen.getByText('Datos posiblemente desactualizados')).toBeInTheDocument()
    })
  })
})
