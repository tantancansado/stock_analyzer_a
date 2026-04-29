import { lazy } from 'react'
import PageTabs from '../components/PageTabs'
import BroadBounceView from './BroadBounceView'
import CatalystScreener from './CatalystScreener'

const MeanReversion = lazy(() => import('./MeanReversion'))
const Momentum      = lazy(() => import('./Momentum'))

export default function EntrySetups() {
  return (
    <PageTabs
      tabs={[
        { id: 'catalyst',       icon: '⚡', label: 'Catalizadores',     content: <CatalystScreener /> },
        { id: 'mean-reversion', icon: '↩', label: 'Mean Reversion',     content: <MeanReversion /> },
        { id: 'momentum',       icon: '↑', label: 'Momentum VCP',       content: <Momentum /> },
        { id: 'broad-bounce',   icon: '🔍', label: 'Universo ampliado', content: <BroadBounceView /> },
      ]}
    />
  )
}
