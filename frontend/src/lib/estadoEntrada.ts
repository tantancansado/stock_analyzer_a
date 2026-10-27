import type { LeapsOpportunity } from '@/api/client'

export type EstadoEntrada = 'ENTRADA' | 'VIGILAR' | 'ESPERAR'

/** Lo accionable primero. Sin estado va al final: no se sabe el timing, así
 *  que no se promociona. Mismo orden que la lista de Value. */
export const ORDEN_ENTRADA: Record<string, number> = { ENTRADA: 0, VIGILAR: 1, ESPERAR: 2 }

export const TEXTO_ENTRADA: Record<EstadoEntrada, string> = {
  ENTRADA: 'Listo para entrar',
  VIGILAR: 'En vigilancia',
  ESPERAR: 'Aún cayendo',
}

/** Un solo estado de entrada por fila: el técnico, rebajado si el veredicto de
 *  entrada (`entry_verdict_agent`) dice esperar o evitar.
 *
 *  Eran dos motores pintando cosas distintas en la misma fila: CNI salía con
 *  el filtro «Entra» y la etiqueta «ESPERA» (27-oct-2026) — técnicamente en
 *  suelo, pero con resultados en 3 días. El veredicto decía WAIT en 52 de 53
 *  filas y el filtro no lo miraba.
 *    ENTRADA + WAIT  → VIGILAR (en suelo, pero hoy no: p. ej. resultados)
 *    cualquier AVOID → ESPERAR
 */
export function estadoEfectivo(
  tecnico: string | null | undefined,
  veredicto?: string | null,
): EstadoEntrada | null {
  if (veredicto === 'AVOID') return 'ESPERAR'
  if (tecnico === 'ENTRADA' && veredicto === 'WAIT') return 'VIGILAR'
  return tecnico === 'ENTRADA' || tecnico === 'VIGILAR' || tecnico === 'ESPERAR' ? tecnico : null
}

/** El «por qué cae» que investiga why_cheap_analyzer, en lenguaje llano. */
export const POR_QUE_CAE: Record<string, string> = {
  DETERIORO:   'El negocio está peor',
  CICLICO:     'Parte baja del ciclo',
  EVENTO:      'Shock puntual',
  SENTIMIENTO: 'Sentimiento, no el negocio',
}

type ConEstado = Pick<LeapsOpportunity, 'entry_readiness' | 'opportunity_score'>

/** Por estado de entrada y, dentro de cada uno, por score. Un LEAPS con 84 que
 *  dice ESPERAR no puede encabezar la lista por encima de uno que se puede
 *  comprar hoy. */
export function ordenaPorEntrada<T extends ConEstado>(lista: readonly T[]): T[] {
  return [...lista].sort((a, b) => {
    const ra = ORDEN_ENTRADA[a.entry_readiness ?? ''] ?? 9
    const rb = ORDEN_ENTRADA[b.entry_readiness ?? ''] ?? 9
    return ra !== rb ? ra - rb : b.opportunity_score - a.opportunity_score
  })
}
