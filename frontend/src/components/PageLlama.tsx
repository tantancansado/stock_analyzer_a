import { useLocation } from 'react-router-dom'
import { NAV_PRIMARY, NAV_SECONDARY } from '@/lib/nav'

const ALL = [...NAV_PRIMARY, ...NAV_SECONDARY]

function matchLogo(pathname: string): string | undefined {
  const hit = ALL.find(item => item.logo && (pathname === item.path || pathname.startsWith(`${item.path}/`)))
  return hit?.logo
}

export default function PageLlama() {
  const { pathname } = useLocation()
  const logo = matchLogo(pathname)
  if (!logo) return null

  return (
    <img
      src={`${import.meta.env.BASE_URL}${logo}`}
      alt=""
      aria-hidden="true"
      className="pointer-events-none fixed top-16 right-4 md:right-6 w-9 h-9 md:w-11 md:h-11 rounded-full opacity-20 hover:opacity-60 transition-opacity duration-300 z-20 select-none"
      draggable={false}
    />
  )
}
