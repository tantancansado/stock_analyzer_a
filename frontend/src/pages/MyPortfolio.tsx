import { lazy } from 'react'
import PageTabs from '../components/PageTabs'
import { BarChart3, Wallet } from 'lucide-react'

const PersonalPortfolio = lazy(() => import('./PersonalPortfolio'))
const Portfolio         = lazy(() => import('./Portfolio'))

export default function MyPortfolio() {
  return (
    <PageTabs
      tabs={[
        { id: 'positions',  icon: Wallet, label: 'Mis Posiciones', content: <PersonalPortfolio /> },
        { id: 'signals',    icon: BarChart3, label: 'Seguimiento de las ideas', content: <Portfolio /> },
      ]}
    />
  )
}
