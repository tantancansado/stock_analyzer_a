import SwiftUI

/// Skin Cybertruck, la misma de la web: fondo oscuro, cian eléctrico y
/// esquinas afiladas. Los valores salen de `frontend/src/index.css` para que
/// las dos apps no deriven — si cambia una, cambia la otra a mano.
enum Theme {
    /// hsl(194 100% 48%) — el `--primary` de la web.
    static let primary = Color(red: 0, green: 0.737, blue: 0.961)

    static let background = Color(red: 0.039, green: 0.047, blue: 0.063)
    static let surface = Color(red: 0.071, green: 0.086, blue: 0.110)
    static let border = Color.white.opacity(0.10)

    static let text = Color(red: 0.898, green: 0.925, blue: 0.953)
    static let textMuted = Color(red: 0.549, green: 0.600, blue: 0.667)

    static let positive = Color(red: 0.204, green: 0.827, blue: 0.600)
    static let negative = Color(red: 0.937, green: 0.325, blue: 0.314)
    static let warning = Color(red: 0.961, green: 0.620, blue: 0.043)

    /// `--radius: 0.25rem`. Afiladas a propósito: es la marca del skin.
    static let radius: CGFloat = 4
    static let radiusCard: CGFloat = 10
}

/// El equivalente nativo de `.glass`: superficie translúcida con borde fino.
/// En la web es `backdrop-filter: blur()`; aquí `.ultraThinMaterial` da el
/// mismo efecto sin coste de repintado, que es justo la ventaja de ser nativo.
struct GlassCard: ViewModifier {
    func body(content: Content) -> some View {
        content
            .background(.ultraThinMaterial.opacity(0.6), in: RoundedRectangle(cornerRadius: Theme.radiusCard))
            .background(Theme.surface.opacity(0.7), in: RoundedRectangle(cornerRadius: Theme.radiusCard))
            .overlay {
                RoundedRectangle(cornerRadius: Theme.radiusCard)
                    .strokeBorder(Theme.border, lineWidth: 1)
            }
    }
}

extension View {
    func glassCard() -> some View { modifier(GlassCard()) }
}

/// Etiqueta pequeña en versalitas — el `text-[0.55rem] uppercase tracking-widest`
/// que la web usa para rotular cada dato.
struct DataLabel: View {
    let text: String

    var body: some View {
        Text(text.uppercased())
            .font(.system(size: 9, weight: .bold))
            .tracking(1.2)
            .foregroundStyle(Theme.textMuted.opacity(0.7))
    }
}
