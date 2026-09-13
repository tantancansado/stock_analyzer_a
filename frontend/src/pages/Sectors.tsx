import { lazy } from 'react'
import PageTabs from '../components/PageTabs'
import SectorRotation from './SectorRotation'
import { BarChart3, RefreshCw } from 'lucide-react'

const SectorComparison = lazy(() => import('./SectorComparison'))

export default function Sectors() {
  return (
    <PageTabs
      tabs={[
        { id: 'rotation',    icon: RefreshCw, label: 'Rotación',   content: <SectorRotation /> },
        { id: 'comparison',  icon: BarChart3, label: 'Comparativa FCF', content: <SectorComparison /> },
      ]}
    />
  )
}
