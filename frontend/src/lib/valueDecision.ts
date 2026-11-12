import type { EntryVerdictKind, ValueOpportunity } from '@/api/client'
import { enZonaDorada } from './bandasUpside'

export type ValueDecisionKind = 'ready' | 'watch' | 'wait' | 'avoid'

export interface ValueDecision {
  kind: ValueDecisionKind
  label: string
  headline: string
  detail: string
  badgeClass: string
  panelClass: string
}

interface DecisionInput {
  row: ValueOpportunity
  hasTrap?: boolean
  hasExit?: boolean
  hasEntry?: boolean
  hasSmartMoney?: boolean
  hasSqueeze?: boolean
  veredicto?: EntryVerdictKind | null
}

const GOOD_GRADES = new Set(['A', 'B', 'EXCELLENT', 'STRONG'])

// Lo que impide entrar HOY aunque la empresa sea buena y esté barata. Es la
// misma lectura que hace el veredicto de entrada (`entry_verdict_agent.py`, que
// veta con «timing dice X» y con la divergencia ALTA), así que las dos
// etiquetas no pueden ya contradecirse.
//
// SAP.DE salía con «LISTO» y «ESPERA» a la vez: la primera salía de una regla
// copiada en cinco sitios que no miraba el veredicto, y la segunda ES el
// veredicto. Mientras no se conoce el veredicto ni el timing no hay nada que
// contradecir, y se decide con el resto de la regla.
export function hayFrenoDeEntrada(
  row: Pick<ValueOpportunity, 'entry_readiness' | 'upside_divergence'>,
  veredicto?: EntryVerdictKind | null,
): boolean {
  return (
    veredicto === 'WAIT' ||
    veredicto === 'AVOID' ||
    row.entry_readiness === 'ESPERAR' ||
    row.entry_readiness === 'VIGILAR' ||
    row.upside_divergence === 'ALTA'
  )
}

// Única definición de «lista para entrar». La usan la etiqueta LISTO de las dos
// páginas de Value, el veredicto de la fila y la tarjeta del Centro de mando.
export function esListo(row: ValueOpportunity, veredicto?: EntryVerdictKind | null): boolean {
  const nearEarnings = row.days_to_earnings != null && row.days_to_earnings >= 0 && row.days_to_earnings <= 7
  // Value US (value_bands.nota_value): lista es la de PRIORIDAD sin resultados
  // encima. El timing no frena: dentro de la puerta, lo que cae bajo su media
  // descendente es lo que mejor ha salido a 12 meses en 2020-2025 y a 90 días en
  // 2026 (+7,0 contra +1,7), así que vetarlo descartaba justo lo bueno.
  // Ni los resultados cerca ni Cerebro la sacan: la regla se midió con ellos dentro
  // y la casa dice que una de Prioridad es comprable (los avisos se dicen, no frenan).
  if (row.value_grupo) return row.value_grupo === 'PRIORIDAD'
  // Una sola condición de upside, y con la banda declarada.
  //
  // Antes había dos, y las dos sobre la MISMA variable: `upside >= 10` y
  // `rr >= 1.5`, que es `upside >= 12` porque `risk_reward_ratio` se calcula
  // como `analyst_upside_pct / 8`. El segundo suelo era el que mandaba, más
  // estricto, y estaba escrito en unidades de otra cosa.
  //
  // Y ninguno tenía techo: un upside del 27% —fuera de la banda dorada, en la
  // franja pegada al HARD REJECT— salía como "listo para entrar".
  const upside = row.analyst_upside_pct
  const hasGoodUpside = upside == null || enZonaDorada(upside)
  return (
    (row.value_score ?? 0) >= 65 &&
    GOOD_GRADES.has((row.conviction_grade ?? '').toUpperCase()) &&
    hasGoodUpside &&
    !nearEarnings &&
    !row.earnings_warning &&
    row.cerebro_signal !== 'EXIT' &&
    row.cerebro_signal !== 'TRAP' &&
    !hayFrenoDeEntrada(row, veredicto)
  )
}

export function getValueDecision({
  row,
  hasTrap = false,
  hasExit = false,
  hasEntry = false,
  hasSmartMoney = false,
  hasSqueeze = false,
  veredicto = null,
}: DecisionInput): ValueDecision {
  const score = row.value_score ?? 0
  const grade = (row.conviction_grade ?? '').toUpperCase()
  const upside = row.analyst_upside_pct
  const nearEarnings = row.days_to_earnings != null && row.days_to_earnings >= 0 && row.days_to_earnings <= 7
  const hasBadUpside = upside != null && upside < 0
  const hasGoodUpside = upside == null || enZonaDorada(upside)
  const isReady = esListo(row, veredicto)
  const salida = hasExit || row.cerebro_signal === 'EXIT'

  // Value US: dos grupos, y el texto dice el dato de esa empresa. Los avisos son
  // hechos y no cambian el grupo ni aconsejan esperar: si una tarjeta de Prioridad
  // dice «Esperar», «revísala» o «trampa», la lista dice una cosa y la fila otra (le
  // pasaba a la vista completa el 12-nov con INTU, ADBE y BRO). Medidas, las señales
  // de Cerebro no separan (AVOID +8,6 a 90 días, neutras -1,5), así que no se dicen.
  const avisoGrupo = nearEarnings
    ? ` ${row.days_to_earnings === 0 ? 'Resultados hoy' : row.days_to_earnings === 1 ? 'Resultados mañana' : `Resultados en ${row.days_to_earnings} días`}.`
    : ''
  if (row.value_grupo === 'PRIORIDAD') {
    const z = row.per_z != null ? row.per_z.toLocaleString('es-ES', { maximumFractionDigits: 1 }) : null
    const ventas = row.ventas_anual_pct != null ? row.ventas_anual_pct.toLocaleString('es-ES', { maximumFractionDigits: 0 }) : null
    const clasica = row.per_z != null && row.per_z < -1 && row.ventas_anual_pct != null && row.ventas_anual_pct >= 10
    // Por recorrido (value_bands.puede_doblar): si además cumple la clásica, se dicen las dos.
    const dobla = row.value_dobla && row.recorrido_propio_pct != null
      ? `Nuestros modelos le ven +${Math.round(row.recorrido_propio_pct)} % con el beneficio en su tendencia: puede doblar.`
      : ''
    const avisos = row.value_avisos ? ` ${row.value_avisos.charAt(0).toUpperCase()}${row.value_avisos.slice(1)}.` : ''
    const porque = clasica || !dobla
      ? `PER a ${z}σ de su media y ventas anuales ${row.ventas_anual_pct != null && row.ventas_anual_pct < 0 ? '' : '+'}${ventas} %.${dobla ? ` ${dobla}` : ''}`
      : dobla
    return {
      kind: 'ready',
      label: 'Prioridad',
      headline: `${porque}${avisos}${avisoGrupo}`,
      detail: `${clasica
        ? 'Barata frente a su propia historia y creciendo: la combinación con ventaja en los dos periodos medidos.'
        : 'Sin crecer al 10 % ni PER bajo su media, pero lo que podía doblar con el beneficio sano ganó en los dos periodos medidos. Es lo más fino de lo medido: pocas empresas.'}${row.entry_readiness === 'ESPERAR' || row.entry_readiness === 'VIGILAR' ? ' Sigue cayendo: a 12 meses eso no ha restado, pero a corto puede bajar más.' : ''}`,
      badgeClass: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400',
      panelClass: 'border-emerald-500/20 bg-emerald-500/5',
    }
  }
  if (row.value_grupo === 'OBSERVAR') {
    return {
      kind: 'watch',
      label: 'Observar',
      headline: `${row.value_falta ? `${row.value_falta.charAt(0).toUpperCase()}${row.value_falta.slice(1)}.` : 'Pasa la puerta, sin ventaja medida.'}${avisoGrupo}`,
      detail: 'Pasa la puerta (barata según nuestra valoración y ventas que no caen), pero sin la combinación que ha dado ventaja. Medido, este grupo rinde como el universo.',
      badgeClass: 'border-sky-500/30 bg-sky-500/10 text-sky-400',
      panelClass: 'border-sky-500/20 bg-sky-500/5',
    }
  }

  if (salida) {
    return {
      kind: 'avoid',
      label: 'Evitar',
      headline: 'Hay una señal de salida.',
      detail: 'La app ve deterioro o riesgo suficiente como para no abrir una posición ahora.',
      badgeClass: 'border-red-500/30 bg-red-500/10 text-red-400',
      panelClass: 'border-red-500/20 bg-red-500/5',
    }
  }

  if (hasTrap || row.cerebro_signal === 'TRAP') {
    return {
      kind: 'avoid',
      label: 'Evitar',
      headline: 'Parece barato, pero puede ser una trampa.',
      detail: 'El sistema detecta riesgo de negocio o calidad que no compensa entrar sin revisar a fondo.',
      badgeClass: 'border-red-500/30 bg-red-500/10 text-red-400',
      panelClass: 'border-red-500/20 bg-red-500/5',
    }
  }

  if (hasBadUpside) {
    return {
      kind: 'avoid',
      label: 'Evitar',
      headline: 'El potencial no compensa el precio actual.',
      detail: 'El consenso apunta a poco margen o margen negativo. Mejor exigir mejor precio.',
      badgeClass: 'border-red-500/30 bg-red-500/10 text-red-400',
      panelClass: 'border-red-500/20 bg-red-500/5',
    }
  }

  if (nearEarnings) {
    return {
      kind: 'wait',
      label: 'Esperar',
      headline: 'Resultados demasiado cerca.',
      detail: 'Puede haber movimiento brusco. Mejor esperar a que pase el evento antes de decidir.',
      badgeClass: 'border-amber-500/30 bg-amber-500/10 text-amber-400',
      panelClass: 'border-amber-500/20 bg-amber-500/5',
    }
  }

  if (isReady || (hasEntry && score >= 60 && hasGoodUpside && !hayFrenoDeEntrada(row, veredicto))) {
    return {
      kind: 'ready',
      label: 'Listo para revisar',
      headline: 'Encaja con calidad, precio y margen.',
      detail: 'Es candidata para mirarla hoy y decidir tamaño solo si encaja con tu cartera.',
      badgeClass: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400',
      panelClass: 'border-emerald-500/20 bg-emerald-500/5',
    }
  }

  if (score >= 60 || GOOD_GRADES.has(grade) || hasEntry || hasSmartMoney || hasSqueeze) {
    return {
      kind: 'watch',
      label: 'Vigilar',
      headline: 'Interesante, pero falta confirmación.',
      detail: 'La empresa merece seguimiento. Espera mejor punto de entrada o más margen.',
      badgeClass: 'border-sky-500/30 bg-sky-500/10 text-sky-400',
      panelClass: 'border-sky-500/20 bg-sky-500/5',
    }
  }

  return {
    kind: 'wait',
    label: 'Esperar',
    headline: 'No hay señal suficientemente clara.',
    detail: 'El sistema no ve una razón fuerte para priorizarla sobre otras ideas.',
    badgeClass: 'border-border/40 bg-muted/20 text-muted-foreground',
    panelClass: 'border-border/30 bg-muted/10',
  }
}
