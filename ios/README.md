# Chia Monitor for iPhone — MVP

This native SwiftUI app reads a Linux Chia miner over SSH. Nothing extra is installed on the miner. The included WidgetKit extension shows the last sanitized snapshot saved by the app.

## Requirements

- iPhone running iOS 17 or newer
- A Mac with Xcode 16 or newer
- SSH enabled on the Chia miner
- The iPhone and miner on the same LAN or an existing VPN such as Tailscale
- The SSH user can run `chia farm summary`, `chia show -s`, and optionally `chia wallet show`

## Run the MVP

1. Open `ChiaMonitor.xcodeproj` in Xcode.
2. Select the **ChiaMonitor** target and choose your Apple Development team.
3. Select the **ChiaWidget** target and use the same team.
4. If Xcode reports an App Group conflict, replace `group.com.diepei.chiamonitor` in both entitlement files and `Shared/FarmSnapshot.swift` with an identifier owned by your team.
5. Connect your iPhone, choose it as the run destination, and press Run.
6. In the app, tap **Demo**, enter the miner hostname/IP, SSH username, port, and password, then save.
7. Long-press the iPhone Home Screen, choose **Add Widget**, search for Chia Monitor, and add the small or medium widget.

The SSH password is stored in the device-only iOS Keychain. The widget receives only health values through the App Group; it never receives the password or SSH configuration.

## Miner preparation

No Chia Monitor software is installed. SSH must already be enabled:

- Ubuntu/Debian: confirm `systemctl status ssh` and allow SSH through the local firewall.
- macOS: enable **System Settings → General → Sharing → Remote Login**.
- Keep SSH private to the LAN or a VPN. Do not expose port 22 directly to the internet.

Test from the Mac before using the app:

```bash
ssh your-user@miner-address 'chia farm summary && chia show -s'
```

## MVP limitations

- Password login only. Private-key authentication is the next recommended feature.
- The current SSH connection accepts the presented host key. Before public distribution, add trusted-host fingerprint onboarding to prevent man-in-the-middle attacks.
- The widget displays the last snapshot collected by the main app. iOS controls widget refresh timing, and widgets cannot reliably open long SSH sessions. Data older than 30 minutes is marked stale.
- Chia CLI output can vary between releases. The parser currently targets standard English output from current Chia releases.
- Linux/macOS miners are the initial target. Windows command adapters are not included yet.
- SMART temperatures and failed plot details are not part of the agentless MVP because they require platform-specific permissions and tools.

## Recommended next milestones

1. SSH private-key authentication and host fingerprint verification
2. A connection test with actionable error messages
3. Multiple miner profiles
4. More Chia CLI fixtures and parser tests
5. Optional background refresh and alert notifications
6. Windows miner support

The project pins [Citadel 0.12.1](https://github.com/orlandos-nl/Citadel) for its Swift SSH client.
