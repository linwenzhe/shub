<!-- 文件名: docs/deploy.md -->
# 典型部署

[← 返回主 README](../README.md)

## 本机访问

```
电脑 A：
  shub> share COM5 --tcp 1000
  MobaXterm → Telnet → 127.0.0.1:1000
```

## 跨机访问

```
电脑 A：
  shub> share COM5

电脑 B（不装 shub）：
  MobaXterm → Telnet → 192.168.1.100:1000
```

## 多串口同时共享

```
电脑 A：
  shub> share COM5
  started share-COM5  (COM5 -> tcp:1000)   (auto port)
  shub> share COM7
  started share-COM7  (COM7 -> tcp:1001)   (auto port)
  shub> share COM9
  started share-COM9  (COM9 -> tcp:1002)   (auto port)

  shub> list -p
    PORT     DESCRIPTION                    SHARE
    COM5     USB-SERIAL CH340               shared on tcp:1000
    COM7     Silicon Labs CP210x            shared on tcp:1001
    COM9     USB-Serial Controller          shared on tcp:1002
```

## 多人同时访问同一串口

服务端支持多客户端：所有人的输入都写入串口，所有输出广播给所有人。多人输入会交错，建议“一人主操，其他人旁观”。

`list -j` 的 `CLIENTS` 列显示当前连接数：

```
shub> list -j
  NAME               STATUS              CLIENTS   DESCRIPTION
  share-COM5         running (3m12s)     2         COM5 -> tcp:1000
```

## 慢客户端处理

每个客户端有独立的发送队列和发送线程：

- 健康客户端不会因为某个慢客户端而收不到数据；
- 某个客户端长期不读、队列积满时，该客户端会被断开，其他客户端不受影响；
- 广播线程不会被任何客户端阻塞，串口读线程也不会因为 TCP 慢而卡住。

## 绑定到指定网卡

多网卡机器默认监听 `0.0.0.0`（所有网卡）。只想暴露在内网网卡上时，编辑 `config/tcp.py`：

```python
BIND_ADDR = "192.168.1.100"
```

## 打包成单文件

```bash
pip install pyinstaller
python build.py
```

输出在 `dist/`，`profiles/` 和 `docs/` 会作为数据目录一起打包。