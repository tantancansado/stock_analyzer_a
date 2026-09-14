import type { LucideIcon } from 'lucide-react'

/**
 * Distintivo de señal — la pieza única para marcar TRAP, EXIT, SMART MONEY,
 * SQUEEZE y compañía.
 *
 * Estas mismas señales estaban escritas a mano en cada página que las
 * enseñaba, y ninguna coincidía con otra: SMART MONEY era ◆ púrpura en las
 * filas de Cerebro y 🐋 violeta en las tarjetas de Value US; SQUEEZE era ↑
 * cian en un sitio y 💥 naranja en otro. Nueve colores, emoji mezclados con
 * flechas, y dos formas distintas de pastilla. Puestos juntos no parecían el
 * mismo sistema.
 *
 * Cuatro tonos con significado y una familia de iconos. El tamaño `micro` es
 * para filas densas de tabla; `normal` para tarjetas.
 */

export type TonoSenal = 'favor' | 'aviso' | 'alarma' | 'info' | 'neutro'

export const TONOS_SENAL: Record<TonoSenal, string> = {
  favor:  'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  aviso:  'bg-amber-500/15 text-amber-400 border-amber-500/30',
  alarma: 'bg-red-500/15 text-red-400 border-red-500/35',
  info:   'bg-primary/12 text-primary border-primary/30',
  neutro: 'bg-muted/40 text-muted-foreground border-border/40',
}

interface Props {
  icon: LucideIcon
  texto: string
  tono: TonoSenal
  titulo?: string
  tamano?: 'micro' | 'normal'
}

export default function SignalBadge({ icon: Icon, texto, tono, titulo, tamano = 'normal' }: Readonly<Props>) {
  const micro = tamano === 'micro'
  return (
    <span
      title={titulo}
      className={`inline-flex items-center gap-1 font-bold border tracking-wide whitespace-nowrap ${TONOS_SENAL[tono]} ${
        micro
          ? 'text-micro font-black px-1.5 py-px rounded'
          : 'text-micro px-2 py-0.5 rounded-full'
      }`}
    >
      <Icon size={12} strokeWidth={2.25} className="shrink-0" />
      {texto}
    </span>
  )
}
