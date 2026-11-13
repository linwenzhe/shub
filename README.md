<!-- 文件名: README.md -->

# shub — 局域网串口分发工具

把本机**已显式开启共享**的串口，通过局域网 TCP 暴露出去，让局域网内任意电脑上的终端软件（MobaXterm、PuTTY 等）像操作本地串口一样操作它。

**核心契约**：显式共享 · `IP:port` 映射 · 纯字节透明转发 · 多客户端 · 无客户端软件 · 串口独占 · 无认证无加密 · 交互式管理。

\---

## 目录

* [快速上手](docs/commands.md#快速上手)
* [命令参考](docs/commands.md)
* [档案](docs/profiles.md)
* [与 MobaXterm 配合](docs/mobaxterm.md)
* [典型部署](docs/deploy.md)
* [日志](docs/logging.md)
* [常见问题](docs/faq.md)
* [已知限制](docs/limits.md)
* [安全说明](docs/security.md)
* [项目结构与模块职责](docs/architecture.md)
* [运行测试](docs/testing.md)
* [故障排查](docs/troubleshooting.md)
* [最终验证清单](docs/checklist.md)
* [数据流附录](docs/dataflow.md)
* [变更记录](CHANGELOG.md)

\---

## 定位

```
电脑 A（挂串口）              电脑 B（MobaXterm）
┌──────────────────┐        ┌──────────────────┐
│ COM5             │        │ MobaXterm        │
│   ↓              │        │   ↓ Telnet/Raw   │
│ shub             │◄─网络─►│ 192.168.1.100:1000
│ share COM5       │        │                  │
│ --tcp 1000       │        │ （B 不装 shub）    │
└──────────────────┘        └──────────────────┘
```

* **显式共享**：只有本地 `share` 过的 COM 口才会监听 TCP 端口；未共享的串口不可访问。
* **`IP:port` 映射**：每个已共享串口对应一个独立 TCP 端口，远端按 `IP:port` 访问对应串口。
* **纯字节透明转发**：不解析、不转换、不处理换行符、不记录指令。
* **多客户端**：串口输出广播给所有健康客户端；所有客户端输入都写入串口。
* **无客户端软件**：对端只需普通 Telnet / Raw TCP 终端。
* **串口独占**：shub 打开期间，其他程序不能打开同一 COM 口。
* **无认证、无加密**：定位是可信局域网，不是缺陷。
* **交互式管理**：`list` / `share` / `unshare` / `save` 只管理共享生命周期，不参与数据内容。

## 安装

```bash
pip install pyserial
```

可选，用来打包成单文件可执行：

```bash
pip install pyinstaller
```

## 启动

```
python main.py        （源码运行）
shub                  （打包后）
```

进入交互式 shell：

```
  shub v0.1  -  LAN serial port distributor (interactive)

  Commands:
    list \[-p|-j]                            List COM ports (-p) or jobs (-j)
    share <port> \[--tcp <port>] \[options]   Share a COM port over TCP
    share --profile <profile>               Share using a profile file
    share --from <profile>                  Same as --profile
    unshare \[port]                          Stop sharing (auto if only one job)
    save <job> as <profile>                 Save a named job as a profile
    save <profile>                          Save the only running job
    save -l <profile>                       Save the most recent job
    save -a \[-y]                            Save all running jobs
    help                                    Show this message
    exit                                    Stop all jobs and quit

  --tcp is optional; without it shub picks the first free port from 1000.
  --profile and --from are equivalent.

  Up/Down arrows cycle through the 5 command names.
```

## 最小示例

电脑 A：

```
shub> share COM5
  started share-COM5  (COM5 -> tcp:1000)   (auto port)
```

电脑 B（不装 shub）：

```
MobaXterm → Telnet/Raw TCP → 192.168.1.100:1000
```

停止：

```
shub> unshare COM5
shub> exit
```

端口以 `share` 输出或 `list -j` 为准；`--tcp` 不写时从 1000 起自动分配。

## 命令一览

|命令|用法|说明|
|-|-|-|
|`list`|`list` / `list -j` / `list -p`|查看 job 或端口|
|`share`|`share <port> \[--tcp <port>]`|直接共享|
||`share --profile <profile>`|从档案启动|
||`share --from <profile>`|与 `--profile` 等价|
|`unshare`|`unshare` / `unshare <port>`|停止共享|
|`save`|`save <job> as <profile>`|指定 job 存档案|
||`save <profile>`|只有 1 个 job 时保存|
||`save -l <profile>`|保存最近 job|
||`save -a \[-y]`|保存所有 job|
|`help` / `exit`|||

详见 [命令参考](docs/commands.md)。

## 项目结构

```
shub/
├── main.py                入口
├── build.py               PyInstaller 打包脚本
├── config/                串口 / TCP / 日志配置
├── logger.py              滚动日志
├── profiles.py            档案读写与路径安全
├── core/                  核心模块（数据面 + 控制面）
├── profiles/              档案目录（含 examples/）
├── docs/                  详细文档
├── tests/                 单元测试
├── README.md              本文件
└── CHANGELOG.md
```

模块职责详见 [项目结构与模块职责](docs/architecture.md)。

## 关键约束

* **只做转发**：不解析串口数据，不处理 `\\r\\n`，不记录指令。
* **不做自动重连**：串口读异常时 job 标记 `failed` 并释放资源；需手动 `unshare` 后重新 `share`。
* **不做认证/加密**：部署在可信局域网；不要暴露到公网。
* **不自动共享未 `share` 的串口**：只有显式 `share` 才会监听端口。

完整列表见 [已知限制](docs/limits.md) 和 [安全说明](docs/security.md)。

