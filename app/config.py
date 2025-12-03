import os


class Config:
    # 尽快换成随机的长字符串
    SECRET_KEY = os.environ.get("VPN_CONTROL_SECRET_KEY", "CHANGE_ME_SECRET")

    # SQLite 数据库
    BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    SQLALCHEMY_DATABASE_URI = (
            os.environ.get("VPN_CONTROL_DB_URI")
            or f"sqlite:///{os.path.join(BASE_DIR, 'vpn_control.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # WireGuard 相关配置（后面你要改）
    # 服务器 wg0 的公钥：在服务器上 wg genkey / wg pubkey 之后填这里
    WG_SERVER_PUBLIC_KEY = os.environ.get("WG_SERVER_PUBLIC_KEY", "CHANGE_ME_WG_PUBKEY")
    # 对外的 Endpoint（可以是公网 IP 或域名）
    WG_ENDPOINT = os.environ.get("WG_ENDPOINT", "vpn.example.com:51820")
    # 客户端使用的 DNS（先指向网关地址，将来你可以搞内部 DNS）
    WG_DNS = os.environ.get("WG_DNS", "10.99.0.1")
    # 客户端路由的网段（先全部导向 10.99.0.0/24）
    WG_ALLOWED_IPS = os.environ.get("WG_ALLOWED_IPS", "10.99.0.0/24")

    # IP 地址池：10.99.0.100 - 10.99.0.200
    WG_IP_POOL_BASE = "10.99.0."
    WG_IP_POOL_START = 100
    WG_IP_POOL_END = 200
