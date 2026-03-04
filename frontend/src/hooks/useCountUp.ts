import { useState, useEffect, useRef } from 'react'

/**
 * Animates a number from 0 to `target` using a cubic ease-out.
 * @param target  Final value (null = no animation, returns 0)
 * @param duration  Animation duration in ms (default 650)
 * @param decimals  Decimal places to round to (default 0 for integers)
 */
export function useCountUp(
  target: number | null | undefined,
  duration = 650,
  decimals = 0,
): number {
  const [value, setValue] = useState(0)
  const rafRef = useRef(0)

  useEffect(() => {
    if (target == null) {
      setValue(0)
      return
    }

    setValue(0)
    let startTime: number | null = null

    const step = (ts: number) => {
      if (startTime == null) startTime = ts
      const progress = Math.min((ts - startTime) / duration, 1)
      const ease = 1 - Math.pow(1 - progress, 3) // cubic ease-out
      setValue(parseFloat((ease * target).toFixed(decimals)))
      if (progress < 1) {
        rafRef.current = requestAnimationFrame(step)
      }
    }

    rafRef.current = requestAnimationFrame(step)
    return () => cancelAnimationFrame(rafRef.current)
  }, [target, duration, decimals])

  return value
}
