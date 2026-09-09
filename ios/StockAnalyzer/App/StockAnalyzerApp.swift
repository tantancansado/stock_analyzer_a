import SwiftUI

@main
struct StockAnalyzerApp: App {
    var body: some Scene {
        WindowGroup {
            RootView()
                .preferredColorScheme(.dark)
                .tint(Theme.primary)
        }
    }
}
