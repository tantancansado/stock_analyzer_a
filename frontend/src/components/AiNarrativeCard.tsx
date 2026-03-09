interface Props {
  narrative: string | null | undefined
  label?: string
  className?: string
}

export default function AiNarrativeCard({ narrative, label = 'Análisis IA', className = '' }: Props) {
  if (!narrative) return null
  return (
    <div className={`rounded-xl border border-indigo-500/25 bg-gradient-to-r from-indigo-500/8 to-transparent overflow-hidden ${className}`}>
      <div className="flex items-center gap-2 px-4 py-2 border-b border-indigo-500/15 bg-indigo-500/8">
        <span className="text-sm leading-none">🤖</span>
        <span className="text-[0.62rem] font-bold text-indigo-400 uppercase tracking-widest">{label}</span>
      </div>
      <p className="px-4 py-3 text-sm text-foreground/85 leading-relaxed">{narrative}</p>
    </div>
  )
}
