import { lazy } from 'react'
import PageTabs from '../components/PageTabs'
import { CalendarDays, Zap } from 'lucide-react'

const EarningsCalendar = lazy(() => import('./EarningsCalendar'))
const CatalystCalendar = lazy(() => import('./CatalystCalendar'))

export default function Calendar() {
  return (
    <PageTabs
      tabs={[
        { id: 'earnings',  icon: CalendarDays, label: 'Earnings',      content: <EarningsCalendar /> },
        { id: 'catalysts', icon: Zap, label: 'Catalizadores', content: <CatalystCalendar /> },
      ]}
    />
  )
}
