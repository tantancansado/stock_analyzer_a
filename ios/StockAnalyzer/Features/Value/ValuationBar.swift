import SwiftUI

/// Dónde está el precio dentro de su rango de 52 semanas, y dónde caen los
/// precios objetivo. Port fiel de `frontend/src/components/ValuationBar.tsx`,
/// incluidas sus dos reglas duras:
///
///   1. **La escala es SIEMPRE el rango de 52 semanas**, nunca los objetivos.
///      Si cada tarjeta escalara a su antojo, la posición del marcador no
///      significaría lo mismo en dos tarjetas seguidas y la lista dejaría de
///      ser comparable de un vistazo — que es para lo que sirve.
///   2. Un objetivo que se sale del rango se clava en el borde con una punta
///      de flecha. El DCF de MSFT sale a $94 con la acción a $484: dejarle
///      estirar la escala aplastaría el rango real hasta hacerlo ilegible.
///      Un modelo roto no puede romper el gráfico.
///
/// Sin dato no se dibuja el marcador. Nunca un objetivo inventado.
struct ValuationBar: View {
    let price: Double
    let pctFromHigh: Double?
    let pctFromLow: Double?
    var targetAnalyst: Double?
    var targetDcf: Double?
    var targetPe: Double?

    private struct Target: Identifiable {
        let label: String
        let value: Double
        let color: Color
        /// 0...1 dentro del rango, ya recortado al borde.
        let position: Double
        let outside: Outside?
        /// Cuántos objetivos hay ya clavados en ese mismo borde. Sin esto, el
        /// DCF y el consenso que se salen por arriba se dibujan uno ENCIMA del
        /// otro y parece que solo hay uno — que es justo lo contrario de lo
        /// que la barra quiere contar: cuando los modelos discrepan, la
        /// dispersión ES la información.
        let stackIndex: Int
        var id: String { label }
    }

    private enum Outside { case above, below }

    private static let colors: [String: Color] = [
        "Consenso": Color(hue: 152 / 360, saturation: 0.70, brightness: 0.72),
        "DCF": Color(hue: 266 / 360, saturation: 0.70, brightness: 0.80),
        "P/E": Color(hue: 38 / 360, saturation: 0.92, brightness: 0.85),
    ]

    var body: some View {
        // El CSV trae distancias, no extremos en dólares: se reconstruyen.
        if price > 0,
           let pctHigh = pctFromHigh, let pctLow = pctFromLow,
           case let high = price / (1 + pctHigh / 100),
           case let low = price / (1 + pctLow / 100),
           high.isFinite, low.isFinite, high > low {
            let span = high - low
            let pricePos = ((price - low) / span).clamped()
            let targets = buildTargets(low: low, span: span)

            VStack(alignment: .leading, spacing: 5) {
                GeometryReader { geo in
                    let w = geo.size.width
                    ZStack(alignment: .leading) {
                        Capsule()
                            .fill(Theme.textMuted.opacity(0.15))
                            .frame(height: 4)
                            .frame(maxHeight: .infinity, alignment: .center)

                        // Recorrido del mínimo al precio actual
                        Capsule()
                            .fill(Theme.primary.opacity(0.35))
                            .frame(width: max(2, w * pricePos), height: 4)
                            .frame(maxHeight: .infinity, alignment: .center)

                        ForEach(targets) { t in
                            TargetMark(target: t)
                                .position(x: markX(t, width: w), y: geo.size.height / 2)
                        }

                        // El precio va encima de los objetivos: es el ancla de
                        // lectura, y un objetivo solapado no debe taparlo.
                        PriceMark()
                            .position(x: (w * pricePos).clamped(to: 3...(w - 3)),
                                      y: geo.size.height / 2)
                    }
                }
                .frame(height: 18)

                HStack(spacing: 0) {
                    Text(Self.money(low))
                    Spacer(minLength: 4)
                    ForEach(targets) { t in
                        HStack(spacing: 3) {
                            Circle().fill(t.color).frame(width: 5, height: 5)
                            Text(t.label)
                        }
                        .padding(.trailing, 6)
                    }
                    Spacer(minLength: 4)
                    Text(Self.money(high))
                }
                .font(.system(size: 9, weight: .medium))
                .foregroundStyle(Theme.textMuted.opacity(0.8))
            }
        }
    }

    private func buildTargets(low: Double, span: Double) -> [Target] {
        let raw: [(String, Double?)] = [
            ("Consenso", targetAnalyst), ("DCF", targetDcf), ("P/E", targetPe),
        ]
        var pinned: [Outside: Int] = [:]
        return raw.compactMap { label, value in
            guard let value, value.isFinite, value > 0 else { return nil }
            let pos = (value - low) / span
            let outside: Outside? = pos > 1 ? .above : (pos < 0 ? .below : nil)
            var stack = 0
            if let outside {
                stack = pinned[outside, default: 0]
                pinned[outside] = stack + 1
            }
            return Target(label: label, value: value,
                          color: Self.colors[label] ?? Theme.primary,
                          position: pos.clamped(), outside: outside, stackIndex: stack)
        }
    }

    /// Los que caen dentro van en su sitio; los clavados en un borde se
    /// escalonan hacia dentro para que se vean los dos.
    private func markX(_ t: Target, width w: CGFloat) -> CGFloat {
        let step: CGFloat = 9
        switch t.outside {
        case .above: return w - 5 - step * CGFloat(t.stackIndex)
        case .below: return 5 + step * CGFloat(t.stackIndex)
        case nil:    return (w * t.position).clamped(to: 4...(w - 4))
        }
    }

    private static func money(_ n: Double) -> String {
        n >= 1000 ? String(format: "%.0f", n) : String(format: "%.2f", n)
    }

    private struct PriceMark: View {
        var body: some View {
            RoundedRectangle(cornerRadius: 1)
                .fill(Theme.text)
                .frame(width: 3, height: 14)
                .shadow(color: .black.opacity(0.6), radius: 2)
        }
    }

    private struct TargetMark: View {
        let target: Target

        var body: some View {
            Group {
                if let outside = target.outside {
                    // Fuera del año: punta de flecha hacia donde cae.
                    Image(systemName: outside == .above ? "arrowtriangle.right.fill" : "arrowtriangle.left.fill")
                        .font(.system(size: 8))
                        .foregroundStyle(target.color)
                } else {
                    Circle()
                        .fill(target.color)
                        .frame(width: 7, height: 7)
                        .overlay(Circle().strokeBorder(Theme.background, lineWidth: 1.5))
                }
            }
        }
    }
}

private extension Double {
    func clamped() -> Double { Swift.min(1, Swift.max(0, self)) }
}

private extension CGFloat {
    func clamped(to range: ClosedRange<CGFloat>) -> CGFloat {
        guard range.lowerBound <= range.upperBound else { return self }
        return Swift.min(range.upperBound, Swift.max(range.lowerBound, self))
    }
}
