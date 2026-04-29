import { Bell, BellOff, BellRing, Loader2 } from 'lucide-react'
import { usePushNotifications } from '../hooks/usePushNotifications'

export default function PushNotificationButton() {
  const { state, subscribe, unsubscribe } = usePushNotifications()

  if (state === 'unsupported') return null

  if (state === 'loading') {
    return (
      <button
        disabled
        className="p-1.5 rounded-md text-muted-foreground/40"
        aria-label="Cargando notificaciones"
      >
        <Loader2 className="w-4 h-4 animate-spin" />
      </button>
    )
  }

  if (state === 'denied') {
    return (
      <button
        disabled
        title="Notificaciones bloqueadas en el navegador — actívalas en Ajustes del sitio"
        className="p-1.5 rounded-md text-muted-foreground/40 cursor-not-allowed"
        aria-label="Notificaciones bloqueadas"
      >
        <BellOff className="w-4 h-4" />
      </button>
    )
  }

  if (state === 'subscribed') {
    return (
      <button
        onClick={unsubscribe}
        title="Notificaciones push activas — click para desactivar"
        className="p-1.5 rounded-md text-emerald-400 hover:bg-emerald-500/10 transition-colors"
        aria-label="Desactivar notificaciones"
      >
        <BellRing className="w-4 h-4" />
      </button>
    )
  }

  // unsubscribed
  return (
    <button
      onClick={subscribe}
      title="Activar alertas push — te avisamos cuando Cerebro detecte entradas VALUE o señales HIGH"
      className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/30 transition-colors"
      aria-label="Activar notificaciones"
    >
      <Bell className="w-4 h-4" />
    </button>
  )
}
