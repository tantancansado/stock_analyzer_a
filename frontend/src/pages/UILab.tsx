import { Brain, ChevronRight, LayoutDashboard, Wallet, AlertTriangle } from 'lucide-react'
import { Button, Card, Chip } from '@heroui/react'
import { Card as ShadCard, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { useState } from 'react'

/* Banco de pruebas: los mismos tres bloques del Centro de mando pintados dos
   veces —con lo que tenemos hoy y con HeroUI— para poder compararlos de un
   vistazo en vez de opinar de memoria. Es temporal: o adoptamos la librería o
   esta página se borra. */

const ACCIONES = [
  { texto: 'MCO ha alcanzado el precio objetivo', color: 'text-emerald-400' },
  { texto: 'ASML lleva 3 días bajo el stop de tesis', color: 'text-red-400' },
  { texto: 'Revisar tesis de NVO — margen en caída', color: 'text-amber-400' },
]

function Seccion({ titulo, nota, children }: { titulo: string; nota: string; children: React.ReactNode }) {
  return (
    <section className="mb-10">
      <div className="mb-4 flex items-baseline gap-3 border-b border-border/30 pb-2">
        <h2 className="text-titulo font-bold tracking-tight">{titulo}</h2>
        <span className="text-mini text-muted-foreground">{nota}</span>
      </div>
      {children}
    </section>
  )
}

export default function UILab() {
  const [tab, setTab] = useState<'resumen' | 'cerebro'>('resumen')
  const [tabH, setTabH] = useState<'resumen' | 'cerebro'>('resumen')

  return (
    <>
      <div className="mb-6">
        <h1 className="text-3xl font-extrabold tracking-tight mb-2 gradient-title">Banco de pruebas</h1>
        <p className="text-titulo text-muted-foreground">
          Los mismos bloques, con el diseño de hoy y con HeroUI. Página temporal.
        </p>
      </div>


      {/* ── Lo que hemos medido ──────────────────────────────────────── */}
      <Seccion titulo="Lo medido" nota="datos, no impresiones">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 mb-5">
          {[
            { n: '+43 KB', d: 'CSS extra (+4,3 KB comprimido) importando solo los 6 componentes que usamos. El import completo costaba +408 KB.' },
            { n: '+29 KB', d: 'JS comprimido por página que use HeroUI. Es React Aria, y es lo que trae la accesibilidad.' },
            { n: '46 / 89', d: 'Tokens de HeroUI que nuestros nombres rompen. Nueve chocan de frente y envenenan otros 37 derivados.' },
            { n: '310', d: 'Ediciones para quitar el choque de raíz: los tokens ya son colores completos, no tripletes sueltos. Hecho.' },
          ].map(({ n, d }) => (
            <div key={n} className="glass rounded-xl p-4 border border-border/30">
              <div className="text-2xl font-extrabold tracking-tight mb-1 font-mono">{n}</div>
              <p className="text-apoyo text-muted-foreground leading-snug">{d}</p>
            </div>
          ))}
        </div>
        <div className="glass rounded-xl p-4 border border-success/25">
          <div className="flex items-start gap-3">
            <AlertTriangle size={16} className="text-success shrink-0 mt-0.5" />
            <p className="text-cuerpo text-muted-foreground leading-relaxed">
              <strong className="text-foreground">Lo que costaba no verlo.</strong>{' '}
              HeroUI y nosotros llamábamos <code className="font-mono text-apoyo">--success</code>,{' '}
              <code className="font-mono text-apoyo">--background</code>,{' '}
              <code className="font-mono text-apoyo">--accent</code>… a cosas distintas. Los nuestros eran
              tripletes sueltos («152 55% 28%»), los suyos colores completos, y los nuestros ganaban la
              cascada: sus botones salían sin fondo y sus chips en blanco. Nueve choques directos
              envenenaban otros 37 derivados, porque{' '}
              <code className="font-mono text-apoyo">color-mix(in oklab, var(--success) 15%, transparent)</code>{' '}
              con un triplete dentro también es inválido — 46 de sus 89 tokens rotos, y ni un aviso en el
              build. Perseguirlos uno a uno habría sido deuda, así que se hizo el arreglo de raíz: nuestros
              126 tokens ya son colores completos, como manda Tailwind v4, y los 184 usos que los envolvían
              quedaron desenvueltos. Los chips de arriba se arreglaron solos.
            </p>
          </div>
        </div>
      </Seccion>

      {/* ── Pestañas ─────────────────────────────────────────────────── */}
      <Seccion titulo="Pestañas" nota="hoy · .seg-tab">
        <div className="flex gap-1 p-1 mb-6 bg-muted/20 rounded-lg border border-border/30 w-fit">
          {([
            { id: 'resumen' as const, label: 'Resumen', icon: LayoutDashboard },
            { id: 'cerebro' as const, label: 'Cerebro IA', icon: Brain },
          ]).map(({ id, label, icon: Icon }) => (
            <button key={id} onClick={() => setTab(id)} className={cn('seg-tab', tab === id && 'active')}>
              <Icon size={16} className={tab === id ? (id === 'cerebro' ? 'text-violet-400' : 'text-primary') : ''} />
              {label}
            </button>
          ))}
        </div>

        <div className="text-mini text-muted-foreground mb-2">HeroUI · Button</div>
        <div className="lab-heroui flex gap-1 p-1 w-fit rounded-xl bg-muted/20 border border-border/30">
          {([
            { id: 'resumen' as const, label: 'Resumen', icon: LayoutDashboard },
            { id: 'cerebro' as const, label: 'Cerebro IA', icon: Brain },
          ]).map(({ id, label, icon: Icon }) => (
            <Button
              key={id}
              size="sm"
              variant={tabH === id ? 'primary' : 'ghost'}
              onPress={() => setTabH(id)}
            >
              <Icon size={16} />
              {label}
            </Button>
          ))}
        </div>
      </Seccion>

      {/* ── Botones ──────────────────────────────────────────────────── */}
      <Seccion titulo="Botones" nota="las 7 variantes de HeroUI">
        <div className="lab-heroui flex flex-wrap gap-2">
          {(['primary', 'secondary', 'tertiary', 'outline', 'ghost', 'danger', 'danger-soft'] as const).map(v => (
            <Button key={v} variant={v} size="sm">{v}</Button>
          ))}
        </div>
      </Seccion>

      {/* ── Chips ────────────────────────────────────────────────────── */}
      <Seccion titulo="Badges" nota="hoy: span con bg/15 · HeroUI: Chip">
        <div className="flex flex-wrap items-center gap-2 mb-5">
          <span className="text-mini px-1.5 py-0.5 rounded-full bg-primary/15 text-primary font-bold">4 señales</span>
          <span className="text-mini px-1.5 py-0.5 rounded-full bg-red-500/15 text-red-400 font-bold">2 alertas</span>
          <span className="text-mini px-1.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 font-bold">Grado A</span>
        </div>
        <div className="lab-heroui flex flex-wrap items-center gap-2">
          {(['accent', 'danger', 'success', 'warning', 'default'] as const).map(c => (
            <Chip key={c} color={c} size="sm" variant="soft">{c}</Chip>
          ))}
        </div>
      </Seccion>

      {/* ── Tarjeta de acciones ──────────────────────────────────────── */}
      <Seccion titulo="Tarjeta" nota="hoy: .glass + shadcn Card · HeroUI: Card">
        <div className="grid gap-5 lg:grid-cols-2">
          <ShadCard className="glass border border-primary/20">
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-3">
                <Wallet size={16} className="text-primary" />
                <span className="text-mini font-bold uppercase tracking-[0.14em] text-primary/70">Acciones pendientes</span>
                <span className="text-mini px-1.5 py-0.5 rounded-full bg-primary/15 text-primary font-bold">{ACCIONES.length}</span>
              </div>
              <div className="space-y-1.5">
                {ACCIONES.map((a, i) => (
                  <div key={i} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-muted/10 border border-border/20">
                    <AlertTriangle size={12} className={a.color} />
                    <span className="text-cuerpo text-foreground/80 flex-1">{a.texto}</span>
                    <ChevronRight size={12} className="text-muted-foreground/30" />
                  </div>
                ))}
              </div>
            </CardContent>
          </ShadCard>

          <Card className="lab-heroui">
            <Card.Header>
              <Card.Title>Acciones pendientes</Card.Title>
              <Card.Description>Mi cartera · {ACCIONES.length} avisos</Card.Description>
            </Card.Header>
            <Card.Content>
              <div className="space-y-1.5">
                {ACCIONES.map((a, i) => (
                  <div key={i} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-muted/10 border border-border/20">
                    <AlertTriangle size={12} className={a.color} />
                    <span className="text-cuerpo flex-1">{a.texto}</span>
                    <ChevronRight size={12} className="opacity-40" />
                  </div>
                ))}
              </div>
            </Card.Content>
            <Card.Footer>
              <Button size="sm" variant="primary">Ver cartera</Button>
              <Button size="sm" variant="ghost">Descartar</Button>
            </Card.Footer>
          </Card>
        </div>
      </Seccion>
    </>
  )
}
