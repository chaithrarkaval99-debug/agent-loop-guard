"""Two interchangeable LLM backends. Both return an LLMResponse in Anthropic block format."""
import json, os, re
from dataclasses import dataclass


@dataclass
class LLMResponse:
    blocks: list          # [{"type":"text",...} | {"type":"tool_use","id","name","input"}]
    input_tokens: int
    output_tokens: int

    @property
    def text(self):
        return " ".join(b["text"] for b in self.blocks if b["type"] == "text")


class AnthropicLLM:
    """Real model. Needs `pip install anthropic` and ANTHROPIC_API_KEY."""
    def __init__(self, model=None):
        import anthropic
        self.client = anthropic.Anthropic()
        self.model = model or os.getenv("MODEL", "claude-haiku-5-5")

    def step(self, system, messages, tools):
        r = self.client.messages.create(model=self.model, max_tokens=1024,
                                        system=system, tools=tools, messages=messages)
        blocks = []
        for b in r.content:
            if b.type == "text":
                blocks.append({"type": "text", "text": b.text})
            elif b.type == "tool_use":
                blocks.append({"type": "tool_use", "id": b.id, "name": b.name, "input": b.input})
        return LLMResponse(blocks, r.usage.input_tokens, r.usage.output_tokens)


class MockLLM:
    """Scripted 'agent' with the classic flaw: when search returns nothing it retries.
    vary=False -> retries the exact same call; vary=True -> retries with slightly changed args."""
    def __init__(self, vary=False):
        self.vary = vary
        self.n = 0

    def _last_tool_result(self, messages):
        last = messages[-1]
        if last["role"] != "user" or isinstance(last["content"], str):
            return None, None
        res = last["content"][0]
        for m in reversed(messages[:-1]):
            if m["role"] == "assistant":
                for b in m["content"]:
                    if b["type"] == "tool_use" and b["id"] == res["tool_use_id"]:
                        return b["name"], res["content"]
        return None, None

    def step(self, system, messages, tools):
        self.n += 1
        name = re.search(r"My name is (.+?)\.", messages[0]["content"]).group(1)
        tool, result = self._last_tool_result(messages)
        calls = sum(m["role"] == "assistant" for m in messages)

        if tool is None:
            blocks = self._call("search_orders", {"customer_name": name})
        elif tool == "search_orders" and result.startswith("No results"):
            n = f"{name} {calls}" if self.vary else name
            blocks = self._call("search_orders", {"customer_name": n})
        elif tool == "search_orders":
            blocks = self._call("get_order_status", {"order_id": re.search(r"ORD-\d+", result).group()})
        else:
            blocks = [{"type": "text", "text": f"Your order status: {result}."}]
        return LLMResponse(blocks, len(json.dumps(messages)) // 4 + 200, 40)

    def _call(self, name, args):
        return [{"type": "tool_use", "id": f"toolu_{self.n}", "name": name, "input": args}]
