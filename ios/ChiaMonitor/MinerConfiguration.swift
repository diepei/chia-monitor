import Foundation

struct MinerConfiguration: Codable, Equatable {
    var name = "My Chia Farm"
    var host = ""
    var port = 22
    var username = ""

    var isComplete: Bool { !host.trimmingCharacters(in: .whitespaces).isEmpty && !username.trimmingCharacters(in: .whitespaces).isEmpty }
}

enum ConfigurationStore {
    private static let key = "minerConfiguration"

    static func load() -> MinerConfiguration {
        guard let data = UserDefaults.standard.data(forKey: key), let value = try? JSONDecoder().decode(MinerConfiguration.self, from: data) else { return .init() }
        return value
    }

    static func save(_ value: MinerConfiguration) {
        UserDefaults.standard.set(try? JSONEncoder().encode(value), forKey: key)
    }
}
