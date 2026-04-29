import { useState, useEffect, useCallback } from 'react'
import { apiClient } from '../api/client'

type PushState = 'unsupported' | 'denied' | 'subscribed' | 'unsubscribed' | 'loading'

function urlBase64ToUint8Array(base64String: string): ArrayBuffer {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = atob(base64)
  const arr = new Uint8Array(raw.length)
  for (let i = 0; i < raw.length; i++) arr[i] = raw.charCodeAt(i)
  return arr.buffer as ArrayBuffer
}

async function getVapidKey(): Promise<string | null> {
  try {
    const res = await apiClient.get<{ key: string }>('/api/push/vapid-public-key')
    return res.data.key
  } catch {
    return null
  }
}

export function usePushNotifications() {
  const [state, setState] = useState<PushState>('loading')

  useEffect(() => {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
      setState('unsupported')
      return
    }
    if (Notification.permission === 'denied') {
      setState('denied')
      return
    }
    navigator.serviceWorker.ready.then(reg =>
      reg.pushManager.getSubscription()
    ).then(sub => {
      setState(sub ? 'subscribed' : 'unsubscribed')
    }).catch(() => setState('unsubscribed'))
  }, [])

  const subscribe = useCallback(async () => {
    if (!('serviceWorker' in navigator)) return
    setState('loading')
    try {
      const vapidKey = await getVapidKey()
      if (!vapidKey) { setState('unsubscribed'); return }

      const permission = await Notification.requestPermission()
      if (permission !== 'granted') { setState('denied'); return }

      const reg = await navigator.serviceWorker.ready
      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapidKey),
      })

      await apiClient.post('/api/push/subscribe', sub.toJSON())
      setState('subscribed')
    } catch (e) {
      console.error('Push subscribe failed:', e)
      setState('unsubscribed')
    }
  }, [])

  const unsubscribe = useCallback(async () => {
    setState('loading')
    try {
      const reg = await navigator.serviceWorker.ready
      const sub = await reg.pushManager.getSubscription()
      if (sub) {
        await apiClient.post('/api/push/unsubscribe', { endpoint: sub.endpoint })
        await sub.unsubscribe()
      }
      setState('unsubscribed')
    } catch (e) {
      console.error('Push unsubscribe failed:', e)
      setState('subscribed')
    }
  }, [])

  return { state, subscribe, unsubscribe }
}
