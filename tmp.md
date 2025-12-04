# key

```text
S_PRIV = mCqcYgkgHiKiTpEYmeT/0qPpEan8V/s38GHHEBdZh3g=
S_PUB = 0Jyo3iwYaHrqPZv5zp0bzexMyRRVYA9V0T+PqE+m0Sw=
C1_PRIV = 6JZj2U1AcGnKEkg+hBMjIEove8jV0roMF25O/zxWb2M=
C1_PUB = PJVDyfR2OMFgWayruppNwd6KW5M/7iwHafYQKSYw1Eg=
```

`/etc/wireguard/wg0.conf`

```text
[Interface]
# 服务器在虚拟网络里的地址
Address = 10.10.0.1/24

# 监听端口，可以改，但建议固定，后面项目里统一用
ListenPort = 51820

# 服务器私钥
PrivateKey = mCqcYgkgHiKiTpEYmeT/0qPpEan8V/s38GHHEBdZh3g=

# 允许 IP 转发（后续做路由/NAT 用，先开着无害）
PostUp   = sysctl -w net.ipv4.ip_forward=1
PostDown = sysctl -w net.ipv4.ip_forward=0

# 如果你现在用 firewalld，后面再补 NAT 规则，这里先不加 iptables

[Peer]
# Tokamak-1 的公钥
PublicKey = PJVDyfR2OMFgWayruppNwd6KW5M/7iwHafYQKSYw1Eg=

# 允许这个客户端用的虚拟 IP
AllowedIPs = 10.10.0.2/32
```

t1.conf

```text
[Interface]
PrivateKey = 6JZj2U1AcGnKEkg+hBMjIEove8jV0roMF25O/zxWb2M=
Address = 10.10.0.2/32
DNS = 1.1.1.1

[Peer]
PublicKey = 0Jyo3iwYaHrqPZv5zp0bzexMyRRVYA9V0T+PqE+m0Sw=
AllowedIPs = 10.10.0.0/24
Endpoint = 192.168.1.6:51820
PersistentKeepalive = 25
```








