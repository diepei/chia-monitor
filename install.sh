#!/usr/bin/env bash
set -euo pipefail

REPOSITORY="diepei/chia-monitor"
INSTALL_DIR="$HOME/.local/bin"
CONFIG_DIR="$HOME/.config/chia-monitor"
SERVICE_DIR="$HOME/.config/systemd/user"

case "$(uname -s)-$(uname -m)" in
  Linux-x86_64) ASSET="chia-monitor-linux-x86_64" ;;
  Linux-aarch64|Linux-arm64) ASSET="chia-monitor-linux-arm64" ;;
  Darwin-arm64) ASSET="chia-monitor-macos-arm64" ;;
  *) echo "Unsupported platform: $(uname -s) $(uname -m)"; exit 1 ;;
esac

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
BASE_URL="https://github.com/$REPOSITORY/releases/latest/download"

echo "Downloading Chia Monitor..."
curl --fail --location --silent --show-error "$BASE_URL/$ASSET" -o "$TMP_DIR/chia-monitor"
curl --fail --location --silent --show-error "$BASE_URL/SHA256SUMS" -o "$TMP_DIR/SHA256SUMS"

EXPECTED="$(awk -v file="$ASSET" '$2 == file {print $1}' "$TMP_DIR/SHA256SUMS")"
if command -v sha256sum >/dev/null 2>&1; then
  ACTUAL="$(sha256sum "$TMP_DIR/chia-monitor" | awk '{print $1}')"
else
  ACTUAL="$(shasum -a 256 "$TMP_DIR/chia-monitor" | awk '{print $1}')"
fi
if [ -z "$EXPECTED" ] || [ "$EXPECTED" != "$ACTUAL" ]; then
  echo "Checksum verification failed; installation stopped."
  exit 1
fi

mkdir -p "$INSTALL_DIR" "$CONFIG_DIR"
install -m 0755 "$TMP_DIR/chia-monitor" "$INSTALL_DIR/chia-monitor"

if [ ! -f "$CONFIG_DIR/config.yaml" ]; then
  "$INSTALL_DIR/chia-monitor" --init-config --config "$CONFIG_DIR/config.yaml" --chia-root "$HOME/.chia/mainnet"
else
  echo "Keeping existing configuration: $CONFIG_DIR/config.yaml"
fi

if [ "$(uname -s)" = "Linux" ] && command -v systemctl >/dev/null 2>&1; then
  mkdir -p "$SERVICE_DIR"
  SERVICE_FILE="$SERVICE_DIR/chia-monitor.service"
  {
    echo '[Unit]'
    echo 'Description=Chia Monitor agent'
    echo 'After=network-online.target'
    echo
    echo '[Service]'
    echo "ExecStart=$INSTALL_DIR/chia-monitor --config $CONFIG_DIR/config.yaml"
    echo 'Restart=on-failure'
    echo 'RestartSec=10'
    echo 'NoNewPrivileges=true'
    echo
    echo '[Install]'
    echo 'WantedBy=default.target'
  } > "$SERVICE_FILE"
  systemctl --user daemon-reload
  systemctl --user enable --now chia-monitor
  echo "Service started. Check it with: systemctl --user status chia-monitor"
else
  echo "Start the agent with: $INSTALL_DIR/chia-monitor --config $CONFIG_DIR/config.yaml"
fi

echo
echo "Local health check: http://127.0.0.1:8926/healthz"
echo "For Widgy over Tailscale HTTPS: tailscale serve --bg http://127.0.0.1:8926"
