import SwiftUI

/// Las cuatro pantallas de decidir una entrada. El resto del menú de la web
/// (26 destinos) se queda en la web a propósito: en el móvil no se abren
/// Backtest ni Calibration, y portarlas sería meses de trabajo para pantallas
/// que no se usan.
struct RootView: View {
    /// Arranca en Value porque es la única pantalla implementada — abrir en un
    /// placeholder sería una primera impresión falsa. Cuando "Hoy" exista,
    /// vuelve a ser la pestaña inicial.
    @State private var selection: Tabs = .value

    enum Tabs: Hashable { case today, value, setups, leaps }

    var body: some View {
        TabView(selection: $selection) {
            Tab("Hoy", systemImage: "square.grid.2x2", value: Tabs.today) {
                ComingSoonView(
                    title: "Centro de mando",
                    detail: "Régimen de mercado, plan del día y señales de Cerebro. Necesita login de Supabase: son endpoints de la API, no ficheros públicos."
                )
            }
            Tab("Value", systemImage: "dollarsign.circle", value: Tabs.value) {
                ValueListView()
            }
            Tab("Setups", systemImage: "chart.line.uptrend.xyaxis", value: Tabs.setups) {
                ComingSoonView(
                    title: "Entry setups",
                    detail: "Momentum, mean reversion y rebotes técnicos, con su comprobación de catalizador."
                )
            }
            Tab("LEAPS", systemImage: "rocket", value: Tabs.leaps) {
                ComingSoonView(
                    title: "LEAPS",
                    detail: "Calls largas deep-ITM con su gráfico de payoff nativo (Swift Charts)."
                )
            }
        }
        .tint(Theme.primary)
    }
}

struct ComingSoonView: View {
    let title: String
    let detail: String

    var body: some View {
        NavigationStack {
            StatusView(icon: "hammer", title: title, message: detail)
                .background(Theme.background)
                .navigationTitle(title)
        }
    }
}
