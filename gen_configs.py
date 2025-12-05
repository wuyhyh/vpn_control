#!/usr/bin/env python3
"""
gen_configs.py

读取 config.yaml，生成 WireGuard 服务器和客户端配置文件。

- 服务器配置输出到: generated/server/wg0.conf
- 客户端配置输出到: generated/clients/<peer_name>.conf
"""

import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


def load_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("config.yaml root should be a mapping (dictionary)")
    return data


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def join_csv(values: List[str]) -> str:
    return ", ".join(values)


def render_server_conf(server: Dict[str, Any], peers: List[Dict[str, Any]]) -> str:
    """
    生成服务器端 wg0.conf 内容。
    """
    required_fields = ["address", "listen_port", "private_key"]
    for field in required_fields:
        if field not in server:
            raise ValueError(f"server.{field} is required in config.yaml")

    address = server["address"]
    listen_port = server["listen_port"]
    private_key = server["private_key"]

    post_up_cmds = server.get("post_up", [])
    post_down_cmds = server.get("post_down", [])

    lines: List[str] = []
    lines.append("[Interface]")
    lines.append(f"Address = {address}")
    lines.append(f"ListenPort = {listen_port}")
    lines.append(f"PrivateKey = {private_key}")

    # PostUp / PostDown 支持多条命令，按顺序写入
    if post_up_cmds:
        # WireGuard 原生支持多条 PostUp/Down，多个重复键是允许的
        for cmd in post_up_cmds:
            lines.append(f"PostUp = {cmd}")
    if post_down_cmds:
        for cmd in post_down_cmds:
            lines.append(f"PostDown = {cmd}")

    lines.append("")  # 空行分隔

    # 每个 peer 生成一个 [Peer] 段
    for peer in peers:
        name = peer.get("name", "<unnamed>")
        pub = peer.get("public_key")
        if not pub:
            raise ValueError(f"peer '{name}' missing public_key")

        # allowed_ips 是 server 视角下通过该 peer 可达的网段
        allowed_ips = peer.get("allowed_ips")
        if not allowed_ips:
            # 默认至少把 peer 自己的 address 作为 AllowedIPs
            addr = peer.get("address")
            if not addr:
                raise ValueError(
                    f"peer '{name}' missing allowed_ips and address; "
                    "at least one of them must be present"
                )
            allowed_ips = [addr]

        lines.append("[Peer]")
        lines.append(f"# {name}")
        lines.append(f"PublicKey = {pub}")
        lines.append(f"AllowedIPs = {join_csv(allowed_ips)}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def get_server_endpoint(server: Dict[str, Any]) -> Optional[str]:
    """
    从 server 配置中获取 Endpoint "host:port" 字符串。
    如未定义 endpoint_host/endpoint_port，则返回 None。
    """
    host = server.get("endpoint_host")
    port = server.get("endpoint_port")
    if host and port:
        return f"{host}:{port}"
    return None


def render_client_conf(
        server: Dict[str, Any],
        peer: Dict[str, Any],
) -> str:
    """
    生成单个客户端配置文件内容。
    """
    name = peer.get("name", "<unnamed>")

    # peer 本身字段检查
    required_fields = ["address", "private_key"]
    for field in required_fields:
        if field not in peer:
            raise ValueError(f"peer '{name}' missing required field '{field}'")

    address = peer["address"]
    private_key = peer["private_key"]

    # DNS（可选）
    dns_list = peer.get("dns", [])

    # server 字段
    server_pub = server.get("public_key")
    if not server_pub:
        raise ValueError("server.public_key is required to generate client configs")

    # 客户端 AllowedIPs 优先使用 peer.client_allowed_ips，其次 server.client_allowed_ips
    client_allowed_ips = peer.get("client_allowed_ips")
    if not client_allowed_ips:
        client_allowed_ips = server.get("client_allowed_ips")
    if not client_allowed_ips:
        raise ValueError(
            f"peer '{name}' has no client_allowed_ips and server.client_allowed_ips "
            "is not defined; one of them must be present"
        )

    endpoint = get_server_endpoint(server)
    if not endpoint:
        raise ValueError(
            "server.endpoint_host/endpoint_port must be set to generate client configs"
        )

    keepalive = peer.get("persistent_keepalive")

    lines: List[str] = []

    # [Interface]
    lines.append("[Interface]")
    lines.append(f"PrivateKey = {private_key}")
    lines.append(f"Address = {address}")
    if dns_list:
        lines.append(f"DNS = {join_csv(dns_list)}")
    lines.append("")  # 空行

    # [Peer]
    lines.append("[Peer]")
    lines.append(f"# server: {server.get('name', 'server')}")
    lines.append(f"PublicKey = {server_pub}")
    lines.append(f"AllowedIPs = {join_csv(client_allowed_ips)}")
    lines.append(f"Endpoint = {endpoint}")
    if keepalive is not None:
        lines.append(f"PersistentKeepalive = {keepalive}")

    lines.append("")  # 末尾空行方便阅读

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate WireGuard configs from config.yaml"
    )
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        default="config.yaml",
        help="Path to config.yaml (default: ./config.yaml)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        default="generated",
        help="Output directory (default: ./generated)",
    )
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    output_dir = Path(args.output_dir).resolve()

    data = load_config(config_path)

    server = data.get("server")
    peers = data.get("peers")

    if not server or not isinstance(server, dict):
        raise ValueError("config.yaml must contain a 'server' mapping")
    if not peers or not isinstance(peers, list):
        raise ValueError("config.yaml must contain a 'peers' list")

    # 输出目录
    server_dir = output_dir / "server"
    clients_dir = output_dir / "clients"
    ensure_dir(server_dir)
    ensure_dir(clients_dir)

    # 生成服务器配置
    server_conf_text = render_server_conf(server, peers)
    server_conf_path = server_dir / "wg0.conf"
    server_conf_path.write_text(server_conf_text, encoding="utf-8")
    print(f"[+] wrote server config: {server_conf_path}")

    # 生成每个客户端配置
    for peer in peers:
        name = peer.get("name")
        if not name:
            raise ValueError("each peer must have a 'name'")
        client_conf_text = render_client_conf(server, peer)
        client_conf_path = clients_dir / f"{name}.conf"
        client_conf_path.write_text(client_conf_text, encoding="utf-8")
        print(f"[+] wrote client config: {client_conf_path}")


if __name__ == "__main__":
    main()
