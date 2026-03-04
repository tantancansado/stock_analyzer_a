import { Skeleton } from '@/components/ui/skeleton'
import { Card, CardContent } from '@/components/ui/card'

function SkeletonStatCard() {
  return (
    <Card className="glass p-5">
      <Skeleton className="h-2.5 w-1/2 mb-4" />
      <Skeleton className="h-8 w-2/5 mb-3" />
      <Skeleton className="h-2.5 w-3/5" />
    </Card>
  )
}

const ROWS: number[][] = [
  [44, 112, 54, 80, 30, 90, 62, 44, 36, 52, 36],
  [48, 130, 58, 72, 30, 96, 64, 40, 38, 56, 38],
  [40, 104, 55, 76, 30, 82, 68, 50, 34, 48, 34],
  [52, 124, 60, 68, 30, 105, 58, 36, 40, 60, 40],
  [46, 116, 62, 84, 30, 90, 72, 44, 42, 54, 42],
  [43, 108, 56, 78, 30, 86, 65, 48, 38, 50, 38],
]

const COLS = [58, 78, 52, 52, 42, 68, 62, 42, 34, 52, 38]

function SkeletonTable() {
  return (
    <Card className="glass overflow-hidden">
      <CardContent className="p-0">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border/50">
              {COLS.map((w, i) => (
                <th key={i} className="px-3 py-3">
                  <Skeleton style={{ width: w, height: 10 }} />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ROWS.map((cols, r) => (
              <tr key={r} className="border-b border-border/30">
                {cols.map((w, c) => (
                  <td key={c} className="px-3 py-3">
                    <Skeleton style={{ width: w, height: 13 }} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  )
}

export default function Loading() {
  return (
    <div className="animate-fade-in">
      <div className="mb-7">
        <Skeleton className="h-7 w-48 mb-3" />
        <Skeleton className="h-3.5 w-80" />
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
        <SkeletonStatCard />
        <SkeletonStatCard />
        <SkeletonStatCard />
        <SkeletonStatCard />
      </div>
      <SkeletonTable />
    </div>
  )
}

export function ErrorState({ message }: { message: string }) {
  const isConnection =
    message.includes('Network') ||
    message.includes('ECONNREFUSED') ||
    message.includes('ERR_CONNECTION')

  return (
    <div className="rounded-xl border border-destructive/30 bg-destructive/5 px-8 py-7 text-center text-sm font-medium text-destructive">
      {isConnection ? 'No se puede conectar con la API' : message}
      <span className="mt-2 block text-xs font-normal text-muted-foreground">
        {isConnection
          ? 'Ejecuta python3 ticker_api.py en otra terminal'
          : 'Intenta recargar la página'}
      </span>
    </div>
  )
}
