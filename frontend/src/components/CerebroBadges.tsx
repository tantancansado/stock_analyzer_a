import { Zap, LogOut, TrendingDown, TriangleAlert, Flame, Gem, Award, Tag, Activity } from 'lucide-react'
import SignalBadge from './SignalBadge'
import type { TrapInfo, SmartInfo, ExitInfo, DivRiskInfo, PiotrInfo, SqueezeInfo, DecayInfo, SectorRVInfo, EntryInfo } from '../hooks/useCerebroSignals'

/**
 * Distintivos de Cerebro sobre una fila de ticker. La pastilla en sí vive en
 * SignalBadge, que es la misma que usan las tarjetas de Value US: antes cada
 * página dibujaba estas señales por su cuenta y no coincidía ninguna.
 */

interface Props {
  trapInfo?:    TrapInfo
  smInfo?:      SmartInfo
  exitInfo?:    ExitInfo
  divInfo?:     DivRiskInfo
  piotrInfo?:   PiotrInfo
  squeezeInfo?: SqueezeInfo
  decayInfo?:   DecayInfo
  sectorInfo?:  SectorRVInfo
  entryInfo?:   EntryInfo
}

export default function CerebroBadges({ trapInfo, smInfo, exitInfo, divInfo, piotrInfo, squeezeInfo, decayInfo, sectorInfo, entryInfo }: Props) {
  if (!trapInfo && !smInfo && !exitInfo && !divInfo && !piotrInfo && !squeezeInfo && !decayInfo && !sectorInfo && !entryInfo) return null

  return (
    <div className="flex items-center gap-1 flex-wrap mt-0.5">

      {/* ENTRADA — señal positiva, va primero */}
      {entryInfo && (
        <SignalBadge tamano="micro"
          icon={Zap}
          tono="favor"
          texto={entryInfo.signal === 'STRONG_BUY' ? 'STRONG BUY' : 'BUY'}
          titulo={`Cerebro señal de ENTRADA (${entryInfo.signal.replace('_', ' ')}): entry score ${entryInfo.entry_score}`}
        />
      )}

      {/* SALIDA — lo más urgente */}
      {exitInfo && (
        <SignalBadge tamano="micro"
          icon={LogOut}
          tono={exitInfo.severity === 'HIGH' ? 'alarma' : 'aviso'}
          texto="EXIT"
          titulo={`Cerebro recomienda SALIDA de posición (${exitInfo.severity}): ${exitInfo.reasons.slice(0, 2).join(' · ')}`}
        />
      )}

      {/* DETERIORO — aviso temprano, antes de la trampa */}
      {decayInfo && (
        <SignalBadge tamano="micro"
          icon={TrendingDown}
          tono="aviso"
          texto="DETERIORO"
          titulo={`Deterioro de calidad fundamental (${decayInfo.severity}): ${decayInfo.flags.slice(0, 2).join(' · ')}`}
        />
      )}

      {/* TRAMPA DE VALOR */}
      {trapInfo && (
        <SignalBadge tamano="micro"
          icon={TriangleAlert}
          tono={trapInfo.severity === 'HIGH' ? 'alarma' : 'aviso'}
          texto="TRAP"
          titulo={`Cerebro detecta señal TRAMPA — evitar entrada (score ${trapInfo.trap_score}/10): ${trapInfo.flags.slice(0, 2).join(' · ')}`}
        />
      )}

      {/* SHORT SQUEEZE */}
      {squeezeInfo && (
        <SignalBadge tamano="micro"
          icon={Flame}
          tono="info"
          texto="SHORT SQZ"
          titulo={`Potencial SHORT SQUEEZE detectado (${squeezeInfo.severity}): ${squeezeInfo.short_pct_float.toFixed(1)}% short · ${squeezeInfo.flags.slice(0, 2).join(' · ')}`}
        />
      )}

      {/* SMART MONEY — fondos e insiders comprando */}
      {smInfo && (
        <SignalBadge tamano="micro"
          icon={Gem}
          tono="favor"
          texto="SMART MONEY"
          titulo={`Smart Money convergente: ${smInfo.n_hedge_funds} hedge funds + ${smInfo.n_insiders} insiders comprando · conv ${smInfo.convergence_score}`}
        />
      )}

      {/* MEJOR DEL SECTOR / CARO VS PARES */}
      {sectorInfo && (
        sectorInfo.label === 'BEST_IN_SECTOR' ? (
          <SignalBadge tamano="micro"
            icon={Award}
            tono="favor"
            texto="BEST"
            titulo={`Mejor FCF en ${sectorInfo.sector}: rank ${sectorInfo.fcf_rank}/${sectorInfo.fcf_rank_of} (${sectorInfo.fcf_yield_pct.toFixed(1)}% FCF yield)`}
          />
        ) : (
          <SignalBadge tamano="micro"
            icon={Tag}
            tono="neutro"
            texto="PRICEY"
            titulo={`Caro vs peers en ${sectorInfo.sector}: rank ${sectorInfo.fcf_rank}/${sectorInfo.fcf_rank_of}`}
          />
        )
      )}

      {/* DIVIDENDO EN RIESGO */}
      {divInfo && (
        <SignalBadge tamano="micro"
          icon={TriangleAlert}
          tono={divInfo.rating === 'AT_RISK' ? 'alarma' : 'aviso'}
          texto="DIV RIESGO"
          titulo={`Dividendo ${divInfo.rating}: yield ${divInfo.div_yield.toFixed(1)}% — safety score ${divInfo.safety_score}`}
        />
      )}

      {/* PIOTROSKI */}
      {piotrInfo && (
        <SignalBadge tamano="micro"
          icon={Activity}
          tono={piotrInfo.trend === 'IMPROVING' ? 'favor' : 'info'}
          texto={`F-Score ${piotrInfo.piotroski_current}/9`}
          titulo={`Piotroski F${piotrInfo.piotroski_current}/9 · ${piotrInfo.trend.replace('_', ' ')}${piotrInfo.delta !== 0 ? ` (${piotrInfo.delta > 0 ? '+' : ''}${piotrInfo.delta})` : ''}`}
        />
      )}
    </div>
  )
}
