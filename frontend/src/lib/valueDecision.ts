import type { ValueOpportunity } from '@/api/client'

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
}

const GOOD_GRADES = new Set(['A', 'B', 'EXCELLENT', 'STRONG'])

export function getValueDecision({
  row,
  hasTrap = false,
  hasExit = false,
  hasEntry = false,
  hasSmartMoney = false,
  hasSqueeze = false,
}: DecisionInput): ValueDecision {
  const score = row.value_score ?? 0
  const grade = (row.conviction_grade ?? '').toUpperCase()
  const upside = row.analyst_upside_pct
  const rr = row.risk_reward_ratio
  const nearEarnings = row.days_to_earnings != null && row.days_to_earnings <= 7
  const hasBadUpside = upside != null && upside < 0
  const hasGoodUpside = upside == null || upside >= 10
  const hasEnoughReward = rr == null || rr >= 1.5
  const isReady =
    score >= 65 &&
    GOOD_GRADES.has(grade) &&
    hasGoodUpside &&
    hasEnoughReward &&
    !nearEarnings

  if (hasExit || row.cerebro_signal === 'EXIT') {
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

  if (isReady || (hasEntry && score >= 60 && hasGoodUpside)) {
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
