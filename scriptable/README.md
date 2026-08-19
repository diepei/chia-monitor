# Chia Monitor for Scriptable

`ChiaWidget.js` connects directly to the installed Chia Monitor agent over private Tailscale HTTPS. It does not use Chia RPC certificates and never receives wallet keys.

## Setup

1. Complete the miner installation and Tailscale steps in [`widgy/AGENT_SETUP.md`](../widgy/AGENT_SETUP.md).
2. Install **Scriptable** from the App Store.
3. Create a new Scriptable script named `Chia Monitor`.
4. Paste the complete contents of [`ChiaWidget.js`](../ChiaWidget.js).
5. Run the script once inside Scriptable.
6. Choose **Configure**, then enter:
   - the miner's Tailscale HTTPS URL, such as `https://miner.example.ts.net`;
   - the API token printed by the installer.
7. The script tests the connection before saving. The URL and token are stored in Scriptable's Keychain.
8. Add a Scriptable widget to the Home Screen and select `Chia Monitor`.

No JavaScript editing is required.

## Supported widgets

- Small: health score, primary alert, farmer and plot count
- Medium: adds farm size
- Large: adds sync, harvesters, ETW and XCH balance
- Lock Screen inline, circular and rectangular widgets

The widget asks iOS to refresh after 15 minutes, but iOS controls the actual schedule. Tapping it performs an immediate retry.

## Offline and alert behavior

- The last successful snapshot is cached locally.
- Cached or older-than-30-minute data is labeled **STALE**.
- A local notification is created when a new farm alert appears.
- Repeated refreshes do not repeat the same notification.
- Once the problem clears, the same future problem can notify again.

## Reconfigure

Open Scriptable and run `Chia Monitor`, then choose **Change connection**. The new connection is tested before replacing the saved values.

Keep Tailscale connected on the iPhone. Never expose Chia RPC, the monitor endpoint, or SSH through public router port forwarding.
