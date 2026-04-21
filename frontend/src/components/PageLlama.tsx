import { useLocation } from 'react-router-dom'
import {
  LogoOrbit,
  LogoBrainPulse,
  LogoCandleBull,
  LogoRadar,
  LogoInsiders,
  LogoBounce,
  LogoVault,
  LogoSeed,
  LogoSonar,
  LogoChartPeak,
} from './BrandLogos'

type LogoComp = React.ComponentType<{ size?: number; className?: string }>

// Pathname prefix → animated logo. First match wins.
const ROUTE_LOGOS: ReadonlyArray<readonly [string, LogoComp]> = [
  ['/dashboard',      LogoChartPeak],
  ['/cerebro',        LogoBrainPulse],
  ['/value',          LogoCandleBull],
  ['/macro',          LogoRadar],
  ['/insiders',       LogoInsiders],
  ['/bounce',         LogoBounce],
  ['/my-portfolio',   LogoVault],
  ['/owner-earnings', LogoSeed],
  ['/search',         LogoSonar],
]

function pickLogo(pathname: string): LogoComp | null {
  for (const [prefix, Comp] of ROUTE_LOGOS) {
    if (pathname === prefix || pathname.startsWith(`${prefix}/`) || pathname.startsWith(`${prefix}-`)) {
      return Comp
    }
  }
  return null
}

export default function PageLlama() {
  const { pathname } = useLocation()
  const Comp = pickLogo(pathname) ?? LogoOrbit

  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed top-16 right-4 md:right-6 w-9 h-9 md:w-11 md:h-11 opacity-25 hover:opacity-70 transition-opacity duration-300 z-20 select-none"
    >
      <Comp size={44} className="w-full h-full" />
    </div>
  )
}
