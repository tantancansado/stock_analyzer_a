import { lazy } from 'react'
import PageTabs from '../components/PageTabs'
import { Euro, Flag, Globe } from 'lucide-react'

const ValueUS     = lazy(() => import('./ValueUS'))
const ValueEU     = lazy(() => import('./ValueEU'))
const GlobalValue = lazy(() => import('./GlobalValue'))

export default function Value() {
  return (
    <PageTabs
      paramKey="region"
      defaultTab="us"
      tabs={[
        { id: 'us',     icon: Flag, label: 'VALUE US',     content: <ValueUS /> },
        { id: 'eu',     icon: Euro, label: 'VALUE EU',     content: <ValueEU /> },
        { id: 'global', icon: Globe,  label: 'VALUE Global', content: <GlobalValue /> },
      ]}
    />
  )
}
