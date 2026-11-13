<!-- 文件名: docs/dataflow.md -->
# 数据流附录

[← 返回主 README](../README.md)

```
MobaXterm 输入 "help\r"
    ↓ Telnet / Raw TCP
shub share 192.168.1.100:1000
    ↓ pyserial
电脑 A 的 COM5
    ↓ 串口
设备收到 "help\r"，执行
    ↓ 串口
设备回 "Help text\r\n"
    ↓ pyserial
shub share 读线程 → 订阅队列
    ↓ 每客户端发送队列 → 发送线程
    ↓ TCP
MobaXterm 显示 "Help text"
```

每一层“收字节、发字节”，不做解析。

## 数据面关键代码

| 位置 | 作用 | 约束 |
|---|---|---|
| `serial_session._read_loop` | 读串口，把原始字节放进每个订阅队列 | 不解析、不转换 |
| `tcp_server._broadcast_loop` | 从订阅队列取字节，`put_nowait` 到每个客户端队列 | 不阻塞、不丢健康客户端的字节 |
| `tcp_server._Client._send_loop` | 从客户端队列取字节，`sendall` | 慢客户端队列满则断开该客户端 |
| `tcp_server._client_loop` | 读 TCP 客户端字节，`session.send_raw` | 不解析、不转换 |

这三处之外的所有逻辑都在控制面，不碰字节内容。