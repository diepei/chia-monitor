import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var model: FarmViewModel

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 12) {
                    header
                    healthCard
                    metrics
                    if let alert = model.snapshot.alert { alertCard(alert) }
                    freshness
                }
                .padding(16)
            }
            .background(Color.appBackground.ignoresSafeArea())
            .toolbar(.hidden, for: .navigationBar)
            .refreshable { await model.refresh() }
            .sheet(isPresented: $model.showingSetup) { SetupView() }
            .task { if model.configuration.isComplete && model.isDemo { await model.refresh() } }
            .alert("Could not refresh", isPresented: Binding(get: { model.errorMessage != nil }, set: { if !$0 { model.errorMessage = nil } })) {
                Button("OK", role: .cancel) { model.errorMessage = nil }
            } message: { Text(model.errorMessage ?? "Unknown connection error") }
        }
        .preferredColorScheme(.dark)
    }

    private var header: some View {
        HStack {
            HStack(spacing: 9) {
                Text("C").font(.headline.bold()).foregroundStyle(Color.healthGreen).frame(width: 32, height: 32).overlay(RoundedRectangle(cornerRadius: 9).stroke(Color.healthGreen))
                VStack(alignment: .leading, spacing: 1) {
                    Text("CHIA MONITOR").font(.caption2.monospaced().weight(.semibold)).foregroundStyle(.secondary)
                    Text(model.configuration.name).font(.subheadline.weight(.semibold))
                }
            }
            Spacer()
            Button { model.showingSetup = true } label: {
                Label(model.isDemo ? "Demo" : "SSH", systemImage: model.isDemo ? "sparkles" : "lock.fill")
                    .font(.caption.weight(.semibold)).padding(.horizontal, 10).padding(.vertical, 7)
                    .background(Color.cardBackground, in: Capsule()).overlay(Capsule().stroke(Color.cardBorder))
            }.foregroundStyle(.secondary)
        }
    }

    private var healthCard: some View {
        HStack {
            VStack(alignment: .leading, spacing: 7) {
                Text("YOUR FARM IS").font(.caption2.monospaced().weight(.bold)).tracking(1.2).foregroundStyle(.secondary)
                Text(model.snapshot.effectiveStatus.title).font(.system(size: 40, weight: .bold, design: .rounded)).tracking(-1.5)
                Text(healthSubtitle).font(.subheadline).foregroundStyle(.secondary)
            }
            Spacer()
            ZStack {
                Circle().stroke(Color.cardBorder, lineWidth: 7)
                Circle().trim(from: 0, to: Double(model.snapshot.healthScore) / 100).stroke(statusColor, style: StrokeStyle(lineWidth: 7, lineCap: .round)).rotationEffect(.degrees(-90))
                VStack(spacing: 0) { Text("\(model.snapshot.healthScore)").font(.title2.monospacedDigit().bold()); Text("/100").font(.caption2.monospaced()).foregroundStyle(.secondary) }
            }.frame(width: 92, height: 92)
        }
        .padding(20).background(Color.cardBackground, in: RoundedRectangle(cornerRadius: 22)).overlay(RoundedRectangle(cornerRadius: 22).stroke(Color.cardBorder))
    }

    private var metrics: some View {
        LazyVGrid(columns: [.init(.flexible()), .init(.flexible())], spacing: 10) {
            MetricCard(title: "FARMER", value: model.snapshot.farmerOnline ? "Online" : "Offline", detail: "Activity \(compactDuration(model.snapshot.lastActivitySeconds)) ago", icon: "leaf.fill", good: model.snapshot.farmerOnline)
            MetricCard(title: "FULL NODE", value: model.snapshot.nodeSynced ? "Synced" : "Not synced", detail: "Blockchain status", icon: "link", good: model.snapshot.nodeSynced)
            MetricCard(title: "FARM SIZE", value: String(format: "%.1f TiB", model.snapshot.sizeTiB), detail: "\(model.snapshot.plots) plots", icon: "externaldrive.fill", good: model.snapshot.plots > 0)
            MetricCard(title: "HARVESTERS", value: "\(model.snapshot.harvestersOnline) / \(model.snapshot.harvestersTotal)", detail: "Connected", icon: "desktopcomputer", good: model.snapshot.harvestersOnline == model.snapshot.harvestersTotal)
            MetricCard(title: "TIME TO WIN", value: "~\(compactDuration(model.snapshot.estimatedWinSeconds))", detail: "Estimate", icon: "scope", good: true)
            MetricCard(title: "BALANCE", value: model.snapshot.balanceXCH.map { String(format: "%.3f XCH", $0) } ?? "—", detail: "Confirmed", icon: "wallet.bifold.fill", good: true)
        }
    }

    private func alertCard(_ message: String) -> some View {
        HStack(spacing: 12) { Image(systemName: "exclamationmark.triangle.fill").foregroundStyle(.orange); VStack(alignment: .leading) { Text("Needs attention").font(.subheadline.bold()); Text(message).font(.caption).foregroundStyle(.secondary) }; Spacer() }
            .padding(16).background(Color.orange.opacity(0.09), in: RoundedRectangle(cornerRadius: 16)).overlay(RoundedRectangle(cornerRadius: 16).stroke(Color.orange.opacity(0.25)))
    }

    private var freshness: some View {
        HStack { Text(model.isDemo ? "Showing sample data" : "Updated \(model.snapshot.updatedAt.formatted(.relative(presentation: .named)))"); Spacer(); if model.isLoading { ProgressView() } else { Button("Refresh") { Task { await model.refresh() } }.fontWeight(.semibold) } }
            .font(.caption).foregroundStyle(.secondary).padding(.vertical, 7)
    }

    private var healthSubtitle: String { model.snapshot.alert ?? (model.isDemo ? "Connect your miner to start." : "Everything is farming normally.") }
    private var statusColor: Color { switch model.snapshot.effectiveStatus { case .healthy: .healthGreen; case .warning: .orange; case .critical: .red; case .stale: .gray } }
}

private struct MetricCard: View {
    let title: String, value: String, detail: String, icon: String, good: Bool
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack { Image(systemName: icon).foregroundStyle(good ? Color.healthGreen : .red); Spacer(); Circle().fill(good ? Color.healthGreen : .red).frame(width: 6, height: 6) }
            VStack(alignment: .leading, spacing: 3) { Text(title).font(.caption2.monospaced().weight(.bold)).foregroundStyle(.secondary); Text(value).font(.headline); Text(detail).font(.caption2).foregroundStyle(.secondary).lineLimit(1) }
        }.frame(maxWidth: .infinity, alignment: .leading).padding(15).background(Color.cardBackground, in: RoundedRectangle(cornerRadius: 17)).overlay(RoundedRectangle(cornerRadius: 17).stroke(Color.cardBorder))
    }
}

extension Color {
    static let appBackground = Color(red: 0.025, green: 0.067, blue: 0.047)
    static let cardBackground = Color(red: 0.055, green: 0.105, blue: 0.078)
    static let cardBorder = Color.white.opacity(0.09)
    static let healthGreen = Color(red: 0.35, green: 0.86, blue: 0.53)
}
