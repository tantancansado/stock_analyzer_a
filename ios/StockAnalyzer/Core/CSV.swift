import Foundation

/// Parser de CSV consciente de comillas.
///
/// No vale con `split(separator: ",")`: los CSV del pipeline llevan campos
/// como `health_details` con un dict de Python dentro —
/// `"{'roe_pct': 34.9, 'debt_to_equity': 0.24}"` — y partir por comas a pelo
/// desplaza todas las columnas siguientes de esa fila. El bug no revienta,
/// que es lo peor: rellena precios con trozos de texto.
enum CSV {
    /// Devuelve cada fila como diccionario columna → valor.
    static func parse(_ text: String) -> [[String: String]] {
        var rows = splitRows(text)
        guard !rows.isEmpty else { return [] }
        let header = rows.removeFirst()

        return rows.compactMap { fields in
            // Una fila con menos campos que cabeceras está truncada; se
            // descarta entera en vez de rellenar con vacíos y publicar un
            // dato a medias.
            guard fields.count >= header.count else { return nil }
            var row: [String: String] = [:]
            for (i, key) in header.enumerated() {
                row[key] = fields[i]
            }
            return row
        }
    }

    private static func splitRows(_ text: String) -> [[String]] {
        var rows: [[String]] = []
        var field = ""
        var fields: [String] = []
        var inQuotes = false
        var iterator = text.makeIterator()
        var pending: Character?

        while let c = pending ?? iterator.next() {
            pending = nil

            if inQuotes {
                if c == "\"" {
                    // Comilla doble escapada dentro de campo entrecomillado
                    if let next = iterator.next() {
                        if next == "\"" { field.append("\"") } else { inQuotes = false; pending = next }
                    } else {
                        inQuotes = false
                    }
                } else {
                    field.append(c)
                }
                continue
            }

            switch c {
            case "\"":
                inQuotes = true
            case ",":
                fields.append(field)
                field = ""
            case "\n":
                fields.append(field)
                rows.append(fields)
                fields = []
                field = ""
            case "\r":
                break   // CRLF: el \n siguiente cierra la fila
            default:
                field.append(c)
            }
        }

        if !field.isEmpty || !fields.isEmpty {
            fields.append(field)
            rows.append(fields)
        }
        return rows
    }
}

extension [String: String] {
    /// Número o `nil`. Trata como ausente lo que el pipeline escribe cuando no
    /// tiene el dato: vacío, `nan`, `None`, `NaN`. Nunca devuelve 0 por
    /// defecto — un 0 inventado es exactamente el fallo silencioso que el
    /// backend tiene prohibido (ver CLAUDE.md).
    func number(_ key: String) -> Double? {
        guard let raw = self[key]?.trimmingCharacters(in: .whitespaces), !raw.isEmpty else { return nil }
        let lowered = raw.lowercased()
        guard lowered != "nan", lowered != "none", lowered != "null" else { return nil }
        return Double(raw)
    }

    /// Texto o `nil` si está vacío / es un marcador de ausencia.
    func text(_ key: String) -> String? {
        guard let raw = self[key]?.trimmingCharacters(in: .whitespaces), !raw.isEmpty else { return nil }
        let lowered = raw.lowercased()
        guard lowered != "nan", lowered != "none", lowered != "null" else { return nil }
        return raw
    }

    func bool(_ key: String) -> Bool {
        guard let raw = text(key)?.lowercased() else { return false }
        return raw == "true" || raw == "1"
    }
}
