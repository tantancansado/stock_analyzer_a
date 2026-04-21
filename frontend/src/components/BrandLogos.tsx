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

// ── 3. SA MONOGRAM ──────────────────────────────────────────────────────────
// Monograma "SA" geométrico con reveal. Corporativo y afilado.
export function LogoMonogram({ size = 36, className = '', title = 'Stock Analyzer' }: Readonly<LogoProps>) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" className={className} aria-label={title} role="img">
      <defs>
        <linearGradient id="monoGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="hsl(194 100% 48%)" />
          <stop offset="100%" stopColor="hsl(210 100% 60%)" />
        </linearGradient>
        <style>{`
          @keyframes monoSweep { 0% { transform: translateX(-70%); } 100% { transform: translateX(70%); } }
          @keyframes monoS { 0%,100% { stroke-dashoffset: 0; } 50% { stroke-dashoffset: 2; } }
          .mn-sweep { animation: monoSweep 3s ease-in-out infinite; }
        `}</style>
        <clipPath id="monoClip">
          <rect x="4" y="4" width="56" height="56" rx="8" />
        </clipPath>
      </defs>
      {/* Background */}
      <rect x="4" y="4" width="56" height="56" rx="8" fill="url(#monoGrad)" opacity="0.12" />
      <rect x="4" y="4" width="56" height="56" rx="8" fill="none" stroke="url(#monoGrad)" strokeWidth="1.5" />
      {/* Sweep highlight */}
      <g clipPath="url(#monoClip)">
        <rect className="mn-sweep" x="-24" y="-8" width="20" height="80" fill="hsl(194 100% 65%)" opacity="0.18" transform="skewX(-18)" />
      </g>
      {/* S */}
      <path
        d="M 26 20 Q 18 20 18 24 Q 18 28 23 29 L 29 31 Q 34 32 34 36 Q 34 40 26 40"
        fill="none" stroke="url(#monoGrad)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"
      />
      {/* A */}
      <path
        d="M 36 44 L 42 22 L 48 44 M 38.5 36 L 45.5 36"
        fill="none" stroke="url(#monoGrad)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"
      />
    </svg>
  )
}

// ── 4. ORBIT ────────────────────────────────────────────────────────────────
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
