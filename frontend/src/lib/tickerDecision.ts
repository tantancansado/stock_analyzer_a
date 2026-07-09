// Síntesis de decisión por ticker: combina el modelo Owner Earnings (precio
// de compra para el retorno anual objetivo), su validador IA y el consenso de
// analistas en UN veredicto accionable. El modelo OE manda — es el que mejor
// ha discriminado gangas reales de trampas (CBOE/NDAQ vs MA/V); el consenso
// solo aporta banderas.

export type TickerDecisionKind = 'compra' | 'espera' | 'evita' | 'no_fiable' | 'sin_modelo'

export interface OeModelInput {
  current_price: number | null
  buy_price: number | null
  exit_price: number | null
  exit_year?: number | null
  safety_margin_pct: number | null
  upside_pct?: number | null
  signal?: string
  target_return_pct?: number
  ntm_fcf_yield_pct?: number | null
  historical_fcf_per_share?: Record<string, number>
  red_flags?: Array<{ code: string; severity: 'high' | 'medium' | 'low'; msg: string }>
}

export interface OeAiInput {
  data_quality?: string
  thesis_verdict?: string
  reasoning?: string
  confidence?: number
}

export interface TickerDecisionInput {
  oe: OeModelInput | null | undefined
  oeAi?: OeAiInput | null
  /** Precio live del análisis — prevalece sobre el snapshot del batch. */
  currentPrice?: number | null
  analystUpsidePct?: number | null
  daysToEarnings?: number | null
}

export interface TickerDecision {
  kind: TickerDecisionKind
  label: string
  headline: string
  reasons: string[]
  blockers: string[]
  dataFlags: string[]
  buyPrice: number | null
  exitPrice: number | null
  exitYear: number | null
  /** Margen de seguridad vs precio usado: (buy - price) / buy × 100. */
  safetyMarginPct: number | null
  targetReturnPct: number
  badgeClass: string
}

const BADGE = {
  compra:     'border-emerald-500/40 bg-emerald-500/15 text-emerald-300',
  espera:     'border-amber-500/40 bg-amber-500/15 text-amber-300',
  evita:      'border-red-500/40 bg-red-500/15 text-red-300',
  no_fiable:  'border-orange-500/40 bg-orange-500/10 text-orange-300',
  sin_modelo: 'border-border/40 bg-muted/20 text-muted-foreground',
} as const

const fmtUsd = (v: number) => `$${v.toFixed(v >= 100 ? 0 : 2)}`

export function getTickerDecision({
  oe,
  oeAi = null,
  currentPrice = null,
  analystUpsidePct = null,
  daysToEarnings = null,
}: TickerDecisionInput): TickerDecision {
  const targetReturnPct = oe?.target_return_pct ?? 15

  if (!oe || oe.buy_price == null || oe.buy_price <= 0) {
    return {
      kind: 'sin_modelo',
      label: 'SIN MODELO',
      headline: 'Este ticker no está en el batch de Owner Earnings — no hay precio de compra calculado.',
      reasons: [],
      blockers: [],
      dataFlags: [],
      buyPrice: null,
      exitPrice: null,
      exitYear: null,
      safetyMarginPct: null,
      targetReturnPct,
      badgeClass: BADGE.sin_modelo,
    }
  }

  const buy = oe.buy_price
  const price = currentPrice ?? oe.current_price
  const exitPrice = oe.exit_price ?? null
  const exitYear = oe.exit_year ?? null

  // Margen de seguridad con el precio más fresco disponible (misma fórmula
  // que el pipeline: relativo al buy_price).
  const margin = price != null && price > 0 ? ((buy - price) / buy) * 100 : oe.safety_margin_pct

  // ── Banderas de calidad de datos (casos HESAY/ASAZY: números atractivos
  //    sobre datos rotos — sin datos fiables no hay veredicto) ────────────────
  const dataFlags: string[] = []
  const fcfYears = Object.keys(oe.historical_fcf_per_share ?? {}).length
  if (oe.historical_fcf_per_share != null && fcfYears < 3) {
    dataFlags.push(`Histórico de FCF/acción insuficiente (${fcfYears} años, mínimo 3) — el modelo no es fiable`)
  }
  if (oe.ntm_fcf_yield_pct != null && oe.ntm_fcf_yield_pct > 25) {
    dataFlags.push(`FCF yield NTM implausible (${oe.ntm_fcf_yield_pct.toFixed(1)}%) — probable error de divisa o unidades`)
  }
  for (const rf of oe.red_flags ?? []) {
    if (rf.severity === 'high') dataFlags.push(rf.msg)
  }
  const aiQuality = (oeAi?.data_quality ?? '').toUpperCase()
  if (aiQuality && aiQuality !== 'RELIABLE') {
    dataFlags.push(`El validador IA marca los datos como ${aiQuality}`)
  }

  if (dataFlags.length > 0) {
    return {
      kind: 'no_fiable',
      label: 'DATOS NO FIABLES',
      headline: 'El modelo tiene datos rotos o incompletos para este ticker — no operes con estas cifras.',
      reasons: [],
      blockers: [],
      dataFlags,
      buyPrice: buy,
      exitPrice,
      exitYear,
      safetyMarginPct: margin,
      targetReturnPct,
      badgeClass: BADGE.no_fiable,
    }
  }

  // ── Razones y bloqueos ────────────────────────────────────────────────────
  const reasons: string[] = []
  const blockers: string[] = []
  const aiVerdict = (oeAi?.thesis_verdict ?? '').toUpperCase()
  const aiConf = oeAi?.confidence

  if (margin != null && margin >= 0) {
    reasons.push(`Margen de seguridad del ${margin.toFixed(0)}% sobre el precio de compra objetivo`)
  }
  if (aiVerdict === 'BUY') {
    reasons.push(`El validador IA respalda la tesis${aiConf != null ? ` (confianza ${aiConf}%)` : ''}`)
  }
  if (analystUpsidePct != null && analystUpsidePct >= 10 && analystUpsidePct < 25) {
    reasons.push(`Upside de consenso en zona dorada (+${analystUpsidePct.toFixed(0)}%)`)
  }
  if (oe.ntm_fcf_yield_pct != null && oe.ntm_fcf_yield_pct >= 5) {
    reasons.push(`FCF yield NTM del ${oe.ntm_fcf_yield_pct.toFixed(1)}%`)
  }

  if (daysToEarnings != null && daysToEarnings <= 7) {
    blockers.push(`Earnings en ${daysToEarnings} días — riesgo de evento`)
  }
  if (analystUpsidePct != null && analystUpsidePct >= 30) {
    blockers.push(`Upside de consenso ≥30% (+${analystUpsidePct.toFixed(0)}%) — patrón histórico de value trap`)
  }
  if (analystUpsidePct != null && analystUpsidePct < 0) {
    blockers.push('El consenso de analistas está por debajo del precio actual')
  }
  for (const rf of oe.red_flags ?? []) {
    if (rf.severity === 'medium') blockers.push(rf.msg)
  }

  // ── Veredicto ─────────────────────────────────────────────────────────────
  // Upside ≥30% es hard-reject histórico (0% aciertos en 55 señales): manda
  // sobre todo lo demás.
  if (analystUpsidePct != null && analystUpsidePct >= 30) {
    return {
      kind: 'evita',
      label: 'EVITA',
      headline: 'Parece regalada y eso es exactamente el problema: el gap con el consenso delata algo que el modelo no ve.',
      reasons,
      blockers,
      dataFlags,
      buyPrice: buy,
      exitPrice,
      exitYear,
      safetyMarginPct: margin,
      targetReturnPct,
      badgeClass: BADGE.evita,
    }
  }

  const inBuyZone = margin != null && margin >= 0

  // IA rechaza la tesis con el precio ya en zona de compra → el problema no es
  // el precio, es el negocio o los datos: fuera.
  if (aiVerdict === 'AVOID' && inBuyZone) {
    blockers.push(`El validador IA rechaza la tesis pese al precio${aiConf != null ? ` (confianza ${aiConf}%)` : ''}`)
    return {
      kind: 'evita',
      label: 'EVITA',
      headline: 'Cotiza barata según el modelo, pero el validador IA rechaza la tesis — barato no es suficiente.',
      reasons,
      blockers,
      dataFlags,
      buyPrice: buy,
      exitPrice,
      exitYear,
      safetyMarginPct: margin,
      targetReturnPct,
      badgeClass: BADGE.evita,
    }
  }

  if (inBuyZone) {
    return {
      kind: 'compra',
      label: 'COMPRA',
      headline: `Cotiza en o por debajo de su precio de compra objetivo — a este precio el modelo proyecta ≥${targetReturnPct}%/año.`,
      reasons,
      blockers,
      dataFlags,
      buyPrice: buy,
      exitPrice,
      exitYear,
      safetyMarginPct: margin,
      targetReturnPct,
      badgeClass: BADGE.compra,
    }
  }

  // Precio por encima del buy_price → esperar al precio, no rechazar la empresa.
  if (aiVerdict === 'AVOID') {
    blockers.push(`El validador IA confirma la sobrevaloración actual${aiConf != null ? ` (confianza ${aiConf}%)` : ''}`)
  }
  const pctAbove = price != null && price > 0 ? ((price - buy) / buy) * 100 : null
  return {
    kind: 'espera',
    label: `ESPERA A ${fmtUsd(buy)}`,
    headline: pctAbove != null
      ? `Buena empresa a mal precio: cotiza un ${pctAbove.toFixed(0)}% por encima del precio que daría el ${targetReturnPct}%/año.`
      : `El precio actual no ofrece el ${targetReturnPct}%/año objetivo — espera a ${fmtUsd(buy)}.`,
    reasons,
    blockers,
    dataFlags,
    buyPrice: buy,
    exitPrice,
    exitYear,
    safetyMarginPct: margin,
    targetReturnPct,
    badgeClass: BADGE.espera,
  }
}
