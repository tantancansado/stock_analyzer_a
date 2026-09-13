import { lazy } from 'react'
import PageTabs from '../components/PageTabs'
import { Fuel, Globe, Radar } from 'lucide-react'

const MacroRadar     = lazy(() => import('./MacroRadar'))
const MacroCountries = lazy(() => import('./MacroCountries'))
const MacroStress    = lazy(() => import('./MacroStress'))

export default function Macro() {
  return (
    <PageTabs
      tabs={[
        { id: 'radar',     icon: Radar, label: 'Radar',   content: <MacroRadar /> },
        { id: 'countries', icon: Globe, label: 'Países',  content: <MacroCountries /> },
        { id: 'stress',    icon: Fuel, label: 'Stress',  content: <MacroStress /> },
      ]}
    />
  )
}
