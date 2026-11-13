<!-- 文件名: docs/checklist.md -->
# 最终验证清单

[← 返回主 README](../README.md)

| # | 操作 | 预期 |
|---|---|---|
| 1 | `python main.py` | 进入 `shub>` |
| 2 | `help` | 显示 5 条核心命令 |
| 3 | `ports` | `unknown command 'ports'` |
| 4 | `load gd32` | `unknown command 'load'` |
| 5 | `foo` | `unknown command 'foo'` |
| 6 | `share` | `'share' requires arguments. ...` |
| 7 | `share COM5` | 自动分配端口，输出含 `(auto port)`，不打印 IP |
| 8 | `share COM7` | 自动分配下一个端口，如 1001 |
| 9 | `share COM9 --tcp 2000` | 严格使用 2000 |
| 10 | `share COM9 --tcp 1000`（1000 已占用） | 报错 `Cannot listen on 0.0.0.0:1000` |
| 11 | 本机 MobaXterm Telnet 连 `127.0.0.1:1000` | 直接对话 COM5 |
| 12 | 远端 MobaXterm Telnet 连 `电脑A的IP:1000` | 直接对话 COM5 |
| 13 | `SHARE COM5` | 能启动共享（大小写不敏感） |
| 14 | `share --profile gd32` | 从档案启动 |
| 15 | `share --from gd32` | 与 `--profile` 等价 |
| 16 | `share --profile ../evil` | `Invalid profile name: '../evil'` |
| 17 | `share --profile gd32 --tcp 1001` | `cannot combine --profile/--from with other arguments` |
| 18 | `share COM5 --tcp 0` | `tcp_port must be between 1 and 65535` |
| 19 | `list` | 等价 `list -j`，列出 job |
| 20 | `list -j` | 列出 job，含 `CLIENTS` 列 |
| 21 | `list -p` | 列出 COM 口及共享状态 |
| 22 | `list -p -j` | 报错：两个视图不能同时显示 |
| 23 | `list foo` | `unknown argument for 'list': foo` |
| 24 | `list -h` | 显示 `list` 帮助 |
| 25 | `save share-COM5 as gd32` | 创建 `profiles/gd32.json` |
| 26 | `save gd32`（只有 1 个 job） | 创建/覆盖档案 |
| 27 | `save gd32`（多个 job） | 报错并列出 `save <job> as gd32` 等写法 |
| 28 | `save -l gd32` | 保存最近启动的 job |
| 29 | `save -l` | `'-l' requires a profile name` |
| 30 | `save -y` | `'-y' is only valid with '-a'` |
| 31 | `save -x` | `unknown option for save: -x` |
| 32 | `save gd32 -l` | `old save syntax is no longer supported` |
| 33 | `save gd32 share-COM5` | `missing 'as' keyword` |
| 34 | `save -a` | 保存所有 job |
| 35 | `save -a -y` | 保存所有 job，跳过覆盖确认 |
| 36 | 1 个 job 时 `unshare` | 自动卸载，串口释放 |
| 37 | 多 job 时 `unshare` | 报错并列出可用 `unshare COMx` |
| 38 | 0 个 job 时 `unshare` | `no jobs are running` |
| 39 | `unshare -h` | 显示 unshare 帮助 |
| 40 | 上下键循环 | 5 条命令循环切换 |
| 41 | 中文输入后退格 | 一次清两列，无残留 |
| 42 | 两个客户端同时连接，一个不读 | 另一个仍正常收发，慢客户端最终被断开 |
| 43 | 拔掉 USB 串口 | job 显示 `failed`，端口释放 |
| 44 | `python -m unittest discover tests -v` | 所有测试通过 |