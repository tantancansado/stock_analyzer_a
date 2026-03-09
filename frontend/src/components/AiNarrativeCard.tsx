import { Card, CardContent } from '@/components/ui/card'

interface Props {
  narrative: string | null | undefined
  label?: string
  className?: string
}

export default function AiNarrativeCard({ narrative, label = 'Análisis IA', className = '' }: Props) {
  if (!narrative) return null
  return (
    <Card className={`glass border border-indigo-500/20 bg-indigo-500/5 ${className}`}>
      <CardContent className="p-4">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-sm">🤖</span>
          <p className="text-[0.65rem] font-bold text-indigo-400 uppercase tracking-wider">{label}</p>
        </div>
        <p className="text-sm text-foreground/90 leading-relaxed">{narrative}</p>
      </CardContent>
    </Card>
  )
}
