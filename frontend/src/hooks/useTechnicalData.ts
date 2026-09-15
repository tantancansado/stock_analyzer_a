import { fetchTechnicalSignals } from '../api/client'
import type { TechnicalSignal, TechnicalSummary } from '../api/client'

export type TechnicalData = { signals: TechnicalSignal[]; summary: TechnicalSummary[] }

let cache: TechnicalData | null = null
/* Cuántas veces seguidas ha fallado la carga. Antes esto era un `failed = true`
   definitivo: un solo fallo —un wifi que parpadea al abrir la app— dejaba la
   sesión ENTERA sin señales técnicas, sin reintento y sin decirlo. Y el efecto
   no se ve como un error, se ve como «hoy no hay señales», que es justo la
   lectura contraria. Tres intentos y se para, que era lo que la variable quería
   evitar: pedir sin fin contra una API caída. */
let fallosSeguidos = 0
const MAX_INTENTOS = 3
let promise: Promise<void> | null = null
const listeners: Array<(d: TechnicalData) => void> = []

export function subscribeToTechnicalData(cb: (d: TechnicalData) => void): () => void {
  // Already loaded — call back async so it doesn't fire during render
  if (cache !== null) {
    const d = cache
    let cancelled = false
    const id = setTimeout(() => { if (!cancelled) cb(d) }, 0)
    return () => { cancelled = true; clearTimeout(id) }
  }

  // Agotados los reintentos: se para para no machacar una API caída.
  if (fallosSeguidos >= MAX_INTENTOS) return () => {}

  listeners.push(cb)
  if (promise === null) {
    promise = fetchTechnicalSignals()
      .then(d => {
        cache = d
        fallosSeguidos = 0
        const fns = listeners.splice(0)
        for (const fn of fns) fn(d)
      })
      .catch((e: unknown) => {
        fallosSeguidos++
        promise = null
        listeners.splice(0)
        // Sin esto el fallo no existía en ningún sitio: ni en la interfaz ni en
        // la consola. Al menos que quede rastro para diagnosticarlo.
        console.error(
          `[technical] carga fallida (${fallosSeguidos}/${MAX_INTENTOS})` +
          (fallosSeguidos >= MAX_INTENTOS ? ' — sin más reintentos esta sesión' : ''), e)
      })
  }
  return () => {
    const idx = listeners.indexOf(cb)
    if (idx !== -1) listeners.splice(idx, 1)
  }
}

export function getTechnicalCache(): TechnicalData | null {
  return cache
}

/** Reset for testing or manual retry */
export function resetTechnicalCache() {
  cache = null
  fallosSeguidos = 0
  promise = null
  listeners.splice(0)
}
