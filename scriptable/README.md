# Chia Monitor for Scriptable

`ChiaWidget.js` is the only phone client in this MVP. It connects to the agent installed on the Windows miner through private Tailscale HTTPS.

## Setup on iPhone

1. Install Tailscale, sign into the same tailnet as the Windows miner, and leave VPN access enabled.
2. Install **Scriptable** from the App Store.
3. Create a script named `Chia Monitor`.
4. Paste the complete contents of [ChiaWidget.js](../ChiaWidget.js).
5. Run the script once inside Scriptable.
6. Tap **Configure** and enter:
   - the miner URL shown by `tailscale serve status`, for example `https://miner.example.ts.net`;
   - the `api_token` from `%LOCALAPPDATA%\ChiaMonitor\config.yaml` on Windows.
7. The script tests the connection before securely saving both values in Scriptable's Keychain.
8. Add a Scriptable widget to the Home Screen and select `Chia Monitor`.

No JavaScript editing is required.

## Widget sizes

- Small: health, primary alert, farmer, and plots
- Medium: also shows farm size
- Large: also shows sync, harvesters, estimated time to win, and XCH balance
- Lock Screen: inline, circular, and rectangular layouts

iOS decides the actual refresh frequency. The widget requests an update every 15 minutes, caches the last successful reading, labels data older than 30 minutes as **STALE**, and sends one notification when a new farm alert appears.

To change the URL or token, open Scriptable and run the script again.

Do not use a public IP or router port forwarding. The URL should be the private Tailscale `https://...ts.net` address.
