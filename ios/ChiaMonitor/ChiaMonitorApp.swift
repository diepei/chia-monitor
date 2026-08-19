import SwiftUI

@main
struct ChiaMonitorApp: App {
    @StateObject private var model = FarmViewModel()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(model)
        }
    }
}
