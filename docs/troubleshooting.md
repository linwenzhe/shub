<!-- 文件名: docs/troubleshooting.md -->
# 故障排查

[← 返回主 README](../README.md)

## 日志

- 查看日志：`shub/logs/shub.log`（滚动，最多 2MB × 3）
- 调日志级别：`config/log.py` 里 `LOG_LEVEL = "DEBUG"` 重启
- 关闭日志：`config/log.py` 里 `LOG_ENABLED = False` 重启

## 端口与串口

- 确认端口占用：`netstat -ano | findstr :1000`
- 确认串口占用：设备管理器 → 端口 → 右键属性

## job 显示 `failed`

查看日志中 `Serial ... read error`，检查 USB 串口连接，`unshare` 后重新 `share`。不会自动重连。

## 某客户端被断开

日志中 `Client ... send queue full, dropping`，说明该客户端读得太慢；检查对端终端或网络。

## 自动端口分配失败

日志里会有 `No free TCP port on 0.0.0.0 in range 1000-65535`。检查是否有大量程序占用端口，或调整 `config/tcp.py` 的 `TCP_PORT_START` / `TCP_PORT_END`。

## 显式端口被占用

报错 `Cannot listen on 0.0.0.0:1000`。换端口，或不写 `--tcp` 让 shub 自动选。刚停掉的 share 可能进入 TIME_WAIT，等 2–4 分钟。