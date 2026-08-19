# Widgy with the Chia Monitor agent

This is the recommended Widgy setup. It refreshes without running an SSH Shortcut and supports the complete health snapshot. Chia RPC remains bound to localhost; only the small read-only monitor endpoint is reachable through Tailscale.

## 1. Install the agent

After a GitHub release has been published, run this as the normal Chia user on a supported Linux miner:

```bash
curl -fsSL https://raw.githubusercontent.com/diepei/chia-monitor/main/install.sh | bash
```

The installer:

- detects Linux x86-64 or ARM64;
- downloads one standalone binary;
- verifies its SHA-256 checksum;
- generates a random API token and prints it once;
- creates a user-level systemd service;
- never opens or modifies Chia RPC ports.

Save the printed Widgy API token. The configuration is stored at `~/.config/chia-monitor/config.yaml`.

## 2. Make it reachable privately

Install/sign in to Tailscale on the miner and iPhone, then run on the miner:

```bash
tailscale serve --bg http://127.0.0.1:8926
tailscale serve status
```

Copy the HTTPS `*.ts.net` address. Do not port-forward the agent, SSH, or Chia RPC through the router.

Test from the iPhone while connected to Tailscale:

```text
https://your-miner.your-tailnet.ts.net/healthz
```

It should return `{"ok":true}`. Farm data remains protected by the API token.

## 3. Connect Widgy

For each dynamic text layer in Widgy:

1. Choose **Data → JSON Endpoint**.
2. Set the endpoint to `https://your-miner.your-tailnet.ts.net/api/widgy`.
3. Use method **GET**.
4. Add header `Authorization` with value `Bearer YOUR_API_TOKEN`.
5. Run the endpoint and select the desired JSON field.

The endpoint is intentionally flat so every value is easy to select:

| Widgy field | Example |
|---|---|
| `health_score` | `96` |
| `health_label` | `Healthy` |
| `health_color` | `#59DB87` |
| `farmer_status` | `Online` |
| `node_status` | `Synced` |
| `plots` | `742` |
| `farm_size` | `73.4 TiB` |
| `harvesters` | `2 / 2` |
| `activity` | `18s` |
| `etw` | `12d` |
| `balance` | `4.126 XCH` |
| `failed_plots` | `0` |
| `alert` | `Everything is farming normally` |
| `updated` | `10:15` |

Add a **Reload Widget** tap action to refresh on demand. Widgy and iOS still decide background refresh timing, but no SSH interaction is needed from the phone.

## Updating or removing

Run the installer again after a new release to replace only the binary and preserve the configuration.

To stop and disable the Linux user service:

```bash
systemctl --user disable --now chia-monitor
```

The agent is read-only. It has no endpoints for sending XCH, changing keys, plotting, or starting/stopping Chia services.
