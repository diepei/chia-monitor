import Foundation

struct FarmSnapshot: Codable, Equatable {
    var healthScore: Int
    var status: FarmStatus
    var farmerOnline: Bool
    var nodeSynced: Bool
    var plots: Int
    var sizeTiB: Double
    var harvestersOnline: Int
    var harvestersTotal: Int
    var lastActivitySeconds: Int?
    var estimatedWinSeconds: Int?
    var balanceXCH: Double?
    var alert: String?
    var updatedAt: Date

    static let demo = FarmSnapshot(
        healthScore: 96, status: .healthy, farmerOnline: true, nodeSynced: true,
        plots: 742, sizeTiB: 73.4, harvestersOnline: 2, harvestersTotal: 2,
        lastActivitySeconds: 18, estimatedWinSeconds: 1_036_800, balanceXCH: 4.126,
        alert: nil, updatedAt: .now
    )

    var isStale: Bool { Date().timeIntervalSince(updatedAt) > 30 * 60 }
    var effectiveStatus: FarmStatus { isStale ? .stale : status }
}

enum FarmStatus: String, Codable {
    case healthy, warning, critical, stale

    var title: String {
        switch self { case .healthy: "Healthy"; case .warning: "Check farm"; case .critical: "Critical"; case .stale: "Data stale" }
    }
}

enum SharedStore {
    static let appGroup = "group.com.diepei.chiamonitor"
    private static let snapshotKey = "farmSnapshot"

    static func save(_ snapshot: FarmSnapshot) {
        guard let data = try? JSONEncoder().encode(snapshot) else { return }
        UserDefaults(suiteName: appGroup)?.set(data, forKey: snapshotKey)
    }

    static func load() -> FarmSnapshot? {
        guard let data = UserDefaults(suiteName: appGroup)?.data(forKey: snapshotKey) else { return nil }
        return try? JSONDecoder().decode(FarmSnapshot.self, from: data)
    }
}

func compactDuration(_ seconds: Int?) -> String {
    guard let seconds else { return "—" }
    if seconds < 60 { return "\(seconds)s" }
    if seconds < 3_600 { return "\(seconds / 60)m" }
    if seconds < 86_400 { return "\(seconds / 3_600)h" }
    return "\(seconds / 86_400)d"
}
