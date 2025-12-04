import os
from pathlib import Path
import socket


def _read_wg_server_pubkey() -> str:
    """
    优先从环境变量 WG_SERVER_PUBLIC_KEY 读取；
    否则从 /etc/wireguard/server.key.pub 读取；
    如果都失败，返回空字符串。
    """
    env_val = os.environ.get("WG_SERVER_PUBLIC_KEY")
    if env_val:
        return env_val.strip()

    path = Path("/etc/wireguard/server.key.pub")
    try:
        return path.read_text(encoding="ascii").strip()
    except FileNotFoundError:
        return ""


def _detect_server_ip(default: str = "127.0.0.1") -> str:
    """
    自动探测当前服务器对外使用的 IPv4 地址。

    做法：建立一个 UDP socket 连接到 8.8.8.8:80，并读取本地的
    sockname()。不真正发包，只是借这个系统调用拿到“默认出口 IP”。

    如果探测失败，则返回 default。
    """
    # 如果用户显式指定了 WG_SERVER_IP，就直接用它
    env_ip = os.environ.get("WG_SERVER_IP")
    if env_ip:
        return env_ip.strip()

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 这里地址无所谓，只要是公网 IP 即可
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return default


def _default_endpoint() -> str:
    """
    构造默认的 WireGuard Endpoint。

    规则：
    - 端口从 WG_PORT 环境变量读取，默认 51820；
    - IP 通过 _detect_server_ip() 自动探测。
    """
    port = os.environ.get("WG_PORT", "51820").strip()
    ip = _detect_server_ip()
    return f"{ip}:{port}"


class Config:
    # ================== Flask / 数据库 ==================

    # 尽快换成随机的长字符串，或者通过环境变量注入
    SECRET_KEY = os.environ.get("VPN_CONTROL_SECRET_KEY", "CHANGE_ME_SECRET")

    # SQLite 数据库
    BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    SQLALCHEMY_DATABASE_URI = (
            os.environ.get("VPN_CONTROL_DB_URI")
            or f"sqlite:///{os.path.join(BASE_DIR, 'vpn_control.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ================== WireGuard 通用配置 ==================

    # 接口名 & 监听端口
    WG_INTERFACE = os.environ.get("WG_INTERFACE", "wg0")
    WG_PORT = int(os.environ.get("WG_PORT", "51820"))

    # 服务端公钥：优先环境变量，其次 /etc/wireguard/server.key.pub
    WG_SERVER_PUBLIC_KEY = _read_wg_server_pubkey()

    # Endpoint：
    # 1. 如果设置了 WG_ENDPOINT 环境变量，直接用；
    # 2. 否则自动探测当前服务器出口 IP，拼成 "<IP>:<WG_PORT>"。
    WG_ENDPOINT = os.environ.get("WG_ENDPOINT") or _default_endpoint()

    # 客户端使用的 DNS（目前指向 WG 网关自身）
    WG_DNS = os.environ.get("WG_DNS", "10.99.0.1")

    # 客户端路由的网段（默认全导到 VPN 网段）
    WG_ALLOWED_IPS = os.environ.get("WG_ALLOWED_IPS", "10.99.0.0/24")

    # 服务器端配置文件路径（基础模板 & 实际生效配置）
    WG_SERVER_BASE_CONF = os.environ.get(
        "WG_SERVER_BASE_CONF", "/etc/wireguard/wg0-base.conf"
    )
    WG_SERVER_CONF = os.environ.get(
        "WG_SERVER_CONF", "/etc/wireguard/wg0.conf"
    )

    # ================== IP 地址池 ==================
    # IP 地址池：10.99.0.100 - 10.99.0.200（含两端）
    WG_IP_POOL_BASE = os.environ.get("WG_IP_POOL_BASE", "10.99.0.")
    WG_IP_POOL_START = int(os.environ.get("WG_IP_POOL_START", "100"))
    WG_IP_POOL_END = int(os.environ.get("WG_IP_POOL_END", "200"))
