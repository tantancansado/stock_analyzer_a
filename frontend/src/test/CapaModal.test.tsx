import { describe, it, expect } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { useState } from 'react'
import CapaModal from '@/components/CapaModal'

/**
 * Lo que se comprueba aquí no es que el modal "tenga" un atributo: es que el
 * tabulador no se escapa. Ninguno de los cinco modales de la app lo impedía, y
 * el síntoma no se ve —el foco sigue recorriendo la página de debajo, oculta
 * tras el fondo oscuro— así que solo lo caza una prueba que tabule de verdad.
 */

function Banco({ sinAutoFoco = false }: { sinAutoFoco?: boolean }) {
  const [abierto, setAbierto] = useState(false)
  return (
    <>
      <button onClick={() => setAbierto(true)}>abrir</button>
      <button>de la pagina</button>
      {abierto && (
        <CapaModal onClose={() => setAbierto(false)} etiqueta="Diálogo de prueba" sinAutoFoco={sinAutoFoco}>
          <div>
            <button>primero</button>
            <button>segundo</button>
            <button onClick={() => setAbierto(false)}>cerrar</button>
          </div>
        </CapaModal>
      )}
    </>
  )
}

describe('CapaModal', () => {
  it('se anuncia como diálogo modal', async () => {
    const user = userEvent.setup()
    render(<Banco />)
    await user.click(screen.getByText('abrir'))

    const dialogo = screen.getByRole('dialog')
    expect(dialogo).toHaveAttribute('aria-modal', 'true')
    expect(dialogo).toHaveAccessibleName('Diálogo de prueba')
  })

  it('el tabulador da la vuelta dentro y no alcanza la página de debajo', async () => {
    const user = userEvent.setup()
    render(<Banco />)
    await user.click(screen.getByText('abrir'))

    // `autoFocus` ya deja el foco en el primero al abrir, así que el ciclo
    // empieza en el segundo.
    expect(document.activeElement?.textContent).toBe('primero')

    const ciclo = ['segundo', 'cerrar', 'primero', 'segundo', 'cerrar', 'primero']
    // Dos vueltas enteras: si se escapara, en algún punto el foco caería en
    // «de la pagina» o en «abrir».
    for (const texto of ciclo) {
      await user.tab()
      expect(document.activeElement?.textContent).toBe(texto)
    }
  })

  it('Mayús+Tab hacia atrás tampoco se escapa', async () => {
    const user = userEvent.setup()
    render(<Banco />)
    await user.click(screen.getByText('abrir'))

    for (let i = 0; i < 5; i++) {
      await user.tab({ shift: true })
      expect(['primero', 'segundo', 'cerrar']).toContain(document.activeElement?.textContent)
    }
  })

  it('al cerrar, el foco vuelve a quien lo abrió', async () => {
    const user = userEvent.setup()
    render(<Banco />)
    const abrir = screen.getByText('abrir')
    await user.click(abrir)
    await user.click(screen.getByText('cerrar'))

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    await waitFor(() => expect(document.activeElement).toBe(abrir))
  })

  it('Escape cierra', async () => {
    const user = userEvent.setup()
    render(<Banco />)
    await user.click(screen.getByText('abrir'))
    await user.keyboard('{Escape}')

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('bloquea el scroll del fondo mientras está abierto, y lo devuelve al cerrar', async () => {
    const user = userEvent.setup()
    render(<Banco />)
    // React Aria bloquea en <html>, no en <body> como hacían los modales a
    // mano. Mismo efecto y además cubre el rebote de Safari en iOS.
    const raiz = document.documentElement
    const antes = raiz.style.overflow

    await user.click(screen.getByText('abrir'))
    expect(raiz.style.overflow).toBe('hidden')

    await user.click(screen.getByText('cerrar'))
    await waitFor(() => expect(raiz.style.overflow).toBe(antes))
  })
})

/**
 * Y que nadie vuelva a montar una capa a mano.
 *
 * Los cinco modales de la app se escribieron cada uno por su lado y ninguno
 * atrapaba el foco. No es que se hiciera mal: es que hacerlo bien son cuatro
 * piezas (foco atrapado, foco devuelto, bloqueo de scroll y ARIA) y nadie las
 * escribe las cuatro cuando lo que quiere es enseñar una tesis.
 */
describe('nadie reimplementa la capa', () => {
  const raiz = join(__dirname, '..')
  const fuentes: { ruta: string; texto: string }[] = []
  const recorrer = (dir: string) => {
    for (const e of readdirSync(dir, { withFileTypes: true })) {
      const ruta = join(dir, e.name)
      if (e.isDirectory()) { if (e.name !== 'test') recorrer(ruta) }
      else if (e.name.endsWith('.tsx')) fuentes.push({ ruta: ruta.slice(raiz.length + 1), texto: readFileSync(ruta, 'utf-8') })
    }
  }
  recorrer(raiz)

  /** Los que se superponen a la página: los reconoce su propio `aria-modal`. */
  const capas = fuentes.filter(f =>
    f.ruta !== 'components/CapaModal.tsx' && /aria-modal|role="dialog"/.test(f.texto))

  it('todo lo que dice ser un diálogo pasa por CapaModal', () => {
    const sueltos = capas.filter(f => !f.texto.includes('CapaModal')).map(f => f.ruta)
    expect(sueltos, 'usar <CapaModal>: trae foco, scroll y ARIA de una pieza').toEqual([])
  })

  it('nadie bloquea el scroll del body por su cuenta', () => {
    // Un contador a mano falla con modales anidados: el de dentro devuelve el
    // scroll al cerrarse y la página se mueve con el de fuera abierto.
    const sueltos = fuentes
      .filter(f => f.ruta !== 'components/CapaModal.tsx' && /document\.body\.style\.overflow/.test(f.texto))
      .map(f => f.ruta)
    expect(sueltos, 'lo hace usePreventScroll dentro de CapaModal').toEqual([])
  })
})
