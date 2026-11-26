"""
Thin Gemini wrapper shared by BOTH the agent and the workflow, so the race is
apples-to-apples: identical model, identical temperature, identical token/cost math.

The only thing that differs between the two systems is WHO decides the tool order
(the model, in a loop, vs. hard-coded Python). Everything about how a single model
call is made and metered lives here.
"""
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# ---- Frozen model + params (stamped identically onto agent and workflow) -------
MODEL = "gemini-2.5-flash"
TEMPERATURE = 0.0

# ---- Pricing (USD per 1,000,000 tokens). Edit here if Google changes rates. -----
# Gemini bills input tokens and output tokens; for 2.5 Flash, "thinking" tokens are
# billed as output. We therefore treat (total_tokens - prompt_tokens) as billed output.
PRICE_IN_PER_M = 0.30
PRICE_OUT_PER_M = 2.50

_client = genai.Client(
    api_key=os.environ.get("GEMINI_API_KEY"),
    http_options=types.HttpOptions(api_version="v1beta"),  # system_instruction needs v1beta, not v1
)


@dataclass
class Meter:
    """Running meter summed across EVERY model call of one question.

    Summing per-call (not just the final call) is the whole point: the agent loop
    re-sends the growing message list every lap, so a single question's token bill
    is the SUM over laps, not the last lap. The workflow makes exactly one call.
    """
    calls: int = 0
    prompt_tokens: int = 0
    output_tokens: int = 0   # billed output = total - prompt (includes thinking)
    total_tokens: int = 0
    cost_usd: float = 0.0
    per_call: list = field(default_factory=list)

    def add(self, usage):
        p = int(getattr(usage, "prompt_token_count", 0) or 0)
        t = int(getattr(usage, "total_token_count", 0) or 0)
        out = max(t - p, 0)
        cost = (p / 1_000_000) * PRICE_IN_PER_M + (out / 1_000_000) * PRICE_OUT_PER_M
        self.calls += 1
        self.prompt_tokens += p
        self.output_tokens += out
        self.total_tokens += t
        self.cost_usd += cost
        self.per_call.append({"prompt": p, "output": out, "total": t, "cost_usd": round(cost, 8)})
        return t, cost


def generate(contents, system_instruction, tools=None):
    """One metered Gemini call. Returns the raw response; caller feeds it to a Meter.

    tools=None -> plain generation (used by the workflow's single compose call).
    tools=[...] -> function-calling with AUTOMATIC calling DISABLED, so our loop
    drives the tools explicitly and can meter every lap.
    """
    cfg_kwargs = {"system_instruction": system_instruction, "temperature": TEMPERATURE}
    if tools is not None:
        cfg_kwargs["tools"] = tools
        cfg_kwargs["automatic_function_calling"] = types.AutomaticFunctionCallingConfig(disable=True)
    config = types.GenerateContentConfig(**cfg_kwargs)
    return _client.models.generate_content(model=MODEL, contents=contents, config=config)
