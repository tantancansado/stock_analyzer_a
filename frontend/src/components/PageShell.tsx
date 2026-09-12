import React from 'react'
import PageHeader from './PageHeader'
import Loading, { ErrorState } from './Loading'

interface Props {
  readonly title: React.ReactNode
  readonly subtitle?: React.ReactNode
  /** Acciones a la derecha de la cabecera (botones, CSV, filtros). */
  readonly actions?: React.ReactNode
  readonly loading?: boolean
  readonly error?: string | null
  /** Se antepone a la cabecera: banners de datos obsoletos y similares. */
  readonly banner?: React.ReactNode
  /** Opcional: en el camino de carga/error no hay contenido que pintar. */
  readonly children?: React.ReactNode
}

/**
 * Cabecera + estados de una página, en un solo sitio.
 *
 * Existe porque 26 páginas hacían `if (loading) return <Loading/>` y
 * `if (error) return <ErrorState/>` ANTES de pintar su cabecera. El efecto:
 * cuando la API no responde —cosa que pasa— la pantalla se queda con un
 * mensaje de error y sin ningún indicio de en qué sección estás. Lo mismo
 * mientras carga.
 *
 * Aquí la estructura permanece y lo único que cambia es el contenido, que es
 * como se comporta una app nativa: la barra y el título no desaparecen
 * porque una petición vaya lenta o falle.
 */
export default function PageShell({
  title, subtitle, actions, loading, error, banner, children,
}: Props) {
  return (
    <>
      {banner}
      <PageHeader title={title} subtitle={subtitle}>{actions}</PageHeader>
      {loading ? <Loading conCabecera={false} /> : error ? <ErrorState message={error} /> : children}
    </>
  )
}
