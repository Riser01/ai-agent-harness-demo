"""The same harness, rebuilt as a LangGraph graph: the seven parts again, under LangGraph's names.

harness.py builds the loop, the gate, the memory and the trace by hand so you can see why each exists. LangGraph is a
framework that packages some of those ideas: you describe the steps as a graph, and it saves the state and can pause for
a human. Reading this file next to harness.py shows that nothing new happens. The loop is a cycle in a graph, the gate
is interrupt(), memory is a checkpointer, the trace is stream(). Learn the parts once and you can recognise them in
any agent framework. It reuses tools.py, handover_note and the model contract from the plain version, and only the
engine changes.

Where the seven parts live in this engine (line numbers are for this file as shipped)
    1 Loop      the edge that sends act back to decide (line 144) is the loop; the conditional edges (130,
                134) pick the exits. The step cap is a counter in the state (line 70), so a pause cannot
                reset it, and recursion_limit (155) is only a backstop.
    2 Tools     the act node (line 105): validate, run once, never retried; a failure becomes an error line.
    3 Context   cut() (line 63) caps every result. There is no history window in this engine.
    4 Memory    the checkpointer (line 146) saves the state after every node, keyed by thread_id. The state's
                shape is GState (line 44); its history is append-only.
    5 Gates     the gate node (line 85) calls interrupt() (95), which pauses and saves the whole run;
                the driver resumes it with the human's answer (196). Default deny and the denial cap are here too.
    6 Verify    the check node (line 117) runs verify(state) after the model says "final".
    7 Trace     stream() (line 183) is the flight recorder; record() (line 160) turns each update into
                one trace line, in the same format as the plain harness.
    + Recovery  the hand-over note is built on the way out (202); the recursion backstop is caught at 198.

Differences from the plain harness, on purpose, to keep this file small
    * An unknown tool is treated as irreversible and gated (the plain harness refuses it outright).
    * There is no repeat check, no history window and no checkpoint hook. The step cap, denial cap, gate and verify
      are all here.

Requires:  pip install -r requirements.txt    (langgraph 1.2.23)
"""
import operator
import json
from typing import Annotated, Any, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from harness import RunResult, TraceEntry, handover_note


class GState(TypedDict):
    """The graph's state (part 4, memory). `history` is append-only: the reducer adds new lines instead of replacing."""
    history: Annotated[list[str], operator.add]
    pending: "dict | None"      # the call the model proposed and the harness has not run yet
    steps: int                  # model calls so far: THIS is the step cap, and it survives pauses
    denials: int
    status: str                 # empty until a node decides the run is over
    answer: str


def _args(args: dict) -> str:
    """Args as JSON text, same format as the plain harness."""
    return json.dumps(args, sort_keys=True, default=str)


def build_graph(model, tools, verify, max_steps, max_result_chars, max_denials, state):
    """Wire the four nodes and the edges, and compile with a checkpointer. `state` is the tools' own to-do list."""
    by_name = {t.name: t for t in tools}

    def cut(text: str) -> str:
        """[part 3, Context] Cut every result, as in the plain harness."""
        return text if len(text) <= max_result_chars else text[:max_result_chars] + " [truncated]"

    # NODE decide [part 1, Loop] = harness steps 1 to 3: ask the model. The step cap is a counter in state, so a pause cannot reset it.
    def decide(s: GState):
        """Ask the model. Returns only the keys it changes."""
        if s["steps"] >= max_steps:
            return {"pending": None, "status": "step-limit", "answer": "stopped: step limit reached"}
        try:
            d = model(s["history"])
            if not isinstance(d, dict) or ("final" not in d and "tool" not in d):
                raise ValueError("malformed model output")
        except Exception as err:
            return {"pending": None, "status": "model-error", "answer": f"stopped: the model call failed ({err})"}
        if "final" in d:
            return {"steps": s["steps"] + 1, "pending": None, "answer": str(d["final"])}
        args = d.get("args") if isinstance(d.get("args"), dict) else {}
        call = {"tool": str(d["tool"]), "args": args}
        return {"steps": s["steps"] + 1, "pending": call, "history": [f"assistant wants {call['tool']} {_args(args)}"]}

    # NODE gate [part 5, Gates] = harness step 6. interrupt() pauses the whole graph and saves it; the human's answer resumes it.
    def gate(s: GState):
        """Irreversible (or unknown) tools wait for a human. On resume this node re-runs from the top, so no side effects here."""
        call = s["pending"]
        tool = by_name.get(call["tool"])
        if tool is not None and tool.risk != "irreversible":
            return {}
        try:
            words = tool.describe(call["args"], state) if tool and tool.describe else f"{call['tool']} {_args(call['args'])}"
        except Exception:
            words = f"{call['tool']} {_args(call['args'])}"
        if interrupt({"tool": call["tool"], "args": call["args"], "words": words}):
            return {}
        denials = s["denials"] + 1
        update = {"pending": None, "denials": denials,
                  "history": [f"denied: {call['tool']} {_args(call['args'])} was not approved. Do not retry it."]}
        if denials >= max_denials:
            update.update(status="denied-limit", answer="stopped: too many actions were denied")
        return update

    # NODE act [part 2, Tools] = harness steps 5 and 7. A failure becomes an error line the model can read.
    def act(s: GState):
        """Validate, then run the tool. Never retried."""
        call = s["pending"]
        tool = by_name.get(call["tool"])
        try:
            problem = f"unknown tool {call['tool']}" if tool is None else tool.validate(call["args"])
            line = f"error: {problem}" if problem else f"tool: {tool.run(call['args'], state)}"
        except Exception as err:
            line = f"error: {err}"
        return {"pending": None, "history": [cut(line)]}

    # NODE check [part 6, Verify] = harness step 2 after "final": look at the world, not at the model's claim.
    def check(s: GState):
        """After 'final': run the verifier and pick the final status."""
        problem = None
        if verify is not None:
            try:
                problem = verify(state)
            except Exception as err:
                problem = f"the check itself crashed: {err}"
        if problem:
            return {"status": "failed-verification", "answer": f"not done: {problem}"}
        return {"status": "done-with-denials" if s["denials"] else "done"}

    # EDGES [part 1, Loop] = the exits of the loop: plain functions that pick the next node.
    def after_decide(s: GState):
        """A status means stop; a pending call means the gate; otherwise the model said final."""
        return "stop" if s["status"] else ("gate" if s["pending"] else "check")

    def after_gate(s: GState):
        """Denial cap reached means stop; an allowed call goes to act; a denied one goes back to the model."""
        return "stop" if s["status"] else ("act" if s["pending"] else "decide")

    g = StateGraph(GState)
    for name, node in (("decide", decide), ("gate", gate), ("act", act), ("check", check)):
        g.add_node(name, node)
    g.add_edge(START, "decide")
    g.add_conditional_edges("decide", after_decide, {"gate": "gate", "check": "check", "stop": END})
    g.add_conditional_edges("gate", after_gate, {"act": "act", "decide": "decide", "stop": END})
    g.add_edge("act", "decide")                      # the cycle: this edge IS the loop
    g.add_edge("check", END)
    return g.compile(checkpointer=InMemorySaver())   # [part 4, Memory]: state saved after every node, per thread_id


def run_graph(goal, *, model, tools, state, max_steps=10, max_result_chars=300, max_denials=3,
              approve=None, verify=None, thread_id="t1") -> RunResult:
    """Run the graph and return the same RunResult as harness.run, so agent.py and the tests do not care which engine ran."""
    graph = build_graph(model, tools, verify, max_steps, max_result_chars, max_denials, state)
    # recursion_limit is only a BACKSTOP (it counts node runs and restarts on every resume); `steps` is the real cap.
    # One step runs at most about 3 nodes (decide, gate, act), so 6 per step plus 10 spare is generous and never binds first.
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": max_steps * 6 + 10}
    payload: Any = {"history": [f"user: {goal}"], "pending": None, "steps": 0, "denials": 0, "status": "", "answer": ""}
    trace: list[TraceEntry] = []
    step = 0

    def record(node: str, delta: dict) -> None:
        """[part 7, Trace] Turn one stream() update into a trace line. stream() is the graph's built-in flight recorder."""
        nonlocal step
        step = delta.get("steps", step)
        for line in delta.get("history", []):      # each history line a node added becomes one trace line
            if line.startswith("assistant wants "):      # the model asked for a tool
                trace.append(TraceEntry(step, "decide", line[len("assistant wants "):]))
            elif line.startswith("denied: "):            # the human (or default) said no
                trace.append(TraceEntry(step, "denied", line[len("denied: "):].split(" was not approved")[0]))
            elif line.startswith("error: "):             # bad input, unknown tool, or a failing tool
                trace.append(TraceEntry(step, "error", line))
            else:                                        # anything else is a tool result ("tool: ...")
                trace.append(TraceEntry(step, "tool", line[len("tool: "):]))
        if node == "decide" and "answer" in delta and not delta.get("status"):
            trace.append(TraceEntry(step, "decide", f"final: {delta['answer']}"))
        if delta.get("status") and node != "check":
            trace.append(TraceEntry(step, "stop", delta["answer"]))
        if node == "check" and delta.get("status") == "failed-verification":
            trace.append(TraceEntry(step, "stop", delta["answer"]))

    try:
        while True:
            paused = None
            for update in graph.stream(payload, config, stream_mode="updates"):
                for node, delta in update.items():
                    if node == "__interrupt__":
                        paused = delta[0].value               # the graph is paused at the gate, state saved
                        trace.append(TraceEntry(step, "pause", f"paused at the gate, state saved: {paused['words']}"))
                    else:
                        record(node, delta or {})
            if paused is None:
                break
            try:
                allowed = bool(approve(paused["tool"], paused["args"], paused["words"])) if approve else False
            except Exception:
                allowed = False                               # default deny, as in the plain harness
            payload = Command(resume=allowed)                 # resume the SAME thread from its checkpoint
        values = graph.get_state(config).values
    except GraphRecursionError:                               # backstop only
        values = {**graph.get_state(config).values, "status": "step-limit", "answer": "stopped: backstop limit reached"}
        trace.append(TraceEntry(step, "stop", values["answer"]))
    status = values["status"]
    return RunResult(status, values["answer"], values["denials"], trace, handover_note(status, goal, trace))
