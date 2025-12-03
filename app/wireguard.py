import os
import subprocess
from typing import Tuple

from .config import Config
from .models import Device, db

# 服务器端 WireGuard 配置文件路径
SERVER_BASE_CONF = "/etc/wireguard/wg0-base.conf"
SERVER_CONF = "/etc/wireguard/wg0.conf"


def _get_used_host_numbers() -> set[int]:
    used = set()
    for d in Device.query.all():
        if not d.wg_ip:
            continue
        ip_part = d.wg_ip.split("/")[0]
        host_str = ip_part.split(".")[-1]
        try:
            used.add(int(host_str))
        except ValueError:
            continue
    return used


def allocate_ip() -> str:
    """从 IP 池中分配一个未使用的地址，返回 '10.99.0.X/32'"""
    used = _get_used_host_numbers()
    for host in range(Config.WG_IP_POOL_START, Config.WG_IP_POOL_END + 1):
        if host not in used:
            return f"{Config.WG_IP_POOL_BASE}{host}/32"
    raise RuntimeError("IP 池已满，请扩展地址范围")


def generate_keys() -> Tuple[str, str]:
    """
    生成 WireGuard 私钥/公钥对。

    需要系统已安装 `wg` 命令。
    如果失败，则返回占位字符串，方便先跑通整体流程。
    """
    try:
        priv = (
            subprocess.check_output(["wg", "genkey"], text=True)
            .strip()
        )
        pub = (
            subprocess.check_output(["wg", "pubkey"], input=priv + "\n", text=True)
            .strip()
        )
        return priv, pub
    except Exception:
        # 占位：方便你先调试其他逻辑
        return "CHANGE_ME_PRIVATE_KEY", "CHANGE_ME_PUBLIC_KEY"


def build_client_config(device: Device) -> str:
    """根据 Device 生成客户端配置文本"""
    return f"""[Interface]
Address = {device.wg_ip}
PrivateKey = {device.wg_private_key}
DNS = {Config.WG_DNS}

[Peer]
PublicKey = {Config.WG_SERVER_PUBLIC_KEY}
Endpoint = {Config.WG_ENDPOINT}
AllowedIPs = {Config.WG_ALLOWED_IPS}
PersistentKeepalive = 25
"""


def apply_server_config() -> None:
    """
    根据数据库中的设备列表生成 /etc/wireguard/wg0.conf，
    然后重启 wg0 接口，使配置生效。
    """
    if not os.path.exists(SERVER_BASE_CONF):
        raise RuntimeError(f"服务器基础配置 {SERVER_BASE_CONF} 不存在")

    # 1) 读基础配置
    with open(SERVER_BASE_CONF, "r") as f:
        base = f.read().rstrip() + "\n\n"

    # 2) 拼接所有设备的 [Peer] 段（只包含未撤销的设备）
    peers_lines: list[str] = []
    devices = Device.query.filter_by(revoked=False).all()

    for d in devices:
        peers_lines.append("[Peer]")
        peers_lines.append(f"PublicKey = {d.wg_public_key}")
        peers_lines.append(f"AllowedIPs = {d.wg_ip}")
        peers_lines.append("")

    content = base + "\n".join(peers_lines) + "\n"

    # 3) 写入 wg0.conf
    with open(SERVER_CONF, "w") as f:
        f.write(content)
    os.chmod(SERVER_CONF, 0o600)

    # 4) 重启 wg0 接口（简单粗暴版本）
    #    如果 wg0 还没 up，down 会失败但我们忽略它
    subprocess.run(["wg-quick", "down", "wg0"], check=False)
    subprocess.run(["wg-quick", "up", "wg0"], check=True)
