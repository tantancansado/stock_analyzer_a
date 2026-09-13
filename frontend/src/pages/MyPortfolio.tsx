import { lazy } from 'react'
import PageTabs from '../components/PageTabs'
import { BarChart3, Brain, Wallet } from 'lucide-react'

const PersonalPortfolio = lazy(() => import('./PersonalPortfolio'))
const Portfolio         = lazy(() => import('./Portfolio'))
const Strategies        = lazy(() => import('./Strategies'))

export default function MyPortfolio() {
  return (
    <PageTabs
      tabs={[
        { id: 'positions',  icon: Wallet, label: 'Mis Posiciones', content: <PersonalPortfolio /> },
        { id: 'strategies', icon: Brain, label: 'Estrategias IA', content: <Strategies /> },
        { id: 'signals',    icon: BarChart3, label: 'Signal Tracker', content: <Portfolio /> },
      ]}
    />
  )
}
