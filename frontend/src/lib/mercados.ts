/**
 * Europa y Global, apagados el 8-nov-2026. El usuario compra casi solo en EE. UU.:
 * «ya que las ignoro, ahorramos tiempo y dinero; menos es más». No se borra nada.
 *
 * Para volver a encenderlos:
 *   1. `true` aquí, y `npm run build`.
 *   2. `MERCADOS_FUERA_DE_EEUU: 'on'` en .github/workflows/daily-analysis.yml, para
 *      que el pipeline vuelva a calcularlos. Sin eso la app enseñaría datos viejos.
 */
export const EUROPA_Y_GLOBAL = false
