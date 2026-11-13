<!-- 文件名: docs/commands.md -->
# 命令参考

[← 返回主 README](../README.md)

## 快速上手

### 步骤 1：电脑 A（挂着串口的电脑）

```
shub> list -p
  PORT     DESCRIPTION                    SHARE
  COM5     USB-SERIAL CH340               not shared

shub> share COM5
  started share-COM5  (COM5 -> tcp:1000)   (auto port)
```

`--tcp` 不写时，shub 从 1000 开始找第一个可用端口。要固定端口就写 `share COM5 --tcp 1000`。

记住电脑 A 的 IP（`ipconfig` 查看，假设 `192.168.1.100`）。

### 步骤 2：电脑 B（MobaXterm，不装 shub）

```
Session → Telnet（或 Raw TCP）
  Remote host: 192.168.1.100
  Port:        1000
  → 连接
```

**直接对话 COM5。** 电脑 B 上什么都不用装。

### 步骤 3：停止

```
shub> unshare COM5          （电脑 A，停止共享并关闭串口）
shub> exit                   （退出，所有 job 自动停止）
```

## 交互式 shell 基础

### 只接受 5 条命令

```
list / share / unshare / save / help
```

外加 `exit` / `quit` 退出。命令名大小写不敏感，参数按原样传给对应命令。

```
shub> foo
  error: unknown command 'foo'. Type 'help' for the list of commands.

shub> ports
  error: unknown command 'ports'. Type 'help' for the list of commands.
```

### 上下键循环

按 **↑** / **↓** 在 5 条命令名之间循环：`list → share → unshare → save → help → list → ...`

- 翻到某条命令后可以补充参数再回车；
- 按其他字符（字母/退格）退出循环模式；
- 再次按 ↑/↓ 从循环列表重新开始。

### 其他输入行为

- **退格**：按显示宽度清除（中文一次清两列）；
- **Ctrl+C**：退出 REPL；
- **不记录历史**：上下键只循环 5 条命令模板；
- **不支持左右移动光标、Home/End**。

## `list` — 查看端口或 job

```
shub> list [-p|-j]
```

| 写法 | 行为 |
|---|---|
| `list` | 默认等价 `list -j` |
| `list -j` | 列出所有 job（`--jobs` 同义） |
| `list -p` | 列出 COM 口及共享状态（`--ports` 同义） |
| `list -h` | 显示帮助 |
| `list -p -j` | 报错：两个视图不能同时显示 |
| `list foo` | 报错：未知参数 |

`list -p` 示例：

```
shub> list -p
  PORT     DESCRIPTION                    SHARE
  COM5     USB-SERIAL CH340               shared on tcp:1000
  COM7     Silicon Labs CP210x            not shared
```

`list -j` 示例：

```
shub> list -j
  NAME               STATUS              CLIENTS   DESCRIPTION
  share-COM5         running (3m12s)     2         COM5 -> tcp:1000
```

`STATUS` 可能是 `running (XmYYs)` / `stopped` / `failed`。`failed` 表示串口读线程异常退出，共享已失效，需 `unshare` 清理后重新 `share`。

## `share` — 共享串口

### 方式 A：直接命令行

```
shub> share <串口> [--tcp <端口>] [选项]
```

| 参数 | 说明 |
|---|---|
| `<串口>` | 如 `COM5`（必填） |
| `--tcp <端口>` | 可选，1–65535。不写则从 1000 开始自动找第一个可用端口 |
| `--baud N` | 波特率（115200） |
| `--bytesize N` | 数据位 5/6/7/8（8） |
| `--parity X` | 校验位 N/E/O/M/S（N） |
| `--stopbits N` | 停止位 1/2（1） |
| `--flow X` | 流控 none/rts/xon（none） |

**端口分配规则**：

| 情况 | 行为 |
|---|---|
| 不写 `--tcp` | 从 1000 开始跳过被占用端口，使用第一个可用端口，输出标注 `(auto port)` |
| 写 `--tcp 1000`，1000 可用 | 严格使用 1000 |
| 写 `--tcp 1000`，1000 被占用 | **报错**，不自增 |

### 方式 B：从档案启动

```
shub> share --profile <档案名>
shub> share --from <档案名>
```

`--profile` 和 `--from` 完全等价。档案里写什么就用什么，不接受任何其他参数。

### 互斥

- 用 `--profile` / `--from` 时不能同时给串口名或任何 `--xxx` 参数；
- 给串口名时不能用 `--profile` / `--from`。

```
shub> share --profile gd32 --tcp 1001
  error: cannot combine --profile/--from with other arguments.
```

### 同一串口不能重复共享

```
shub> share COM5
  error: COM5 is already shared on tcp:1000. Use 'unshare COM5' first.
```

## `unshare` — 停止共享

```
shub> unshare [串口]
```

- 不指定串口：当前只有 1 个 job 时卸载它；多个 job 时报错列出可用写法；
- 指定串口：卸载该串口的共享；
- `unshare -h`：显示帮助。

**行为**：停止共享、关闭 TCP 监听、**关闭串口**，释放给其他程序。所有通过 TCP 连接该串口的会话会被立即断开。

## `save` — 把运行中的 job 存成档案

```
shub> save <job> as <档案名>
shub> save <档案名>
shub> save -l <档案名>
shub> save -a [-y]
```

| 写法 | 场景 | 行为 |
|---|---|---|
| `save share-COM5 as gd32` | 指定 job | 把 `share-COM5` 存成 `gd32.json` |
| `save gd32` | 只有 1 个 job | 保存那个 job |
| `save gd32` | 多个 job | 报错，列出可用写法 |
| `save -l gd32` | 任意（≥1 个 job） | 保存最近启动的 job |
| `save -a` | 任意（≥1 个 job） | 保存所有运行中的 job |
| `save -a -y` | 任意 | 跳过所有覆盖确认 |
| `save -l` | — | 报错：`-l` 后必须跟档案名 |
| `save -y` | — | 报错：`-y` 只能配合 `-a` |
| `save -x` | — | 报错：未知选项 |
| `save gd32 -l` | — | 报错：旧语法已废弃 |
| `save gd32 share-COM5` | — | 报错：缺少 `as` 关键字 |

**`save -a` 命名**：文件名自动用 job 名，`share-COM5` 存成 `profiles/share-COM5.json`。

**保存的是实际端口**：如果 job 是自动分配端口启动的，档案会写入实际端口。再 `share --profile` 时是固定端口；想要继续自动分配，手写档案时省略 `tcp_port`。

## `help` / `exit`

- `help` 显示命令列表；
- `exit` / `quit` 停止所有 job，释放所有串口和端口；
- `Ctrl+C` / `Ctrl+D` 同样退出；
- `list -h` / `share -h` / `save -h` / `unshare -h` 显示对应帮助。