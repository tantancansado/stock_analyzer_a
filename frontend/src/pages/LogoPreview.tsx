import { useState } from 'react'
import { LogoCandleBull, LogoChartPeak, LogoMonogram, LogoOrbit } from '../components/BrandLogos'
import LlamaLogo from '../components/LlamaLogo'
import { Button } from '@/components/ui/button'

type LogoKey = 'llama' | 'candle' | 'chart' | 'mono' | 'orbit'

const LOGOS: { key: LogoKey; name: string; blurb: string; Comp: React.ComponentType<{ size?: number; className?: string }> }[] = [
  { key: 'candle', name: '1 · Candle Bull', blurb: 'Vela japonesa alcista + flecha que se dibuja. Glow respirando.', Comp: LogoCandleBull },
  { key: 'chart',  name: '2 · Chart Peak', blurb: 'Línea de precio trazándose con dot pulsante al final.',           Comp: LogoChartPeak },
  { key: 'mono',   name: '3 · SA Monogram', blurb: 'Monograma geométrico con barrido de luz (sweep).',              Comp: LogoMonogram },
  { key: 'orbit',  name: '4 · Orbit',       blurb: 'Radar de señales: núcleo pulsante + 2 órbitas girando.',        Comp: LogoOrbit },
]

export default function LogoPreview() {
  const [selected, setSelected] = useState<LogoKey>('candle')

  return (
    <>
      <div className="mb-7 animate-fade-in-up">
        <h1 className="text-2xl font-extrabold tracking-tight mb-2 gradient-title">Logo Preview</h1>
        <p className="text-sm text-muted-foreground">4 opciones animadas · dime cuál te gusta más y la instalo en el header</p>
      </div>

      {/* Comparación con el actual */}
      <div className="mb-6 rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 animate-fade-in-up">
        <div className="text-[0.6rem] font-bold uppercase tracking-widest text-amber-400/80 mb-2">Logo actual (referencia)</div>
        <div className="flex items-center gap-4">
          <LlamaLogo size={36} />
          <LlamaLogo size={56} />
          <LlamaLogo size={96} />
        </div>
      </div>

      {/* Grid de candidatos */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {LOGOS.map(({ key, name, blurb, Comp }) => (
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
            <div className="px-4 py-2.5 border-b border-border/20 flex items-center justify-between">
              <span className="text-sm font-bold tracking-tight">{name}</span>
              {selected === key && (
                <span className="text-[0.6rem] font-bold uppercase tracking-widest text-primary">Seleccionado</span>
              )}
            </div>
            <div className="p-6 flex items-center justify-center gap-6 bg-gradient-to-br from-background to-muted/10 min-h-[140px]">
              <Comp size={36} />
              <Comp size={56} />
              <Comp size={96} />
            </div>
            <div className="px-4 py-2.5 border-t border-border/20 text-xs text-muted-foreground/80">
              {blurb}
            </div>
          </button>
        ))}
      </div>

      {/* Mock del header con el logo elegido */}
      <div className="rounded-xl border border-border/40 bg-muted/5 animate-fade-in-up" style={{ overflow: 'clip' }}>
        <div className="px-4 py-2.5 border-b border-border/20">
          <span className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground/70">
            Mock · header sidebar con "{LOGOS.find(l => l.key === selected)?.name ?? ''}"
          </span>
        </div>
        <div className="p-5 bg-gradient-to-r from-background to-muted/5">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl overflow-hidden flex-shrink-0 shadow-md shadow-primary/10">
              {(() => {
                const hit = LOGOS.find(l => l.key === selected)
                if (!hit) return null
                const C = hit.Comp
                return <C size={36} />
              })()}
            </div>
            <div className="min-w-0">
              <h1 className="text-[1.05rem] font-bold tracking-tight leading-tight">Stock Analyzer</h1>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-8 p-4 rounded-xl border border-primary/20 bg-primary/5 text-sm text-muted-foreground animate-fade-in-up">
        <span className="font-semibold text-foreground">Dime cuál te mola</span> (1/2/3/4) y lo instalo en el <code className="font-mono text-primary">App.tsx</code>, sustituyendo el logo de la llama en todos los sitios. Puedo ajustar colores, velocidad de animación o proporciones.
      </div>

      {/* Botones rápidos */}
      <div className="mt-4 flex flex-wrap gap-2">
        {LOGOS.map(({ key, name }) => (
          <Button
            key={key}
            variant={selected === key ? 'default' : 'outline'}
            size="sm"
            onClick={() => setSelected(key)}
          >
            {name}
          </Button>
        ))}
      </div>
    </>
  )
}
