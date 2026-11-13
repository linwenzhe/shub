<!-- 文件名: docs/architecture.md -->
# 项目结构与模块职责

[← 返回主 README](../README.md)

```
shub/
├── main.py                入口，只调用 Repl().run()
├── build.py               PyInstaller 单文件打包
├── config/
│   ├── __init__.py        重导出，保持 from config import X
│   ├── serial.py          串口默认值 + build_serial_cfg
│   ├── tcp.py             BIND_ADDR / TCP_PORT_START / TCP_PORT_END / 队列大小
│   └── log.py             日志开关
├── logger.py              滚动文件日志 + 控制台 WARNING
├── profiles.py            档案读写、路径安全、必填字段校验
├── core/
│   ├── errors.py          统一异常体系
│   ├── session_protocol.py  SerialSessionLike Protocol
│   ├── serial_session.py   串口独占打开、读线程、订阅、原始写
│   ├── tcp_server.py       TCP 多客户端、每客户端发送队列、端口自动分配
│   ├── serve_runner.py     共享生命周期编排，暴露实际端口，可注入工厂
│   ├── line_reader.py      Windows 上下键循环、中文宽度清行
│   ├── job.py              Job 状态与生命周期，不依赖 REPL
│   ├── save_service.py     纯保存逻辑，confirm 回调解耦 UI
│   ├── save_parser.py      save 语法纯函数解析
│   ├── share_args.py       share 参数解析与校验
│   └── repl.py             交互、命令分发、显示
├── profiles/
│   ├── gd32.json
│   └── examples/
├── docs/
├── tests/
├── README.md
└── CHANGELOG.md
```

## 依赖方向

```
main → repl → serve_runner → serial_session / tcp_server
                    ↓
              errors / logger / config
repl → save_service → profiles
repl → save_parser（纯函数）
repl → share_args → profiles / config
job → serve_runner
tcp_server → session_protocol（只依赖 Protocol）
```

单向依赖，无循环。

## 数据面与控制面

- **数据面**：`serial_session._read_loop` → 订阅队列 → `tcp_server._broadcast_loop` → 每客户端发送队列 → 发送线程 → TCP；客户端输入 → `_client_loop` → `session.send_raw`。三处关键代码保持字节透明。
- **控制面**：`repl` 只管理 job 生命周期、命令解析、显示；`save_service` 只做 Job → JSON；`save_parser` / `share_args` 只做语法解析。

## 本轮架构优化

- **拆 `repl.py` 上帝类**：`Job` → `core/job.py`；保存逻辑 → `core/save_service.py`；保存语法 → `core/save_parser.py`；share 解析 → `core/share_args.py`。
- **save 业务与 UI 解耦**：`save_service` 不 `print`、不 `input()`，通过 `confirm_overwrite` 回调确认覆盖，可独立单测。
- **Protocol 落地**：`TcpSerialServer` 的 `session` 参数标注为 `SerialSessionLike`。
- **端口自动分配下沉**：`TcpSerialServer._bind_auto()` 探测和绑定同一动作，无竞态。
- **ServeRunner 可注入工厂**：`session_factory` / `server_factory` 便于测试，不碰真实串口和 socket。
- **config 拆分**：`config/{serial,tcp,log}.py`，`config/__init__.py` 重导出，调用方零改动。