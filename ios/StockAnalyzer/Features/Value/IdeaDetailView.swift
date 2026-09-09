import SwiftUI

/// Ficha de una idea: los niveles de la operación y por qué está en la lista.
///
/// La salida se plantea SIEMPRE a precio objetivo por valoración, nunca a un
/// % fijo de ganancia ni a un nivel técnico — es la regla de decisión del
/// usuario y la app no debe sugerir lo contrario ni de pasada.
struct IdeaDetailView: View {
    let idea: ValueOpportunity

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                headline

                if let price = idea.currentPrice {
                    VStack(alignment: .leading, spacing: 8) {
                        DataLabel(text: "Precio sobre el rango de 52 semanas")
                        ValuationBar(
                            price: price,
                            pctFromHigh: idea.pctFrom52wHigh,
                            pctFromLow: idea.pctFrom52wLow,
                            targetAnalyst: idea.targetAnalyst,
                            targetDcf: idea.targetDcf,
                            targetPe: idea.targetPe
                        )
                    }
                    .padding(14)
                    .glassCard()
                }

                levels

                if let reason = idea.entryReadinessReason {
                    section("Lectura técnica", reason)
                }

                if let why = idea.whyCheap {
                    section("Por qué está barata", idea.whyCheapSummary ?? why.label)
                }

                verification
            }
            .padding(14)
        }
        .background(Theme.background)
        .navigationTitle(idea.ticker)
        .navigationBarTitleDisplayMode(.inline)
    }

    private var headline: some View {
        VStack(alignment: .leading, spacing: 6) {
            if let name = idea.companyName {
                Text(name)
                    .font(.system(size: 17, weight: .bold))
                    .foregroundStyle(Theme.text)
            }
            HStack(spacing: 8) {
                if let readiness = idea.entryReadiness { ReadinessBadge(readiness: readiness) }
                if let sector = idea.sector {
                    Text(sector)
                        .font(.system(size: 11))
                        .foregroundStyle(Theme.textMuted)
                }
            }
            if let timing = idea.entryTiming {
                Text(timing)
                    .font(.system(size: 12, weight: .medium))
                    .foregroundStyle(Theme.primary)
                    .padding(.top, 2)
            }
        }
    }

    private var levels: some View {
        HStack(spacing: 10) {
            level("Entrada", idea.entryPrice, tint: Theme.primary)
            level("Stop", idea.stopLoss, tint: Theme.negative)
            level("Objetivo", idea.exitPrice, tint: Theme.positive)
        }
    }

    private func level(_ label: String, _ value: Double?, tint: Color) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            DataLabel(text: label)
            Text(value.map { "$" + String(format: "%.2f", $0) } ?? "—")
                .font(.system(size: 15, weight: .bold))
                .monospacedDigit()
                .foregroundStyle(tint)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .glassCard()
    }

    private func section(_ title: String, _ body: String) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            DataLabel(text: title)
            Text(body)
                .font(.system(size: 13))
                .foregroundStyle(Theme.text.opacity(0.9))
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .glassCard()
    }

    /// Quién validó el dato importa: US pasa por Claude y EU/global por
    /// Qwen — dos listones distintos, y mezclarlos sin marca sería vender
    /// como equivalente lo que no lo es.
    @ViewBuilder
    private var verification: some View {
        if idea.aiVerified {
            let who = idea.verifiedBy?.lowercased() == "groq" ? "Qwen" : "Claude"
            HStack(spacing: 7) {
                Image(systemName: "checkmark.seal.fill")
                    .foregroundStyle(Theme.positive)
                Text("Datos verificados por \(who)")
                    .foregroundStyle(Theme.textMuted)
                if let confidence = idea.aiConfidence {
                    Text("· \(Int(confidence))%")
                        .foregroundStyle(Theme.textMuted.opacity(0.7))
                        .monospacedDigit()
                }
            }
            .font(.system(size: 11))
        }
    }
}
