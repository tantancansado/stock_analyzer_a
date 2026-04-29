import { lazy } from 'react'
import PageTabs from '../components/PageTabs'
import SectorRotation from './SectorRotation'

const SectorComparison = lazy(() => import('./SectorComparison'))

export default function Sectors() {
  return (
    <PageTabs
      tabs={[
        { id: 'rotation',    icon: '🔄', label: 'Rotación',   content: <SectorRotation /> },
        { id: 'comparison',  icon: '📊', label: 'Comparativa FCF', content: <SectorComparison /> },
      ]}
    />
  )
}
