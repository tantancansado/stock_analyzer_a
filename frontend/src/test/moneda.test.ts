import { describe, it, expect } from 'vitest'
import { divisaDe, precio } from '../lib/moneda'

describe('divisaDe', () => {
  it('un ticker sin sufijo es dólares', () => {
    expect(divisaDe('AAPL')).toBe('USD')
    expect(divisaDe('BRK.B')).toBe('USD')   // sufijo de clase, no de bolsa
  })

  it('reconoce las bolsas europeas', () => {
    expect(divisaDe('AI.PA')).toBe('EUR')
    expect(divisaDe('G24.DE')).toBe('EUR')
    expect(divisaDe('NESN.SW')).toBe('CHF')
  })

  it('Londres cotiza en peniques', () => {
    expect(divisaDe('AUTO.L')).toBe('GBp')
    expect(divisaDe('LSEG.L')).toBe('GBp')
  })

  it('reconoce Japón, Canadá y Australia', () => {
    expect(divisaDe('4684.T')).toBe('JPY')
    expect(divisaDe('CSU.TO')).toBe('CAD')
    expect(divisaDe('TNE.AX')).toBe('AUD')
  })

  it('una divisa explícita manda sobre el sufijo', () => {
    expect(divisaDe('AUTO.L', 'USD')).toBe('USD')
  })
})

describe('precio', () => {
  it('el caso que motivó esto: Auto Trader no vale 489 dólares', () => {
    // 489,80 peniques son unas 4,90 libras. Se enseñaba como "$489.80".
    expect(precio(489.8, 'AUTO.L')).toBe('489.80p')
    expect(precio(489.8, 'AUTO.L')).not.toContain('$')
  })

  it('mantiene el dólar para lo americano', () => {
    expect(precio(361.99, 'AVGO')).toBe('$361.99')
  })

  it('pone el símbolo de cada bolsa', () => {
    expect(precio(120.5, 'AI.PA')).toBe('€120.50')
    expect(precio(88, 'CSU.TO')).toBe('C$88.00')
    expect(precio(3200, '4684.T')).toBe('¥3200.00')
  })

  it('sin dato devuelve un guion, no "$undefined"', () => {
    expect(precio(null, 'AAPL')).toBe('—')
    expect(precio(undefined, 'AAPL')).toBe('—')
    expect(precio(NaN, 'AAPL')).toBe('—')
  })
})
