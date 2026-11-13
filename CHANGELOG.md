<!-- 文件名: CHANGELOG.md -->
# Changelog

## v0.1.0

### 命令

- 核心命令 5 条：`list` / `share` / `unshare` / `save` / `help`，外加 `exit` / `quit`。
- `ports` 合并进 `list -p`；`list` 默认等价 `list -j`。
- `list -j` 增加 `CLIENTS` 列，显示当前连接数。
- `share --profile` 与 `share --from` 等价；`-f` / `-P` 不再使用。
- `share --tcp` 可选：不写时从 `TCP_PORT_START`（1000）开始自动分配；显式指定被占用则报错，不自增。
- `save` 新语法：`save <job> as <profile>` / `save <profile>` / `save -l <profile>` / `save -a [-y]`。
- 旧 `save <profile> -l` 语法废弃，报错提示新写法。

### 修复

- 路径穿越：`profile_path` 拒绝 `/` `\` `..` 和绝对路径，并用 `realpath` 校验。
- `unshare` 无参数被拦截。
- `save -l` / `save -y` 单独输入被当作档案名。
- 中文宽字符退格残留。
- 空命令列表 `ZeroDivisionError`。
- `SerialSession` 内部死队列内存泄漏。
- TCP 广播持锁 `sendall`，慢客户端拖死全服；改为每客户端独立发送队列 + 发送线程，队列满断开慢客户端。
- 串口读线程异常后 job 仍显示 `running`；改为标记 `failed` 并释放资源。
- TCP 端口非法时串口泄漏。
- 大写 `SHARE` 解析失败。
- `load_profile` 未捕获 `UnicodeDecodeError`。
- `list` / `unshare` / `save` 多余参数未严格校验。

### 工程

- `config.py` 拆为 `config/{serial,tcp,log}.py`，`config/__init__.py` 重导出。
- 新增 `BIND_ADDR`、`TCP_PORT_START`、`TCP_PORT_END`、`TCP_CLIENT_QUEUE_SIZE`。
- TCP 端口自动分配下沉到 `TcpSerialServer._bind_auto()`，探测和绑定同一动作，无竞态。
- 每个客户端 socket 开启 `SO_KEEPALIVE`。
- `ServeRunner` 支持注入 `session_factory` / `server_factory`，便于测试。
- `repl.py` 拆分：`Job` → `core/job.py`；保存逻辑 → `core/save_service.py`；保存语法 → `core/save_parser.py`；`share` 解析 → `core/share_args.py`。
- `TcpSerialServer` 使用 `SerialSessionLike` 类型标注。
- 新增 `build.py`（PyInstaller 单文件打包）和 `profiles/examples/`。
- README 拆分为主索引 + `docs/` 多文件。

### 测试

- `test_profiles.py`：档案读写、路径穿越、非 UTF-8、无 `tcp_port`。
- `test_save_service.py`：创建 / 跳过 / 覆盖 / 批量。
- `test_save_parser.py`：`save` 所有语法分支。
- `test_share_args.py`：直接模式、profile 模式、冲突、端口范围。
- `test_serve_runner.py`：生命周期、TCP 失败关闭 session、自动端口回填、串口异常。
- `test_tcp_server.py`：广播、输入聚合、全字节透明、断开不影响他人、客户端计数、端口自动 / 固定冲突 / 跳过占用。