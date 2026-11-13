<!-- 文件名: docs/logging.md -->
# 日志

[← 返回主 README](../README.md)

日志**仅用于调试**，不是日常操作的一部分。默认情况下：

- 终端只显示错误提示（`print` 输出）；
- 日志文件 `logs/shub.log` 记录连接/断开/错误等关键事件（`INFO` 级别）；
- 正常使用时不需要关心日志。

## 配置

都在 `config/log.py`：

| 配置 | 默认 | 说明 |
|---|---|---|
| `LOG_ENABLED` | `True` | `False` 时完全关闭日志 |
| `LOG_LEVEL` | `"INFO"` | 文件日志级别 |
| `LOG_DIR` | `"logs"` | 日志目录 |
| `LOG_MAX_BYTES` | 2MB | 单文件上限 |
| `LOG_BACKUP_COUNT` | 3 | 备份数 |

**没有运行时命令**：改日志配置需要编辑 `config/log.py` 并重启。

## 常见日志

| 日志 | 含义 |
|---|---|
| `Client ... connected` | 远端连接成功 |
| `Client ... disconnected` | 远端断开 |
| `Client ... send queue full, dropping` | 该客户端读得太慢，被断开 |
| `Serial ... read error` | 串口读线程异常，job 会标记 `failed` |
| `Serial session failed` | 同上，由 `ServeRunner` 记录 |
| `TCP server listening on ...` | TCP 监听成功 |
| `TCP server stopped` | TCP 监听已关闭 |