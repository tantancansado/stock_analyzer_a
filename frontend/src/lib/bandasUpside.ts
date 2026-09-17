/**
 * Banda de `analyst_upside_pct` — espejo de `value_bands.py`.
 *
 * CLAUDE.md: «Las bandas de upside viven en value_bands.py — integrator,
 * tracker y conviction las importan de ahí; NUNCA hardcodear una banda inline».
 * El frontend no tenía de dónde importarlas, así que cada pantalla escribió la
 * suya: seis copias del `>= 10 && < 25`, y otras tantas que se quedaban en el
 * suelo y pintaban de verde cualquier upside por encima de 10 — sin techo, o
 * sea premiando también la franja que peor rinde.
 *
 * Hay un test que compara estos números con los de `value_bands.py`: si allí
 * cambian y aquí no, falla.
 */

/** Por debajo, el upside no compensa el riesgo de la posición. */
export const UPSIDE_MIN = 10

/**
 * Fin de la zona dorada [10, 30). Subido de 25 a 30 el 17-sep-2026: sobre las
 * señales del periodo limpio con 90 días cerrados, [25,30) acierta el 62% con
 * +3,73% de media y [10,25) el 61% con +2,78% — indistinguibles. El corte en
 * 25 venía de un «sin evidencia clara» que dejó de serlo. Ver value_bands.py.
 */
export const UPSIDE_GOLDEN_MAX = 30

/** Desde aquí es señal de trampa: 0% de acierto en 55 señales reales. */
export const UPSIDE_HARD_REJECT = 30

// 'transicion' era la franja [25,30). Desaparece el 17-sep-2026 al subir
// GOLDEN_MAX a 30: los dos cortes coinciden y no queda hueco entre ellos. Se
// quita el estado en vez de dejarlo como código muerto que nadie puede
// alcanzar.
export type BandaUpside = 'sin-dato' | 'flojo' | 'dorada' | 'trampa'

export function bandaUpside(upside: number | null | undefined): BandaUpside {
  if (upside == null || Number.isNaN(upside)) return 'sin-dato'
  if (upside >= UPSIDE_HARD_REJECT) return 'trampa'
  if (upside >= UPSIDE_MIN) return 'dorada'
  return 'flojo'
}

/** ¿Está en la única banda que ha funcionado? */
export function enZonaDorada(upside: number | null | undefined): boolean {
  return bandaUpside(upside) === 'dorada'
}

/** Color de texto por banda. Un upside alto NO es verde: es la franja mala. */
export function colorUpside(upside: number | null | undefined): string {
  switch (bandaUpside(upside)) {
    case 'dorada':     return 'text-emerald-400'
    case 'trampa':     return 'text-red-400'
    default:           return 'text-muted-foreground'
  }
}
