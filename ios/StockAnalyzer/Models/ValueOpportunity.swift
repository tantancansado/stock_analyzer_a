import Foundation

/// Una oportunidad VALUE tal y como la publica `value_opportunities_filtered.csv`.
///
/// Solo se modelan los campos que la app nativa usa para decidir. El CSV trae
/// ~150 columnas; arrastrarlas todas aquí sería ruido, y la tesis completa se
/// consulta en la web, que ya la muestra entera.
struct ValueOpportunity: Identifiable, Sendable, Hashable {
    let ticker: String
    let companyName: String?
    let sector: String?

    let currentPrice: Double?
    let entryPrice: Double?
    let stopLoss: Double?
    let exitPrice: Double?

    let valueScore: Double?
    let analystUpsidePct: Double?

    /// Distancias al máximo/mínimo de 52 semanas. El CSV no trae los extremos
    /// en dólares, solo estas distancias: la barra los reconstruye.
    let pctFrom52wHigh: Double?
    let pctFrom52wLow: Double?

    let targetAnalyst: Double?
    let targetDcf: Double?
    let targetPe: Double?

    let entryReadiness: EntryReadiness?
    let entryReadinessReason: String?
    let entryTiming: String?

    let whyCheap: WhyCheap?
    let whyCheapSummary: String?

    let aiVerdict: String?
    let aiConfidence: Double?
    let aiVerified: Bool
    /// 'claude' o 'groq' — dos niveles de fiabilidad distintos, no se mezclan.
    let verifiedBy: String?

    let daysToEarnings: Double?
    let daysInList: Double?
    let upsideDivergence: String?

    var id: String { ticker }

    init?(row: [String: String]) {
        guard let ticker = row.text("ticker") else { return nil }
        self.ticker = ticker
        companyName = row.text("company_name")
        sector = row.text("sector")

        currentPrice = row.number("current_price")
        entryPrice = row.number("entry_price")
        stopLoss = row.number("stop_loss")
        exitPrice = row.number("exit_price")

        valueScore = row.number("value_score")
        analystUpsidePct = row.number("analyst_upside_pct")

        pctFrom52wHigh = row.number("pct_from_52w_high")
        pctFrom52wLow = row.number("pct_from_52w_low")

        targetAnalyst = row.number("target_price_analyst")
        targetDcf = row.number("target_price_dcf")
        targetPe = row.number("target_price_pe")

        entryReadiness = row.text("entry_readiness").flatMap(EntryReadiness.init(rawValue:))
        entryReadinessReason = row.text("entry_readiness_reason")
        entryTiming = row.text("entry_timing")

        whyCheap = row.text("why_cheap").flatMap(WhyCheap.init(rawValue:))
        whyCheapSummary = row.text("why_cheap_resumen")

        aiVerdict = row.text("ai_verdict")
        aiConfidence = row.number("ai_confidence")
        aiVerified = row.bool("ai_verified")
        verifiedBy = row.text("verified_by")

        daysToEarnings = row.number("days_to_earnings")
        daysInList = row.number("days_in_list")
        upsideDivergence = row.text("upside_divergence")
    }
}

/// Veredicto técnico de entrada. Los textos son los de la web, no traducciones
/// nuevas: la app y el móvil tienen que decir lo mismo.
enum EntryReadiness: String, Sendable {
    case entrada = "ENTRADA"
    case vigilar = "VIGILAR"
    case esperar = "ESPERAR"

    var label: String {
        switch self {
        case .entrada: "Listo para entrar"
        case .vigilar: "En vigilancia"
        case .esperar: "Aún cayendo"
        }
    }
}

/// Por qué ha caído. Solo `DETERIORO` veta; el resto informa.
enum WhyCheap: String, Sendable {
    case deterioro = "DETERIORO"
    case ciclico = "CICLICO"
    case evento = "EVENTO"
    case sentimiento = "SENTIMIENTO"

    var label: String {
        switch self {
        case .deterioro: "El negocio está peor"
        case .ciclico: "Parte baja del ciclo"
        case .evento: "Shock puntual"
        case .sentimiento: "Sentimiento, no el negocio"
        }
    }
}
