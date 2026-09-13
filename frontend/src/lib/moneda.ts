/**
 * Divisa de cotización a partir del sufijo de bolsa del ticker.
 *
 * El frontend escribía `$` a pelo delante de cualquier precio. La lista
 * principal tiene 13 tickers que no cotizan en dólares (AI.PA, 4684.T,
 * CSU.TO, TNE.AX, AUTO.L…), así que salían con símbolo de dólar.
 *
 * El caso peor son las británicas: Londres cotiza en PENIQUES, no en libras.
 * Auto Trader a 489,80 peniques —unas 4,90 £— se enseñaba como "$489.80", que
 * se lee como casi quinientos dólares. No es un detalle estético: es un precio
 * equivocado por dos órdenes de magnitud. (Lo mismo que avisa
 * currency_normalizer.py en el backend sobre el PER 100x de esos tickers.)
 */

const DIVISA_POR_SUFIJO: Record<string, string> = {
  L:  'GBp',   // Londres cotiza en peniques
  IL: 'USD',   // Londres, línea internacional en dólares
  PA: 'EUR', DE: 'EUR', F: 'EUR', AS: 'EUR', BR: 'EUR', MC: 'EUR',
  MI: 'EUR', LS: 'EUR', VI: 'EUR', IR: 'EUR', HE: 'EUR',
  SW: 'CHF', S: 'CHF',
  ST: 'SEK', OL: 'NOK', CO: 'DKK',
  T:  'JPY',
  TO: 'CAD', V: 'CAD',
  AX: 'AUD', NZ: 'NZD',
  HK: 'HKD', SI: 'SGD',
}

const SIMBOLO: Record<string, string> = {
  USD: '$', EUR: '€', GBP: '£', CHF: 'CHF ', JPY: '¥',
  CAD: 'C$', AUD: 'A$', NZD: 'NZ$', HKD: 'HK$', SGD: 'S$',
  SEK: 'kr ', NOK: 'kr ', DKK: 'kr ',
}

/** Divisa en la que cotiza un ticker. USD si no tiene sufijo conocido. */
export function divisaDe(ticker: string | null | undefined, explicita?: string | null): string {
  if (explicita) return explicita
  const t = String(ticker || '').trim().toUpperCase()
  const punto = t.lastIndexOf('.')
  if (punto <= 0) return 'USD'
  return DIVISA_POR_SUFIJO[t.slice(punto + 1)] ?? 'USD'
}

/**
 * Precio con su divisa de verdad.
 *
 * Los peniques se enseñan como tal («489,80p»), que es como los cotiza la
 * propia bolsa de Londres: convertir a libras exigiría un tipo de cambio que
 * aquí no hay, y fingir dólares es justo el error que esto viene a arreglar.
 */
export function precio(
  valor: number | null | undefined,
  ticker?: string | null,
  divisaExplicita?: string | null,
  decimales = 2,
): string {
  if (valor == null || Number.isNaN(valor)) return '—'
  const divisa = divisaDe(ticker, divisaExplicita)
  const n = valor.toFixed(decimales)
  if (divisa === 'GBp') return `${n}p`
  return `${SIMBOLO[divisa] ?? `${divisa} `}${n}`
}
