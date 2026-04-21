import { useState } from 'react'
import {
  LogoOrbit,
  LogoCandleBull,
  LogoChartPeak,
  LogoBrainPulse,
  LogoRadar,
  LogoInsiders,
  LogoBounce,
  LogoVault,
  LogoSeed,
  LogoSonar,
} from '../components/BrandLogos'

type LogoDef = {
  key: string
  name: string
  usage: string
  Comp: React.ComponentType<{ size?: number; className?: string }>
}

const LOGOS: LogoDef[] = [
  { key: 'orbit',     name: 'Orbit',        usage: 'Sidebar + favicon (marca principal)', Comp: LogoOrbit },
  { key: 'candle',    name: 'Candle Bull',  usage: 'Header Value US / Value EU',         Comp: LogoCandleBull },
  { key: 'chart',     name: 'Chart Peak',   usage: 'Header Dashboard',                   Comp: LogoChartPeak },
  { key: 'brain',     name: 'Brain Pulse',  usage: 'Página Cerebro (ornamento)',         Comp: LogoBrainPulse },
  { key: 'radar',     name: 'Radar',        usage: 'Página Macro (ornamento)',           Comp: LogoRadar },
  { key: 'insiders',  name: 'Insiders',     usage: 'Página Insiders (ornamento)',        Comp: LogoInsiders },
  { key: 'bounce',    name: 'Bounce',       usage: 'Página Rebotes (ornamento)',         Comp: LogoBounce },
  { key: 'vault',     name: 'Vault',        usage: 'Página Mi cartera (ornamento)',      Comp: LogoVault },
  { key: 'seed',      name: 'Seed',         usage: 'Página Owner Earnings (ornamento)',  Comp: LogoSeed },
  { key: 'sonar',     name: 'Sonar',        usage: 'Página Buscar (ornamento)',          Comp: LogoSonar },
]

export default function LogoPreview() {
  const [selected, setSelected] = useState<string>('orbit')

  return (
    <>
      <div className="mb-7 animate-fade-in-up">
        <h1 className="text-2xl font-extrabold tracking-tight mb-2 gradient-title">Sistema de logos animados</h1>
        <p className="text-sm text-muted-foreground">10 SVGs animados · uno principal (Orbit) + 9 temáticos por sección. Click en cualquiera para ver el mock.</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 mb-6">
        {LOGOS.map(({ key, name, usage, Comp }) => (
          <button
            key={key}
            type="button"
            onClick={() => setSelected(key)}
            className={`text-left rounded-xl border transition-all animate-fade-in-up ${
              selected === key
                ? 'border-primary bg-primary/5 shadow-lg shadow-primary/10'
                : 'border-border/40 hover:border-border/70 bg-muted/5'
            }`}
            style={{ overflow: 'clip' }}
          >
            <div className="p-5 flex items-center justify-center bg-gradient-to-br from-background to-muted/10 min-h-[110px]">
              <Comp size={64} />
            </div>
            <div className="px-3 py-2 border-t border-border/20">
              <div className="text-sm font-bold tracking-tight">{name}</div>
              <div className="text-[0.62rem] text-muted-foreground/70 leading-snug mt-0.5">{usage}</div>
            </div>
          </button>
        ))}
      </div>

      {/* Tamaños — logo seleccionado a 3 sizes */}
      <div className="rounded-xl border border-border/40 bg-muted/5 animate-fade-in-up mb-6" style={{ overflow: 'clip' }}>
        <div className="px-4 py-2.5 border-b border-border/20 flex items-center justify-between">
          <span className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground/70">
            Seleccionado: {LOGOS.find(l => l.key === selected)?.name}
          </span>
          <span className="text-[0.6rem] text-muted-foreground/50">
            {LOGOS.find(l => l.key === selected)?.usage}
          </span>
        </div>
        <div className="p-8 flex items-center justify-center gap-10 bg-gradient-to-br from-background to-muted/10">
          {(() => {
            const hit = LOGOS.find(l => l.key === selected)
            if (!hit) return null
            const C = hit.Comp
            return (
              <>
                <C size={32} />
                <C size={56} />
                <C size={96} />
                <C size={160} />
              </>
            )
          })()}
        </div>
      </div>

      <div className="p-4 rounded-xl border border-primary/20 bg-primary/5 text-sm text-muted-foreground animate-fade-in-up">
        <span className="font-semibold text-foreground">Sistema completo.</span> La llama ha sido reemplazada en todos los sitios. En cada página verás arriba a la derecha el logo temático correspondiente (decoración sutil, se hace más visible al pasar el ratón).
      </div>
    </>
  )
}
