import { useLocation, useNavigate } from 'react-router-dom'
import { Compass } from 'lucide-react'
import EmptyState from '@/components/EmptyState'

/**
 * Pantalla para una ruta que no existe.
 *
 * Antes no había ninguna: cualquier URL desconocida —un enlace viejo, una
 * ruta que se movió a pestaña, un typo— dejaba la aplicación COMPLETAMENTE en
 * blanco, sin decir qué había pasado ni ofrecer salida más allá de abrir el
 * menú. Se descubrió con `#/macro-stress`, que existió como página y hoy vive
 * dentro de Macro.
 */
export default function NoEncontrada() {
  const { pathname } = useLocation()
  const navigate = useNavigate()

  return (
    <>
      <h1 className="sr-only">Página no encontrada</h1>
      <EmptyState
        icon={<Compass size={32} strokeWidth={1.5} />}
        title="Esta página no existe"
        subtitle={`No hay nada en ${pathname}. Puede que el enlace sea antiguo o que la sección se haya movido dentro de otra.`}
        action={{ label: 'Ir al Centro de mando', onClick: () => navigate('/dashboard', { replace: true }) }}
      />
    </>
  )
}
