<!-- 文件名: docs/faq.md -->
# 常见问题

[← 返回主 README](../README.md)

**Q：`share` 之后怎么连？**

- 本机：`127.0.0.1:<实际端口>`
- 远端：`电脑A的IP:<实际端口>`
- 其他电脑不需要装 shub
- 实际端口看 `share` 输出或 `list -j`

**Q：`share COM5` 不写 `--tcp` 会怎样？**

从 1000 开始找第一个可用端口，输出标注 `(auto port)`。1000 被占用就用 1001，再被占用就 1002，依此类推。

**Q：`share COM5 --tcp 1000` 报 "Cannot listen on port 1000"**

显式指定的 1000 被占用。换端口，或不写 `--tcp` 让 shub 自动选。刚停掉的 share 可能进入 TIME_WAIT，等 2–4 分钟或换端口。

**Q：`share --profile` 和 `share --from` 有区别吗？**

没有，完全等价。

**Q：原来的 `-f` 怎么没了？**

改为 `--profile` 或 `--from`。`-f` 容易和 force 混淆，`-p` 容易和 port 混淆。

**Q：原来的 `ports` 命令怎么没了？**

已合并进 `list -p`。直接输入 `ports` 会报 `unknown command 'ports'`。

**Q：原来的 `list` 怎么用？**

`list` 默认就是 `list -j`，行为不变；`list -p` 看端口。

**Q：`load gd32` 报 "unknown command: load"**

已改为 `share --profile gd32` 或 `share --from gd32`。

**Q：`SHARE COM5` 能用吗？**

能。命令名大小写不敏感。

**Q：`share COM5` 报 "already shared"**

COM5 已在共享，先 `unshare COM5`。

**Q：`share COM5 --tcp 0` 或 `--tcp 65536` 报错**

端口必须在 1–65535。

**Q：`share COM5` 报 "Port COM5 not found"**

设备管理器确认 COM 号；`list -p` 列出当前可用串口。

**Q：`share --profile gd32` 报 "cannot combine ..."**

`--profile` / `--from` 不能和其他参数同时给。要覆盖参数，改档案内容。

**Q：`share --profile ../evil` 报 "Invalid profile name"**

档案名只能是纯文件名，不能含 `/` `\` `..` 或绝对路径。

**Q：`list -p -j` 报错**

两个视图不能同时显示，分开执行。

**Q：`save -l` 报 "'-l' requires a profile name"**

`-l` 后必须跟档案名，如 `save -l gd32`。

**Q：`save gd32 -l` 报 "old save syntax is no longer supported"**

旧语法已废弃，改用 `save -l gd32`。

**Q：`save -y` 报 "'-y' is only valid with '-a'"**

`-y` 只能配合 `-a`，如 `save -a -y`。

**Q：`save -x` 报 "unknown option for save"**

`save` 只接受 `-a`、`-l`、`-y`、`-h`。

**Q：`save gd32 share-COM5` 报 "missing 'as' keyword"**

新语法是 `save <job> as <档案名>`，如 `save share-COM5 as gd32`。

**Q：`save gd32` 报 "multiple jobs are running"**

当前有多个 job，必须显式指定：`save share-COM5 as gd32`、`save -l gd32`、`save -a`。

**Q：`save` 出来的档案端口是固定的吗？**

是。`save` 记录 job 的实际端口。想要自动分配，手写档案时省略 `tcp_port`。

**Q：`unshare` 报 "multiple jobs are running"**

必须指定卸载哪个：`unshare COM5`、`unshare COM7`，或 `list -j` 查看。

**Q：`list -j` 里某个 job 显示 `failed`**

串口读线程异常退出（例如 USB 串口被拔出）。该共享已失效，用 `unshare <COM口>` 清理后重新 `share`。

**Q：输入字符显示两次（`hheellpp`）**

MobaXterm 本地回显 + 设备回显叠加。右键 → Change terminal settings → Local echo → Force off。详见 [MobaXterm 配合](mobaxterm.md)。

**Q：一次回车出现两行提示符**

MobaXterm 的 Line ending 改 `CR`。