import SwiftUI

struct SetupView: View {
    @EnvironmentObject private var model: FarmViewModel
    @Environment(\.dismiss) private var dismiss
    @State private var configuration: MinerConfiguration
    @State private var password = ""
    @State private var error: String?

    init() { _configuration = State(initialValue: ConfigurationStore.load()) }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Farm name", text: $configuration.name)
                    TextField("IP address or hostname", text: $configuration.host).textInputAutocapitalization(.never).autocorrectionDisabled()
                    TextField("SSH username", text: $configuration.username).textInputAutocapitalization(.never).autocorrectionDisabled()
                    TextField("Port", value: $configuration.port, format: .number).keyboardType(.numberPad)
                    SecureField("SSH password", text: $password)
                } header: { Text("Miner connection") } footer: { Text("The password is stored in this iPhone's Keychain and is never shared with the widget.") }

                Section("Before connecting") {
                    Label("SSH must be enabled on the miner", systemImage: "checkmark.circle")
                    Label("Your phone must be on the same network or VPN", systemImage: "wifi")
                    Label("Chia must be available for this SSH user", systemImage: "leaf")
                }
                if let error { Section { Text(error).foregroundStyle(.red) } }
            }
            .navigationTitle("Connect your farm")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Cancel") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) { Button("Save") { save() }.disabled(!configuration.isComplete || password.isEmpty) }
            }
        }
    }

    private func save() {
        do { try model.save(configuration: configuration, password: password); dismiss(); Task { await model.refresh() } }
        catch { self.error = error.localizedDescription }
    }
}
