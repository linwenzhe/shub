<!-- 文件名: docs/profiles.md -->
# 档案

[← 返回主 README](../README.md)

档案是 JSON 文件，**固定存放在程序目录的 `profiles/` 下**。文件名只能是纯文件名（不能含 `/` `\` `..` 或绝对路径）。

两种使用方式：

- **手写**：直接用文本编辑器创建；
- **`save` 生成**：在 REPL 里调好参数后 `save share-COM5 as gd32`。

## 格式

```json
{
  "serial_port": "COM5",
  "baudrate": 115200,
  "bytesize": 8,
  "parity": "N",
  "stopbits": 1,
  "flow": "none",
  "tcp_port": 1000
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `serial_port` | ✅ | 串口名，如 `COM5` |
| `tcp_port` | 可选 | TCP 监听端口，1–65535。不写则自动分配 |
| `baudrate` | 可选 | 波特率，默认 115200 |
| `bytesize` | 可选 | 数据位，默认 8 |
| `parity` | 可选 | 校验位，默认 `N` |
| `stopbits` | 可选 | 停止位，默认 1 |
| `flow` | 可选 | 流控，默认 `none` |

`share --profile gd32` 等价于 `share COM5 --tcp 1000`。省略字段用 `config/serial.py` 默认值；省略 `tcp_port` 则自动分配。

档案必须是 UTF-8 编码的 JSON 对象；非 UTF-8 或非对象会报 `ProfileError`。

## 示例集合

`profiles/examples/` 下有可直接复制改名的示例：

- `stm32.json`：STM32，COM7 / 115200 / tcp 1001
- `esp32.json`：ESP32，COM9 / 115200 / tcp 1002
- `ch340.json`：CH340，COM5 / 115200 / **无 `tcp_port`**（演示自动分配）

复制到 `profiles/` 下即可：

```
copy profiles\examples\stm32.json profiles\myboard.json
```

## 路径安全

- 档案名只能是纯文件名；
- 拒绝 `/`、`\`、`..`、绝对路径；
- 最终路径用 `realpath` 校验必须位于 `profiles/` 下；
- 以上任一失败抛 `ProfileError`。

```
shub> share --profile ../evil
  error: Invalid profile name: '../evil'. Path separators are not allowed.
```