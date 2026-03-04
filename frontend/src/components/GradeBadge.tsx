import { cn } from '@/lib/utils'

interface Props {
  grade?: string
  score?: number
}

export default function GradeBadge({ grade, score }: Props) {
  if (!grade) return <span className="text-muted-foreground">—</span>
  const title = score ? `Conviction ${score}/100` : ''
  return (
    <span
      className={cn(
        'inline-flex items-center justify-center px-2 py-0.5 rounded-md border text-xs font-bold tracking-wide min-w-[26px]',
        `grade-${grade}`
      )}
      title={title}
    >
      {grade}
    </span>
  )
}
