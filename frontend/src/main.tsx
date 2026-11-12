import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
import './index.css'
import App from './App'
import { AuthProvider } from './context/AuthContext'
import { registerSW } from 'virtual:pwa-register'

// Una versión nueva se instalaba sola, pero la pantalla abierta seguía con la vieja
// hasta recargar (a veces dos veces): el 12-nov el usuario vio la tabla de antes de
// un arreglo ya publicado. En modo autoUpdate, registerSW recarga la página cuando la
// nueva toma el control; además se busca al volver a la app y cada media hora, porque
// en el móvil la app se queda abierta días.
registerSW({
  immediate: true,
  onRegisteredSW(_url, registro) {
    if (!registro) return
    const buscar = () => {
      if (document.visibilityState === 'visible' && navigator.onLine) registro.update().catch(() => {})
    }
    document.addEventListener('visibilitychange', buscar)
    setInterval(buscar, 30 * 60_000)
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <HashRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </HashRouter>
  </StrictMode>,
)
