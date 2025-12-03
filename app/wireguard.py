import subprocess
from typing import Tuple

from pathlib import Path
from .config import Config
from .models import Device, db


def _get_used_host_numbers() -> set[int]:
    used = set()
    for d in Device.query.all():
        if not d.wg_ip:
            continue
        # 例如 "10.99.0.101/32"
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
    如果你暂时没装 wg，可以先返回占位字符串。
    """
    try:
        # 生成私钥
        priv = (
            subprocess.check_output(["wg", "genkey"], text=True)
            .strip()
        )
        # 根据私钥生成公钥
        pub = (
            subprocess.check_output(["wg", "pubkey"], input=priv + "\n", text=True)
            .strip()
        )
        return priv, pub
    except Exception:
        # 占位：方便你先跑通整个系统，然后再换成真实 wg 调用
        return "CHANGE_ME_PRIVATE_KEY", "CHANGE_ME_PUBLIC_KEY"


def build_client_config(device: Device) -> str:
    """根据 Device 生成客户端配置文本"""
    from .config import Config  # 避免循环导入

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


def render_peers_config() -> str:
    """把所有未吊销设备渲染成 [Peer] 段文本"""
    peers = []
    devices = Device.query.filter_by(revoked=False).all()
    for d in devices:
        peers.append(
            f"""[Peer]
PublicKey = {d.wg_public_key}
AllowedIPs = {d.wg_ip}
"""
        )
    return "\n".join(peers)


def apply_server_config() -> None:
    """
    用 base 配置 + 所有设备 Peer 重建 /etc/wireguard/wg0.conf，
    然后重启 wg0 接口。

    简单起见：直接 wg-quick down/up。
    小团队实验环境可以接受短暂中断。
    """
    base_path = Path(Config.WG_SERVER_BASE_CONF)
    conf_path = Path(Config.WG_SERVER_CONF)

    base_text = base_path.read_text().strip()
    peers_text = render_peers_config()

    full = base_text + "\n\n" + peers_text + "\n"

    tmp_path = conf_path.with_suffix(".conf.tmp")
    tmp_path.write_text(full)

    # 覆盖正式配置
    tmp_path.replace(conf_path)

    # 重启 wg0
    subprocess.run(["wg-quick", "down", "wg0"], check=False)
    subprocess.run(["wg-quick", "up", "wg0"], check=True)
