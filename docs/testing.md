<!-- 文件名: docs/testing.md -->
# 运行测试

[← 返回主 README](../README.md)

```bash
cd shub/
python -m unittest discover tests -v
```

## 覆盖范围

| 文件 | 覆盖 |
|---|---|
| `test_profiles.py` | 档案读写、路径穿越、非 UTF-8、无 `tcp_port` |
| `test_save_service.py` | 创建 / 跳过 / 覆盖 / 批量保存 / confirm 回调 |
| `test_save_parser.py` | `save` 所有语法分支，含旧语法报错 |
| `test_share_args.py` | 直接模式、profile 模式、`--from` 等价、冲突、端口范围、缺参 |
| `test_serve_runner.py` | 生命周期、TCP 失败关闭 session、自动端口回填、串口异常、`wait` 返回 |
| `test_tcp_server.py` | 广播、输入聚合、全字节透明、断开不影响他人、客户端计数、端口自动 / 固定冲突 / 跳过占用 |

## 交互层

`list` / `save` 语法分发、上下键循环、中文退格等交互层行为，建议按 [最终验证清单](checklist.md) 手工验证。