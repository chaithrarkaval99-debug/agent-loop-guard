"""Step 6: run the 50 tasks before (guards off) and after (guards on), print the comparison.
   python eval.py          -> mock LLM, free, instant
   python eval.py --live   -> real Claude (needs ANTHROPIC_API_KEY; try --n 10 first)"""
import argparse, json
from pathlib import Path
from agent import Guards, run_agent, ROOT
from llm import MockLLM, AnthropicLLM

NAMES = ["John Smith", "Priya Sharma", "Ananya Rao", "Rahul Verma", "Meera Iyer",
         "Arjun Nair", "Kavya Reddy", "Sanjay Gupta", "Divya Menon", "Vikram Singh"]


def typo(name):                      # "Smith" -> "Smiht"  => search_orders returns nothing
    return name[:-2] + name[-1] + name[-2]


def make_tasks(n=50):
    tasks = []
    for i in range(n):
        name = NAMES[i % len(NAMES)]
        bad = i % 5 in (1, 3)        # 40% of tasks have a misspelled name
        shown = typo(name) if bad else name
        tasks.append({"id": i, "bad": bad, "vary": bad and i % 3 == 0,
                      "text": f"Where is my order? My name is {shown}."})
    return tasks


def run_all(tasks, live, guards):
    out = []
    for t in tasks:
        llm = AnthropicLLM() if live else MockLLM(vary=t["vary"])
        out.append(run_agent(t, llm, guards))
    return out


def summarize(label, rs):
    n = len(rs)
    s = {"label": label, "stuck_rate": sum(r.stuck for r in rs) / n,
         "avg_steps": sum(r.steps for r in rs) / n, "avg_cost": sum(r.cost for r in rs) / n,
         "by_status": {k: sum(r.status == k for r in rs) for k in sorted({r.status for r in rs})}}
    print(f"{label:8} stuck {s['stuck_rate']*100:5.1f}% | steps/task {s['avg_steps']:5.2f} | "
          f"cost/task ${s['avg_cost']:.5f} | {s['by_status']}")
    return s


def save_traces(folder, rs, k=3):
    d = ROOT / "traces" / folder; d.mkdir(parents=True, exist_ok=True)
    for r in [r for r in rs if r.stuck][:k]:
        (d / f"task_{r.task_id}.json").write_text(json.dumps(
            {"status": r.status, "steps": r.steps, "cost": r.cost, "trace": r.trace}, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--live", action="store_true")
    ap.add_argument("--n", type=int, default=50); a = ap.parse_args()
    tasks = make_tasks(a.n)

    before = run_all(tasks, a.live, Guards(enabled=False))
    ok = [r.cost for r in before if r.status == "done"]
    budget = 3 * (sum(ok) / len(ok))                 # Step 3: 3x avg *normal* task cost
    print(f"budget per task = 3 x avg normal cost = ${budget:.5f}\n")
    after = run_all(tasks, a.live, Guards(enabled=True, budget_usd=budget))

    sb, sa = summarize("BEFORE", before), summarize("AFTER", after)
    save_traces("before", before); save_traces("after", after)
    (ROOT / "results.json").write_text(json.dumps({"before": sb, "after": sa}, indent=2))
    print(f"\nEscalated tickets: {sum(bool(r.ticket) for r in after)}  (see tickets/)")
