import { lazy, Suspense } from 'react'
import PageTabs from '../components/PageTabs'
import Loading from '../components/Loading'
import { Euro, Flag, Globe } from 'lucide-react'
import { EUROPA_Y_GLOBAL } from '@/lib/mercados'

const ValueUS     = lazy(() => import('./ValueUS'))
const ValueEU     = lazy(() => import('./ValueEU'))
const GlobalValue = lazy(() => import('./GlobalValue'))

export default function Value() {
  // Con Europa y Global apagados, una pestaña sola no es una pestaña: Value US a secas.
  if (!EUROPA_Y_GLOBAL) return <Suspense fallback={<Loading />}><ValueUS /></Suspense>
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
