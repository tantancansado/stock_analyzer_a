interface Props {
  size?: number
  className?: string
  title?: string
}

export default function LlamaLogo({ size = 28, className = '', title = 'Stock Analyzer' }: Props) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 64 64"
      width={size}
      height={size}
      className={className}
      role="img"
      aria-label={title}
    >
      <title>{title}</title>
      <defs>
        <linearGradient id="llama-body" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="currentColor" stopOpacity="1" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0.72" />
        </linearGradient>
      </defs>

      {/* Neck + body silhouette */}
      <path
        d="M22 58 L22 34 Q22 20 30 18 Q36 17 38 20 L38 10 Q38 6 42 6 Q46 6 46 10 L46 20 Q54 24 54 34 L54 58 Z"
        fill="url(#llama-body)"
      />

      {/* Inner ear */}
      <path d="M40 8 L42 14 L44 8 Z" fill="currentColor" opacity="0.35" />

      {/* Eye (investor glasses frame) */}
      <circle cx="41" cy="24" r="3.2" fill="#0a0a0a" />
      <circle cx="41" cy="24" r="3.2" fill="none" stroke="#fff" strokeWidth="0.8" opacity="0.9" />
      <circle cx="41.9" cy="23" r="0.9" fill="#fff" />

      {/* Nose / muzzle */}
      <ellipse cx="45.5" cy="30" rx="3" ry="2" fill="#0a0a0a" opacity="0.85" />
      <circle cx="46" cy="29.5" r="0.6" fill="#fff" opacity="0.6" />

      {/* Chart line climbing across the body — the "value" signal */}
      <polyline
        points="24,50 28,46 32,48 36,42 40,44 44,36 48,38 52,30"
        fill="none"
        stroke="#22c55e"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* Chart dot at peak */}
      <circle cx="52" cy="30" r="1.8" fill="#22c55e" />
      <circle cx="52" cy="30" r="3" fill="#22c55e" opacity="0.25" />

      {/* Feet hint */}
      <rect x="24" y="56" width="5" height="3" rx="1" fill="currentColor" opacity="0.8" />
      <rect x="47" y="56" width="5" height="3" rx="1" fill="currentColor" opacity="0.8" />
    </svg>
  )
}
