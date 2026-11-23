**[▶ Live demo]**[▶ Live demo](https://chaithrarkaval99-debug.github.io/agent-loop-guard/)**t guards.- try a misspelled name and compare with and without

# Loop detection + token budget agent

A support agent that stops itself before it burns money and escalates to a human.

## Run
    python eval.py                       # mock LLM, no API key
    pip install anthropic && export ANTHROPIC_API_KEY=...
    python eval.py --live --n 10         # real Claude (start small)

## Files
- tools.py  – fake orders DB; `search_orders` fails on misspelled names (the trap)
- llm.py    – MockLLM (loops on purpose) and AnthropicLLM
- agent.py  – loop + guards: step limit, cost budget, repeat detection, escalation
- eval.py   – 50 tasks, before vs after, saves traces/ and tickets/

## Results (mock, 50 tasks)
| | stuck rate | steps/task | cost/task |
|---|---|---|---|
| Before (no guards) | 40% | 11.8 | $0.01282 |
| After (guards)     | 40% | 3.7  | $0.00197 |

Cost per task down ~85%. The 20 stuck tasks now escalate to tickets instead of running away.
Stuck rate stays 40% because guards stop runaways, they don't fix the agent's recovery.
To lower it too, add a nudge ("that returned nothing, try another approach / ask the user to confirm spelling").
