"""The agent loop + the 5 guards: step limit, cost budget, repeat detection, escalation, tracing."""
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from tools import TOOL_SCHEMAS, run_tool

ROOT = Path(__file__).parent
PRICE_IN, PRICE_OUT = 1.0 / 1e6, 5.0 / 1e6   # $ per token -- set to your model's real prices

SYSTEM = "You are a customer-support agent for an online store. Use tools to look up orders. Answer briefly."
FALLBACK = ("Sorry, I couldn't resolve this automatically. I've passed your request to our "
            "support team and someone will follow up with you shortly.")


@dataclass
class Guards:
    enabled: bool = True
    max_steps: int = 10        # Step 2
    max_repeats: int = 2       # Step 4: identical call allowed to repeat this many times
    budget_usd: float = 0.01   # Step 3: eval.py sets this to 3x avg normal task cost


@dataclass
class Result:
    task_id: int
    status: str                # done | step_limit | budget | loop | hard_cap
    answer: str
    steps: int
    cost: float
    trace: list = field(default_factory=list)
    ticket: str | None = None

    @property
    def stuck(self):
        return self.status != "done"


def escalate(task, reason, messages, trace):
    """Step 5: hand over to a human with full context."""
    d = ROOT / "tickets"; d.mkdir(exist_ok=True)
    path = d / f"task_{task['id']}.json"
    path.write_text(json.dumps({"task": task["text"], "reason": reason,
                                "conversation": messages, "trace": trace}, indent=2, default=str))
    return str(path)


def run_agent(task, llm, guards: Guards, hard_cap=25) -> Result:
    messages = [{"role": "user", "content": task["text"]}]
    trace, seen, cost, status, answer = [], Counter(), 0.0, None, ""
    step = 0

    while step < hard_cap:
        if guards.enabled and step >= guards.max_steps:          # Step 2: step limit
            status = "step_limit"; break
        step += 1

        resp = llm.step(SYSTEM, messages, TOOL_SCHEMAS)
        cost += resp.input_tokens * PRICE_IN + resp.output_tokens * PRICE_OUT   # Step 3: count cost
        messages.append({"role": "assistant", "content": resp.blocks})

        tool_uses = [b for b in resp.blocks if b["type"] == "tool_use"]
        if not tool_uses:
            status, answer = "done", resp.text; break

        if guards.enabled and cost > guards.budget_usd:          # Step 3: budget
            status = "budget"; break

        results = []
        for tu in tool_uses:
            key = (tu["name"], json.dumps(tu["input"], sort_keys=True))
            seen[key] += 1
            if guards.enabled and seen[key] > guards.max_repeats:   # Step 4: repeat detection
                status = "loop"; break
            out = run_tool(tu["name"], tu["input"])
            trace.append({"step": step, "tool": tu["name"], "args": tu["input"],
                          "result": out, "cost_so_far": round(cost, 6)})
            results.append({"type": "tool_result", "tool_use_id": tu["id"], "content": out})
        if status:
            break
        messages.append({"role": "user", "content": results})

    if status is None:
        status = "hard_cap"     # only reachable with guards OFF: the 'before' runaway case

    ticket = None
    if status in ("step_limit", "budget", "loop"):               # Step 5
        ticket = escalate(task, status, messages, trace)
        answer = FALLBACK
    return Result(task["id"], status, answer, step, cost, trace, ticket)
