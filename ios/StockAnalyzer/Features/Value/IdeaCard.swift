import SwiftUI

/// Una idea como tarjeta. Port de `IdeaMobileCard.tsx`, con su mismo orden de
/// lectura, que es el orden de la decisión:
///
///   ¿qué es? → ¿puedo entrar? → ¿por qué está barata? → ¿cuánto puedo ganar?
///
/// Todo lo que no responde a eso (R:R, P(win), Magic Formula, sector…) se
/// queda fuera. Regla del proyecto: un dato, un solo dispositivo de énfasis —
/// el veredicto lo lleva el badge y la tarjeta va neutra.
struct IdeaCard: View {
    let idea: ValueOpportunity

    private var earningsSoon: Bool {
        guard let d = idea.daysToEarnings else { return false }
        return d <= 7
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            header

            if let why = idea.whyCheap {
                Text("Por qué está barata: \(Text(why.label).foregroundStyle(Theme.text.opacity(0.95)))")
                    .font(.system(size: 12))
                    .foregroundStyle(Theme.text.opacity(0.7))
                    .padding(.top, 10)
            }

            HStack(alignment: .top, spacing: 8) {
                metric("Precio", idea.currentPrice.map { "$" + String(format: "%.2f", $0) })
                metric("Potencial", idea.analystUpsidePct.map { upside in
                    (upside > 0 ? "+" : "") + String(format: "%.0f%%", upside)
                }, tint: upsideTint)
                metric("Score", idea.valueScore.map { String(format: "%.0f", $0) })
            }
            .padding(.top, 12)

            if let price = idea.currentPrice {
                ValuationBar(
                    price: price,
                    pctFromHigh: idea.pctFrom52wHigh,
                    pctFromLow: idea.pctFrom52wLow,
                    targetAnalyst: idea.targetAnalyst,
                    targetDcf: idea.targetDcf,
                    targetPe: idea.targetPe
                )
                .padding(.top, 12)
            }

            if earningsSoon || idea.upsideDivergence == "ALTA" {
                warnings.padding(.top, 10)
            }
        }
        .padding(14)
        .glassCard()
    }

    private var header: some View {
        HStack(alignment: .top, spacing: 10) {
            TickerAvatar(ticker: idea.ticker)

            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 6) {
                    Text(idea.ticker)
                        .font(.system(size: 15, weight: .bold, design: .monospaced))
                        .foregroundStyle(Theme.primary)

                    if let readiness = idea.entryReadiness {
                        ReadinessBadge(readiness: readiness)
                    }
                }
                if let name = idea.companyName {
                    Text(name)
                        .font(.system(size: 11))
                        .foregroundStyle(Theme.textMuted)
                        .lineLimit(1)
                }
            }

            Spacer(minLength: 0)

            Image(systemName: "chevron.right")
                .font(.system(size: 12, weight: .semibold))
                .foregroundStyle(Theme.textMuted.opacity(0.4))
                .padding(.top, 2)
        }
    }

    private var upsideTint: Color? {
        guard let upside = idea.analystUpsidePct else { return nil }
        // Zona dorada [10,25): se premia esa banda, no el upside alto — un
        // upside enorme es señal de trampa de valor, no de oportunidad.
        return upside >= 10 ? Theme.positive : Theme.textMuted
    }

    private func metric(_ label: String, _ value: String?, tint: Color? = nil) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            DataLabel(text: label)
            Text(value ?? "—")
                .font(.system(size: 14, weight: .bold))
                .monospacedDigit()
                .foregroundStyle(tint ?? Theme.text)
                .lineLimit(1)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var warnings: some View {
        HStack(spacing: 12) {
            if earningsSoon, let days = idea.daysToEarnings {
                Label("Resultados en \(Int(days))d", systemImage: "calendar.badge.clock")
            }
            if idea.upsideDivergence == "ALTA" {
                Label("Los modelos no confirman el potencial", systemImage: "exclamationmark.triangle")
            }
        }
        .font(.system(size: 10))
        .foregroundStyle(Theme.warning)
        .labelStyle(.titleAndIcon)
    }
}

/// Cuadrito con las iniciales. La web tira de logos remotos; aquí no compensa
/// una petición extra por fila para un adorno — el ticker ya identifica.
struct TickerAvatar: View {
    let ticker: String

    var body: some View {
        RoundedRectangle(cornerRadius: Theme.radius)
            .fill(Theme.primary.opacity(0.12))
            .overlay {
                Text(String(ticker.prefix(2)))
                    .font(.system(size: 12, weight: .heavy, design: .monospaced))
                    .foregroundStyle(Theme.primary.opacity(0.9))
            }
            .overlay {
                RoundedRectangle(cornerRadius: Theme.radius)
                    .strokeBorder(Theme.primary.opacity(0.25), lineWidth: 1)
            }
            .frame(width: 34, height: 34)
    }
}

struct ReadinessBadge: View {
    let readiness: EntryReadiness

    private var color: Color {
        switch readiness {
        case .entrada: Theme.positive
        case .vigilar: Theme.primary
        case .esperar: Theme.negative
        }
    }

    var body: some View {
        Text(readiness.label.uppercased())
            .font(.system(size: 9, weight: .bold))
            .tracking(0.5)
            .foregroundStyle(color)
            .padding(.horizontal, 7)
            .padding(.vertical, 3)
            .background(color.opacity(0.15), in: Capsule())
            .overlay(Capsule().strokeBorder(color.opacity(0.3), lineWidth: 1))
    }
}
