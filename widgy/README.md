# Chia Monitor with Widgy — agentless MVP

This version installs nothing on the Chia miner. An iOS Shortcut connects using SSH, runs read-only Chia commands, and saves small text files to iCloud Drive. Widgy displays those files.

## How it works

```text
Widgy tap → iOS Shortcut → SSH → existing Chia CLI
                              ↓
Widgy text layers ← iCloud text files
```

Widgy cannot connect through SSH itself. Chia RPC is also unsuitable: it requires local TLS certificates and Chia explicitly warns not to expose its RPC ports publicly. The Shortcut route preserves the zero-install requirement.

## 1. Create the Shortcut

Open **Shortcuts** on the iPhone and create a shortcut named `Refresh Chia Monitor`.

1. Add **Run Script over SSH**.
2. Enter the miner host, SSH username, password/key and port.
3. Copy the complete contents of `chia-snapshot.sh` into the Script field.
4. Add **Get Dictionary from Input** using the SSH action's result.
5. For each entry in the table below, add **Get Dictionary Value**, then **Save File**.
6. Save to the `Shortcuts/ChiaMonitor` folder in iCloud Drive. Disable **Ask Where to Save** and enable **Overwrite If File Exists**.

| Dictionary key | File name |
|---|---|
| `status_title` | `status.txt` |
| `score` | `score.txt` |
| `farmer` | `farmer.txt` |
| `synced` | `synced.txt` |
| `plots` | `plots.txt` |
| `size` | `size.txt` |
| `activity` | `activity.txt` |
| `etw` | `etw.txt` |
| `alert` | `alert.txt` |
| `updated` | `updated.txt` |

Run the Shortcut once. Confirm the ten files appear under **Files → iCloud Drive → Shortcuts → ChiaMonitor**.

## 2. Build the Widgy layout

Create a medium Widgy and use the same dark green visual hierarchy as the app:

- Top-left: static text `CHIA FARM`
- Top-right: Files text → `status.txt`
- Large central value: Files text → `score.txt`
- Small suffix beside it: static text `/100`
- Bottom row: Files text layers for `farmer.txt`, `plots.txt`, and `size.txt`
- Alert line: Files text → `alert.txt`
- Footer: static `Updated` plus Files text → `updated.txt`

For each dynamic text layer, choose **Data → Files → File** and select the matching file in `Shortcuts/ChiaMonitor`.

Add a full-size transparent **Tap Action** layer configured to run the `Refresh Chia Monitor` Shortcut. After the Shortcut completes, reopen or reload Widgy so it reads the updated files.

Suggested colors:

- Background: `#07110D`
- Panel: `#0E1914`
- Healthy: `#59DB87`
- Warning: `#F2BD5E`
- Critical: `#F06D66`
- Secondary text: `#8D9B94`

## Important limitations

- Refresh is user-triggered. Widgy cannot reliably run an SSH session during background widget refresh.
- The iPhone must be on the miner's LAN or an existing VPN such as Tailscale.
- SSH must already be enabled. Do not expose SSH or Chia RPC directly to the internet.
- Files are deliberately separate because Widgy's Files text source does not provide the same JSON-path selection as a public JSON endpoint.
- This reads farmer, sync, plots, size, activity and ETW. Disk SMART/temperature requires tools and permissions that are not guaranteed on every miner.

Widgy supports file-backed text layers and tap actions that run Shortcuts; its JSON endpoint option is better suited to public HTTPS APIs. Chia's RPC endpoints require client certificates and should remain private.
