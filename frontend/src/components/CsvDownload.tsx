import { downloadCsv } from '../api/client'

interface CsvDownloadProps {
  dataset: string
  label?: string
  className?: string
}

export default function CsvDownload({ dataset, label, className }: CsvDownloadProps) {
  return (
    <button
      onClick={() => downloadCsv(dataset)}
      title={`Descargar ${dataset}.csv`}
      className={`text-xs px-3 py-1 rounded border border-border/50 text-muted-foreground hover:text-foreground hover:border-primary transition-colors ${className ?? ''}`}
    >
      ↓ {label ?? 'CSV'}
    </button>
  )
}
