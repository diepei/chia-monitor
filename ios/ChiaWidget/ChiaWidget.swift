import SwiftUI
import WidgetKit

struct FarmEntry: TimelineEntry { let date: Date; let snapshot: FarmSnapshot }

struct FarmProvider: TimelineProvider {
    func placeholder(in context: Context) -> FarmEntry { .init(date: .now, snapshot: .demo) }
    func getSnapshot(in context: Context, completion: @escaping (FarmEntry) -> Void) { completion(.init(date: .now, snapshot: SharedStore.load() ?? .demo)) }
    func getTimeline(in context: Context, completion: @escaping (Timeline<FarmEntry>) -> Void) {
        let value = SharedStore.load() ?? .demo
        completion(Timeline(entries: [.init(date: .now, snapshot: value)], policy: .after(Date().addingTimeInterval(15 * 60))))
    }
}

struct ChiaWidgetView: View {
    @Environment(\.widgetFamily) private var family
    let entry: FarmEntry
    private var snapshot: FarmSnapshot { entry.snapshot }
    private var accent: Color { switch snapshot.effectiveStatus { case .healthy: Color(red: 0.35, green: 0.86, blue: 0.53); case .warning: .orange; case .critical: .red; case .stale: .gray } }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack { Text("CHIA FARM").font(.caption2.monospaced().bold()).foregroundStyle(.secondary); Spacer(); Circle().fill(accent).frame(width: 7, height: 7); Text(snapshot.effectiveStatus.title.uppercased()).font(.system(size: 9, weight: .bold, design: .monospaced)).foregroundStyle(accent) }
            Spacer(minLength: 8)
            HStack(alignment: .lastTextBaseline, spacing: 5) { Text("\(snapshot.healthScore)").font(.system(size: family == .systemSmall ? 38 : 42, weight: .bold, design: .rounded)); Text("/100").font(.caption.monospaced()).foregroundStyle(.secondary) }
            Text(snapshot.alert ?? (snapshot.farmerOnline ? "Farming normally" : "Farmer offline")).font(.caption).foregroundStyle(.secondary).lineLimit(1)
            Spacer(minLength: 8)
            HStack {
                stat("FARMER", snapshot.farmerOnline ? "Online" : "Offline")
                Spacer(); stat("PLOTS", "\(snapshot.plots)")
                if family != .systemSmall { Spacer(); stat("SIZE", String(format: "%.1f TiB", snapshot.sizeTiB)) }
            }
            Text("Updated \(snapshot.updatedAt, style: .relative) ago").font(.system(size: 8, design: .monospaced)).foregroundStyle(.tertiary).padding(.top, 8)
        }
        .containerBackground(Color(red: 0.025, green: 0.067, blue: 0.047), for: .widget)
    }

    private func stat(_ label: String, _ value: String) -> some View { VStack(alignment: .leading, spacing: 2) { Text(label).font(.system(size: 8, weight: .bold, design: .monospaced)).foregroundStyle(.secondary); Text(value).font(.caption.bold()) } }
}

@main
struct ChiaWidget: Widget {
    let kind = "ChiaWidget"
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: FarmProvider()) { ChiaWidgetView(entry: $0) }
            .configurationDisplayName("Chia Farm Health")
            .description("See whether your Chia farm is healthy at a glance.")
            .supportedFamilies([.systemSmall, .systemMedium])
    }
}
