import { useState } from 'react'

/**
 * «Más datos»: el patrón de toda la app desde el 12-nov-2026. Por defecto, lo que
 * se entiende sin conocer la regla; los números, detrás de este botón. El usuario:
 * «aunque tengamos los datos tiene que ser intuitivo para un usuario» y «si alguien
 * quiere verlos, que tenga la opción de mostrarlos».
 *
 * Lo de detrás son DATOS, nunca veredictos de reglas anteriores: un ESPERA o un
 * EXIT al lado de una de Prioridad no es un dato, es otra decisión.
 *
 * La elección se recuerda por página en este navegador (es una preferencia de
 * pantalla, nada más); sin almacenamiento, vale para esta visita.
 */
export function useMasDatos(pagina: string): [boolean, () => void] {
  const clave = `sa-mas-datos:${pagina}`
  const [activo, setActivo] = useState(() => {
    try { return localStorage.getItem(clave) === '1' } catch { return false }
  })
  const alternar = () => setActivo(v => {
    try { localStorage.setItem(clave, v ? '0' : '1') } catch { /* solo esta visita */ }
    return !v
  })
  return [activo, alternar]
}

export function BotonMasDatos({ activo, onClick, className = '' }: {
  activo: boolean
  onClick: () => void
  className?: string
}) {
  return (
    <button
      type="button"
      aria-pressed={activo}
      onClick={onClick}
      className={`filter-btn ${activo ? 'active' : ''} ${className}`}
    >
      {activo ? 'Menos datos' : 'Más datos'}
    </button>
  )
}
