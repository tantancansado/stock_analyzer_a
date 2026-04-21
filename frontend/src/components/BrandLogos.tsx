interface LogoProps {
  readonly size?: number
  readonly className?: string
  readonly title?: string
}

// ── 1. CANDLE BULL ──────────────────────────────────────────────────────────
// Vela japonesa alcista + flecha que se dibuja cada ~4s. Glow "respirando".
export function LogoCandleBull({ size = 36, className = '', title = 'Stock Analyzer' }: Readonly<LogoProps>) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" className={className} aria-label={title} role="img">
      <defs>
        <linearGradient id="candleBullGrad" x1="0" y1="1" x2="0" y2="0">
          <stop offset="0%" stopColor="hsl(162 85% 45%)" />
          <stop offset="100%" stopColor="hsl(194 100% 48%)" />
        </linearGradient>
        <filter id="candleBullGlow">
          <feGaussianBlur stdDeviation="1.2" result="b" />
          <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
        <style>{`
          @keyframes candleBullBreathe { 0%,100% { opacity: 0.35; } 50% { opacity: 0.9; } }
          @keyframes candleBullDraw { 0% { stroke-dashoffset: 44; } 45% { stroke-dashoffset: 0; } 90% { stroke-dashoffset: 0; opacity: 1; } 100% { stroke-dashoffset: 0; opacity: 0; } }
          .cb-glow { animation: candleBullBreathe 3.2s ease-in-out infinite; transform-origin: center; }
          .cb-arrow { stroke-dasharray: 44; stroke-dashoffset: 44; animation: candleBullDraw 4s ease-in-out infinite; }
        `}</style>
      </defs>
      {/* Wick (mecha) */}
      <line x1="32" y1="8" x2="32" y2="16" stroke="url(#candleBullGrad)" strokeWidth="2" strokeLinecap="round" />
      <line x1="32" y1="48" x2="32" y2="56" stroke="url(#candleBullGrad)" strokeWidth="2" strokeLinecap="round" />
      {/* Body (cuerpo vela) — rectángulo afilado */}
      <rect x="20" y="16" width="24" height="32" rx="2" fill="url(#candleBullGrad)" opacity="0.15" stroke="url(#candleBullGrad)" strokeWidth="1.8" filter="url(#candleBullGlow)" />
      {/* Arrow up — se dibuja */}
      <g className="cb-arrow" stroke="hsl(194 100% 65%)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" fill="none">
        <path d="M 26 38 L 32 26 L 38 38" />
        <path d="M 32 26 L 32 42" />
      </g>
      {/* Glow breathing */}
      <rect className="cb-glow" x="18" y="14" width="28" height="36" rx="3" fill="none" stroke="hsl(194 100% 55%)" strokeWidth="0.6" opacity="0.35" />
    </svg>
  )
}

// ── 2. CHART PEAK ───────────────────────────────────────────────────────────
// Línea de chart que se dibuja progresivamente, con picos y valle. Loop.
export function LogoChartPeak({ size = 36, className = '', title = 'Stock Analyzer' }: Readonly<LogoProps>) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" className={className} aria-label={title} role="img">
      <defs>
        <linearGradient id="chartPeakGrad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="hsl(194 100% 48%)" />
          <stop offset="60%" stopColor="hsl(162 85% 50%)" />
          <stop offset="100%" stopColor="hsl(142 80% 55%)" />
        </linearGradient>
        <linearGradient id="chartPeakFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="hsl(194 100% 48%)" stopOpacity="0.35" />
          <stop offset="100%" stopColor="hsl(194 100% 48%)" stopOpacity="0" />
        </linearGradient>
        <style>{`
          @keyframes chartPeakDraw { 0% { stroke-dashoffset: 120; } 40% { stroke-dashoffset: 0; } 85% { stroke-dashoffset: 0; opacity: 1; } 100% { stroke-dashoffset: 0; opacity: 0.5; } }
          @keyframes chartPeakDotPulse { 0%,100% { r: 2.4; opacity: 1; } 50% { r: 4; opacity: 0.6; } }
          @keyframes chartPeakFillIn { 0% { opacity: 0; } 55% { opacity: 1; } 100% { opacity: 0.6; } }
          .cp-line { stroke-dasharray: 120; stroke-dashoffset: 120; animation: chartPeakDraw 4.5s ease-in-out infinite; }
          .cp-dot { animation: chartPeakDotPulse 1.6s ease-in-out infinite; }
          .cp-fill { opacity: 0; animation: chartPeakFillIn 4.5s ease-in-out infinite; }
        `}</style>
      </defs>
      {/* Border sutil afilado */}
      <rect x="4" y="4" width="56" height="56" rx="6" fill="none" stroke="hsl(194 100% 48% / 0.12)" strokeWidth="1" />
      {/* Gridlines */}
      <line x1="8" y1="48" x2="56" y2="48" stroke="hsl(194 100% 48% / 0.08)" strokeWidth="0.5" strokeDasharray="2 2" />
      <line x1="8" y1="32" x2="56" y2="32" stroke="hsl(194 100% 48% / 0.08)" strokeWidth="0.5" strokeDasharray="2 2" />
      {/* Fill bajo la línea */}
      <path className="cp-fill" d="M 8 44 L 18 36 L 26 42 L 36 22 L 46 30 L 56 14 L 56 52 L 8 52 Z" fill="url(#chartPeakFill)" />
      {/* Línea principal */}
      <path className="cp-line" d="M 8 44 L 18 36 L 26 42 L 36 22 L 46 30 L 56 14" fill="none" stroke="url(#chartPeakGrad)" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
      {/* Dot al final — pulse */}
      <circle className="cp-dot" cx="56" cy="14" r="2.4" fill="hsl(142 80% 55%)" />
    </svg>
  )
}

// ── 3. ORBIT ────────────────────────────────────────────────────────────────
// Núcleo pulsante + 2 órbitas + satélites que giran. "Radar de señales".
export function LogoOrbit({ size = 36, className = '', title = 'Stock Analyzer' }: Readonly<LogoProps>) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" className={className} aria-label={title} role="img">
      <defs>
        <radialGradient id="orbitCore" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0%" stopColor="hsl(194 100% 70%)" />
          <stop offset="60%" stopColor="hsl(194 100% 48%)" />
          <stop offset="100%" stopColor="hsl(194 100% 40% / 0)" />
        </radialGradient>
        <linearGradient id="orbitRing" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="hsl(194 100% 48%)" stopOpacity="0.7" />
          <stop offset="100%" stopColor="hsl(194 100% 48%)" stopOpacity="0.1" />
        </linearGradient>
        <style>{`
          @keyframes orbitSpin { to { transform: rotate(360deg); } }
          @keyframes orbitSpinRev { to { transform: rotate(-360deg); } }
          @keyframes orbitPulse { 0%,100% { r: 4; opacity: 1; } 50% { r: 6; opacity: 0.7; } }
          @keyframes orbitHalo { 0%,100% { opacity: 0.2; } 50% { opacity: 0.55; } }
          .o-ring-a { animation: orbitSpin 6s linear infinite; transform-origin: 32px 32px; }
          .o-ring-b { animation: orbitSpinRev 9s linear infinite; transform-origin: 32px 32px; }
          .o-core { animation: orbitPulse 2.2s ease-in-out infinite; transform-origin: center; }
          .o-halo { animation: orbitHalo 2.2s ease-in-out infinite; transform-origin: center; }
        `}</style>
      </defs>
      {/* Halo exterior */}
      <circle className="o-halo" cx="32" cy="32" r="28" fill="url(#orbitCore)" opacity="0.2" />
      {/* Órbita A (horizontal-ish) */}
      <g className="o-ring-a">
        <ellipse cx="32" cy="32" rx="24" ry="10" fill="none" stroke="url(#orbitRing)" strokeWidth="1.2" />
        <circle cx="56" cy="32" r="2.2" fill="hsl(162 85% 55%)" />
        <circle cx="8" cy="32" r="1.6" fill="hsl(194 100% 65%)" opacity="0.7" />
      </g>
      {/* Órbita B (diagonal) */}
      <g className="o-ring-b">
        <ellipse cx="32" cy="32" rx="10" ry="24" fill="none" stroke="url(#orbitRing)" strokeWidth="1.2" transform="rotate(45 32 32)" />
        <circle cx="32" cy="8" r="2" fill="hsl(210 100% 65%)" transform="rotate(45 32 32)" />
      </g>
      {/* Core pulsante */}
      <circle className="o-core" cx="32" cy="32" r="4" fill="url(#orbitCore)" />
      <circle cx="32" cy="32" r="2" fill="hsl(194 100% 85%)" />
    </svg>
  )
}

// ── BRAIN PULSE (Cerebro) ──────────────────────────────────────────────────
// Red neuronal: nodos pulsando + sinapsis que se encienden en cascada.
export function LogoBrainPulse({ size = 36, className = '', title = 'Cerebro' }: Readonly<LogoProps>) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" className={className} aria-label={title} role="img">
      <defs>
        <radialGradient id="bpNode" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0%" stopColor="hsl(271 91% 75%)" />
          <stop offset="100%" stopColor="hsl(271 91% 50% / 0)" />
        </radialGradient>
        <style>{`
          @keyframes bpNodeA { 0%,100% { r: 2.5; opacity: 1; } 50% { r: 4; opacity: 0.6; } }
          @keyframes bpNodeB { 0%,100% { r: 2; opacity: 0.7; } 50% { r: 3.2; opacity: 1; } }
          @keyframes bpSynapse { 0%,100% { stroke-dashoffset: 0; opacity: 0.25; } 50% { stroke-dashoffset: 12; opacity: 0.9; } }
          .bp-n1 { animation: bpNodeA 2.2s ease-in-out infinite; transform-origin: center; }
          .bp-n2 { animation: bpNodeB 2.8s ease-in-out infinite 0.3s; transform-origin: center; }
          .bp-n3 { animation: bpNodeA 2.5s ease-in-out infinite 0.6s; transform-origin: center; }
          .bp-n4 { animation: bpNodeB 3.1s ease-in-out infinite 0.9s; transform-origin: center; }
          .bp-syn { stroke-dasharray: 4 4; animation: bpSynapse 3s linear infinite; }
        `}</style>
      </defs>
      {/* Synapses (líneas neurales) */}
      <g stroke="hsl(271 91% 65%)" strokeWidth="1.2" fill="none">
        <line className="bp-syn" x1="18" y1="20" x2="32" y2="32" />
        <line className="bp-syn" x1="46" y1="18" x2="32" y2="32" style={{ animationDelay: '0.5s' }} />
        <line className="bp-syn" x1="14" y1="44" x2="32" y2="32" style={{ animationDelay: '1s' }} />
        <line className="bp-syn" x1="48" y1="46" x2="32" y2="32" style={{ animationDelay: '1.5s' }} />
        <line className="bp-syn" x1="18" y1="20" x2="46" y2="18" style={{ animationDelay: '0.8s' }} />
        <line className="bp-syn" x1="14" y1="44" x2="48" y2="46" style={{ animationDelay: '1.3s' }} />
      </g>
      {/* Halos */}
      <circle cx="32" cy="32" r="6" fill="url(#bpNode)" opacity="0.4" />
      {/* Nodos */}
      <circle className="bp-n1" cx="18" cy="20" r="2.5" fill="hsl(271 91% 70%)" />
      <circle className="bp-n2" cx="46" cy="18" r="2" fill="hsl(271 91% 60%)" />
      <circle className="bp-n3" cx="14" cy="44" r="2.5" fill="hsl(280 85% 65%)" />
      <circle className="bp-n4" cx="48" cy="46" r="2" fill="hsl(260 95% 70%)" />
      {/* Core node */}
      <circle cx="32" cy="32" r="3.5" fill="hsl(271 91% 75%)" />
      <circle cx="32" cy="32" r="1.5" fill="white" opacity="0.9" />
    </svg>
  )
}

// ── RADAR SWEEP (Macro) ────────────────────────────────────────────────────
// Radar circular con barrido giratorio — clásico de vigilancia global.
export function LogoRadar({ size = 36, className = '', title = 'Macro' }: Readonly<LogoProps>) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" className={className} aria-label={title} role="img">
      <defs>
        <linearGradient id="radarSweep" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="hsl(346 85% 55%)" stopOpacity="0.85" />
          <stop offset="50%" stopColor="hsl(346 85% 55%)" stopOpacity="0.25" />
          <stop offset="100%" stopColor="hsl(346 85% 55%)" stopOpacity="0" />
        </linearGradient>
        <radialGradient id="radarBg" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0%" stopColor="hsl(346 85% 55%)" stopOpacity="0.12" />
          <stop offset="100%" stopColor="hsl(346 85% 55%)" stopOpacity="0" />
        </radialGradient>
        <style>{`
          @keyframes rdSpin { to { transform: rotate(360deg); } }
          @keyframes rdBlip { 0%,70%,100% { opacity: 0; } 80% { opacity: 1; } }
          .rd-sweep { animation: rdSpin 3.5s linear infinite; transform-origin: 32px 32px; }
          .rd-blip-a { animation: rdBlip 3.5s linear infinite; transform-origin: center; }
          .rd-blip-b { animation: rdBlip 3.5s linear infinite 1.2s; transform-origin: center; }
          .rd-blip-c { animation: rdBlip 3.5s linear infinite 2.4s; transform-origin: center; }
        `}</style>
      </defs>
      <circle cx="32" cy="32" r="26" fill="url(#radarBg)" />
      {/* Anillos concéntricos */}
      <circle cx="32" cy="32" r="26" fill="none" stroke="hsl(346 85% 55% / 0.25)" strokeWidth="0.8" />
      <circle cx="32" cy="32" r="18" fill="none" stroke="hsl(346 85% 55% / 0.2)" strokeWidth="0.6" />
      <circle cx="32" cy="32" r="10" fill="none" stroke="hsl(346 85% 55% / 0.15)" strokeWidth="0.6" />
      {/* Cruz */}
      <line x1="6" y1="32" x2="58" y2="32" stroke="hsl(346 85% 55% / 0.15)" strokeWidth="0.5" />
      <line x1="32" y1="6" x2="32" y2="58" stroke="hsl(346 85% 55% / 0.15)" strokeWidth="0.5" />
      {/* Sweep */}
      <g className="rd-sweep">
        <path d="M 32 32 L 58 32 A 26 26 0 0 0 54.5 19 Z" fill="url(#radarSweep)" />
      </g>
      {/* Blips */}
      <circle className="rd-blip-a" cx="44" cy="22" r="1.8" fill="hsl(346 85% 70%)" />
      <circle className="rd-blip-b" cx="20" cy="38" r="1.6" fill="hsl(346 85% 70%)" />
      <circle className="rd-blip-c" cx="38" cy="46" r="1.8" fill="hsl(346 85% 70%)" />
      {/* Centro */}
      <circle cx="32" cy="32" r="2" fill="hsl(346 85% 65%)" />
    </svg>
  )
}

// ── INSIDERS BADGE (Insiders) ─────────────────────────────────────────────
// Escudo con tick / compras insider pulsando hacia arriba.
export function LogoInsiders({ size = 36, className = '', title = 'Insiders' }: Readonly<LogoProps>) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" className={className} aria-label={title} role="img">
      <defs>
        <linearGradient id="insGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="hsl(271 91% 65%)" />
          <stop offset="100%" stopColor="hsl(271 91% 40%)" />
        </linearGradient>
        <style>{`
          @keyframes insTick { 0% { stroke-dashoffset: 20; } 40% { stroke-dashoffset: 0; } 90% { stroke-dashoffset: 0; opacity: 1; } 100% { stroke-dashoffset: 0; opacity: 0; } }
          @keyframes insBounce { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-2px); } }
          .ins-tick { stroke-dasharray: 20; stroke-dashoffset: 20; animation: insTick 3s ease-in-out infinite; }
          .ins-arrow { animation: insBounce 1.8s ease-in-out infinite; transform-origin: center; }
        `}</style>
      </defs>
      {/* Shield */}
      <path d="M 32 8 L 52 14 L 52 34 Q 52 48 32 56 Q 12 48 12 34 L 12 14 Z"
        fill="url(#insGrad)" opacity="0.15" stroke="url(#insGrad)" strokeWidth="2" strokeLinejoin="round" />
      {/* Tick mark */}
      <path className="ins-tick" d="M 22 32 L 29 39 L 44 24"
        fill="none" stroke="hsl(271 91% 75%)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      {/* Up arrow small */}
      <g className="ins-arrow">
        <path d="M 46 20 L 46 14 M 43 17 L 46 14 L 49 17"
          fill="none" stroke="hsl(271 91% 80%)" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" opacity="0.8" />
      </g>
    </svg>
  )
}

// ── BOUNCE CROSSHAIR (Rebotes) ─────────────────────────────────────────────
// Crosshair de francotirador con onda que rebota desde el suelo.
export function LogoBounce({ size = 36, className = '', title = 'Rebotes' }: Readonly<LogoProps>) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" className={className} aria-label={title} role="img">
      <defs>
        <linearGradient id="bnGrad" x1="0" y1="1" x2="0" y2="0">
          <stop offset="0%" stopColor="hsl(20 95% 55%)" />
          <stop offset="100%" stopColor="hsl(40 95% 60%)" />
        </linearGradient>
        <style>{`
          @keyframes bnBall { 0%,100% { cy: 48; r: 3; } 50% { cy: 20; r: 2.5; } }
          @keyframes bnGround { 0%,100% { opacity: 0.2; } 50% { opacity: 0.8; } }
          @keyframes bnCross { 0%,100% { opacity: 0.4; } 50% { opacity: 1; } }
          .bn-ball { animation: bnBall 1.6s cubic-bezier(0.5, 0, 0.5, 1) infinite; }
          .bn-ground { animation: bnGround 1.6s ease-in-out infinite; transform-origin: center; }
          .bn-cross { animation: bnCross 2.2s ease-in-out infinite; transform-origin: center; }
        `}</style>
      </defs>
      {/* Crosshair circles */}
      <g className="bn-cross" stroke="hsl(20 95% 55% / 0.55)" strokeWidth="1" fill="none">
        <circle cx="32" cy="32" r="24" />
        <circle cx="32" cy="32" r="14" strokeWidth="0.7" />
        <line x1="32" y1="4" x2="32" y2="12" />
        <line x1="32" y1="52" x2="32" y2="60" />
        <line x1="4" y1="32" x2="12" y2="32" />
        <line x1="52" y1="32" x2="60" y2="32" />
      </g>
      {/* Ground line (soporte) */}
      <line className="bn-ground" x1="16" y1="52" x2="48" y2="52" stroke="url(#bnGrad)" strokeWidth="2" strokeLinecap="round" />
      {/* Bouncing ball */}
      <circle className="bn-ball" cx="32" cy="48" r="3" fill="url(#bnGrad)" />
    </svg>
  )
}

// ── WALLET VAULT (Mi cartera) ──────────────────────────────────────────────
// Caja fuerte con dial rotando + barras de valor subiendo.
export function LogoVault({ size = 36, className = '', title = 'Mi cartera' }: Readonly<LogoProps>) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" className={className} aria-label={title} role="img">
      <defs>
        <linearGradient id="vtGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="hsl(162 85% 50%)" />
          <stop offset="100%" stopColor="hsl(142 80% 45%)" />
        </linearGradient>
        <style>{`
          @keyframes vtDial { to { transform: rotate(360deg); } }
          @keyframes vtBar { 0%,100% { transform: scaleY(1); } 50% { transform: scaleY(1.15); } }
          .vt-dial { animation: vtDial 8s linear infinite; transform-origin: 32px 32px; }
          .vt-b1 { animation: vtBar 2s ease-in-out infinite; transform-origin: 20px 44px; }
          .vt-b2 { animation: vtBar 2s ease-in-out infinite 0.3s; transform-origin: 28px 44px; }
          .vt-b3 { animation: vtBar 2s ease-in-out infinite 0.6s; transform-origin: 36px 44px; }
          .vt-b4 { animation: vtBar 2s ease-in-out infinite 0.9s; transform-origin: 44px 44px; }
        `}</style>
      </defs>
      {/* Box */}
      <rect x="8" y="10" width="48" height="44" rx="3" fill="url(#vtGrad)" opacity="0.12"
        stroke="url(#vtGrad)" strokeWidth="1.8" />
      {/* Dial */}
      <circle cx="32" cy="26" r="9" fill="none" stroke="url(#vtGrad)" strokeWidth="1.5" />
      <g className="vt-dial">
        <line x1="32" y1="26" x2="32" y2="19" stroke="hsl(162 85% 60%)" strokeWidth="2" strokeLinecap="round" />
        <circle cx="32" cy="19" r="1.2" fill="hsl(162 85% 70%)" />
      </g>
      <circle cx="32" cy="26" r="1.5" fill="hsl(162 85% 70%)" />
      {/* Bars */}
      <rect className="vt-b1" x="18" y="40" width="4" height="4"  rx="0.5" fill="hsl(162 85% 55%)" />
      <rect className="vt-b2" x="26" y="38" width="4" height="6"  rx="0.5" fill="hsl(162 85% 55%)" />
      <rect className="vt-b3" x="34" y="36" width="4" height="8"  rx="0.5" fill="hsl(162 85% 60%)" />
      <rect className="vt-b4" x="42" y="34" width="4" height="10" rx="0.5" fill="hsl(162 85% 65%)" />
    </svg>
  )
}

// ── OWNER SEED (Owner Earnings) ────────────────────────────────────────────
// Semilla que crece: brote con hojas + raíces de flujo. FCF orgánico.
export function LogoSeed({ size = 36, className = '', title = 'Owner Earnings' }: Readonly<LogoProps>) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" className={className} aria-label={title} role="img">
      <defs>
        <linearGradient id="sdGrad" x1="0" y1="1" x2="0" y2="0">
          <stop offset="0%" stopColor="hsl(180 85% 40%)" />
          <stop offset="100%" stopColor="hsl(162 85% 55%)" />
        </linearGradient>
        <style>{`
          @keyframes sdGrow { 0% { transform: scaleY(0.85); opacity: 0.7; } 50% { transform: scaleY(1); opacity: 1; } 100% { transform: scaleY(0.85); opacity: 0.7; } }
          @keyframes sdLeaf { 0%,100% { transform: rotate(-4deg); } 50% { transform: rotate(4deg); } }
          @keyframes sdDrop { 0% { cy: 50; opacity: 0; } 50% { opacity: 1; } 100% { cy: 58; opacity: 0; } }
          .sd-stem { animation: sdGrow 3s ease-in-out infinite; transform-origin: 32px 52px; }
          .sd-leaf-l { animation: sdLeaf 3.2s ease-in-out infinite; transform-origin: 32px 32px; }
          .sd-leaf-r { animation: sdLeaf 3.2s ease-in-out infinite reverse; transform-origin: 32px 32px; }
          .sd-drop-a { animation: sdDrop 2.5s ease-in infinite; }
          .sd-drop-b { animation: sdDrop 2.5s ease-in infinite 1.2s; }
        `}</style>
      </defs>
      {/* Soil (base) */}
      <path d="M 10 52 Q 32 46 54 52 L 54 58 L 10 58 Z" fill="url(#sdGrad)" opacity="0.2" />
      <line x1="10" y1="52" x2="54" y2="52" stroke="url(#sdGrad)" strokeWidth="1.5" opacity="0.6" />
      {/* Roots (raíces flow) */}
      <g stroke="url(#sdGrad)" strokeWidth="1" fill="none" opacity="0.5">
        <path d="M 32 52 Q 26 55 22 58" />
        <path d="M 32 52 Q 38 55 42 58" />
        <path d="M 32 52 L 32 58" />
      </g>
      {/* Stem */}
      <g className="sd-stem">
        <line x1="32" y1="52" x2="32" y2="28" stroke="url(#sdGrad)" strokeWidth="2.4" strokeLinecap="round" />
      </g>
      {/* Leaves */}
      <ellipse className="sd-leaf-l" cx="24" cy="30" rx="6" ry="3.5" fill="url(#sdGrad)" opacity="0.85" transform="rotate(-30 24 30)" />
      <ellipse className="sd-leaf-r" cx="40" cy="26" rx="6" ry="3.5" fill="url(#sdGrad)" transform="rotate(25 40 26)" />
      {/* Sparkle drops (cash drops) */}
      <circle className="sd-drop-a" cx="28" cy="50" r="1.2" fill="hsl(162 85% 70%)" />
      <circle className="sd-drop-b" cx="36" cy="50" r="1.2" fill="hsl(162 85% 70%)" />
    </svg>
  )
}

// ── SEARCH SONAR (Buscar) ─────────────────────────────────────────────────
// Lupa con ondas sonar expandiéndose.
export function LogoSonar({ size = 36, className = '', title = 'Buscar' }: Readonly<LogoProps>) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" className={className} aria-label={title} role="img">
      <defs>
        <linearGradient id="snGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="hsl(210 40% 75%)" />
          <stop offset="100%" stopColor="hsl(210 40% 55%)" />
        </linearGradient>
        <style>{`
          @keyframes snWave { 0% { r: 12; opacity: 0.9; } 100% { r: 26; opacity: 0; } }
          .sn-w1 { animation: snWave 2.2s ease-out infinite; transform-origin: 26px 26px; }
          .sn-w2 { animation: snWave 2.2s ease-out infinite 0.7s; transform-origin: 26px 26px; }
          .sn-w3 { animation: snWave 2.2s ease-out infinite 1.4s; transform-origin: 26px 26px; }
        `}</style>
      </defs>
      {/* Sonar waves */}
      <circle className="sn-w1" cx="26" cy="26" r="12" fill="none" stroke="hsl(210 60% 65%)" strokeWidth="1.2" />
      <circle className="sn-w2" cx="26" cy="26" r="12" fill="none" stroke="hsl(210 60% 65%)" strokeWidth="1.2" />
      <circle className="sn-w3" cx="26" cy="26" r="12" fill="none" stroke="hsl(210 60% 65%)" strokeWidth="1.2" />
      {/* Lens */}
      <circle cx="26" cy="26" r="12" fill="url(#snGrad)" opacity="0.15" stroke="url(#snGrad)" strokeWidth="2.2" />
      <circle cx="23" cy="23" r="3" fill="hsl(210 60% 80%)" opacity="0.5" />
      {/* Handle */}
      <line x1="35" y1="35" x2="52" y2="52" stroke="url(#snGrad)" strokeWidth="3.5" strokeLinecap="round" />
    </svg>
  )
}
