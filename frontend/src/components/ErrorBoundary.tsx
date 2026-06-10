import { Component, type ReactNode, type ErrorInfo } from 'react'

interface Props { children: ReactNode; resetKey?: string }
interface State { error: Error | null; resetKey: string }

const IMPORT_ERROR_RELOAD_KEY = 'sa-import-error-reload'
const IMPORT_ERROR_PATTERNS = [
  'importing a module script failed',
  'failed to fetch dynamically imported module',
  'error loading dynamically imported module',
  'failed to import',
  'chunkloaderror',
]

function isImportError(error: Error | null): boolean {
  const message = `${error?.name ?? ''} ${error?.message ?? ''}`.toLowerCase()
  return IMPORT_ERROR_PATTERNS.some(pattern => message.includes(pattern))
}

function clearImportErrorReloadFlag() {
  try {
    sessionStorage.removeItem(IMPORT_ERROR_RELOAD_KEY)
  } catch { /* best-effort, ignore */ }
}

async function recoverAppShell() {
  try {
    if ('serviceWorker' in navigator) {
      const regs = await navigator.serviceWorker.getRegistrations()
      await Promise.all(regs.map(reg => reg.unregister()))
    }
  } catch { /* best-effort, ignore */ }

  try {
    if ('caches' in window) {
      const keys = await caches.keys()
      await Promise.all(keys.map(key => caches.delete(key)))
    }
  } catch { /* best-effort, ignore */ }

  window.location.reload()
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null, resetKey: '' }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { error }
  }

  // Auto-reset when user navigates to a different route
  static getDerivedStateFromProps(props: Props, state: State): Partial<State> | null {
    const key = props.resetKey ?? ''
    if (key !== state.resetKey) {
      return { error: null, resetKey: key }
    }
    return null
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack)

    if (isImportError(error)) {
      try {
        if (sessionStorage.getItem(IMPORT_ERROR_RELOAD_KEY) !== '1') {
          sessionStorage.setItem(IMPORT_ERROR_RELOAD_KEY, '1')
          void recoverAppShell()
          return
        }
        clearImportErrorReloadFlag()
      } catch { /* best-effort, ignore */ }
    }
  }

  componentDidMount() {
    if (!this.state.error) clearImportErrorReloadFlag()
  }

  componentDidUpdate(_prevProps: Props, prevState: State) {
    if (prevState.error && !this.state.error) clearImportErrorReloadFlag()
  }

  render() {
    if (this.state.error) {
      const importError = isImportError(this.state.error)
      return (
        <div className="min-h-[60vh] flex flex-col items-center justify-center p-8 text-center">
          <div className="text-5xl mb-4 opacity-30">⚠️</div>
          <h2 className="text-lg font-bold text-foreground mb-2">
            {importError ? 'La app necesita actualizarse' : 'Algo salió mal'}
          </h2>
          <p className="text-sm text-muted-foreground mb-4 max-w-md">
            {importError
              ? 'Hay una versión nueva y el navegador intentó abrir una pieza antigua. Actualiza la app para continuar.'
              : this.state.error.message || 'Error inesperado en esta sección.'}
          </p>
          {importError ? (
            <button
              onClick={() => { void recoverAppShell() }}
              className="text-xs px-4 py-2 rounded border border-primary/40 text-primary hover:bg-primary/10 transition-colors"
            >
              Actualizar ahora
            </button>
          ) : (
            <button
              onClick={() => this.setState({ error: null })}
              className="text-xs px-4 py-2 rounded border border-primary/40 text-primary hover:bg-primary/10 transition-colors"
            >
              Reintentar
            </button>
          )}
        </div>
      )
    }
    return this.props.children
  }
}
