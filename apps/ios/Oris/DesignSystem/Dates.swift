import Foundation

/// Dates à la française, comme sur le site : « lundi 21 septembre », « 19:44 ».
enum DateOris {
    private static let francais = Locale(identifier: "fr_FR")

    static func lire(_ texte: String?) -> Date? {
        guard let texte else { return nil }
        let complet = ISO8601DateFormatter()
        complet.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return complet.date(from: texte) ?? ISO8601DateFormatter().date(from: texte)
    }

    /// « 1990-03-08 » (date de naissance).
    static func lireJour(_ texte: String) -> Date? {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.dateFormat = "yyyy-MM-dd"
        return f.date(from: texte)
    }

    private static func format(_ date: Date, _ modele: String) -> String {
        let f = DateFormatter()
        f.locale = francais
        f.setLocalizedDateFormatFromTemplate(modele)
        return f.string(from: date)
    }

    static func jour(_ date: Date) -> String {
        let f = DateFormatter()
        f.locale = francais
        f.dateFormat = "EEEE d MMMM"
        return f.string(from: date)
    }

    static func heure(_ date: Date) -> String {
        let f = DateFormatter()
        f.locale = francais
        f.dateFormat = "HH:mm"
        return f.string(from: date)
    }

    static func court(_ date: Date) -> String {
        let f = DateFormatter()
        f.locale = francais
        f.dateFormat = "dd/MM/yyyy"
        return f.string(from: date)
    }

    /// « Aujourd'hui », « Hier » ou rien : le bandeau de jour ajoute la date en clair.
    static func repere(_ date: Date, maintenant: Date = Date()) -> String? {
        let calendrier = Calendar.current
        if calendrier.isDate(date, inSameDayAs: maintenant) { return "Aujourd’hui" }
        if let hier = calendrier.date(byAdding: .day, value: -1, to: maintenant),
           calendrier.isDate(date, inSameDayAs: hier) { return "Hier" }
        return nil
    }
}

extension EncounterSummary {
    /// Début de l'écoute, à défaut la création du dossier.
    var date: Date? { DateOris.lire(startedAt) ?? DateOris.lire(createdAt) }
}
