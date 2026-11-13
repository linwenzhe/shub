<!-- 文件名: docs/mobaxterm.md -->
# 与 MobaXterm 配合

[← 返回主 README](../README.md)

## 新建会话

```
Session → Telnet（或 Raw TCP）
  Remote host: 192.168.1.100（电脑 A 的 IP）
  Port:        1000（share 的实际端口）
```

同机访问时把 IP 换成 `127.0.0.1`。端口以 `share` 输出或 `list -j` 为准。

## 推荐设置

**Terminal settings**：

- Local echo: 关（见下文）
- **Line ending: `CR`**（letter-shell 类设备的关键）

**Log**：勾选 `Log terminal output to`。

**MultiExec**：打开多个会话后，用 `MultiExec` 同时发指令。

## 换行符（重要）

Windows 风格终端默认发 `\r\n`。letter-shell 类设备（GD32、STM32 CLI）只认 `\r`，收到 `\r\n` 会**触发两次回车**。

**解决**：MobaXterm 的 `Settings → Configuration → Terminal → Line ending` 设为 `CR`。

shub 不处理换行符——发什么到串口就是什么。

## 输入字符显示两次（`hheellpp`）

现象：敲 `help`，屏幕显示 `hheellpp`，但设备返回结果准确。

原因：**MobaXterm 本地回显 + 设备回显，叠加了两次**。

**解决**：

1. 在 MobaXterm 的终端窗口里，**右键** → **Change terminal settings...**
2. 找到 **Local echo**（本地回显）
3. 设为 **Force off**（强制关闭）
4. 点 OK 应用

**替代方案**：改用 PuTTY 的 Raw 模式（默认本地回显关闭）。

## 一次回车出现两行提示符

MobaXterm 的 Line ending 改 `CR`。