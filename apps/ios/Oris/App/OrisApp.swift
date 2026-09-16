import SwiftUI

@main
struct OrisApp: App {
    var body: some Scene {
        WindowGroup {
            RootView(client: APIClient(baseURL: AppConfiguration.apiBaseURL))
        }
    }
}

enum AppConfiguration {
    /// Adresse de l'API. Sur simulateur, `localhost` désigne le Mac.
    /// Surchargée par la variable d'environnement `ORIS_API_URL` (schéma Xcode).
    static var apiBaseURL: URL {
        if let override = ProcessInfo.processInfo.environment["ORIS_API_URL"],
           let url = URL(string: override) {
            return url
        }
        return URL(string: "http://localhost:8000")!
    }
}
