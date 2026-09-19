/**
 * El `$` escrito a mano volvió, y la app tiene tickers que no cotizan en dólares.
 *
 * La regla existe desde que Auto Trader, a 489,80 PENIQUES, se enseñaba como
 * «$489.80»: el símbolo equivocado con la magnitud equivocada engaña más que
 * no poner nada, porque 489,80 peniques son 4,90 £.
 *
 * CLAUDE.md lo dice —«Nunca escribir `$` delante de un precio. Usar `precio()`
 * de `lib/moneda.ts`»— pero era una regla escrita y sin test, así que el
 * 19-sep-2026 había vuelto en ocho sitios, incluido el gráfico de precios y la
 * tarjeta de idea del MÓVIL, que es donde más se mira.
 *
 * Lo que NO se prohíbe: `$` delante de un importe que es en dólares por
 * definición y no la cotización de un valor — capitalizaciones, primas de
 * opciones, materias primas, el capital de la cartera. Se distinguen por el
 * CONCEPTO que formatean, no por el fichero: eximir un fichero entero deja
 * pasar el siguiente precio que alguien escriba ahí dentro.
 */
import { readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const RAIZ = join(__dirname, '..')

/** Conceptos que SÍ van en dólares pase lo que pase, con su motivo. */
const EN_DOLARES: { patron: RegExp; motivo: string }[] = [
  { patron: /market_?cap|mcap/i,          motivo: 'capitalización de mercado' },
  { patron: /premium|prima/i,             motivo: 'primas de opciones del mercado US' },
  { patron: /usd/i,                       motivo: 'el nombre de la variable ya declara la divisa' },
  { patron: /total_value|portfolioSize|totalValue/i, motivo: 'capital de la cartera' },
  { patron: /annualDividends|dividend/i,  motivo: 'dividendo anual agregado' },
  { patron: /value_usd|volume|flujo/i,    motivo: 'importe agregado de flujo' },
  { patron: /par_value/i,                 motivo: 'valor nominal de un bono' },
  { patron: /item\.(price|week52|avg_2y)/, motivo: 'materias primas, cotizan en USD' },
  { patron: /\/ 1_?000|1e9|1e12|toFixed\(1\)\}B|\}M`|\}K`/, motivo: 'cifra agregada en M/B/K' },
]

/**
 * Líneas concretas, no ficheros enteros.
 *
 * Son la rama final de un formateador de importes cuyas otras ramas (M, K, B)
 * ya están cubiertas arriba: cuando la cifra es pequeña se devuelve tal cual y
 * la línea se queda sin ninguna pista de que habla de dinero agregado.
 *
 * Van por contenido exacto a propósito. Eximir el fichero dejaría pasar el
 * siguiente precio que alguien escriba dentro, que es justo como volvió el
 * bug.
 */
const LINEAS_EXENTAS: Record<string, string> = {
  'lib/formatters.ts:return `${sign}$${abs.toFixed(0)}`':
    'rama pequeña de fmtMoney; las de M/B están exentas arriba',
  'pages/Confluencia.tsx:return `$${v}`':
    'rama pequeña del formateador de flujo de opciones',
  'pages/OptionsFlow.tsx:return `$${v.toFixed(0)}`':
    'rama pequeña del formateador de primas',
}

function ficheros(dir: string): string[] {
  const out: string[] = []
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, e.name)
    if (e.isDirectory()) {
      if (e.name === 'test' || e.name === 'node_modules') continue
      out.push(...ficheros(p))
    } else if (/\.tsx?$/.test(e.name)) out.push(p)
  }
  return out
}

describe('nada de $ escrito a mano delante de una cotización', () => {
  const sospechosos: string[] = []
  for (const f of ficheros(RAIZ)) {
    const rel = f.slice(RAIZ.length + 1)
    readFileSync(f, 'utf8').split('\n').forEach((linea, i) => {
      const t = linea.trimStart()
      if (t.startsWith('//') || t.startsWith('*')) return
      if (!/`[^`]*\$\$\{/.test(linea)) return
      if (EN_DOLARES.some(({ patron }) => patron.test(linea))) return
      if (`${rel}:${linea.trim()}` in LINEAS_EXENTAS) return
      sospechosos.push(`${rel}:${i + 1}  ${linea.trim().slice(0, 90)}`)
    })
  }

  it('ningún sitio pinta el símbolo a mano sobre un precio', () => {
    expect(sospechosos, `usar precio() de lib/moneda.ts:\n  ${sospechosos.join('\n  ')}`)
      .toHaveLength(0)
  })

  it('cada excepción dice qué concepto cubre', () => {
    for (const { motivo } of EN_DOLARES) expect(motivo.length).toBeGreaterThan(15)
    for (const motivo of Object.values(LINEAS_EXENTAS)) expect(motivo.length).toBeGreaterThan(15)
  })

  it('las líneas exentas siguen existiendo tal cual', () => {
    // Una exención de una línea que ya no está es ruido que despista, y peor:
    // esconde que el código de al lado cambió sin revisarse.
    for (const clave of Object.keys(LINEAS_EXENTAS)) {
      const corte = clave.indexOf(':')
      const [rel, linea] = [clave.slice(0, corte), clave.slice(corte + 1)]
      const texto = readFileSync(join(RAIZ, rel), 'utf8')
      expect(texto.includes(linea), `ya no existe: ${clave}`).toBe(true)
    }
  })

  it('precio() pone peniques donde toca', async () => {
    const { precio } = await import('@/lib/moneda')
    expect(precio(489.8, 'AUTO.L')).toBe('489.80p')
    expect(precio(489.8, 'AAPL')).toBe('$489.80')
    expect(precio(null, 'AAPL')).toBe('—')
  })

  it('el detector caza un caso nuevo si aparece', () => {
    const linea = "  {d.current_price != null ? `$${d.current_price.toFixed(2)}` : '—'}"
    expect(/`[^`]*\$\$\{/.test(linea)).toBe(true)
    expect(EN_DOLARES.some(({ patron }) => patron.test(linea))).toBe(false)
  })
})
