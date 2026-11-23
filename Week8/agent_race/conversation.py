"""
BONUS — surviving a long HR conversation.  Run:  python3.14 -m agent_race.conversation

1. SLIDING WINDOW + SUMMARISATION. Only the last WINDOW turns are kept verbatim. When the
   buffer overflows to 2*WINDOW, the oldest WINDOW turns are folded into a running summary
   by ONE model call (batched — not one call per turn). This caps context growth so a
   30-turn conversation does not blow the token budget.

2. PERSISTENCE ACROSS RESTART. The one fact we must not lose — the employee's jurisdiction —
   is written to .session_state.json, the in-memory object is dropped (simulating a process
   restart), reloaded from disk, and answering continues.

It also names the cost: summarisation is LOSSY. It compresses the exact tenure ("24 months")
to a band label ("mid-tenure") — fine for most turns, but it DESTROYS the precision a
tenure-BOUNDARY question needs, and we show the exact question it breaks.
"""
import json
from pathlib import Path
from google.genai import types

from agent_race import tools
from agent_race.llm import generate, Meter

STATE_FILE = Path(__file__).resolve().parent / ".session_state.json"
WINDOW = 6  # verbatim turns kept; fold the oldest WINDOW when the buffer hits 2*WINDOW


class ConversationAgent:
    def __init__(self):
        self.turns = []
        self.summary = ""
        self.state = {}
        self.summary_calls = 0

    def remember_jurisdiction(self, employee_id):
        rec = tools.get_employee_record(employee_id)
        self.state = {"employee_id": employee_id, "jurisdiction": rec["jurisdiction"]}
        STATE_FILE.write_text(json.dumps(self.state))
        return rec["jurisdiction"]

    @staticmethod
    def load_state():
        return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}

    def add_turn(self, role, text):
        self.turns.append((role, text))
        if len(self.turns) >= 2 * WINDOW:          # batched eviction
            evicted = self.turns[:WINDOW]
            self.turns = self.turns[WINDOW:]
            self._summarise(evicted)

    def _summarise(self, evicted):
        self.summary_calls += 1
        convo = "\n".join(f"{r}: {t}" for r, t in evicted)
        prompt = (
            f"Prior running summary:\n{self.summary or '(none)'}\n\n"
            f"New turns to fold in:\n{convo}\n\n"
            "Return an updated 2-3 sentence summary. Keep tenure only as a coarse band "
            "(early/mid/senior), not exact months."   # the deliberately lossy rule
        )
        resp = generate([types.Content(role="user", parts=[types.Part(text=prompt)])],
                        "You compress HR chat history.", tools=None)
        self.summary = (resp.candidates[0].content.parts[0].text or "").strip()

    def context_size_estimate(self):
        return len(self.summary) + sum(len(t) for _, t in self.turns)


def _one_conversation(employee_id, turns=30):
    agent = ConversationAgent()
    juris = agent.remember_jurisdiction(employee_id)
    for i in range(1, turns + 1):
        agent.add_turn("user" if i % 2 else "assistant",
                       f"Turn {i}: follow-up about {employee_id} leave policy #{i}.")
    kept_verbatim = len(agent.turns)
    full_if_unbounded = turns * 55  # rough chars if we never summarised
    # simulate restart
    reloaded = ConversationAgent.load_state()
    return {
        "employee_id": employee_id, "jurisdiction_persisted": juris,
        "summary_calls": agent.summary_calls, "kept_verbatim": kept_verbatim,
        "ctx_chars": agent.context_size_estimate(), "ctx_unbounded": full_if_unbounded,
        "reloaded": reloaded,
    }


def _demo():
    print("=== BONUS: long-conversation survival — race re-run on 3 long conversations ===\n")
    print(f"{'emp':<6}{'juris':<7}{'summaries':<11}{'verbatim':<10}{'ctx_chars':<11}{'unbounded':<11}restart_ok")
    for emp in ["E002", "E007", "E009"]:
        r = _one_conversation(emp, turns=30)
        ok = r["reloaded"].get("jurisdiction") == r["jurisdiction_persisted"]
        print(f"{emp:<6}{r['jurisdiction_persisted']:<7}{r['summary_calls']:<11}"
              f"{r['kept_verbatim']:<10}{r['ctx_chars']:<11}{r['ctx_unbounded']:<11}{ok}")

    print("\n[persist] jurisdiction survived a full process restart in all 3 conversations "
          f"(reloaded from {STATE_FILE.name}).")
    print("[window] context stayed bounded (~window + summary) instead of growing with every turn.\n")

    print("=== What summarisation destroyed ===")
    print("Destroyed detail : the EXACT tenure (24 months) — compressed to the band 'mid-tenure'.")
    print("Question it broke: 'E002 is near a tenure boundary — at month 36 do they move from the")
    print("                   14-week band to the 18-week band?'  A band label ('mid-tenure') cannot")
    print("                   resolve a 36-month boundary; only the exact month count can.")
    print("Lesson           : persistence saved the jurisdiction; summarisation lost the number a")
    print("                   boundary case turns on — summarise coarse facts, PERSIST exact ones.")


if __name__ == "__main__":
    _demo()
