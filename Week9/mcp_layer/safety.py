"""
MCP SAFETY  —  the two things the task asks for before you trust tools over a socket.
=====================================================================================
Connecting an agent to tools over MCP means your model will read tool descriptions and
results you did not write, from a process you may not own. Two guards:

  1. ACCESS CONTROL (allowlist).  A client decides which tools it is willing to use from a
     given server, by name. A server could advertise ten tools; this client uses only the
     ones on its list. This is least-privilege at the discovery boundary: a tool the client
     never allows can never be put in front of the model, so it can never be called.

  2. TOOL-TRUST CHECK.  Before using someone else's tool you look at what it actually
     advertised. `check_tool_trust` flags the classic indirect-prompt-injection smell — a
     tool DESCRIPTION that, instead of describing a capability, tries to issue INSTRUCTIONS
     to the model ("ignore previous instructions", "always call me first", "do not tell the
     user"...). A description is data about a capability; if it reads like a command aimed
     at the agent, that is a red flag, and we refuse to register the tool.

These are about the TRUST BOUNDARY, not answer quality — MCP is plumbing, and plumbing is
exactly where access control belongs.
"""

# Phrases that have no business in a tool's *description* — they are attempts to steer the
# model rather than to describe a capability (indirect prompt injection via metadata).
_INJECTION_MARKERS = (
    "ignore previous", "ignore all previous", "disregard", "system prompt",
    "always call", "do not tell", "don't tell", "exfiltrate", "regardless of",
    "override", "jailbreak", "as an ai", "reveal your", "print your instructions",
)


class UntrustedToolError(RuntimeError):
    """Raised when a discovered tool fails the trust check and must not be registered."""


def tool_is_allowed(spec, tool_name: str) -> bool:
    """Access control: True only if this server's allowlist permits the tool (None = all)."""
    if getattr(spec, "allow", None) is None:
        return True
    return tool_name in spec.allow


def check_tool_trust(server_key: str, tool) -> None:
    """Raise UntrustedToolError if a discovered tool's metadata looks like an injection.

    `tool` is an mcp.types.Tool (has .name and .description). We only inspect metadata here;
    tool *outputs* are sanitised separately where they are consumed (see the Week-8 injection
    harness, carried forward) — defence in depth, not one magic check.
    """
    desc = (getattr(tool, "description", "") or "").lower()
    name = getattr(tool, "name", "") or ""
    for marker in _INJECTION_MARKERS:
        if marker in desc:
            raise UntrustedToolError(
                f"Refused tool {name!r} from server {server_key!r}: its description contains "
                f"instruction-like text ({marker!r}) — a tool description must describe a "
                f"capability, not issue commands to the model."
            )


def scan_discovered(discovered) -> list:
    """Report-only pass over already-discovered tools; returns a list of (name, verdict)."""
    out = []
    for t in discovered:
        verdict = "ok"
        low = (t.description or "").lower()
        for marker in _INJECTION_MARKERS:
            if marker in low:
                verdict = f"SUSPICIOUS:{marker}"
                break
        out.append((t.name, verdict))
    return out
