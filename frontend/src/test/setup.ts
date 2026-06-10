import '@testing-library/jest-dom'
import { vi } from 'vitest'

// Supabase env vars aren't loaded in the test env; stub them so createClient()
// in src/lib/supabase.ts doesn't throw "supabaseUrl is required" at import time.
vi.stubEnv('VITE_SUPABASE_URL', 'http://localhost:54321')
vi.stubEnv('VITE_SUPABASE_ANON_KEY', 'test-anon-key')

// Vitest 4.x persistent localStorage feature can provide a broken localStorage
// when --localstorage-file has no valid path. Ensure a full in-memory implementation.
const makeStorage = () => {
  let store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => { store[key] = String(value) },
    removeItem: (key: string) => { delete store[key] },
    clear: () => { store = {} },
    get length() { return Object.keys(store).length },
    key: (i: number) => Object.keys(store)[i] ?? null,
  }
}

Object.defineProperty(globalThis, 'localStorage', { value: makeStorage(), writable: true })
Object.defineProperty(globalThis, 'sessionStorage', { value: makeStorage(), writable: true })

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

Object.defineProperty(globalThis, 'ResizeObserver', { value: ResizeObserverMock, writable: true })

if (!Element.prototype.scrollIntoView) {
  Object.defineProperty(Element.prototype, 'scrollIntoView', {
    value: () => {},
    writable: true,
  })
}
