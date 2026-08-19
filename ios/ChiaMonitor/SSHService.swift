import Citadel
import Foundation

enum SSHService {
    // Fixed, read-only commands. No user input is interpolated into the remote shell.
    private static let command = #"""
export PATH="$HOME/.local/bin:$HOME/chia-blockchain/venv/bin:$PATH"
CHIA="$(command -v chia 2>/dev/null || true)"
if [ -z "$CHIA" ] && [ -x "$HOME/chia-blockchain/venv/bin/chia" ]; then CHIA="$HOME/chia-blockchain/venv/bin/chia"; fi
echo '===FARM==='
if [ -n "$CHIA" ]; then "$CHIA" farm summary 2>&1; else echo 'Chia command not found'; fi
echo '===END_FARM==='
echo '===NODE==='
if [ -n "$CHIA" ]; then "$CHIA" show -s 2>&1; fi
echo '===END_NODE==='
echo '===WALLET==='
if [ -n "$CHIA" ]; then "$CHIA" wallet show 2>&1 </dev/null; fi
echo '===END_WALLET==='
LOG="$HOME/.chia/mainnet/log/debug.log"
if [ -r "$LOG" ]; then
  LAST="$(grep -E 'eligible for farming|Signage point' "$LOG" | tail -1 | cut -c1-19)"
  if [ -n "$LAST" ]; then python3 -c "import datetime,time; print('LAST_ACTIVITY_SECONDS='+str(max(0,int(time.time()-datetime.datetime.fromisoformat('$LAST').timestamp()))))" 2>/dev/null; fi
fi
"""#

    static func fetch(configuration: MinerConfiguration, password: String) async throws -> FarmSnapshot {
        let settings = SSHClientSettings(
            host: configuration.host,
            port: configuration.port,
            authenticationMethod: { .passwordBased(username: configuration.username, password: password) },
            hostKeyValidator: .acceptAnything()
        )
        let client = try await SSHClient.connect(to: settings)
        do {
            let buffer = try await client.executeCommand(command, maxResponseSize: 2 * 1_024 * 1_024, mergeStreams: true)
            try await client.close()
            return try ChiaOutputParser.parse(String(buffer: buffer))
        } catch {
            try? await client.close()
            throw error
        }
    }
}
