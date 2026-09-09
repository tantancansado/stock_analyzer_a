import SwiftUI

struct ValueListView: View {
    @State private var store = ValueStore()

    var body: some View {
        NavigationStack {
            Group {
                switch store.state {
                case .idle, .loading:
                    ProgressView()
                        .controlSize(.large)
                        .tint(Theme.primary)
                        .frame(maxWidth: .infinity, maxHeight: .infinity)

                case .loaded(let ideas):
                    list(ideas)

                case .empty:
                    // Cero picks NO es un fallo: el gate solo publica lo que la
                    // IA verifica, y hay días que no pasa nada. Decirlo tal
                    // cual evita que parezca que la app está rota.
                    StatusView(
                        icon: "checkmark.seal",
                        title: "Hoy no hay picks",
                        message: "El filtro de calidad no ha validado ninguna oportunidad en \(store.region.rawValue). No es un error: prefiere cero señales antes que señales falsas.",
                        action: { Task { await store.load() } }
                    )

                case .failed(let message):
                    StatusView(
                        icon: "wifi.exclamationmark",
                        title: "No se han podido cargar",
                        message: message,
                        action: { Task { await store.load() } }
                    )
                }
            }
            .background(Theme.background)
            .navigationTitle("Value")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Picker("Región", selection: $store.region) {
                        ForEach(ValueStore.Region.allCases) { Text($0.rawValue).tag($0) }
                    }
                    .pickerStyle(.menu)
                    .tint(Theme.primary)
                }
            }
        }
        .task { if case .idle = store.state { await store.load() } }
    }

    private func list(_ ideas: [ValueOpportunity]) -> some View {
        ScrollView {
            LazyVStack(spacing: 10) {
                ForEach(ideas) { idea in
                    NavigationLink(value: idea) {
                        IdeaCard(idea: idea)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 10)
        }
        .scrollContentBackground(.hidden)
        .refreshable { await store.load() }
        .navigationDestination(for: ValueOpportunity.self) { IdeaDetailView(idea: $0) }
    }
}

/// Estado vacío / de error, con reintento. Un solo componente para los dos:
/// cambian el icono y el texto, no la forma.
struct StatusView: View {
    let icon: String
    let title: String
    let message: String
    var action: (() -> Void)?

    var body: some View {
        VStack(spacing: 12) {
            Image(systemName: icon)
                .font(.system(size: 34, weight: .light))
                .foregroundStyle(Theme.textMuted.opacity(0.5))
            Text(title)
                .font(.system(size: 16, weight: .semibold))
                .foregroundStyle(Theme.text)
            Text(message)
                .font(.system(size: 13))
                .foregroundStyle(Theme.textMuted)
                .multilineTextAlignment(.center)
            if let action {
                Button("Reintentar", action: action)
                    .font(.system(size: 13, weight: .semibold))
                    .tint(Theme.primary)
                    .padding(.top, 2)
            }
        }
        .padding(28)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
