import React from 'react'

interface PageHeaderProps {
  title: React.ReactNode
  subtitle?: React.ReactNode
  children?: React.ReactNode  // right-side actions (buttons, badges, etc.)
}

/**
 * Cabecera de página: título + subtítulo, y acciones opcionales.
 *
 * En móvil las acciones van DEBAJO, no al lado. Cuando compartían fila, el
 * bloque de acciones llevaba `shrink-0` y el del título `flex-1 min-w-0`: a
 * 390px los botones se quedaban con todo el ancho y al título le sobraban
 * ~100px, así que "VALUE US" se partía en "VALI / US" y el subtítulo caía en
 * una columna de una palabra por línea. Con tres botones (Vista clara, CSV,
 * CSV Full) la página era ilegible de arriba.
 *
 * `flex-wrap` en las acciones para que repartan en varias líneas en vez de
 * comprimirse, y `min-w-0` en el título para que el texto pueda cortarse en
 * lugar de forzar el ancho del contenedor.
 */
export default function PageHeader({ title, subtitle, children }: PageHeaderProps) {
  return (
    <div className="mb-7 animate-fade-in-up flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
      <div className="min-w-0 sm:flex-1">
        <h1 className="text-xl sm:text-2xl font-extrabold tracking-tight gradient-title mb-1 leading-tight text-balance">
          {title}
        </h1>
        {subtitle && <p className="text-sm text-muted-foreground">{subtitle}</p>}
      </div>
      {children && (
        <div className="flex flex-wrap items-center gap-2 sm:shrink-0 sm:mt-0.5">{children}</div>
      )}
    </div>
  )
}
