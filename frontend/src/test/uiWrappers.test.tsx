import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

describe('ui wrappers', () => {
  it('renders Badge variants', () => {
    render(<Badge variant="green">Activo</Badge>)
    expect(screen.getByText('Activo')).toBeInTheDocument()
  })

  it('renders a semantic separator when decorative is false', () => {
    render(<Separator decorative={false} orientation="vertical" />)
    expect(screen.getByRole('separator')).toHaveAttribute('aria-orientation', 'vertical')
  })

  it('renders the table wrappers and caption', () => {
    render(
      <Table>
        <TableCaption>Resumen</TableCaption>
        <TableHeader>
          <TableRow>
            <TableHead>Ticker</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow>
            <TableCell>AAPL</TableCell>
          </TableRow>
        </TableBody>
      </Table>,
    )

    expect(screen.getByRole('table')).toBeInTheDocument()
    expect(screen.getByText('Resumen')).toBeInTheDocument()
    expect(screen.getByText('Ticker')).toBeInTheDocument()
    expect(screen.getByText('AAPL')).toBeInTheDocument()
  })
})
