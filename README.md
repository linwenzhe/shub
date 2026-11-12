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
    save <profile> [job | -l]               Save a running job as a profile
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
shub> load <档案名>
```

读 `profiles/<档案名>.json`，按 `type` 自动分派：

- `"type": "serve"` → 自动执行 `share` 流程
- `"type": "connect"` → 自动执行 `connect` 流程

**`load` 就是启动**，执行完 job 已经在后台跑了，不需要再敲 `share` 或 `connect`。

档案适合**固定配置**的串口，避免每次手敲参数。默认参数只是"常见值"，档案是"你的值"。

**示例**：

```
shub> load gd32
  started share-COM5  (COM5 -> tcp:1000)

shub> list
  NAME               KIND     STATUS              DESCRIPTION
  share-COM5         share    running (0m05s)     COM5 -> tcp:1000
```

### 5.6 `save` — 把运行中的 job 存成档案

```
shub> save <档案名> [job名 | -l]
```

**`job` 是什么**：每次 `share` 或 `connect` 启动，都会在后台创建一个 job。`list` 里的 `NAME` 列就是 job 名：

```
shub> list
  NAME               KIND     STATUS              DESCRIPTION
  share-COM5         share    running (3m20s)     COM5 -> tcp:1000
  share-COM7         share    running (0m10s)     COM7 -> tcp:1001
   ↑
   这些就是 job 名
```

**参数说明**：

| 写法 | 场景 | 行为 |
|---|---|---|
| `save gd32` | 只有一个 job | 保存那个 job |
| `save gd32` | 多个 job | **报错**，提示用 `list` 查看，列出可用写法 |
| `save gd32 -l` | 任意 | 保存**最近启动**的 job（`-l` = latest） |
| `save gd32 share-COM5` | 指定 job | 保存指定的 job |

**档案类型由 job 类型自动决定**：

- share job → `serve` 档案（串口参数 + TCP 参数 + 密码）
- connect job → `connect` 档案（远端地址 + 本地端口 + 密码）

**同名档案存在时覆盖**，并提示 `overwrote`。

**示例（serve 类型，单个 job）**：

```
shub> share COM5 --tcp 1000 --baud 9600
  started share-COM5  (COM5 -> tcp:1000)

shub> save gd32
  created C:\shub\profiles\gd32.json
    serve: COM5 -> tcp:1000
```

**示例（多个 job 时）**：

```
shub> list
  NAME               KIND     STATUS              DESCRIPTION
  share-COM5         share    running (3m20s)     COM5 -> tcp:1000
  share-COM7         share    running (0m10s)     COM7 -> tcp:1001

shub> save gd32
  error: multiple jobs are running. Specify which job to save:
    save gd32 -l                 (most recent: share-COM7)
    save gd32 share-COM5
    save gd32 share-COM7
  Use 'list' to see all jobs.

shub> save gd32 -l
  created C:\shub\profiles\gd32.json
    serve: COM7 -> tcp:1001   (most recent)

shub> save gd32 share-COM5
  created C:\shub\profiles\gd32.json
    serve: COM5 -> tcp:1000
```

**示例（connect 类型）**：

```
shub> connect 192.168.1.100:1000 --local 2000
  started connect-2000  (192.168.1.100:1000 -> 127.0.0.1:2000)

shub> save lab-server
  created C:\shub\profiles\lab-server.json
    connect: 192.168.1.100:1000 -> 127.0.0.1:2000
```

**无密码时**：档案里写 `"no_password": true` 而不是 `password`。

### 5.7 `list` — 列出所有 job

```
shub> list
  NAME               KIND     STATUS              DESCRIPTION
  share-COM5         share    running (3m12s)     COM5 -> tcp:1000
  connect-2000       connect  running (0m30s)     192.168.1.100:1000 -> 127.0.0.1:2000
```

### 5.8 `help` / `exit`

- `help` 显示命令列表
- `exit` / `quit` 停止所有 job，释放所有串口和端口
- `Ctrl+C` 或 `Ctrl+D` 同样退出

`share -h` / `connect -h` / `load -h` 显示对应命令的完整选项。参数错误时也会打印完整帮助。

## 6. 档案

档案是**JSON 文件**，放在 `shub/profiles/` 下。两种使用方式：

- **手写**：直接用文本编辑器创建，适合"先想好参数再共享"
- **`save` 生成**：在 REPL 里调好参数后 `save gd32`，程序自动写入，适合"试出来再存"

**档案分两种，由 `"type"` 字段区分**：

### serve 档案（`profiles/gd32.json`）

`"type": "serve"`，含**串口参数 + TCP 参数 + 密码**，因为 `share` 这个动作同时涉及打开串口和监听 TCP：

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

`"type": "connect"`，只含**TCP 参数 + 密码**，因为 `connect` 只做 TCP 转发，不碰串口硬件：

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

### 为什么 serve 档案要串口参数，connect 档案不需要

| 档案 type | 包含什么 | 为什么 |
|---|---|---|
| `serve` | 串口参数 + TCP 参数 + 密码 | 要打开本地串口 + 监听 TCP |
| `connect` | 远端 TCP 地址 + 本地端口 + 密码 | 只做 TCP 转发，不碰串口 |

`connect` 的串口参数由远端 `share` 时决定，本地无法改。

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

### 本机也访问自己共享的串口

```
电脑 A：
  shub> share COM5 --tcp 1000
  shub> connect 127.0.0.1:1000 --local 2000
  MobaXterm → Raw TCP → 127.0.0.1:2000
```

本机通过 `connect` 中转，和远端访问路径完全一致，不需要特殊处理。因为 `share` 打开串口后独占，本机想用同一个串口只能走 TCP 路径。

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

**Q：`save gd32` 报 "multiple jobs are running"**

- 当前有多个 job 在跑，必须显式指定保存哪个
- 选项：
  - `save gd32 -l` — 保存最近启动的 job
  - `save gd32 <job名>` — 保存指定的 job
- 报错里会列出可用的写法，复制粘贴即可
- 用 `list` 查看所有 job 名

**Q：`save` 报 "no jobs to save"**

- 当前没有运行中的 job，先用 `share` 或 `connect` 启动一个
- 或者已经 `unshare` 了，job 不在 `list` 里了，无法再 save

**Q：`serve COM5 --tcp 1000` 报 "unknown command: serve"**

- 本工具没有 `serve` 这个命令，用 `share`
- `serve` 曾是 `share` 的别名，现已删除

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
- **`save` 只能保存运行中的 job**：`unshare` 之后再 `save` 会找不到 job。如果调好参数想长期保留，先 `save` 再 `unshare`
- **没有 `serve` 别名**：只支持 `share`

## 11. 运行测试

```bash
cd shub/
python -m unittest discover tests -v
```

覆盖范围：

- `tests/test_profiles.py`：档案读取和保存的成功与各种失败路径（15 个用例）
- `tests/test_handshake.py`：密码握手协议的 round-trip（4 个用例）
- `tests/test_tcp_server.py`：多客户端广播、客户端输入聚合、密码拒绝（5 个用例）

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