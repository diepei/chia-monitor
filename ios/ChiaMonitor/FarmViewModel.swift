import Foundation
import WidgetKit

@MainActor
final class FarmViewModel: ObservableObject {
    @Published var configuration = ConfigurationStore.load()
    @Published var snapshot = SharedStore.load() ?? .demo
    @Published var isDemo = SharedStore.load() == nil
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var showingSetup = false

    func refresh() async {
        guard configuration.isComplete, let password = KeychainStore.password() else { showingSetup = true; return }
        isLoading = true; errorMessage = nil
        do {
            let newSnapshot = try await SSHService.fetch(configuration: configuration, password: password)
            snapshot = newSnapshot; isDemo = false
            SharedStore.save(newSnapshot)
            WidgetCenter.shared.reloadAllTimelines()
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    func save(configuration: MinerConfiguration, password: String) throws {
        try KeychainStore.savePassword(password)
        ConfigurationStore.save(configuration)
        self.configuration = configuration
        showingSetup = false
    }
}
