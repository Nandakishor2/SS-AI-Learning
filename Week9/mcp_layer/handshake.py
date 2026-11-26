"""
RAW JSON-RPC — look at the wire ONCE so MCP stops being a mystery.
==================================================================
Everything else in this package uses the MCP SDK, which hides the bytes. This file does
the opposite: it spawns the HRIS server and speaks the protocol BY HAND over stdio, so you
can read the exact frames that `initialize` / `tools/list` / `tools/call` put on the wire.

MCP stdio framing is dead simple: each JSON-RPC 2.0 message is ONE line of JSON (newline
delimited) on stdin/stdout. Requests carry an `id` and get a response with the same `id`;
notifications carry no `id` and get nothing back. That is the entire transport.

    python3.14 -m mcp_layer.handshake
"""
import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SERVER = _ROOT / "mcp_layer" / "servers" / "hris_server.py"


def _send(proc, msg):
    line = json.dumps(msg)
    print(f"\n──► CLIENT sends:\n{json.dumps(msg, indent=2)}")
    proc.stdin.write(line + "\n")
    proc.stdin.flush()


def _read_response(proc, want_id):
    """Read newline-delimited frames until the response with id == want_id arrives."""
    while True:
        line = proc.stdout.readline()
        if not line:
            raise RuntimeError("server closed the pipe")
        line = line.strip()
        if not line:
            continue
        msg = json.loads(line)
        if msg.get("id") == want_id:
            print(f"\n◄── SERVER replies:\n{json.dumps(msg, indent=2)}")
            return msg
        # a server-initiated notification/log; show it dimmed and keep reading
        print(f"\n   · server not/log: {json.dumps(msg)[:160]}")


def main():
    proc = subprocess.Popen(
        [sys.executable, str(_SERVER)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, bufsize=1, cwd=str(_ROOT),
    )
    try:
        print("=" * 70)
        print("RAW MCP OVER STDIO  —  one request per line, response matched by id")
        print("=" * 70)

        # 1) initialize — the capability handshake
        _send(proc, {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "week9-handshake-demo", "version": "1.0"},
            },
        })
        init = _read_response(proc, 1)
        server_info = init.get("result", {}).get("serverInfo", {})
        print(f"\n   → handshake done. Server identifies as: {server_info}")

        # 2) initialized — a NOTIFICATION (no id, no reply). Required before normal use.
        _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        print("   (no reply expected — notifications have no id)")

        # 3) tools/list — DISCOVERY. This is how the agent learns the tool it never coded.
        _send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        listed = _read_response(proc, 2)
        names = [t["name"] for t in listed.get("result", {}).get("tools", [])]
        print(f"\n   → discovered tools: {names}")

        # 4) tools/call — invoke the discovered tool. This is one 'dispatch' call on the wire.
        _send(proc, {
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "get_employee_record", "arguments": {"employee_id": "E002"}},
        })
        _read_response(proc, 3)

        print("\n" + "=" * 70)
        print("That is MCP: initialize → (initialized) → tools/list → tools/call.")
        print("The server never knew which model asked. The AI runs on the CLIENT side.")
        print("=" * 70)
    finally:
        proc.stdin.close()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    main()
