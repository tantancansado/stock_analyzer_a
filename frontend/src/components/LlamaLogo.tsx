interface Props {
  readonly size?: number
  readonly className?: string
  readonly title?: string
}

export default function LlamaLogo({ size = 28, className = '', title = 'Stock Analyzer' }: Readonly<Props>) {
  return (
    <img
      src={`${import.meta.env.BASE_URL}llama.png`}
      width={size}
      height={size}
      alt={title}
      className={className}
      style={{ objectFit: 'contain' }}
    />
  )
}
