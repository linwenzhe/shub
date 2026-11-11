# 文件名: commands.py
"""Command registry: usage / desc / detail for help and dispatch."""

COMMANDS = {
    "ports": {
        "usage": "shub:ports",
        "desc": "List available COM ports on this machine",
        "detail": "Enumerates via pyserial and shows device descriptions.",
    },
    "open": {
        "usage": "shub:open <port> [baud] [8N1] [--flow none|rts|xon] [--newline crlf|lf|cr|none]",
        "desc": "Open a local serial session in current window and switch to it",
        "detail": "Only port is required; others default. "
                  "Letter-shell style devices usually need --newline cr.",
    },
    "open-new": {
        "usage": "shub:open-new <port> [baud] [8N1] [--flow ...] [--newline ...]",
        "desc": "Open a local serial session in a new console window",
        "detail": "Spawns an independent shub instance; args are forwarded as-is.",
    },
    "connect": {
        "usage": "shub:connect <ip:port> [--password <pass>]",
        "desc": "Connect to a remote shared session in current window",
        "detail": "Target must be shared via shub:share. Default password is 123456.",
    },
    "connect-new": {
        "usage": "shub:connect-new <ip:port> [--password <pass>]",
        "desc": "Connect to a remote shared session in a new console window",
        "detail": "Spawns an independent shub instance.",
    },
    "switch": {
        "usage": "shub:switch <name>",
        "desc": "Switch current session",
        "detail": "Session name is usually the COM port or ip:port.",
    },
    "close": {
        "usage": "shub:close [name]",
        "desc": "Close a session (current if omitted)",
        "detail": "Also stops sharing and running script on that session.",
    },
    "list": {
        "usage": "shub:list",
        "desc": "List all sessions and their states",
        "detail": "Shows name, type, baudrate, share port, and password state.",
    },
    "save": {
        "usage": "shub:save <name|path>",
        "desc": "Save current session config; primary copy always in profiles/",
        "detail": "With name only, save to profiles/<name>.json. "
                  "With path, save to profiles/<basename>.json and copy to the path. "
                  "Overwrites existing files; .json extension optional.",
    },
    "load": {
        "usage": "shub:load <name|path>",
        "desc": "Load a config file and open the session",
        "detail": "Name only -> load from profiles/. Path -> load from that path only "
                  "(no fallback). Type field decides serial or remote. "
                  "Existing session with same name is switched to instead.",
    },
    "profiles": {
        "usage": "shub:profiles",
        "desc": "List all configs under profiles/",
        "detail": "Only valid .json files with a 'type' field are listed.",
    },
    "forget": {
        "usage": "shub:forget <name>",
        "desc": "Delete a config under profiles/ (primary copy only)",
        "detail": "External copies are not affected.",
    },
    "share": {
        "usage": "shub:share [port] [--password <pass>] [--no-password]",
        "desc": "Start TCP broadcast of current session",
        "detail": "Port auto-assigned from 1000 upward if omitted. Default password 123456.",
    },
    "unshare": {
        "usage": "shub:unshare",
        "desc": "Stop broadcast of current session, release the port",
        "detail": "Session is kept; local serial port remains usable.",
    },
    "shared": {
        "usage": "shub:shared [COM|port]",
        "desc": "Query shared state",
        "detail": "No arg: list all shared sessions. "
                  "COM name: check that session. "
                  "Pure number: check that share port.",
    },
    "script": {
        "usage": "shub:script <file> [interval_ms] [--loop] [--stop]",
        "desc": "Send a script file line by line",
        "detail": "Lines starting with # are shown but not sent. Empty lines are sent as-is. "
                  "Default interval 100ms.",
    },
    "export": {
        "usage": "shub:export <file>",
        "desc": "Export command history to a file",
        "detail": "Overwrites the file. Empty history is not saved.",
    },
    "help": {
        "usage": "shub:help [command]",
        "desc": "Show command list or detailed help for one command",
        "detail": "No arg: list all. With arg: show one command's details.",
    },
    "send": {
        "usage": "shub:send <text>",
        "desc": "Send raw text that starts with the shub: prefix",
        "detail": "Escape hatch for sending device data that begins with the command prefix.",
    },
    "exit": {
        "usage": "shub:exit",
        "desc": "Exit the program",
        "detail": "Closes all sessions and stops all sharing.",
    },
}