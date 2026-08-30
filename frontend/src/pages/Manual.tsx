import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  BookOpen, Compass, Workflow, Bot, Shield, HelpCircle, Search,
  LayoutDashboard, Brain, DollarSign, Radar, Users, Crosshair,
  Wallet, Calculator, TrendingUp, Activity, PieChart,
  Bell, CalendarDays, AlertTriangle, Ruler, FlaskConical, Shuffle, Database, Landmark, Rocket,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import PageHeader from '../components/PageHeader'

// ── Types ─────────────────────────────────────────────────────────────────────

type Section = {
  id: string
  title: string
  icon: LucideIcon
  group: 'intro' | 'pages' | 'agents' | 'concepts'
}

// ── Sections index ────────────────────────────────────────────────────────────

const SECTIONS: Section[] = [
  // Intro
  { id: 'bienvenida',         title: 'Bienvenida',            icon: BookOpen,   group: 'intro' },
  { id: 'filosofia',          title: 'Filosofía Value/GARP',  icon: Compass,    group: 'intro' },
  { id: 'como-leer',          title: 'Cómo leer los datos',   icon: HelpCircle, group: 'intro' },
  { id: 'flujo-diario',       title: 'Flujo diario sugerido', icon: Workflow,   group: 'intro' },

  // Pages
  { id: 'dashboard',          title: 'Dashboard',             icon: LayoutDashboard, group: 'pages' },
  { id: 'cerebro',            title: 'Cerebro',               icon: Brain,           group: 'pages' },
  { id: 'value',              title: 'Value (US/EU/Global)',  icon: DollarSign,      group: 'pages' },
  { id: 'macro',              title: 'Macro Radar',           icon: Radar,           group: 'pages' },
  { id: 'insiders',           title: 'Insiders',              icon: Users,           group: 'pages' },
  { id: 'bounce',             title: 'Rebotes técnicos',      icon: Crosshair,       group: 'pages' },
  { id: 'mi-cartera',         title: 'Mi cartera',            icon: Wallet,          group: 'pages' },
  { id: 'owner-earnings',     title: 'Owner Earnings',        icon: Calculator,      group: 'pages' },
  { id: 'buscar',             title: 'Buscar ticker',         icon: Search,          group: 'pages' },
  { id: 'entry-setups',       title: 'Entry setups',          icon: TrendingUp,      group: 'pages' },
  { id: 'leaps',              title: 'LEAPS deep-ITM',        icon: Rocket,          group: 'pages' },
  { id: 'options',            title: 'Options flow',          icon: Activity,        group: 'pages' },
  { id: 'sectores',           title: 'Sectores',              icon: PieChart,        group: 'pages' },
  { id: 'alertas',            title: 'Alertas',               icon: Bell,            group: 'pages' },
  { id: 'calendario',         title: 'Calendario earnings',   icon: CalendarDays,    group: 'pages' },
  { id: 'dividend-traps',     title: 'Dividend traps',        icon: AlertTriangle,   group: 'pages' },
  { id: 'position-sizing',    title: 'Position sizing',       icon: Ruler,           group: 'pages' },
  { id: 'backtest',           title: 'Backtest',              icon: FlaskConical,    group: 'pages' },
  { id: 'comparar',           title: 'Comparar tickers',      icon: Shuffle,         group: 'pages' },
  { id: 'datos',              title: 'Exportar datos',        icon: Database,        group: 'pages' },
  { id: 'bonos',              title: 'Bonos & Preferentes',   icon: Landmark,        group: 'pages' },

  // Agents
  { id: 'agentes-overview',   title: 'Agentes — visión general', icon: Bot, group: 'agents' },
  { id: 'agente-fundamental', title: 'Fundamental scorer',    icon: Bot, group: 'agents' },
  { id: 'agente-super-score', title: 'Super Score Integrator',icon: Bot, group: 'agents' },
  { id: 'agente-ai-filter',   title: 'AI Quality Filter',     icon: Bot, group: 'agents' },
  { id: 'agente-thesis',      title: 'Thesis Generator',      icon: Bot, group: 'agents' },
  { id: 'agente-entry-exit',  title: 'Entry/Exit Calculator', icon: Bot, group: 'agents' },
  { id: 'agente-mean-rev',    title: 'Mean Reversion',        icon: Bot, group: 'agents' },
  { id: 'agente-bounce',      title: 'Bounce Trader',         icon: Bot, group: 'agents' },
  { id: 'agente-insiders',    title: 'Insider Scanners',      icon: Bot, group: 'agents' },
  { id: 'agente-options',     title: 'Options Flow Detector', icon: Bot, group: 'agents' },
  { id: 'agente-sector',      title: 'Sector Rotation',       icon: Bot, group: 'agents' },
  { id: 'agente-macro',       title: 'Macro / Country Scanner', icon: Bot, group: 'agents' },
  { id: 'agente-catalyst',    title: 'Catalyst Scanner',      icon: Bot, group: 'agents' },
  { id: 'agente-portfolio',   title: 'Portfolio Tracker',     icon: Bot, group: 'agents' },
  { id: 'agente-leaps',       title: 'LEAPS Analyzer',        icon: Bot, group: 'agents' },
  { id: 'agente-why-cheap',   title: 'Why Cheap',             icon: Bot, group: 'agents' },
  { id: 'agente-ml-scorer',  title: 'ML Scorer',             icon: Bot, group: 'agents' },
  { id: 'agente-cerebro',     title: 'Cerebro (orquestador)', icon: Bot, group: 'agents' },

  // Concepts
  { id: 'glosario',           title: 'Glosario',              icon: Shield, group: 'concepts' },
  { id: 'faq',                title: 'Preguntas frecuentes',  icon: HelpCircle, group: 'concepts' },
]

const GROUP_LABELS: Record<Section['group'], string> = {
  intro: 'Empieza aquí',
  pages: 'Secciones de la app',
  agents: 'Agentes del pipeline',
  concepts: 'Glosario y ayuda',
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function SectionHeader({ id, icon: Icon, title, subtitle }: { id: string; icon: LucideIcon; title: string; subtitle?: string }) {
  return (
    <header id={id} className="group scroll-mt-20 mb-4">
      <div className="flex items-center gap-2.5">
        <Icon size={18} className="text-primary transition-transform duration-300 group-hover:scale-110" />
        <h2 className="text-xl font-extrabold tracking-tight">{title}</h2>
      </div>
      {subtitle && <p className="text-sm text-muted-foreground mt-1">{subtitle}</p>}
    </header>
  )
}

function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`glass rounded-xl border border-border/40 p-5 mb-6 transition-colors duration-300 hover:border-border/70 ${className}`}>
      {children}
    </div>
  )
}

function OpenLink({ to, label }: { to: string; label?: string }) {
  return (
    <Link
      to={to}
      className="inline-flex items-center gap-1 text-[0.78rem] font-semibold text-primary hover:text-primary/80 transition-colors"
    >
      {label ?? 'Abrir sección'} →
    </Link>
  )
}

// Color-code metric semantics (green=good, amber=caution, red=bad)
function Pill({ tone, children }: { tone: 'green' | 'amber' | 'red' | 'blue' | 'slate'; children: React.ReactNode }) {
  const map = {
    green: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    amber: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    red:   'bg-red-500/10 text-red-400 border-red-500/30',
    blue:  'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
    slate: 'bg-slate-500/10 text-muted-foreground border-slate-500/30',
  }[tone]
  return <span className={`inline-flex items-center text-[0.68rem] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md border ${map}`}>{children}</span>
}

// ── Main component ────────────────────────────────────────────────────────────

export default function Manual() {
  const [active, setActive] = useState<string>(SECTIONS[0].id)
  const [query, setQuery] = useState('')
  const [jumpTo, setJumpTo] = useState('')
  const [progress, setProgress] = useState(0)

  // IntersectionObserver for active TOC highlight
  useEffect(() => {
    const observer = new IntersectionObserver(
      entries => {
        const visible = entries.filter(e => e.isIntersecting).sort((a, b) => a.target.getBoundingClientRect().top - b.target.getBoundingClientRect().top)
        if (visible[0]) setActive((visible[0].target as HTMLElement).id)
      },
      { rootMargin: '-20% 0px -60% 0px', threshold: 0 }
    )
    SECTIONS.forEach(s => {
      const el = document.getElementById(s.id)
      if (el) observer.observe(el)
    })
    return () => observer.disconnect()
  }, [])

  // Barra de progreso de lectura — es un documento largo (30+ secciones), da
  // referencia de cuánto queda sin tener que mirar la scrollbar del navegador.
  // rAF-throttled: un listener de scroll sin esto dispara en cada pixel.
  useEffect(() => {
    let ticking = false
    function computeProgress() {
      const doc = document.documentElement
      const max = doc.scrollHeight - doc.clientHeight
      setProgress(max > 0 ? Math.min(100, (doc.scrollTop / max) * 100) : 0)
      ticking = false
    }
    function onScroll() {
      if (!ticking) {
        requestAnimationFrame(computeProgress)
        ticking = true
      }
    }
    computeProgress()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return SECTIONS
    return SECTIONS.filter(s => s.title.toLowerCase().includes(q))
  }, [query])

  const byGroup = useMemo(() => {
    const m: Record<string, Section[]> = {}
    filtered.forEach(s => { (m[s.group] ??= []).push(s) })
    return m
  }, [filtered])

  return (
    <div className="mb-7 animate-fade-in-up">
      {/* Barra de progreso de lectura, pegada bajo el topbar sticky */}
      <div
        className="fixed left-0 z-40 h-0.5 bg-primary/70 transition-[width] duration-150 ease-out"
        style={{ top: 'var(--topbar-height, 50px)', width: `${progress}%` }}
        aria-hidden="true"
      />

      <PageHeader
        title="Manual de usuario"
        subtitle="Cómo funciona cada sección, qué hace cada agente y cómo interpretar los datos. Pensado para empezar de cero."
      />

      {/* Mobile section jump — el TOC con buscador de abajo solo se ve desde lg */}
      <div className="lg:hidden mb-5">
        <select
          value={jumpTo}
          onChange={e => {
            const id = e.target.value
            document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
            setJumpTo('')
          }}
          className="w-full px-3 py-2.5 text-sm rounded-md bg-muted/20 border border-border/40 focus:border-primary/60 focus:outline-none transition-colors"
        >
          <option value="" disabled>Saltar a una sección…</option>
          {(['intro', 'pages', 'agents', 'concepts'] as const).map(g => (
            <optgroup key={g} label={GROUP_LABELS[g]}>
              {SECTIONS.filter(s => s.group === g).map(s => (
                <option key={s.id} value={s.id}>{s.title}</option>
              ))}
            </optgroup>
          ))}
        </select>
      </div>

      <div className="flex gap-8">
        {/* TOC */}
        <aside className="hidden lg:block w-60 shrink-0">
          <div className="sticky top-20">
            <div className="relative mb-3">
              <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground/50" />
              <input
                type="text"
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Buscar en manual…"
                className="w-full pl-8 pr-3 py-1.5 text-[0.78rem] rounded-md bg-muted/20 border border-border/40 focus:border-primary/60 focus:outline-none transition-colors"
              />
            </div>
            <nav className="text-[0.82rem] space-y-4 max-h-[calc(100vh-9rem)] overflow-y-auto">
              {(['intro', 'pages', 'agents', 'concepts'] as const).map(g => {
                const items = byGroup[g]
                if (!items?.length) return null
                return (
                  <div key={g}>
                    <div className="text-[0.6rem] uppercase tracking-[0.18em] font-bold text-muted-foreground/50 mb-1.5 px-2">
                      {GROUP_LABELS[g]}
                    </div>
                    <ul className="space-y-0.5">
                      {items.map(s => (
                        <li key={s.id}>
                          <a
                            href={`#${s.id}`}
                            className={`flex items-center gap-2 pl-2 pr-2 py-1 rounded-md border-l-2 transition-all duration-200 ${
                              active === s.id
                                ? 'border-l-primary bg-primary/10 text-primary font-semibold translate-x-0.5'
                                : 'border-l-transparent text-muted-foreground hover:text-foreground hover:bg-muted/30'
                            }`}
                          >
                            <s.icon size={12} strokeWidth={1.75} className="shrink-0" />
                            <span className="truncate">{s.title}</span>
                          </a>
                        </li>
                      ))}
                    </ul>
                  </div>
                )
              })}
            </nav>
          </div>
        </aside>

        {/* Content */}
        <article className="flex-1 min-w-0 max-w-3xl text-[0.92rem] leading-relaxed">

          {/* ──────────────── Intro ──────────────── */}

          <SectionHeader id="bienvenida" icon={BookOpen} title="Bienvenida"
            subtitle="Qué es Stock Analyzer y qué puedes hacer aquí." />
          <Card>
            <p className="mb-3">
              <b>Stock Analyzer</b> es un sistema de análisis de acciones orientado a inversores que buscan <b>compañías sólidas a precio razonable</b>,
              no especulación a corto plazo. Combina tres capas:
            </p>
            <ul className="list-disc pl-5 space-y-1.5 mb-3">
              <li><b>Un pipeline automatizado</b> que cada día puntúa miles de empresas (US + Europa) por calidad fundamental, momentum, insiders y señales técnicas.</li>
              <li><b>Agentes especializados</b> que cruzan esos datos (ver <a href="#agentes-overview" className="text-primary hover:underline">Agentes</a>) y generan oportunidades filtradas por IA.</li>
              <li><b>Una interfaz en tiempo real</b> (esta app) donde ves rankings, tu cartera, alertas, backtests y análisis individual por ticker.</li>
            </ul>
            <p className="text-sm text-muted-foreground">
              Si es tu primera vez, empieza por <a href="#flujo-diario" className="text-primary hover:underline">Flujo diario sugerido</a>.
            </p>
          </Card>

          <SectionHeader id="filosofia" icon={Compass} title="Filosofía Value/GARP"
            subtitle="Por qué este sistema rechaza cosas que otros recomendarían." />
          <Card>
            <p className="mb-3">
              La app sigue la escuela de <b>Peter Lynch y Warren Buffett</b>: comprar negocios buenos cuando están temporalmente baratos, no perseguir la acción de moda.
              En la práctica esto significa:
            </p>
            <ul className="list-disc pl-5 space-y-1.5 mb-3">
              <li><b>ROE negativo = descarte automático.</b> Una empresa que destruye capital no es una oportunidad, por muy barata que parezca.</li>
              <li><b>Upside analista negativo = descarte.</b> Si todos los analistas que siguen la empresa piensan que está sobrevalorada, no la compramos.</li>
              <li><b>Upside ≥ 30% también se descarta — es lo contrario de una ganga.</b> Medido sobre señales reales: 0% de acierto por encima de ese umbral. Un hueco tan grande entre precio y objetivo casi siempre significa que el precio se desplomó por algo que el modelo todavía no ve, no que el mercado se equivoca en tu favor. La zona que sí funciona es <b>[10%, 25%)</b> — 83% de acierto.</li>
              <li><b>Dato faltante ≠ dato bueno.</b> Cuando un score por defecto es 50 (información no disponible), el sistema <u>no puntúa</u> — prefiere no recomendar a inventarse números.</li>
              <li><b>Se vende a precio objetivo, nunca a un % fijo de ganancia ni a un nivel técnico.</b> El objetivo se calcula (múltiplo × BPA limpio, DCF, consenso), y una empresa excepcional aguanta hasta el objetivo completo mientras una mediocre no.</li>
            </ul>
            <p className="text-sm text-muted-foreground">
              Esto explica por qué a veces el Dashboard muestra "0 oportunidades momentum" durante correcciones. Es correcto — preferimos cero señales antes que señales falsas.
            </p>
          </Card>

          <SectionHeader id="como-leer" icon={HelpCircle} title="Cómo leer los datos"
            subtitle="Códigos de color, banners y qué significa cada score." />
          <Card>
            <p className="font-semibold mb-2">Código de color general</p>
            <div className="flex flex-wrap gap-2 mb-4">
              <Pill tone="green">Verde · bueno / confirmado</Pill>
              <Pill tone="amber">Ámbar · precaución / dato sospechoso</Pill>
              <Pill tone="red">Rojo · riesgo alto / descarte</Pill>
              <Pill tone="blue">Azul · informativo / neutral</Pill>
            </div>

            <p className="font-semibold mb-2">Banners de frescura de datos</p>
            <ul className="list-disc pl-5 space-y-1.5 mb-4 text-sm">
              <li><Pill tone="green">Datos en vivo</Pill> el módulo se actualizó hoy.</li>
              <li><Pill tone="amber">Módulo no actualizado hoy</Pill> el pipeline corrió pero este módulo concreto no generó datos.</li>
              <li><Pill tone="red">Pipeline no ejecutado en X días</Pill> fallo sistémico — clic en "Lanzar pipeline" para disparar manualmente.</li>
            </ul>

            <p className="font-semibold mb-2">Scores clave</p>
            <ul className="list-disc pl-5 space-y-1.5 text-sm">
              <li><b>value_score (0–100):</b> combinado de fundamentales + insiders + opciones + sector + mean reversion. Ver <a href="#agente-super-score" className="text-primary hover:underline">Super Score Integrator</a>.</li>
              <li><b>Grade A/B/C/D:</b> conviction grade. A = alta convicción (≥3 positivos, ≤1 red flag). D = evitar.</li>
              <li>
                <b>Upside de analistas — la zona importa más que el número.</b> No es "cuanto más, mejor": la banda <b>[10%, 25%)</b> es la única con acierto alto medido (83%);
                por debajo de 10% el margen no compensa el riesgo, y por encima de 30% el sistema lo descarta directamente (ver <a href="#filosofia" className="text-primary hover:underline">Filosofía</a>).
                Un R:R muy alto (≥3) sobre esta métrica salió medido como la <u>peor</u> banda en señales reales — no lo uses como filtro de calidad por sí solo.
              </li>
              <li><b>FCF %:</b> Free Cash Flow yield (FCF / market cap). ≥5% sólido, ≥8% excepcional, negativo = red flag.</li>
              <li><b>Por qué está barata (why_cheap):</b> DETERIORO / CÍCLICO / EVENTO / SENTIMIENTO / sin datos. Solo DETERIORO descarta el pick — el resto son caídas que no vienen del negocio rompiéndose. Ver <a href="#agente-why-cheap" className="text-primary hover:underline">Why Cheap</a>.</li>
            </ul>
          </Card>

          <SectionHeader id="flujo-diario" icon={Workflow} title="Flujo diario sugerido"
            subtitle="Qué mirar cada mañana en orden recomendado." />
          <Card>
            <ol className="list-decimal pl-5 space-y-3">
              <li>
                <b>Dashboard</b> → estado del mercado, top 5 VALUE y alertas urgentes del día.
                <div className="text-xs text-muted-foreground mt-0.5">Si ves banner rojo "Pipeline no ejecutado", lánzalo antes de seguir.</div>
              </li>
              <li>
                <b>Cerebro</b> → el agente de IA te resume qué hacer hoy (entradas sugeridas, exits, alertas).
                <div className="text-xs text-muted-foreground mt-0.5">Es tu "briefing matinal" — si solo tienes 2 minutos, mira esto.</div>
              </li>
              <li>
                <b>Mi cartera</b> → ¿alguna posición con señal de salida o earnings mañana?
              </li>
              <li>
                <b>Value (US o EU)</b> → filtra por Grade A/B, FCF ≥ 5%, R:R ≥ 2. Las tablas tienen filas expandibles con la tesis completa.
              </li>
              <li>
                <b>Insiders</b> → cuando directivos compran con su propio dinero, es una de las señales menos ruidosas del mercado.
              </li>
              <li>
                <b>Alertas</b> → configura emails para precios objetivo que te importen, así no tienes que mirar la app todo el rato.
              </li>
            </ol>
          </Card>

          {/* ──────────────── Pages ──────────────── */}

          <h2 className="text-lg font-bold uppercase tracking-widest text-muted-foreground/60 mt-10 mb-4 pb-1 border-b border-border/30">
            Secciones de la app
          </h2>

          <SectionHeader id="dashboard" icon={LayoutDashboard} title="Dashboard"
            subtitle="Tu página de inicio — una foto del estado del mercado y tus mejores oportunidades." />
          <Card>
            <p className="font-semibold mb-1">Qué verás</p>
            <ul className="list-disc pl-5 space-y-1.5 text-sm mb-3">
              <li><b>Régimen de mercado:</b> BULL / CORRECTION / BEAR según breadth e índices. Afecta cuántas señales momentum se muestran.</li>
              <li><b>Top 5 VALUE US + EU:</b> las mejores ideas filtradas por IA. Clic para ver tesis.</li>
              <li><b>Portfolio win rate:</b> % de acierto de las recomendaciones pasadas (7d/14d/30d).</li>
              <li><b>Mini-widgets:</b> insiders recientes, options flow inusual, mean reversion candidates.</li>
            </ul>
            <OpenLink to="/dashboard" />
          </Card>

          <SectionHeader id="cerebro" icon={Brain} title="Cerebro"
            subtitle="El agente IA que cruza todos los datos y te dice qué hacer hoy." />
          <Card>
            <p className="mb-3">
              Cerebro es el <b>briefing proactivo</b>: en lugar de mirar 15 tablas, te da un resumen ordenado por urgencia.
              Cruza convergencias (ej. un ticker con insider buying + options alcistas + rebote técnico a la vez) y destaca lo importante.
            </p>
            <p className="font-semibold mb-1">Secciones del briefing</p>
            <ul className="list-disc pl-5 space-y-1.5 text-sm mb-3">
              <li><b>Entradas sugeridas:</b> tickers con convergencia VALUE + técnico óptimo hoy.</li>
              <li><b>Smart money:</b> dónde están comprando insiders + instituciones.</li>
              <li><b>Exit warnings:</b> tus posiciones con señal de venta.</li>
              <li><b>Value traps:</b> empresas "baratas" con problemas estructurales. Aléjate.</li>
              <li><b>Calidad decayendo:</b> ROE o márgenes que empeoran — revisar tesis.</li>
              <li><b>Short squeeze potential:</b> alta short interest + accumulation.</li>
            </ul>
            <OpenLink to="/dashboard?tab=cerebro" />
          </Card>

          <SectionHeader id="value" icon={DollarSign} title="Value (US / EU / Global)"
            subtitle="Ranking principal de oportunidades value con grades A–D." />
          <Card>
            <p className="mb-3">
              Usa las pestañas para cambiar entre <b>US</b>, <b>Europa</b> o <b>Global</b>. La tabla se puede filtrar por:
            </p>
            <ul className="list-disc pl-5 space-y-1.5 text-sm mb-3">
              <li><b>Grade:</b> A (mejor), B, C, D (evitar).</li>
              <li><b>Sector:</b> útil para diversificar.</li>
              <li><b>FCF%</b> mínimo.</li>
              <li><b>R:R</b> mínimo.</li>
              <li><b>Ocultar earnings en &lt; 7 días:</b> evita entradas arriesgadas cerca de resultados.</li>
            </ul>
            <p className="text-sm mb-3">
              <b>Expandir una fila</b> muestra la <i>conviction panel</i>: positivos (ej. "ROE 22%, FCF 8%, insider buying"), red flags (ej. "analyst revisions cayendo") y la tesis generada por IA.
            </p>
            <div className="mt-3"><OpenLink to="/value" /></div>
          </Card>

          <SectionHeader id="macro" icon={Radar} title="Macro Radar"
            subtitle="Contexto macro por país — ¿en qué regímenes económicos estamos?" />
          <Card>
            <p className="mb-3">
              Te muestra <b>ciclos de deuda</b> (Dalio), <b>inflación</b>, <b>soberanía monetaria</b> y <b>bancos centrales</b> por país.
              Útil para decidir rotaciones sectoriales y evitar países con riesgo sistémico.
            </p>
            <ul className="list-disc pl-5 space-y-1.5 text-sm mb-3">
              <li><b>Tab "Radar":</b> visión global — expansión vs recesión.</li>
              <li><b>Tab "Países":</b> ficha detallada por país (PIB, inflación, política monetaria).</li>
            </ul>
            <OpenLink to="/macro-radar" />
          </Card>

          <SectionHeader id="insiders" icon={Users} title="Insiders"
            subtitle="Compras de directivos con su propio dinero — señal fuerte de infravaloración." />
          <Card>
            <p className="mb-3">
              Los directivos compran por una sola razón: creen que la acción subirá. Vender tiene 100 razones (diversificar, impuestos, divorcio). Por eso <b>solo miramos compras</b>.
            </p>
            <ul className="list-disc pl-5 space-y-1.5 text-sm mb-3">
              <li><b>Confidence score:</b> normaliza importe, número de insiders, recencia y calidad (CEO &gt; director).</li>
              <li><b>Filtros US / EU / All</b> arriba a la derecha.</li>
              <li><b>Cluster buys:</b> cuando varios insiders compran en pocos días — señal mucho más fuerte que uno solo.</li>
            </ul>
            <OpenLink to="/insiders" />
          </Card>

          <SectionHeader id="bounce" icon={Crosshair} title="Rebotes técnicos (Bounce)"
            subtitle="RSI2 extremo + confirmación multi-indicador, para trades de 1–3 DÍAS." />
          <Card>
            <p className="mb-3">
              Esta sección es <b>más técnica y más arriesgada</b> que Value, y de horizonte mucho más corto: 1–3 días, no semanas. Dos tipos de señal:
            </p>
            <ul className="list-disc pl-5 space-y-1.5 text-sm mb-3">
              <li><b>Rebote con convicción:</b> caída técnica en empresa fundamentalmente sólida — tamaño normal, puede convertirse en posición.</li>
              <li><b>Rebote técnico puro:</b> solo señales técnicas, sin respaldo fundamental — tamaño pequeño, objetivo +5–7%, stop ajustado.</li>
            </ul>
            <p className="text-sm text-muted-foreground mb-3">
              Úsala solo si ya dominas stops y tamaño de posición. No es el core del sistema.
            </p>
            <OpenLink to="/bounce" />
          </Card>

          <SectionHeader id="mi-cartera" icon={Wallet} title="Mi cartera"
            subtitle="Tus posiciones + histórico de señales dadas por el sistema." />
          <Card>
            <p className="mb-3">
              Dos pestañas:
            </p>
            <ul className="list-disc pl-5 space-y-1.5 text-sm mb-3">
              <li><b>Mis posiciones:</b> carga tu cartera manual (persiste local). El sistema la cruza con Cerebro para avisarte de exits.</li>
              <li><b>Historial de señales:</b> todas las recomendaciones pasadas con performance 7d/14d/30d. Útil para validar el sistema.</li>
            </ul>
            <OpenLink to="/my-portfolio" />
          </Card>

          <SectionHeader id="owner-earnings" icon={Calculator} title="Owner Earnings"
            subtitle="Valoración estilo Buffett — FCF real, no beneficio contable." />
          <Card>
            <p className="mb-3">
              Calcula <b>Owner Earnings</b> (FCF ajustado a capex de mantenimiento) y compara con el precio actual. Da tres precios objetivo:
            </p>
            <ul className="list-disc pl-5 space-y-1.5 text-sm mb-3">
              <li><b>DCF conservador</b> (crecimiento perpetuo bajo).</li>
              <li><b>Múltiplo P/E histórico</b>.</li>
              <li><b>Target analistas</b> (mediana).</li>
            </ul>
            <p className="text-sm text-muted-foreground">
              Usa esta herramienta cuando ya tengas un ticker candidato y quieras confirmar margen de seguridad.
            </p>
            <div className="mt-3"><OpenLink to="/owner-earnings" /></div>
          </Card>

          <SectionHeader id="buscar" icon={Search} title="Buscar ticker"
            subtitle="Ficha completa individual — el lugar para investigar cualquier empresa a fondo." />
          <Card>
            <p className="mb-3">Busca por ticker o nombre. La ficha muestra:</p>
            <ul className="list-disc pl-5 space-y-1.5 text-sm mb-3">
              <li><b>Resumen:</b> precio, market cap, sector, descripción.</li>
              <li><b>Salud financiera:</b> current ratio, debt/equity, operating margin, interest coverage, FCF/share, payout ratio.</li>
              <li><b>Scores:</b> value, momentum, fundamental, piotroski, greenblatt, VCP.</li>
              <li><b>Earnings:</b> fecha, warning si faltan &lt;7 días, catalyst si hay actualización positiva.</li>
              <li><b>Tesis generada por IA</b> + comparativa con pares del sector.</li>
            </ul>
            <OpenLink to="/search" />
          </Card>

          <SectionHeader id="entry-setups" icon={TrendingUp} title="Entry setups"
            subtitle="Patrones técnicos combinados — catalizadores, VCP y mean reversion en un solo lugar." />
          <Card>
            <p className="mb-3">Cuatro pestañas:</p>
            <ul className="list-disc pl-5 space-y-1.5 text-sm mb-3">
              <li><b>Catalizadores:</b> filtros sobre el universo curado — por ejemplo "upside en zona dorada" (10–25%), earnings próximos, etc.</li>
              <li><b>Mean Reversion:</b> soporte, volumen y RSI para rebotes en el universo curado (Oversold Bounce, Bull Flag Pullback).</li>
              <li><b>Momentum VCP:</b> Volatility Contraction Pattern estilo Minervini — tendencias Stage 2 confirmadas.</li>
              <li><b>Universo Ampliado:</b> el mismo escaneo de rebotes técnicos pero sobre el S&amp;P 500 completo, no solo el universo curado — con objetivo y stop fijos (+4% / −2.5%) para que target y stop caigan siempre del lado correcto del precio.</li>
            </ul>
            <p className="text-sm text-muted-foreground">
              Todo setup publicado pasa antes por un validador que descarta configuraciones imposibles: objetivo por debajo del precio, stop por encima de la entrada, o riesgo/beneficio por debajo de 1:1.
            </p>
            <div className="mt-3"><OpenLink to="/entry-setups" /></div>
          </Card>

          <SectionHeader id="leaps" icon={Rocket} title="LEAPS deep-ITM"
            subtitle="Calls largas (2027-2028) muy dentro de dinero — sustituto apalancado de comprar la acción." />
          <Card>
            <p className="mb-3">
              No es especulación con opciones: es una forma de tener la MISMA exposición que comprar acciones de una empresa de calidad, con menos capital inmovilizado
              (delta 0.70–0.92, vencimiento &gt;13 meses). El "riesgo" real es perder la prima si la tesis se rompe del todo antes del vencimiento.
            </p>
            <p className="font-semibold mb-1 text-sm">Cada oportunidad viene clasificada por situación</p>
            <ul className="list-disc pl-5 space-y-1.5 text-sm mb-3">
              <li><b>Caída circunstancial:</b> ha caído desde máximos pero los fundamentales parecen intactos.</li>
              <li><b>Calidad a buen precio:</b> no se ha disparado, cotiza a múltiplo razonable — no es "barata por pánico", es calidad a precio justo.</li>
              <li><b>Dip de ganador:</b> ha subido mucho en el año y ahora corrige.</li>
            </ul>
            <p className="text-sm mb-3">
              <b>Ventaja neta:</b> compara el contrato con comprar la acción directamente, descontando YA el coste de cruzar el spread de compra/venta ida y vuelta —
              un apalancamiento bruto grande puede quedar en casi nada (o negativo) una vez se resta ese coste real.
            </p>
            <p className="text-sm text-muted-foreground">
              Cada contrato mostrado ya pasó el filtro de Claude (ver <a href="#agente-leaps" className="text-primary hover:underline">LEAPS Analyzer</a>) — lo que no se verifica explícitamente como oportunidad razonable no llega a mostrarse, no se marca solo con un aviso.
            </p>
            <div className="mt-3"><OpenLink to="/leaps" /></div>
          </Card>

          <SectionHeader id="options" icon={Activity} title="Options flow"
            subtitle="Flujo de opciones inusual — institucionales posicionándose." />
          <Card>
            <p className="mb-3">
              Detecta <b>volumen de opciones muy por encima de la media</b>, diferenciando alcista (calls) vs bajista (puts).
              Útil como confirmación cruzada — NO como señal aislada.
            </p>
            <OpenLink to="/options" />
          </Card>

          <SectionHeader id="sectores" icon={PieChart} title="Sectores"
            subtitle="Rotación sectorial — qué sectores están fuertes o en corrección." />
          <Card>
            <p className="mb-3">
              El sistema usa rotación <b>contrarian</b>: penaliza sectores sobrecalentados y premia los temporalmente caídos (si los fundamentales aguantan).
            </p>
            <OpenLink to="/sectors" />
          </Card>

          <SectionHeader id="alertas" icon={Bell} title="Alertas"
            subtitle="Configura notificaciones por email cuando se cumplan condiciones." />
          <Card>
            <p className="mb-3">Tipos de alerta soportados:</p>
            <ul className="list-disc pl-5 space-y-1.5 text-sm mb-3">
              <li>Precio &gt; / &lt; umbral.</li>
              <li>Nueva señal VALUE o MOMENTUM en un ticker.</li>
              <li>Cambio de grade (ej. de B a A).</li>
              <li>Insider buying detectado.</li>
            </ul>
            <OpenLink to="/alerts" />
          </Card>

          <SectionHeader id="calendario" icon={CalendarDays} title="Calendario earnings + catalizadores"
            subtitle="Cuándo presentan resultados tus posiciones." />
          <Card>
            <p className="mb-3">
              Dos pestañas: <b>Earnings</b> (próximos 30 días) y <b>Catalysts</b> (FDA, PDUFA, M&amp;A, spin-offs conocidos).
              Filtra por "solo mi cartera" para no ver ruido.
            </p>
            <OpenLink to="/earnings" />
          </Card>

          <SectionHeader id="dividend-traps" icon={AlertTriangle} title="Dividend traps"
            subtitle="Empresas con dividend yield alto pero que están a punto de recortarlo." />
          <Card>
            <p className="mb-3">
              Un yield del 10% no es un regalo — normalmente significa que el mercado descuenta un recorte. Esta sección detecta:
            </p>
            <ul className="list-disc pl-5 space-y-1.5 text-sm">
              <li>Payout ratio &gt; 90% (no sostenible).</li>
              <li>FCF insuficiente para cubrir dividendo.</li>
              <li>Deuda creciente + payout alto.</li>
              <li>Revenue decreciendo + payout alto.</li>
            </ul>
            <div className="mt-3"><OpenLink to="/dividend-traps" /></div>
          </Card>

          <SectionHeader id="position-sizing" icon={Ruler} title="Position sizing"
            subtitle="Cuánto invertir en cada posición según el criterio de Kelly." />
          <Card>
            <p className="mb-3">
              Introduce el tamaño de tu cartera y la tabla calcula cuánto asignar a cada oportunidad en base a:
            </p>
            <ul className="list-disc pl-5 space-y-1.5 text-sm">
              <li><b>Convicción</b> (grade A = más peso).</li>
              <li><b>Volatilidad</b> histórica.</li>
              <li><b>Kelly fraccionado</b> (normalmente 25% del Kelly óptimo — más conservador).</li>
            </ul>
            <div className="mt-3"><OpenLink to="/position-sizing" /></div>
          </Card>

          <SectionHeader id="backtest" icon={FlaskConical} title="Backtest"
            subtitle="Simulador histórico — ¿habría funcionado la estrategia en el pasado?" />
          <Card>
            <p className="mb-3">
              Ejecuta la estrategia actual contra 1–5 años de datos históricos. Muestra:
            </p>
            <ul className="list-disc pl-5 space-y-1.5 text-sm">
              <li>Curva de equity vs S&amp;P 500.</li>
              <li>Drawdown máximo.</li>
              <li>Win rate, profit factor, Sharpe.</li>
              <li>Trades individuales con entry/exit.</li>
            </ul>
            <div className="mt-3"><OpenLink to="/backtest" /></div>
          </Card>

          <SectionHeader id="comparar" icon={Shuffle} title="Comparar tickers"
            subtitle="Tabla side-by-side de métricas clave." />
          <Card>
            <p className="mb-3">
              Añade hasta 5 tickers y compara ROE, márgenes, FCF, growth, múltiplos y scores del sistema. Útil para decidir entre opciones similares.
            </p>
            <OpenLink to="/compare" />
          </Card>

          <SectionHeader id="datos" icon={Database} title="Exportar datos"
            subtitle="Descarga los CSVs crudos." />
          <Card>
            <p className="mb-3">
              Puedes descargar cualquier dataset (value_opportunities, fundamental_scores, insiders, etc.) en formato CSV.
              Útil para análisis propio en Excel / Python.
            </p>
            <OpenLink to="/datos" />
          </Card>

          <SectionHeader id="bonos" icon={Landmark} title="Bonos & Preferentes"
            subtitle="Renta fija y acciones preferentes con rating VALUE." />
          <Card>
            <p className="mb-3">
              La sección Bonos tiene dos partes diferenciadas:
            </p>
            <ul className="list-disc pl-5 space-y-2 text-sm mb-4">
              <li><b>ETFs de bonos</b> — 21 ETFs clasificados por tipo: T-Bills (BIL, SGOV, SHV), Treasury corto (VGSH, SHY), TIPS, IG Corp, High Yield, EUR Govt, EUR IG y EM. Cada uno muestra yield actual, duración, distancia al máximo 52w y rating VALUE (Muy atractivo → Neutral → Caro).</li>
              <li><b>Calculadora de rendimiento</b> — introduce capital y plazo (1m hasta 3 años) y el sistema calcula ganancia, capital final y yield del período por instrumento, usando interés compuesto mensual.</li>
              <li><b>Acciones preferentes</b> — instrumentos híbridos: pagan dividendo fijo como un bono ($25 par, NYSE) pero cotizan como acciones. Ventajas: senior al accionista común, yield 6-8%, sin vencimiento fijo. Riesgo principal: si el precio sube por encima del par ($25) la empresa puede rescatarlas (call risk).</li>
            </ul>
            <div className="bg-muted/20 rounded p-3 text-sm text-muted-foreground space-y-1">
              <p><b>¿Por qué estas preferentes ahora?</b> La Fed subió tipos 0→5.5% en 2022-2023. Las preferentes con cupón del 5.5-6% bajaron de $25 a $18-19 porque los bonos del tesoro pagaban lo mismo. Ahora compras $25 de valor a $18-19 y cobras 7-8% anual. Si los tipos bajan, el precio sube de vuelta hacia $25 (+30% de plusvalía adicional).</p>
            </div>
            <OpenLink to="/bonds" />
          </Card>

          {/* ──────────────── Agents ──────────────── */}

          <h2 className="text-lg font-bold uppercase tracking-widest text-muted-foreground/60 mt-10 mb-4 pb-1 border-b border-border/30">
            Agentes del pipeline
          </h2>

          <SectionHeader id="agentes-overview" icon={Bot} title="Visión general"
            subtitle="Qué agentes corren cada día y en qué orden." />
          <Card>
            <p className="mb-3">
              Cada noche (y varias veces al día) GitHub Actions ejecuta el pipeline en este orden:
            </p>
            <ol className="list-decimal pl-5 space-y-1.5 text-sm mb-3 font-mono text-[0.82rem]">
              <li>sector_rotation</li>
              <li>mean_reversion</li>
              <li>super_score_integrator</li>
              <li>ai_quality_filter</li>
              <li>entry_exit</li>
              <li>thesis_generator</li>
              <li>super_dashboard_generator</li>
              <li>portfolio_tracker</li>
              <li>ticker_data_cache</li>
            </ol>
            <p className="text-sm text-muted-foreground">
              Cada agente produce un CSV que el siguiente lee. Si un agente falla, los siguientes usan el dato del día anterior.
            </p>
          </Card>

          <SectionHeader id="agente-fundamental" icon={Bot} title="Fundamental scorer" />
          <Card>
            <p className="mb-2"><b>Qué hace:</b> descarga datos de yfinance (balance, cuenta de resultados, cash flow) y calcula scores fundamentales.</p>
            <p className="mb-2"><b>Output:</b> <code className="bg-muted/30 px-1 rounded">docs/fundamental_scores.csv</code></p>
            <p className="text-sm text-muted-foreground">
              Calcula ROE, debt/equity, operating margin, FCF yield, payout ratio, Piotroski, Greenblatt ROIC, etc.
              Si un dato falta, el campo queda vacío — <u>nunca inventa un valor</u>.
            </p>
          </Card>

          <SectionHeader id="agente-super-score" icon={Bot} title="Super Score Integrator" />
          <Card>
            <p className="mb-2"><b>Qué hace:</b> combina fundamentales + insiders + opciones + sector + mean reversion + ML en un <code className="bg-muted/30 px-1 rounded">value_score</code> final (0–100).</p>
            <p className="mb-3"><b>Output:</b> <code className="bg-muted/30 px-1 rounded">docs/value_opportunities.csv</code> + <code className="bg-muted/30 px-1 rounded">momentum_opportunities.csv</code></p>
            <p className="font-semibold mb-1 text-sm">Pesos aproximados del value_score:</p>
            <ul className="list-disc pl-5 space-y-0.5 text-sm mb-3">
              <li>Fundamentales: 40 pts (solo si no es el valor por defecto 50).</li>
              <li>Profitability bonus: 15 pts.</li>
              <li>Insiders: 15 pts.</li>
              <li>Institucional: 15 pts.</li>
              <li>Options flow: 10 pts.</li>
              <li>Sector rotation contrarian: 10 pts.</li>
              <li>Mean reversion: 10 pts.</li>
              <li>FCF yield bonus: hasta +8 pts (negativo: −5).</li>
              <li>Dividend quality: +5 pts.</li>
              <li>Buyback activo: +3 pts.</li>
              <li>Analyst revision momentum: ±5 pts.</li>
              <li>Earnings &lt; 7 días: −5 pts.</li>
              <li>R:R: ±3 pts.</li>
            </ul>
            <p className="text-sm mb-2"><b>Hard rejects (value_score = 0):</b></p>
            <ul className="list-disc pl-5 space-y-0.5 text-sm">
              <li>ROE negativo.</li>
              <li>Upside analista negativo (sobrevalorado).</li>
              <li>Upside analista ≥ 30% — value trap: 0% de acierto medido en señales reales por encima de ese umbral.</li>
            </ul>
          </Card>

          <SectionHeader id="agente-ai-filter" icon={Bot} title="AI Quality Filter" />
          <Card>
            <p className="mb-2"><b>Qué hace:</b> un LLM (Groq + Llama) lee cada oportunidad y descarta las que tienen red flags cualitativos no capturables con números (fraude histórico, regulación pendiente, tesis contradictoria).</p>
            <p className="mb-2"><b>Output:</b> <code className="bg-muted/30 px-1 rounded">docs/value_opportunities_filtered.csv</code></p>
            <p className="mb-2 text-sm">
              <b>Después</b>, Claude audita la plausibilidad de los datos de cada pick que sobrevive (precio/target/upside/ROE coherentes entre sí para esa empresa concreta).
              Este paso es un filtro de verdad, no un aviso: solo se publica lo que Claude confirma explícitamente — si no puede verificarlo (sin saldo, fallo de API, respuesta rara), el pick se queda fuera hasta la siguiente ejecución, igual que si lo hubiera rechazado.
            </p>
            <p className="text-sm text-muted-foreground">El Dashboard muestra por defecto los <i>filtrados</i> (más estrictos). En Value US / EU puedes cambiar al listado completo.</p>
          </Card>

          <SectionHeader id="agente-thesis" icon={Bot} title="Thesis Generator" />
          <Card>
            <p className="mb-2"><b>Qué hace:</b> genera la tesis de inversión en lenguaje natural (2–4 párrafos) para cada ticker con grade A/B.</p>
            <p className="text-sm text-muted-foreground">Aparece al expandir una fila en VALUE o en la ficha del ticker. Combina: qué hace la empresa, por qué está barata, catalizadores, riesgos.</p>
          </Card>

          <SectionHeader id="agente-entry-exit" icon={Bot} title="Entry/Exit Calculator" />
          <Card>
            <p className="mb-2"><b>Qué hace:</b> calcula <b>entry price</b>, <b>stop loss</b> (típicamente 8%) y <b>target price</b> para cada oportunidad basado en soporte técnico, volatilidad y upside analista.</p>
            <p className="text-sm text-muted-foreground">Verás estos 3 precios en la conviction panel de VALUE.</p>
          </Card>

          <SectionHeader id="agente-mean-rev" icon={Bot} title="Mean Reversion Detector" />
          <Card>
            <p className="mb-2"><b>Qué hace:</b> detecta acciones que han caído lejos de su media móvil con volumen capitulatorio — candidatas a rebote.</p>
            <p className="text-sm text-muted-foreground">Usa z-score sobre el return de 20 días + ratio de volumen.</p>
          </Card>

          <SectionHeader id="agente-bounce" icon={Bot} title="Bounce Trader" />
          <Card>
            <p className="mb-2"><b>Qué hace:</b> versión más táctica del mean reversion, orientada a trades de 1–4 semanas con stops ajustados. Se conecta a Interactive Brokers (TWS) para ejecutar.</p>
            <p className="text-sm text-muted-foreground">Soporta modo paper (cuenta de simulación) y modo real (<code className="bg-muted/30 px-1 rounded">--live</code>, con confirmación explícita antes de mandar una orden real) — cuál esté activo depende de cómo se lance, no es fijo.</p>
          </Card>

          <SectionHeader id="agente-insiders" icon={Bot} title="Insider Scanners (US + EU)" />
          <Card>
            <p className="mb-2"><b>Qué hace:</b> dos scrapers — uno para SEC Form 4 (US) y otro para regulatory filings europeos (nl.ts para Holanda, etc.).</p>
            <p className="text-sm text-muted-foreground">
              Normaliza importe, rol (CEO &gt; CFO &gt; director), cluster buys. Calcula <code className="bg-muted/30 px-1 rounded">confidence_score</code> que ves en la app.
            </p>
          </Card>

          <SectionHeader id="agente-options" icon={Bot} title="Options Flow Detector" />
          <Card>
            <p className="mb-2"><b>Qué hace:</b> detecta volumen de opciones inusual (&gt; 3× media) con preferencia direccional clara.</p>
            <p className="text-sm text-muted-foreground">Put/call ratio, unusual calls / puts, sentiment score. Alimenta el <code className="bg-muted/30 px-1 rounded">value_score</code> con 10 pts.</p>
          </Card>

          <SectionHeader id="agente-sector" icon={Bot} title="Sector Rotation" />
          <Card>
            <p className="mb-2"><b>Qué hace:</b> clasifica los 11 sectores GICS en expansión / contracción / neutral vs índice.</p>
            <p className="text-sm text-muted-foreground">La lógica es contrarian: un sector en corrección leve suma puntos; un sector sobrecalentado resta.</p>
          </Card>

          <SectionHeader id="agente-macro" icon={Bot} title="Macro / Country Scanner" />
          <Card>
            <p className="mb-2"><b>Qué hace:</b> agrega datos macroeconómicos por país (PIB, inflación, política monetaria, deuda/PIB) y clasifica regímenes.</p>
            <p className="text-sm text-muted-foreground">Usado por la sección Macro Radar. Basado en frameworks de Dalio (ciclo de deuda largo/corto) + soberanía monetaria.</p>
          </Card>

          <SectionHeader id="agente-catalyst" icon={Bot} title="Catalyst Scanner" />
          <Card>
            <p className="mb-2"><b>Qué hace:</b> extrae fechas de eventos conocidos — earnings, FDA / PDUFA (farma), spin-offs, M&amp;A pendientes.</p>
            <p className="text-sm text-muted-foreground">Salidas en la pestaña Catalysts del Calendario.</p>
          </Card>

          <SectionHeader id="agente-portfolio" icon={Bot} title="Portfolio Tracker" />
          <Card>
            <p className="mb-2"><b>Qué hace:</b> guarda cada recomendación hecha por el sistema con su fecha y score, y calcula el return 7d/14d/30d después.</p>
            <p className="mb-2"><b>Output:</b> <code className="bg-muted/30 px-1 rounded">docs/portfolio_tracker/recommendations.csv</code> + <code className="bg-muted/30 px-1 rounded">summary.json</code></p>
            <p className="text-sm text-muted-foreground">Alimenta el widget "Portfolio win rate" del Dashboard. También la pestaña Historial de señales.</p>
          </Card>

          <SectionHeader id="agente-leaps" icon={Bot} title="LEAPS Analyzer" />
          <Card>
            <p className="mb-2"><b>Qué hace:</b> escanea la cadena de opciones del universo de calidad buscando calls deep-ITM (delta 0.70–0.92, vencimiento &gt;13 meses) como sustituto apalancado de la acción — nunca sobre empresas con upside ≥30% (mismo hard-reject de value trap que VALUE).</p>
            <p className="mb-2"><b>Output:</b> <code className="bg-muted/30 px-1 rounded">docs/leaps_opportunities.json</code></p>
            <p className="text-sm text-muted-foreground">
              Claude verifica cada contrato antes de publicarlo (coherencia de los datos + veredicto oportunidad/razonable/evitar). Es un filtro real: lo que no pasa no se muestra,
              igual que en <a href="#agente-ai-filter" className="text-primary hover:underline">AI Quality Filter</a> — no queda como aviso pegado a una fila que se sigue publicando.
            </p>
          </Card>

          <SectionHeader id="agente-why-cheap" icon={Bot} title="Why Cheap" />
          <Card>
            <p className="mb-2"><b>Qué hace:</b> responde la pregunta que decide una compra value — ¿por qué está barata esta empresa? Busca en fuentes reales (resultados, guidance, noticias) y clasifica la caída en una de cuatro categorías.</p>
            <ul className="list-disc pl-5 space-y-0.5 text-sm mb-2">
              <li><b>Deterioro:</b> el negocio está peor de verdad (guidance retirada, márgenes cayendo, pérdida de cuota). Único veredicto que descarta el pick.</li>
              <li><b>Cíclico:</b> el sector está en la parte baja de su ciclo, el negocio aguanta.</li>
              <li><b>Evento:</b> shock puntual y acotado, ya conocido y cuantificable.</li>
              <li><b>Sentimiento:</b> rotación, múltiplos o macro — nada específico de la empresa.</li>
            </ul>
            <p className="text-sm text-muted-foreground">
              Sin búsquedas reales detrás del veredicto, sale "sin datos" — nunca vetando ni respaldando por descarte. Solo se gasta en candidatos que ya tendrían sentido comprar (score suficiente y caída real que explicar).
            </p>
          </Card>

          <SectionHeader id="agente-ml-scorer" icon={Bot} title="ML Win Predictor" />
          <Card>
            <p className="mb-2"><b>Qué hace:</b> entrena un modelo XGBoost calibrado (isotonic) cada día sobre el historial completo de señales VALUE del Portfolio Tracker (1.497+ señales con outcome verificado) y predice la probabilidad real de ganar para cada ticker del universo.</p>
            <p className="mb-2"><b>Output:</b> <code className="bg-muted/30 px-1 rounded">docs/ml_win_probability.json</code> — alimenta <code className="bg-muted/30 px-1 rounded">ml_win_probability</code>/<code className="bg-muted/30 px-1 rounded">ml_win_label</code> y el campo <code className="bg-muted/30 px-1 rounded">ml_score</code> (0-100) del Super Score Integrador.</p>
            <div className="mt-3 space-y-2 text-sm">
              <p className="font-semibold text-foreground/80">Rendimiento del modelo (cross-validation 5-fold):</p>
              <div className="grid grid-cols-2 gap-2">
                <div className="bg-emerald-500/10 border border-emerald-500/20 rounded p-2 text-center">
                  <div className="text-emerald-400 font-bold text-lg">0.88</div>
                  <div className="text-muted-foreground text-xs">ROC-AUC</div>
                </div>
                <div className="bg-emerald-500/10 border border-emerald-500/20 rounded p-2 text-center">
                  <div className="text-emerald-400 font-bold text-lg">0.13</div>
                  <div className="text-muted-foreground text-xs">Brier Score (calibración)</div>
                </div>
              </div>
              <p className="font-semibold text-foreground/80 mt-3">Features por orden de importancia:</p>
              <ul className="space-y-1 text-muted-foreground">
                <li><span className="text-cyan-400 font-medium">1. Régimen × Sector</span> — 12.5% · el régimen de mercado no afecta igual a todos los sectores</li>
                <li><span className="text-cyan-400 font-medium">2. Régimen de mercado</span> — 12.4% · CONFIRMED_UPTREND vs UPTREND_PRESSURE marca la diferencia</li>
                <li><span className="text-cyan-400 font-medium">3. Win rate del sector</span> — 8.8% · historial de acierto por sector, no solo el sector en sí</li>
                <li><span className="text-cyan-400 font-medium">4. FCF Yield %</span> — 8.1% · empresas con caja real ganan más</li>
                <li><span className="text-cyan-400 font-medium">5. Analyst Upside %</span> — 7.9% · el consenso de analistas tiene peso real</li>
              </ul>
              <p className="font-semibold text-foreground/80 mt-3">Win rate histórico por sector:</p>
              <ul className="space-y-1 text-muted-foreground">
                <li>• Sectores ganadores: Energy 71%, Communication Services 48%, Technology 35%</li>
                <li>• Sectores perdedores: Consumer Cyclical 9%, Basic Materials 12% — el modelo los penaliza automáticamente</li>
              </ul>
            </div>
          </Card>

          <SectionHeader id="agente-cerebro" icon={Bot} title="Cerebro (orquestador)" />
          <Card>
            <p className="mb-2"><b>Qué hace:</b> cuando todos los agentes anteriores han terminado, Cerebro cruza sus outputs para detectar:</p>
            <ul className="list-disc pl-5 space-y-1 text-sm mb-2">
              <li>Convergencias (mismo ticker aparece en &gt;2 listas).</li>
              <li>Entradas sugeridas para hoy.</li>
              <li>Exits en tu cartera.</li>
              <li>Value traps nuevas.</li>
              <li>Alertas de calidad decayente.</li>
            </ul>
            <p className="text-sm text-muted-foreground">Es el agente más "inteligente" — el único que toma decisiones cruzando fuentes, no solo puntuando una.</p>
          </Card>

          {/* ──────────────── Glossary + FAQ ──────────────── */}

          <h2 className="text-lg font-bold uppercase tracking-widest text-muted-foreground/60 mt-10 mb-4 pb-1 border-b border-border/30">
            Glosario y ayuda
          </h2>

          <SectionHeader id="glosario" icon={Shield} title="Glosario" />
          <Card>
            <dl className="text-sm space-y-3">
              <div><dt className="font-bold">FCF (Free Cash Flow)</dt><dd className="text-muted-foreground">Caja que genera el negocio después de capex. El flujo que Buffett mira: si es positivo y creciente, la empresa gana dinero de verdad.</dd></div>
              <div><dt className="font-bold">FCF yield</dt><dd className="text-muted-foreground">FCF / market cap. &gt; 5% es sólido, &gt; 8% excelente, negativo = red flag.</dd></div>
              <div><dt className="font-bold">ROE (Return on Equity)</dt><dd className="text-muted-foreground">Beneficio / patrimonio. Mide rentabilidad sobre el capital. Negativo = el sistema descarta automáticamente.</dd></div>
              <div><dt className="font-bold">ROIC (Greenblatt)</dt><dd className="text-muted-foreground">EBIT / capital empleado. Mejor que ROE porque no depende de cómo se financie la empresa.</dd></div>
              <div><dt className="font-bold">PEG ratio</dt><dd className="text-muted-foreground">P/E dividido por crecimiento esperado. &lt; 1 = GARP (growth a precio razonable).</dd></div>
              <div><dt className="font-bold">Piotroski F-Score (0–9)</dt><dd className="text-muted-foreground">9 criterios binarios de calidad financiera (rentabilidad, solvencia, eficiencia). ≥ 7 es fuerte.</dd></div>
              <div><dt className="font-bold">VCP (Volatility Contraction Pattern)</dt><dd className="text-muted-foreground">Patrón técnico Minervini — tres contracciones de volatilidad cada vez más pequeñas antes de breakout.</dd></div>
              <div><dt className="font-bold">Trend Template (0–8)</dt><dd className="text-muted-foreground">8 criterios Minervini de tendencia alcista sostenida (precio &gt; MA50 &gt; MA150 &gt; MA200, etc.).</dd></div>
              <div><dt className="font-bold">R:R (Risk/Reward)</dt><dd className="text-muted-foreground">Upside al target / downside al stop. En rebotes técnicos, el sistema exige mínimo 1:1 para publicar el setup — arriesgar más de lo que se puede ganar no se muestra. En VALUE, un R:R muy alto no es señal de calidad por sí solo: mira la <b>zona de upside</b>, no este ratio suelto.</dd></div>
              <div><dt className="font-bold">Zona dorada de upside</dt><dd className="text-muted-foreground">[10%, 25%) de distancia al precio objetivo del consenso. Es la única banda con acierto alto medido sobre señales reales (83%). Por debajo, poco margen; por encima del 30%, value trap (0% de acierto) — ver <a href="#filosofia" className="text-primary hover:underline">Filosofía</a>.</dd></div>
              <div><dt className="font-bold">Why cheap (deterioro / cíclico / evento / sentimiento)</dt><dd className="text-muted-foreground">Clasificación de por qué cayó el precio, verificada con búsquedas reales. Solo "deterioro" descarta — las otras tres son caídas que no vienen de que el negocio se rompa.</dd></div>
              <div><dt className="font-bold">Stage 2 (Weinstein)</dt><dd className="text-muted-foreground">Fase de tendencia alcista confirmada — la única fase donde se compran momentum setups.</dd></div>
              <div><dt className="font-bold">Cluster buy (insiders)</dt><dd className="text-muted-foreground">Varios directivos comprando en días cercanos. Señal mucho más fuerte que compra aislada.</dd></div>
              <div><dt className="font-bold">Value trap</dt><dd className="text-muted-foreground">Empresa "barata" por una razón estructural: industria en declive, fraude, deuda excesiva. Evitar.</dd></div>
              <div><dt className="font-bold">Grade A / B / C / D</dt><dd className="text-muted-foreground">Conviction grade del filtro IA. A = alta convicción, D = evitar.</dd></div>
              <div><dt className="font-bold">Kelly criterion</dt><dd className="text-muted-foreground">Fórmula óptima de sizing dado edge y odds. La app usa 25% del Kelly completo (más conservador).</dd></div>
            </dl>
          </Card>

          <SectionHeader id="faq" icon={HelpCircle} title="Preguntas frecuentes" />
          <Card>
            <div className="space-y-4 text-sm">
              <div>
                <p className="font-bold mb-1">¿Por qué el Dashboard dice "0 oportunidades momentum"?</p>
                <p className="text-muted-foreground">Porque estamos en régimen CORRECTION o BEAR. Durante correcciones el sistema espera a que se confirmen tendencias Stage 2 — es el comportamiento correcto. Cero señales &gt; señales falsas.</p>
              </div>
              <div>
                <p className="font-bold mb-1">Un ticker tiene ROE −12% pero aparece en VALUE. ¿Por qué?</p>
                <p className="text-muted-foreground">No debería — si lo ves, es un bug. Reporta el ticker. La regla es: ROE negativo = descarte automático (value_score = 0).</p>
              </div>
              <div>
                <p className="font-bold mb-1">¿Qué pasa si un dato falla (rate limit de yfinance, por ejemplo)?</p>
                <p className="text-muted-foreground">El sistema <u>no penaliza ni inventa</u>. Deja el campo vacío y no puntúa esa dimensión. Por eso verás a veces empresas con score bajo pero "Datos en vivo" — significa que hubo datos faltantes en la última corrida.</p>
              </div>
              <div>
                <p className="font-bold mb-1">¿Puedo confiar ciegamente en las recomendaciones?</p>
                <p className="text-muted-foreground">No. El sistema es una ayuda de decisión, no un sustituto. Siempre lee la tesis, revisa los red flags de la conviction panel, y comprueba que encaja con tu horizonte y tolerancia al riesgo.</p>
              </div>
              <div>
                <p className="font-bold mb-1">¿Cada cuánto se actualizan los datos?</p>
                <p className="text-muted-foreground">El pipeline completo corre cada madrugada (UTC). Algunos subsistemas (portfolio news) se refrescan cada 6h. Si el banner "Datos en vivo" no aparece hoy, el pipeline ha fallado.</p>
              </div>
              <div>
                <p className="font-bold mb-1">¿Dónde se guarda mi cartera?</p>
                <p className="text-muted-foreground">Tu cartera personal se sincroniza con tu cuenta (Supabase). Las preferencias locales (modo, filtros) viven en el navegador y no se sincronizan entre dispositivos.</p>
              </div>
              <div>
                <p className="font-bold mb-1">¿Qué hago si encuentro un error?</p>
                <p className="text-muted-foreground">Anota el ticker, la sección y la hora. Escríbeme y miramos el log del pipeline — casi todo tiene causa identificable.</p>
              </div>
            </div>
          </Card>

          <div className="mt-12 mb-8 text-center text-xs text-muted-foreground/60">
            Stock Analyzer — Value/GARP investing, estilo Lynch. Consistencia &gt; héroes.
          </div>
        </article>
      </div>
    </div>
  )
}
