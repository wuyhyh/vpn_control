先把文档给你，然后再讲这四个密钥在密码学上的原理。

---

## 《vpn_control 项目文档 01：单服务器 + 单客户端 WireGuard 虚拟网络配置说明》

### 1. 场景与目标

物理环境：

* 服务器：Rocky Linux

    * 通过无线网卡 `wlp0s20f3` 接入家庭路由器
    * 家庭局域网 IP：`192.168.1.6`
* 客户端：Tokamak-1（Windows 11）

    * 能直接 SSH 登录 `192.168.1.6`（说明物理网络是通的）

目标：

在此基础上，建立一条稳定的 WireGuard 虚拟网络：

* 虚拟网段：`10.10.0.0/24`
* 服务器虚拟 IP：`10.10.0.1`
* Tokamak-1 虚拟 IP：`10.10.0.2`
* 初始阶段只保证：

    * Windows 能 ping `10.10.0.1`
    * 服务器能 ping `10.10.0.2`
    * 不做任何 NAT、不访问其他网段，只验证隧道本身稳定。

---

### 2. 密钥对与标识

在 Rocky 上生成了两对密钥：

* 服务器密钥对（长期静态）：

    * `S_PRIV = mCqcYgkgHiKiTpEYmeT/0qPpEan8V/s38GHHEBdZh3g=`
    * `S_PUB  = 0Jyo3iwYaHrqPZv5zp0bzexMyRRVYA9V0T+PqE+m0Sw=`
* Tokamak-1 客户端密钥对（长期静态）：

    * `C1_PRIV = 6JZj2U1AcGnKEkg+hBMjIEove8jV0roMF25O/zxWb2M=`
    * `C1_PUB  = PJVDyfR2OMFgWayruppNwd6KW5M/7iwHafYQKSYw1Eg=`

约定：

* `S_PRIV`：服务器私钥，仅存在于 Rocky 服务器，绝不泄露。
* `S_PUB`：服务器公钥，分发给所有客户端，用于识别与加密。
* `C1_PRIV`：Tokamak-1 私钥，仅存在于 Tokamak-1。
* `C1_PUB`：Tokamak-1 公钥，写入服务器配置，让服务器识别此客户端。

---

### 3. 服务器端配置（Rocky）

#### 3.1 安装与目录

在 Rocky 上：

```bash
sudo dnf install -y wireguard-tools

sudo mkdir -p /etc/wireguard/keys
sudo chmod 700 /etc/wireguard/keys
```

密钥文件存放在 `/etc/wireguard/keys/` 中（已经生成完毕，这里不再重复命令）。

#### 3.2 `/etc/wireguard/wg0.conf`

创建配置文件：

```bash
sudo mkdir -p /etc/wireguard
sudo chmod 700 /etc/wireguard
sudo nano /etc/wireguard/wg0.conf
```

内容为（已填入实际密钥）：

```ini
[Interface]
# 服务器在虚拟网络中的地址
Address = 10.10.0.1/24

# WireGuard 监听端口
ListenPort = 51820

# 服务器私钥（严格保密）
PrivateKey = mCqcYgkgHiKiTpEYmeT/0qPpEan8V/s38GHHEBdZh3g=

# 启动/停止时开启或关闭 IP 转发
PostUp = sysctl -w net.ipv4.ip_forward=1
PostDown = sysctl -w net.ipv4.ip_forward=0

[Peer]
# Tokamak-1（Windows 客户端）的公钥
PublicKey = PJVDyfR2OMFgWayruppNwd6KW5M/7iwHafYQKSYw1Eg=

# 为该客户端分配的虚拟 IP（单主机 /32）
AllowedIPs = 10.10.0.2/32
```

权限：

```bash
sudo chmod 600 /etc/wireguard/wg0.conf
```

#### 3.3 防火墙

如果启用了 firewalld：

```bash
sudo firewall-cmd --permanent --add-port=51820/udp
sudo firewall-cmd --reload
```

#### 3.4 启动 WireGuard 接口

手动启动测试：

```bash
sudo wg-quick up wg0
```

验证：

```bash
ip addr show wg0
wg show
```

预期：

* `wg0` 设备存在，IP 为 `10.10.0.1/24`。
* `wg show` 显示一个 peer（Tokamak-1），此时还没有 handshake（客户端尚未连接）。

可选：设置开机自启

```bash
sudo systemctl enable wg-quick@wg0
```

---

### 4. 客户端配置（Tokamak-1 / Windows）

#### 4.1 WireGuard for Windows

在 Windows 上安装 WireGuard（官方客户端），使用 GUI 管理。

#### 4.2 新建隧道配置

在 GUI 中：

1. 新建一个空的 tunnel。
2. 编辑配置，内容为：

```ini
[Interface]
# Tokamak-1 的私钥
PrivateKey = 6JZj2U1AcGnKEkg+hBMjIEove8jV0roMF25O/zxWb2M=

# Tokamak-1 在虚拟网络中的地址
Address = 10.10.0.2/32

# DNS 可选，这里设为公共 DNS
DNS = 1.1.1.1

[Peer]
# 服务器公钥
PublicKey = 0Jyo3iwYaHrqPZv5zp0bzexMyRRVYA9V0T+PqE+m0Sw=

# 通过隧道访问的目标网段：这里是整个虚拟网段 10.10.0.0/24
AllowedIPs = 10.10.0.0/24

# 服务器的物理地址（家庭路由器分配的 Wi-Fi IP）
Endpoint = 192.168.1.6:51820

# 为了穿过 NAT，定期发 Keepalive 包（秒）
PersistentKeepalive = 25
```

然后在 GUI 中点击「Activate」启动隧道。

---

### 5. 连通性验证

#### 5.1 从 Windows 到服务器

在 Windows 的 CMD 或 PowerShell 中：

```powershell
ping 10.10.0.1
```

预期：可以 ping 通。

同时检查 WireGuard GUI：

* `Latest handshake` 有时间戳；
* `Transfer` 中的 sent/received 字节数持续增加。

#### 5.2 从服务器到 Windows

在 Rocky 上：

```bash
ping 10.10.0.2
sudo wg show
```

预期：

* ping 正常。
* `wg show` 对应 peer 的 `latest handshake` 有时间，`transfer` 统计有流量。

至此，单服务器 + 单客户端的 WireGuard 虚拟网络搭建完成，通信稳定。

---

### 6. 当前阶段的刻意约束与后续计划

为了避免一上来就复杂化，这一阶段**刻意不做**：

* 不做自动检测服务器 IP，`Endpoint = 192.168.1.6:51820` 完全手工维护；
* 不做任意网段的转发与 NAT，只在 `10.10.0.0/24` 内互通；
* 不使用数据库、不做 Web 管理，仅依赖两个静态配置文件。

后续 vpn_control 项目后端规划：

1. 把本篇文档形式化为 `docs/01-single-server-single-client.md`，作为基础环境说明。
2. 新增一个「配置生成模块」，接收一个简单的数据结构（如 YAML）：

    * `server: { private_key, listen_port, address }`
    * `peers: [ { name, public_key, allowed_ips }, ... ]`
3. 后端脚本只负责**生成**：

    * 服务器用的 `wg0.conf`；
    * 每个客户端的 `<name>.conf`；
      不直接操作系统网络栈，避免状态错乱。

---

## 第二部分：四个密钥在密码学上的工作原理

你给出的四个值是 WireGuard 使用的**椭圆曲线密钥对**，具体是 Curve25519 上的密钥（WireGuard 使用的是 X25519 算法）。

### 1. “公钥 / 私钥”到底是什么意思？

先不看数学细节，只记住两个关键点：

1. 私钥（private key）

    * 是一串随机的 32 字节数据（用安全随机数生成器产生）。
    * 必须严格保密，只存在于本机。
    * 在 WireGuard 里用来：

        * 证明“我是这台机器”（身份认证的一部分）。
        * 与对方的公钥一起，计算出一个共享的对称密钥（用于加密）。

2. 公钥（public key）

    * 由私钥通过一个**不可逆的数学运算**算出来（椭圆曲线上的标量乘法）。
    * 可以公开分发给任何人。
    * 别人拿到你的公钥，无法反推出你的私钥（在数学上被认为几乎不可能）。
    * 在 WireGuard 里用来：

        * 唯一标识一个 peer（配置里的 `[Peer] PublicKey`）。
        * 与对方的私钥一起，计算出共享密钥。

所以：

* `S_PRIV` → 通过 X25519 算法 → `S_PUB`
* `C1_PRIV` → 通过 X25519 算法 → `C1_PUB`

其中计算方向是**单向**的：
你可以从私钥算出公钥，但几乎不可能从公钥算出私钥。

---

### 2. WireGuard 里这四个值是怎么配合工作的？

我们有两台机器：

* 服务器：`S_PRIV` / `S_PUB`
* 客户端：`C1_PRIV` / `C1_PUB`

在配置中：

* 服务端 `wg0.conf` 里：

    * `[Interface] PrivateKey = S_PRIV`
    * `[Peer] PublicKey = C1_PUB`
* 客户端配置里：

    * `[Interface] PrivateKey = C1_PRIV`
    * `[Peer] PublicKey = S_PUB`

当隧道建立（握手）时，大致发生了这些事情（简化版）：

1. 客户端用自己的私钥 `C1_PRIV` 和服务器的公钥 `S_PUB`，做一次椭圆曲线 Diffie-Hellman（ECDH）计算，得到一个“共享秘密”：

    * 记为 `K = DH(C1_PRIV, S_PUB)`

2. 服务器用自己的私钥 `S_PRIV` 和客户端的公钥 `C1_PUB`，也做同样的计算：

    * `K' = DH(S_PRIV, C1_PUB)`

椭圆曲线 Diffie-Hellman 的核心性质是：

> `DH(C1_PRIV, S_PUB) == DH(S_PRIV, C1_PUB)`

也就是：
两边计算出来的“共享秘密”是**完全相同的**，但中间传输的只是一堆用公钥加密过的数据，网络上看不到这两边的私钥。

3. 有了这个共享秘密 `K` 之后，WireGuard 再通过 HKDF 等算法导出真正用于加密数据包的对称密钥，然后用 ChaCha20-Poly1305
   这样的算法来实际加解密每一个 UDP 数据包。

你可以把流程简化理解为：

* 私钥 + 对方公钥 → 得到一个双方一致、别人不知道的随机数（共享秘密）。
* 这个“共享秘密”再加工，变成真正的对称加密密钥。
* 后面所有流量都用对称加密（速度快）。

---

### 3. 为什么要“双方各有一对密钥”？

因为它要做到两件事：

1. **身份确认（我是谁 / 你是谁）**

    * 服务器配置里写着：“允许公钥为 `C1_PUB` 的 peer 访问 `10.10.0.2/32`”。
    * 客户端连接时，用私钥 `C1_PRIV` 参与握手。
    * 如果握手里的签名/计算结果对不上服务器配置中的公钥 `C1_PUB`，服务器就知道“这个不是 Tokamak-1”，直接丢弃。

2. **安全地协商出一个共享密钥**

    * 即前面说的 ECDH：只有拥有正确私钥的一方，才能和对方的公钥一起算出正确的共享秘密。
    * 网络上的中间人即使全部抓包，因为没有私钥，也算不出这个共享秘密。

所以这四个值在拓扑中的角色是：

* `S_PRIV`：服务器的“主身份”和握手私钥；
* `S_PUB`：对外公告“我是这个 VPN 服务器”的标识；
* `C1_PRIV`：Tokamak-1 的“主身份”和握手私钥；
* `C1_PUB`：服务器眼中用来识别 Tokamak-1 的 ID。

---

### 4. 为什么这些 Base64 字符串看起来都差不多？

比如：

```text
mCqcYgkgHiKiTpEYmeT/0qPpEan8V/s38GHHEBdZh3g=
0Jyo3iwYaHrqPZv5zp0bzexMyRRVYA9V0T+PqE+m0Sw=
```

这些其实都是**32 字节二进制数据的 Base64 编码**：

* 对机器来说本质是 32 字节的随机数（私钥）或曲线上的点（公钥）。
* 用 Base64 是为了在配置文件中作为可打印字符串方便拷贝。

WireGuard 对你屏蔽了所有底层细节，你只需要：

* 把私钥贴到 `[Interface] PrivateKey`；
* 把对方的公钥贴到 `[Peer] PublicKey`；
* 双方 IP / 端口 / AllowedIPs 对齐；
* 就能得到一条安全的加密隧道。

---

### 5. 一个现实上的提醒

因为你已经把这组密钥发给我了，这套密钥就**不再适合用于真正的生产环境**（任何拿到这段对话的人都可以伪装 Tokamak-1 或服务器）。

后面如果进入正式部署阶段，建议：

* 重新生成一套新的 server / client 密钥；
* 老的这套密钥只用于学习和实验文档。

---

如果你愿意，下一步我们可以把这一套写成一个项目目录结构，比如：

```text
vpn_control/
  docs/
    01-single-server-single-client.md
  samples/
    server_wg0.conf
    client_tokamak1.conf
```

然后开始设计一个最小的 `gen_configs.py`，从一个简单的 `config.yaml` 生成这两个配置文件，这样你以后只维护 YAML，不手改
wg0.conf。

