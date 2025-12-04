#!/usr/bin/env bash
set -euo pipefail

WG_IF="wg0"
WG_PORT=51820
WG_DIR="/etc/wireguard"
SERVER_KEY="${WG_DIR}/server.key"
SERVER_PUB="${WG_DIR}/server.key.pub"
WG_CONF="${WG_DIR}/${WG_IF}.conf"
SERVER_WG_IP="10.99.0.1/24"

if [[ $EUID -ne 0 ]]; then
  echo "必须用 root 运行。" >&2
  exit 1
fi

# 1) 安装 wireguard-tools
if ! command -v wg >/dev/null 2>&1; then
  dnf install -y epel-release || true
  dnf install -y wireguard-tools
fi

mkdir -p "$WG_DIR"
chmod 700 "$WG_DIR"

# 2) 生成服务器密钥对
if [[ ! -f "$SERVER_KEY" || ! -f "$SERVER_PUB" ]]; then
  umask 077
  wg genkey | tee "$SERVER_KEY" | wg pubkey > "$SERVER_PUB"
fi

SERVER_PRIV=$(cat "$SERVER_KEY")

# 3) 写 wg0.conf 的 [Interface]
cat > "$WG_CONF" <<EOF
[Interface]
Address = ${SERVER_WG_IP}
ListenPort = ${WG_PORT}
PrivateKey = ${SERVER_PRIV}
EOF

chmod 600 "$WG_CONF"

# 4) 防火墙
if command -v firewall-cmd >/dev/null 2>&1; then
  firewall-cmd --permanent --add-port=${WG_PORT}/udp || true
  firewall-cmd --reload || true
fi

# 5) 重启 wg0
wg-quick down "${WG_IF}" >/dev/null 2>&1 || true
wg-quick up "${WG_IF}"

echo "========== wg show =========="
wg show
echo "WireGuard 已初始化。公钥保存在: ${SERVER_PUB}"



