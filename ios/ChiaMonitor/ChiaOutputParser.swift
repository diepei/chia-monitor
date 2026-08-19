import Foundation

enum ChiaOutputParser {
    static func parse(_ output: String) throws -> FarmSnapshot {
        let farm = section("FARM", in: output)
        let node = section("NODE", in: output)
        let wallet = section("WALLET", in: output)

        let plots = intMatch(#"Plot count:\s*([0-9,]+)"#, in: farm) ?? intMatch(#"Total plots:\s*([0-9,]+)"#, in: farm) ?? 0
        let size = doubleMatch(#"Total size of plots:\s*([0-9.]+)\s*TiB"#, in: farm) ?? 0
        let farmerOnline = !farm.localizedCaseInsensitiveContains("Connection error") && !farm.localizedCaseInsensitiveContains("not running") && plots > 0
        let synced = node.localizedCaseInsensitiveContains("Synced") && !node.localizedCaseInsensitiveContains("Not Synced")
        let harvesterCount = intMatch(#"Harvester.*?([0-9]+)"#, in: farm) ?? (farmerOnline ? 1 : 0)
        let etw = parseETW(farm)
        let balance = doubleMatch(#"Total Balance:\s*([0-9.]+)\s*xch"#, in: wallet.lowercased())
        let activity = intMatch(#"LAST_ACTIVITY_SECONDS=([0-9]+)"#, in: output)

        var alerts: [String] = []
        if !farmerOnline { alerts.append("Farmer is offline or has no plots") }
        if !synced { alerts.append("Full node is not synced") }
        if plots == 0 { alerts.append("No active plots detected") }
        if let activity, activity > 300 { alerts.append("No recent farming activity") }

        let critical = !farmerOnline || plots == 0
        let status: FarmStatus = critical ? .critical : alerts.isEmpty ? .healthy : .warning
        let score = max(0, 100 - alerts.reduce(0) { $0 + ($1.contains("offline") || $1.contains("No active") ? 25 : 10) })
        return FarmSnapshot(healthScore: score, status: status, farmerOnline: farmerOnline, nodeSynced: synced, plots: plots, sizeTiB: size, harvestersOnline: harvesterCount, harvestersTotal: harvesterCount, lastActivitySeconds: activity, estimatedWinSeconds: etw, balanceXCH: balance, alert: alerts.first, updatedAt: .now)
    }

    private static func section(_ name: String, in text: String) -> String {
        let start = "===\(name)===", end = "===END_\(name)==="
        guard let a = text.range(of: start), let b = text.range(of: end, range: a.upperBound..<text.endIndex) else { return "" }
        return String(text[a.upperBound..<b.lowerBound])
    }

    private static func intMatch(_ pattern: String, in text: String) -> Int? {
        guard let value = capture(pattern, in: text) else { return nil }
        return Int(value.replacingOccurrences(of: ",", with: ""))
    }

    private static func doubleMatch(_ pattern: String, in text: String) -> Double? {
        capture(pattern, in: text).flatMap(Double.init)
    }

    private static func capture(_ pattern: String, in text: String) -> String? {
        guard let regex = try? NSRegularExpression(pattern: pattern, options: [.caseInsensitive]),
              let match = regex.firstMatch(in: text, range: NSRange(text.startIndex..., in: text)),
              let range = Range(match.range(at: 1), in: text) else { return nil }
        return String(text[range])
    }

    private static func parseETW(_ text: String) -> Int? {
        guard let raw = capture(#"Expected time to win:\s*([^\n]+)"#, in: text) else { return nil }
        let units = [("day", 86_400), ("hour", 3_600), ("minute", 60)]
        for (unit, multiplier) in units {
            if let value = intMatch("([0-9]+)\\s*\(unit)", in: raw) { return value * multiplier }
        }
        return nil
    }
}
