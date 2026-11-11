# shub — 多路串口终端与网络共享工具
## 1. 项目简介

shub 是一个 Windows 下的纯命令行串口终端工具，解决的核心问题是：一台电脑通过串口连着板卡，其他电脑如何通过网络共享操作这个串口。
一个终端里管理多个串口会话（本地 COM 口或远程共享端口），靠命令切换。
本地串口可通过 TCP 广播共享给其他电脑，带简单密码防止误连。
指令记录在本地与远端之间双向可见，来源用 COM 号或 IP:port 区分。
常用设备配置保存为 .json 文件，主副本固定存放在程序目录的 profiles/ 下；shub:save 可额外指定路径，同步复制一份到外部。
支持脚本逐行定时发送、上下键历史、历史导出、自描述帮助、滚动日志、共享状态查询。
针对 letter-shell 类嵌入式 shell（如 GD32），支持 --newline cr，避免敲一次回车设备打印两次提示符。
终端内所有面向用户的文本为英文，避免 Windows 控制台代码页导致中文乱码；日志文件为中文。
纯 Python 实现，配置集中在 config.py，发布为目录版 exe。

## 2. 核心概念

会话（session）：一个独立的串口或网络连接，有独立的读线程、数据队列、广播端口，互不影响。
当前会话：提示符指向的会话，普通输入发给它；shub: 开头的输入是命令。
共享：把本地串口会话通过 TCP 端口广播出去，其他电脑用 shub:connect 或 Telnet 连入。
指令记录：格式为 [shub@来源] 指令内容，来源是本地 COM 号或远端 IP:port。用于让各端知道“谁在操作”，与设备输出严格区分。
配置文件（profile）：每个配置是一个独立 .json 文件。主副本固定在 profiles/ 下，统一管理；shub:save 可额外指定路径，同步写一份到外部。
独占：Windows 驱动层强制一个 COM 口同时只能被一个程序打开；shub 是唯一的“持有者”，再把操作能力通过 TCP 分发出去。

## 3. 功能特性

### 多会话命令行终端

一个终端内同时开多个会话，每个会话独立：串口句柄、读线程、数据队列、广播端口。
提示符 shub [com5]> 显示当前会话，无会话时 shub>。
各会话输出带 [会话名] 前缀，区分来源。
两种新建方式：shub:open（当前窗口）/ shub:open-new（新开窗口），可混用。
一台电脑可以同时：开本地 COM 口、连多个远端共享端口、共享自己的串口。

### 本地串口会话

默认参数：115200 8N1，无流控，换行符 \r\n（均可在 config.py 修改）。
只给端口号即可打开：shub:open com5；需要时覆盖：
shub:open com5 9600 7E1 --flow rts --newline cr
打开前枚举校验：端口不存在时列出可用端口；被其他程序占用时明确提示。
支持流控：--flow none|rts|xon，实际映射到 pyserial 的 rtscts / xonxoff。
支持换行符：--newline crlf|lf|cr|none。

### 换行符说明（重要）

选项	发送的字符	适用场景
crlf	\r\n	Windows 风格、多数设备默认
lf	\n	Linux/macOS 风格
cr	\r	letter-shell 类嵌入式 shell（如 GD32）
none	不追加	需要原样发送时
如果设备上电后打印 gd32device>，敲一次回车设备打印了两行 gd32device>，说明设备把 \r 和 \n 都当回车了，改用 --newline cr 即可只触发一次。

### 远程会话

shub:connect 192.168.0.11:1000 连接别人共享的串口，体验与本地一致。
前提：目标电脑必须已对该会话 shub:share。
连接时携带密码：--password xxx，省略用默认密码 123456。

### 网络共享

shub:share 省略端口自动分配：从 1000 起步，取当前最大已用端口 + 1。
可手动指定：shub:share 2000；被占用则失败。
默认密码 123456，可改：shub:share 1000 --password abc；可关闭：--no-password。
多客户端同时连入，任一客户端数据写入串口，串口数据广播给所有客户端。
密码为明文校验，仅用于防止误连误操作，不是安全机制。
shub:unshare 只关共享、保留会话；shub:close 彻底关闭会话。
shub:shared 查询共享状态：无参数列出全部；带 COM 号查单个会话；带纯数字查共享端口。
只显示端口号，不显示本机 IP：连接方需自备目标机器的 IP（局域网内由对方告知，或通过 ipconfig 获取）。绑定地址为 0.0.0.0，监听所有网卡。
指令记录双向可见
指令记录格式：[shub@来源] 指令内容\n，来源是本地 COM 号（如 com5）或远端 IP:port（如 192.168.0.12:5555）。
两条独立的广播路径：
指令记录：本地发送 → 广播给所有远端；远端发送 → 广播给其他远端（排除发起者）。
设备回显：串口收到的所有数据 → 广播给所有连上的客户端（包括发起者）。

### 设备配置档案（主副本固定 profiles/）

不自动保存，只有显式 shub:save 才写盘。主副本固定存放在程序目录的 profiles/ 下，保证统一管理；同时支持写一份额外副本到用户指定的路径。

命令	作用
shub:save <文件名>	只保存到 profiles/<文件名>.json
shub:save <带路径的文件名>	主副本仍写 profiles/<文件名>.json，同时复制一份到指定路径
shub:load <文件名>	从 profiles/<文件名>.json 加载主副本
shub:load <带路径的文件名>	只从该路径加载；文件不存在直接报错，不回退 profiles/
shub:profiles	列出 profiles/ 下的所有有效配置文件
shub:forget <文件名>	删除 profiles/<文件名>.json 主副本；外部副本不受影响
加载规则：

输入形式	加载来源	文件不存在时
shub:load gd32	profiles/gd32.json	报错“Profile not found”
shub:load gd32.json	同上	同上
shub:load D:\cfg\gd32	只从 D:\cfg\gd32.json	报错“Profile not found”，不回退
shub:load D:\cfg\gd32.json	同上	同上
为什么带路径时不回退：避免“以为加载了外部文件，实际加载的是主副本”的误导。

### 本地串口配置（profiles/gd32.json）：

json
{
  "type": "serial",
  "port": "COM5",
  "baudrate": 115200,
  "bytesize": 8,
  "parity": "N",
  "stopbits": 1,
  "flow": "none",
  "newline": "cr"
}

### 远程连接配置（profiles/lab-server.json）：

json
{
  "type": "remote",
  "host": "192.168.0.11",
  "port": 1000,
  "password": "123456"
}

### 共享状态查询

命令	作用
shub:shared	列出所有已共享的会话
shub:shared com5	查询某个会话是否已共享
shub:shared 1000	查询某个共享端口是否已被本程序占用
注意：shub:shared 只查当前 shub 进程内的共享状态。其他进程（另一个 shub 实例、IPOP 等）持有的串口共享或端口占用，本命令看不到。

### 脚本逐行发送

shub:script cmds.txt 500：每行间隔 500ms 发送到当前会话。

# 开头的行可见但不发送；空行原样发送；--loop 循环；--stop 停止。

脚本绑定在启动它的会话上，切换会话不影响其继续执行；发送失败自动停止。

### 历史与导出

上下方向键切换本次运行的历史，默认保留 100 条（HISTORY_MAX 可调）。
shub:export hist.txt 把历史导出为文本，一行一条，覆盖写入。

### 帮助

shub:help 列出全部命令；shub:help open 显示单条详情。
所有命令的用法和描述集中维护在 commands.py，不会和实现脱节。

### 日志

滚动文件日志：源码运行在 logs/shub.log；打包后在 shub.exe 同级 logs/shub.log。
默认 INFO 级别；排查时把 config.py 的 LOG_LEVEL 改为 DEBUG。
控制台只输出 WARNING 以上，不干扰正常终端交互。
日志文件内容为中文；终端上所有面向用户的提示为英文。

## 4. 命令集（前缀 shub:）

### 会话管理

命令	作用
shub:ports	列出当前系统可用的 COM 口
shub:open <port> [baud] [8N1] [--flow ...] [--newline ...]	当前窗口新建本地串口会话
shub:open-new <port> [baud] [8N1] [--flow ...] [--newline ...]	新开命令行窗口打开本地串口
shub:connect <ip:port> [--password <密码>]	当前窗口新建远程会话
shub:connect-new <ip:port> [--password <密码>]	新开窗口连接远程端口
shub:switch <name>	切换当前会话
shub:close [name]	关闭会话，省略则关当前
shub:list	列出所有会话及状态
shub:exit	退出

### 设备档案

命令	作用
shub:save <文件名|路径>	保存当前会话配置；主副本固定写 profiles/，可选额外副本到指定路径
shub:load <文件名|路径>	带路径 → 只从该路径加载；不带路径 → 从 profiles/ 加载主副本
shub:profiles	列出 profiles/ 下的所有配置文件
shub:forget <文件名>	删除 profiles/ 下的主副本（外部副本不删）

### 网络共享

命令	作用
shub:share [端口] [--password <密码>] [--no-password]	开启 TCP 广播，省略端口自动分配
shub:unshare	关闭当前会话的广播，会话保留
shub:shared [COM口|端口号]	查询共享状态：无参数列全部；带 COM 号查会话；带数字查端口

### 脚本与历史

命令	作用
shub:script <文件> [间隔ms] [--loop] [--stop]	逐行定时发送脚本
shub:export <文件路径>	导出历史命令到文件

### 其他

命令	作用
shub:help [命令]	显示命令列表或单条详情
shub:send <text>	发送以 shub: 开头的原始数据

### 交互规则

以 shub: 开头 → 解析为命令。
不以 shub: 开头 → 原样（补换行符）发给当前会话设备；非空输入在本地显示 > 内容，空输入不回显。
单独输入 shub: → 提示命令为空。
发送以 shub: 开头的原始数据 → 用 shub:send shub:hello 转义。

## 5. 模块职责与解耦点

### 模块	职责

config.py	所有默认值常量
logger.py	滚动日志，旁路记录
input_helper.py	行输入 + 历史
commands.py	命令注册表（纯数据）
profiles.py	主副本 profiles/ 管理 + 可选外部副本
core/serial_session.py	串口独占打开、读线程、订阅、远端输入事件
core/telnet_session.py	远程连接、行缓冲、指令记录识别
core/tcp_broadcast.py	TCP 广播、密码校验、指令记录广播
core/session_manager.py	会话表、端口分配、关闭清理
core/handlers*.py	命令实现
script_sender.py	脚本发送
main.py	装配、主循环、分发、打印线程

### 关键解耦点：

rx_queue 与 subscribe() 独立队列：终端显示和 TCP 广播各自消费，互不抢数据。
input_queue 统一放已格式化字符串：打印线程只管输出。
COMMANDS + HANDLERS：帮助文本与命令实现同源。
profiles.py：主副本与外部副本的路径规则在模块内完成，handlers_profile.py 只负责业务分发。
logger：与业务逻辑无关，只做旁路记录。

## 6. 已知限制

Windows 下 COM 口独占由驱动层强制，程序只需捕获拒绝异常并提示。
USB 转串口设备插拔后 COM 号可能变化，建议用 shub:ports 确认。
串口参数（尤其波特率）必须与设备一致，否则乱码或无数据。
换行符必须与设备约定一致：letter-shell 类设备用 cr，多数设备用 crlf；不确定时先试默认值，观察设备是否一次回车打印两行提示符。
共享必须由目标电脑显式 shub:share，客户端无法强制连接未共享的串口。
远程会话不支持 shub:share，只能共享本地串口。
共享密码明文校验，仅防误连，不防抓包；敏感环境配合内网隔离或隧道。
用普通 Telnet 客户端连设了密码的端口时，需先手动输入密码行，否则服务端会等待密码。
指令记录广播依赖“指令以换行结束、设备输出按行”这一约定；设备输出中若出现与 [shub@ 相同的行首文本，会被误判为指令记录。该前缀在设备输出中极少出现，但并非绝对不可能。
远端一次发送多行指令时，服务端按整块解码后作为一条指令记录广播，不逐行拆分。
设备如果整行 echo 指令，远端会看到“指令记录 + 设备 echo + 结果”三行；优先在设备固件关 echo，shub 侧不做过滤。
自动分配的共享端口不回填空洞；手动指定被占用会失败。
新窗口方式为进程级隔离，配置不共享；同一串口不能被两个实例同时占用。
跨外网共享需端口映射或内网穿透（frp、Cloudflare Tunnel 等）。
多会话同时有数据时终端输出会交错，靠 [会话名] 前缀区分；正在输入的行可能被后台输出刷掉，属命令行固有问题。
脚本文件建议纯 ASCII/UTF-8；设备只认 ASCII 时中文行会出问题。
不支持 Tab 补全；端口号需手动输入。
首版无图形界面，也无 CUI 分栏；CUI 为可选后续增强。
日志默认不记录每条串口收发数据，排查时调 LOG_LEVEL=DEBUG。
配置文件格式为 JSON，用 json.load 读取，不会执行任意代码；但仍建议只加载可信来源的配置文件。
远程配置中的密码为明文存储，仅用于便捷登录，不是安全机制。 需要保密的环境请不保存远程配置，或手动从 JSON 中删除密码字段。
主副本固定为程序目录下的 profiles/。如果程序安装在 C:\Program Files 等受保护目录且没有写权限，保存会失败；请把程序解压到用户可写目录。
shub:load 带路径时不回退到 profiles/：文件不存在直接报错，避免误以为加载成功。想走主副本时，用 shub:load <文件名> 不带路径。
shub:forget 只删主副本，不删外部副本：外部文件由用户自己管理。
shub:profiles 只列出 profiles/ 下含 type 字段的有效 .json 文件；其他文件会被忽略。
shub:share 只显示端口，不显示本机 IP：绑定地址为 0.0.0.0，监听所有网卡；连接方需自备目标机器的 IP（局域网内由对方告知，或通过 ipconfig 获取），再用 shub:connect <ip>:<port> 连接。
shub:shared 只查当前 shub 进程内的共享状态。其他进程（另一个 shub 实例、IPOP 等）持有的串口共享或端口占用，本命令看不到。想确认某个 COM 口是否被别的程序占用，试 shub:open comX：如果打开失败并提示“端口已被占用”，说明有其他程序在占用。
终端内所有面向用户的文本为英文，日志文件仍为中文；如果需要本地化，直接改 commands.py 和 handlers*.py 里的字符串即可。

## 8. 验证顺序

shub:ports — 看可用 COM 口。
shub:open comX --newline cr — 针对 letter-shell 类设备打开串口，敲回车确认只打印一次 gd32device>。
发指令看回显，本地应显示 [comX] > 指令（空回车不显示）。
shub:share 1000 — 开启共享，默认密码 123456，只显示端口号。
shub:shared — 列出所有共享；shub:shared comX 查单个；shub:shared 1000 查端口。
另一台机器 shub:connect 你的IP:1000 — 输入密码，共享操作。
远端敲指令，确认：
本地终端看到 [comX] <remote ip:port> 指令；
其他远端看到 [shub@ip:port] 指令；
发起者不收到自己的指令记录；
设备回显两端都能看到。
本地敲指令，确认远端看到 [shub@comX] 指令，本地看到 [comX] > 指令，两端都看到设备回显。
shub:open-new comY 9600 7E1 --newline cr — 新窗口确认参数正确。
关闭 comX 再 shub:open comX — 确认输出正常。
shub:script cmds.txt 500 — 注释可见不发、空行原样发。
shub:export hist.txt — 导出历史。
拔掉串口后发送指令 — 确认有“Send failed”提示。
shub:save gd32 — 只在 profiles/gd32.json 生成主副本。
shub:save D:\cfg\gd32 — 主副本仍在 profiles/gd32.json，同时在 D:\cfg\gd32.json 生成额外副本。
shub:close 后 shub:load gd32 — 从主副本恢复。
shub:load D:\cfg\gd32 — 从 D:\cfg\gd32.json 加载（外部副本）。
shub:load E:\backup\gd32（不存在的路径）— 直接报错“Profile not found”，不回退 profiles/。
shub:profiles — 列出 profiles/ 下的配置。
shub:forget gd32 — 删除主副本；D:\cfg\gd32.json 仍在。
python main.py --load gd32 — 启动时自动加载主副本。
手动把 JSON 里 port 改成不存在的 COM99，shub:load 应提示端口不存在并列出可用端口。
手动把 JSON 改成非法内容，shub:load 应提示读取失败，不崩溃。
在 profiles/ 放一个其他程序的 .json（没有 type 字段），shub:profiles 应忽略它。
shub:unshare 后 shub:shared 应显示该会话未共享；shub:shared 1000 应显示端口已释放。
