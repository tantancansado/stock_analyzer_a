import Foundation

/// Acceso a los datos publicados por el pipeline.
///
/// Las listas (VALUE, LEAPS, momentum…) son ficheros estáticos en GitHub
/// Pages: públicos, cacheables y sin auth — la misma fuente que usa la web en
/// producción (`VITE_CSV_BASE`), no la API de Railway, que solo tiene el
/// snapshot del momento del deploy. Lo que sí necesita JWT de Supabase es
/// Cerebro / régimen de mercado / cartera, que van contra Railway.
enum DataSource {
    static let staticBase = URL(string: "https://tantancansado.github.io/stock_analyzer_a")!
}

enum DataError: LocalizedError {
    case http(Int)
    case emptyPayload(String)

    var errorDescription: String? {
        switch self {
        case .http(let code): "El servidor respondió \(code)"
        case .emptyPayload(let file): "\(file) llegó vacío"
        }
    }
}

struct DataClient {
    var session: URLSession = .shared

    /// Descarga un fichero publicado y lo devuelve como texto.
    ///
    /// `reloadIgnoringLocalCacheData` a propósito: el pipeline reescribe estos
    /// CSV una vez al día y la caché de iOS los serviría rancios sin avisar —
    /// justo el fallo silencioso que la app ya sufrió en la web (datos
    /// congelados con buena cara). El coste es bajo: son ficheros de 8-30 KB.
    func fetchText(_ path: String) async throws -> String {
        let url = DataSource.staticBase.appending(path: path)
        var request = URLRequest(url: url)
        request.cachePolicy = .reloadIgnoringLocalCacheData
        request.timeoutInterval = 20

        let (data, response) = try await session.data(for: request)
        if let http = response as? HTTPURLResponse, !(200..<300).contains(http.statusCode) {
            throw DataError.http(http.statusCode)
        }
        guard let text = String(data: data, encoding: .utf8), !text.isEmpty else {
            throw DataError.emptyPayload(path)
        }
        return text
    }

    func fetchCSV(_ path: String) async throws -> [[String: String]] {
        CSV.parse(try await fetchText(path))
    }

    func fetchJSON<T: Decodable>(_ path: String, as type: T.Type) async throws -> T {
        let url = DataSource.staticBase.appending(path: path)
        var request = URLRequest(url: url)
        request.cachePolicy = .reloadIgnoringLocalCacheData
        request.timeoutInterval = 20

        let (data, response) = try await session.data(for: request)
        if let http = response as? HTTPURLResponse, !(200..<300).contains(http.statusCode) {
            throw DataError.http(http.statusCode)
        }
        return try JSONDecoder().decode(T.self, from: data)
    }
}
