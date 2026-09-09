import Foundation
import Observation

/// Estado de la pantalla VALUE.
///
/// `.empty` es un estado propio, distinto de `.failed`: que el pipeline
/// publique cero picks es un resultado legítimo (el gate de Claude es
/// fail-closed a propósito — ver CLAUDE.md), no un error de red, y la
/// pantalla tiene que decir cosas distintas en cada caso. Confundirlos es lo
/// que hizo que la web tuviera datos congelados durante semanas con buena cara.
@MainActor
@Observable
final class ValueStore {
    enum Region: String, CaseIterable, Identifiable {
        case us = "US"
        case eu = "Europa"
        case global = "Global"

        var id: String { rawValue }

        var file: String {
            switch self {
            case .us: "value_opportunities_filtered.csv"
            case .eu: "european_value_opportunities_filtered.csv"
            case .global: "global_value_opportunities.csv"
            }
        }
    }

    enum State {
        case idle
        case loading
        case loaded([ValueOpportunity])
        case empty
        case failed(String)
    }

    private(set) var state: State = .idle
    var region: Region = .us {
        didSet { if region != oldValue { Task { await load() } } }
    }

    private let client: DataClient

    init(client: DataClient = DataClient()) {
        self.client = client
    }

    func load() async {
        state = .loading
        do {
            let rows = try await client.fetchCSV(region.file)
            let ideas = rows.compactMap(ValueOpportunity.init(row:))
            state = ideas.isEmpty ? .empty : .loaded(sorted(ideas))
        } catch {
            state = .failed(error.localizedDescription)
        }
    }

    /// Primero lo accionable hoy (ENTRADA), luego por score. El orden de la
    /// lista es el orden en el que el usuario decide, no el del CSV.
    private func sorted(_ ideas: [ValueOpportunity]) -> [ValueOpportunity] {
        ideas.sorted { a, b in
            let ra = a.entryReadiness == .entrada ? 1 : 0
            let rb = b.entryReadiness == .entrada ? 1 : 0
            if ra != rb { return ra > rb }
            return (a.valueScore ?? 0) > (b.valueScore ?? 0)
        }
    }
}
