/**
 * Qué fuentes de datos compartidas no se han podido cargar.
 *
 * Los cachés compartidos (`useTechnicalData`, `useEntryVerdicts`,
 * `useChartSignals`, `usePortfolioConfluence`) devolvían un vacío cuando la
 * carga fallaba, y un vacío se pinta EXACTAMENTE igual que «hoy no hay ninguna
 * señal». Para quien decide sobre si hay señal o no la hay, esa es la lectura
 * contraria: un cero por fallo de red leído como un cero real.
 *
 * Esto no cambia la firma de ningún hook —seis páginas los consumen— sino que
 * los deja apuntar aquí su fallo, y `AvisoDatos` lo enseña una sola vez en la
 * cabecera de la app. El fallo es de un caché compartido, así que es de toda la
 * app: repetir el aviso en cada página sería ruido.
 */

export type FuenteDatos =
  | 'senales-tecnicas'
  | 'veredictos-entrada'
  | 'senales-grafico'
  | 'confluencia'

export const NOMBRE_FUENTE: Record<FuenteDatos, string> = {
  'senales-tecnicas':   'las señales técnicas',
  'veredictos-entrada': 'los veredictos de entrada',
  'senales-grafico':    'las señales de gráfico',
  'confluencia':        'la confluencia con tu cartera',
}

const fallidas = new Set<FuenteDatos>()
const oyentes = new Set<(f: FuenteDatos[]) => void>()

function avisar() {
  const lista = [...fallidas]
  for (const o of oyentes) o(lista)
}

export function marcarFallo(fuente: FuenteDatos): void {
  if (fallidas.has(fuente)) return
  fallidas.add(fuente)
  avisar()
}

/** Al cargar bien se retira el aviso: un fallo pasajero no debe quedarse fijo. */
export function marcarOk(fuente: FuenteDatos): void {
  if (!fallidas.delete(fuente)) return
  avisar()
}

export function fuentesFallidas(): FuenteDatos[] {
  return [...fallidas]
}

export function suscribirse(cb: (f: FuenteDatos[]) => void): () => void {
  oyentes.add(cb)
  return () => { oyentes.delete(cb) }
}

/** Solo para los tests. */
export function reiniciarEstadoDatos(): void {
  fallidas.clear()
  oyentes.clear()
}
