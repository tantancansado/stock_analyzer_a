import type { ReactNode } from 'react'
import { Button } from '@/components/ui/button'

interface EmptyStateProps {
  /** Opcional en variante compacta, donde un icono grande sobra. */
  icon?: string | ReactNode
  title: string
  subtitle?: string
  action?: { label: string; onClick: () => void }
  /**
   * Para huecos DENTRO de una tabla o una tarjeta, no para una página vacía.
   *
   * Existe porque los vacíos compactos se estaban escribiendo a mano uno por
   * uno —"Sin datos", "Sin resultados con los filtros actuales"— con ocho
   * combinaciones distintas de padding y color, y el EmptyState normal
   * (py-16 e icono de 4xl) no cabía ahí.
   */
  compact?: boolean
}

export default function EmptyState({ icon, title, subtitle, action, compact }: EmptyStateProps) {
  return (
    <div className={`flex flex-col items-center justify-center text-center px-6 ${compact ? 'py-7' : 'py-16'}`}>
      {icon && (
        <div
          className={compact ? 'text-xl mb-2 opacity-40' : 'text-4xl mb-4 opacity-45'}
          style={{ animation: 'emptyIconIn 0.5s cubic-bezier(0.34,1.56,0.64,1) both' }}
        >
          {icon}
        </div>
      )}
      <p
        className={compact ? 'text-sm text-muted-foreground' : 'font-medium text-foreground'}
        style={{ animation: 'fadeInUp 0.3s ease both 0.1s' }}
      >
        {title}
      </p>
      {subtitle && (
        <p
          className="text-xs text-muted-foreground mt-1.5 max-w-xs"
          style={{ animation: 'fadeInUp 0.3s ease both 0.18s' }}
        >
          {subtitle}
        </p>
      )}
      {action && (
        <div style={{ animation: 'fadeInUp 0.3s ease both 0.26s' }}>
          <Button
            variant="outline"
            size="sm"
            onClick={action.onClick}
            className="mt-4 text-xs px-3 py-1.5"
          >
            {action.label}
          </Button>
        </div>
      )}
    </div>
  )
}
