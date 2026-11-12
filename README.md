# shub — 局域网串口分发工具

## 1. 定位

shub 把本机的串口通过局域网共享出去，让其他电脑上的终端软件（MobaXterm、PuTTY 等）像操作本地串口一样操作它。

- **交互式 shell**：一个窗口管理所有共享
- **纯字节管道**：不做终端界面、不做脚本群发、不做指令记录，这些交给 MobaXterm
- **不发现设备**：IP 由你自己输入

```
电脑 A（挂串口）              电脑 B（MobaXterm）
┌──────────────────┐        ┌──────────────────┐
│ COM5             │        │ MobaXterm        │
│   ↓              │        │   ↓ Raw TCP      │
│ shub             │        │ 127.0.0.1:2000   │
│ share COM5       │◄─网络─►│   ↑              │
│ --tcp 1000       │        │ shub             │
└──────────────────┘        │ connect ...      │
                            └──────────────────┘
```

## 2. 安装

```bash
pip install pyserial
```

## 3. 启动

```
python main.py        （源码运行）
shub                  （打包后）
```

进入交互式 shell：

```
  shub v0.1  -  LAN serial port distributor (interactive)

  Commands:
    ports                                   List COM ports and share status
    share <port> --tcp <port> [options]     Share a COM port over TCP
    unshare <port>                          Stop sharing a COM port
    connect <ip:port> --local <port>        Forward a remote serial locally
    load <profile>                          Start from a profile file
    list                                    Show all running jobs
    help                                    Show this message
    exit                                    Stop all jobs and quit

  'share -h' / 'connect -h' shows the same options for each command.

shub>
```

## 4. 快速上手

### 步骤 1：电脑 A（挂着串口的电脑）

```
shub> ports
  PORT     DESCRIPTION                    SHARE
  COM5     USB-SERIAL CH340               not shared

shub> share COM5 --tcp 1000
  started share-COM5  (COM5 -> tcp:1000)
```

记住电脑 A 的 IP（`ipconfig` 查看，假设 `192.168.1.100`）。

### 步骤 2：电脑 B（MobaXterm 所在的电脑）

```
shub> connect 192.168.1.100:1000 --local 2000
  started connect-2000  (192.168.1.100:1000 -> 127.0.0.1:2000)
```

### 步骤 3：MobaXterm

1. `Session` → `Raw`
2. **Remote host**: `127.0.0.1`
3. **Port**: `2000`
4. `OK`

现在 MobaXterm 里敲的每个字符都发到电脑 A 的 COM5 上。

### 步骤 4：停止

```
shub> unshare COM5          （电脑 A，释放串口）
shub> exit                   （退出，所有 job 自动停止）
```

## 5. 命令参考

### 5.1 `ports` — 列出串口及共享状态

```
shub> ports
  PORT     DESCRIPTION                    SHARE
  COM5     USB-SERIAL CH340               shared on tcp:1000
  COM7     Silicon Labs CP210x            not shared
  COM9     USB-Serial Controller          not shared
```

### 5.2 `share` — 共享串口

```
shub> share <串口> --tcp <端口> [选项]
```

| 参数 | 说明 |
|---|---|
| `<串口>` | 如 `COM5` |
| `--tcp <端口>` | 监听端口（必填） |
| `--baud N` | 波特率（115200） |
| `--bytesize N` | 数据位 5/6/7/8（8） |
| `--parity X` | 校验位 N/E/O/M/S（N） |
| `--stopbits N` | 停止位 1/2（1） |
| `--flow X` | 流控 none/rts/xon（none） |
| `--password X` | 密码（`123456`） |
| `--no-password` | 关闭密码（仅限可信内网） |

`serve` 是 `share` 的别名，两者等价。

**同一串口不能重复共享**：如果 COM5 已在共享，再 `share COM5 --tcp 1001` 会报错，先 `unshare COM5`。

**不同串口用不同端口**：`COM5 → 1000`、`COM7 → 1001`、`COM9 → 1002`，互不冲突。

### 5.3 `unshare` — 取消共享

```
shub> unshare COM5
  unshared COM5 (released tcp:1000)
```

只停止共享，不关闭串口。串口释放后其他程序（Putty、串口助手）可以打开。

### 5.4 `connect` — 代理远端串口到本地

```
shub> connect <ip:port> --local <本地端口> [选项]
```

| 参数 | 说明 |
|---|---|
| `<ip:port>` | 远端 `shub share` 地址 |
| `--local <端口>` | 本地监听端口，MobaXterm 连这个 |
| `--password X` | 与远端约定密码 |
| `--no-password` | 不对远端发密码 |

本地端口只监听 `127.0.0.1`，局域网其他机器连不上（有意设计，避免转发链）。

### 5.5 `load` — 从档案启动

```
shub> load gd32
```

读 `profiles/gd32.json`，按 `type` 自动分派到 share 或 connect。档案适合**固定配置**的串口，避免每次手敲参数。默认参数只是"常见值"，档案是"你的值"。

### 5.6 `list` — 列出所有 job

```
shub> list
  NAME               KIND     STATUS              DESCRIPTION
  share-COM5         share    running (3m12s)     COM5 -> tcp:1000
  connect-2000       connect  running (0m30s)     192.168.1.100:1000 -> 127.0.0.1:2000
```

### 5.7 `help` / `exit`

- `help` 显示命令列表
- `exit` 停止所有 job，释放所有串口和端口

`share -h` / `connect -h` / `load -h` 显示对应命令的完整选项。参数错误时也会打印完整帮助。

## 6. 档案

档案是**手写的 JSON 文件**，放在 `shub/profiles/` 下。不需要程序生成，直接用文本编辑器写。

### serve 档案（`profiles/gd32.json`）

```json
{
  "type": "serve",
  "serial_port": "COM5",
  "baudrate": 115200,
  "bytesize": 8,
  "parity": "N",
  "stopbits": 1,
  "flow": "none",
  "tcp_port": 1000,
  "password": "123456"
}
```

`load gd32` 等价于 `share COM5 --tcp 1000`。省略字段用 `config.py` 默认值。

### connect 档案（`profiles/lab-server.json`）

```json
{
  "type": "connect",
  "remote": "192.168.1.100:1000",
  "local_port": 2000,
  "password": "123456"
}
```

`load lab-server` 等价于 `connect 192.168.1.100:1000 --local 2000`。

### 无密码档案

```json
{
  "type": "serve",
  "serial_port": "COM5",
  "tcp_port": 1000,
  "no_password": true
}
```

## 7. 与 MobaXterm 的配合

### 7.1 新建会话

```
Session → Raw
  Remote host: 127.0.0.1
  Port:        2000（对应 connect 的 --local）
```

### 7.2 推荐设置

**Terminal settings**：

- Local echo: 关
- **Line ending: `CR`**（letter-shell 类设备的关键，见 7.3）

**Log**：勾选 `Log terminal output to`，这就是 shub 不做"指令记录"的原因。

**MultiExec**：打开多个 Raw TCP 会话后，用 `MultiExec` 同时发指令。

### 7.3 换行符（重要）

Windows 风格终端默认发 `\r\n`。letter-shell 类设备（GD32、STM32 CLI）只认 `\r`，收到 `\r\n` 会**触发两次回车**。

**解决**：MobaXterm 的 `Settings → Configuration → Terminal → Line ending` 设为 `CR`。

shub 不处理换行符——发什么到串口就是什么。

## 8. 典型部署

### 单人访问

```
电脑 A：
  shub> share COM5 --tcp 1000

电脑 B：
  shub> connect 192.168.1.100:1000 --local 2000
  MobaXterm → Raw TCP → 127.0.0.1:2000
```

### 多串口同时共享

```
电脑 A：
  shub> share COM5 --tcp 1000
  shub> share COM7 --tcp 1001
  shub> share COM9 --tcp 1002
  shub> ports
    PORT     DESCRIPTION                    SHARE
    COM5     USB-SERIAL CH340               shared on tcp:1000
    COM7     Silicon Labs CP210x            shared on tcp:1001
    COM9     USB-Serial Controller          shared on tcp:1002
```

### 多人同时访问同一串口

服务端支持多客户端：所有人的输入都写入串口，所有输出广播给所有人。多人输入会交错，建议"一人主操，其他人旁观"。

### 同一台电脑访问多个远端

```
电脑 B：
  shub> connect 192.168.1.100:1000 --local 2000
  shub> connect 192.168.1.101:1000 --local 2001
  shub> connect 192.168.1.102:1000 --local 2002
```

MobaXterm 建三个 Raw TCP 会话分别连 2000 / 2001 / 2002。

## 9. 常见问题

**Q：`ports` 显示 COM5 是 `shared on tcp:1000`，但连不上**

- 检查电脑 A 的防火墙是否放行 1000
- `netstat -ano | findstr :1000` 确认端口在监听

**Q：`share COM5 --tcp 1000` 报 "already shared"**

- COM5 已在共享，先 `unshare COM5` 再重新 share
- `ports` 看当前共享状态

**Q：`share COM5 --tcp 1000` 报 "Cannot listen on port 1000"**

- 同一台电脑上已有另一个程序（或另一个 share）占用了 1000
- `netstat -ano | findstr :1000` 查看
- 换一个端口（`--tcp 1001`）
- 如果刚停掉一个 share，可能是 TIME_WAIT，等 2-4 分钟

**Q：`share COM5 --tcp 1000` 报 "Port COM5 not found"**

- 设备管理器确认 COM 号
- `ports` 列出当前可用串口

**Q：`connect` 报 "Remote rejected handshake"**

- 两边密码不一致，检查 `--password`

**Q：`connect` 报 "Remote connect failed"**

- 检查电脑 A 的 IP、防火墙、网络

**Q：一次回车出现两行提示符**

- MobaXterm 的 Line ending 改 `CR`
- 或用 PuTTY（默认 `CR`）

**Q：按 Ctrl+C 退出 REPL 了吗？**

- Ctrl+C 会退出 REPL，所有 job 自动停止
- Ctrl+D（EOF）和 `exit` 命令也一样

## 10. 已知限制

- **串口独占**：Windows 驱动层强制一个 COM 口同时只能被一个程序打开
- **纯字节管道**：不解析、不转换、不识别命令
- **多客户端输入交错**：需自行协调
- **无加密**：密码明文传输，敏感环境请配合内网隔离或 VPN
- **无设备发现**：IP 手动输入
- **仅 IPv4**
- **`connect` 本地端口仅监听 127.0.0.1**
- **跨外网需额外配置**（端口映射或内网穿透）
- **`--flow xon` 会吃掉 Ctrl+Q / Ctrl+S**
- **不支持 1.5 停止位**
- **Windows 下刚停的端口可能进入 TIME_WAIT**：`SO_EXCLUSIVEADDRUSE` 不允许端口复用，停掉 share 后立即重启同一端口可能失败，等待 2-4 分钟或换端口即可
- **只有交互式模式**：不支持 `shub share COM5 --tcp 1000` 一次性命令

## 11. 运行测试

```bash
cd shub/
python -m unittest discover tests -v
```

覆盖范围：

- `tests/test_profiles.py`：档案读取的成功与各种失败路径
- `tests/test_handshake.py`：密码握手协议的 round-trip（正确/错误/对端关闭）
- `tests/test_tcp_server.py`：多客户端广播、客户端输入聚合、密码拒绝

## 12. 故障排查

- **查看日志**：`shub/logs/shub.log`（滚动，最多 2MB × 3）
- **调日志级别**：`config.py` 里 `LOG_LEVEL = "DEBUG"` 重启
- **确认端口占用**：`netstat -ano | findstr :1000`
- **确认串口占用**：设备管理器 → 端口 → 右键属性

## 附录：数据流

```
MobaXterm 输入 "help\r"
    ↓ Raw TCP
shub connect 127.0.0.1:2000
    ↓ TCP
shub share 192.168.1.100:1000
    ↓ pyserial
电脑 A 的 COM5
    ↓ 串口
设备收到 "help\r"，执行
    ↓ 串口
设备回 "Help text\r\n"
    ↓ pyserial
shub share 读线程 → 广播队列
    ↓ TCP
shub connect → 本地连接
    ↓ Raw TCP
MobaXterm 显示 "Help text"
```

每一层"收字节、发字节"，不做解析。

## 附录：工程结构

```
shub/
├── main.py                  # 极简入口，启动 REPL
├── config.py                # 默认值 + build_serial_cfg()
├── logger.py                # 滚动文件日志
├── profiles.py              # 档案读取
├── README.md
├── requirements.txt         # pyserial
├── core/
│   ├── __init__.py
│   ├── errors.py            # ShubError 体系
│   ├── handshake.py         # 密码握手协议
│   ├── session_protocol.py  # SerialSessionLike Protocol
│   ├── serial_session.py    # 串口独占读写
│   ├── tcp_server.py        # TCP 广播 + 密码校验
│   ├── tcp_client.py        # TCP 转发
│   ├── serve_runner.py      # 共享串口生命周期
│   ├── connect_runner.py    # 远程代理生命周期
│   └── repl.py              # 交互式 shell
├── profiles/
│   ├── gd32.json
│   └── lab-server.json
└── tests/
    ├── __init__.py
    ├── test_profiles.py
    ├── test_handshake.py
    └── test_tcp_server.py
```