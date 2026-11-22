"""The harness: the plain code that stands between a model and the real world.

A model can only propose ("delete task 2"). Everything that decides what actually happens is in this file, and none
of it is a prompt a model could talk its way past: how long the loop may run, which tools exist and what they may be
given, who has to say yes before something irreversible, how much text the model sees, whether "done" is really true,
what was saved, and what happened. If you read one function in the whole project, read run() (line 89). It is one
loop of eight numbered steps, and the comments inside it say which part of the harness each step is.

The file knows nothing about to-do lists. `state` is an opaque object it hands to the tools, and every fact about the
app arrives through a Tool (see tools.py). That is why the same engine could run an email or a payments agent
unchanged, and why it can be tested with a fake model and no network.

Where the seven parts live (line numbers are for this file as shipped)
    1 Loop      the for-loop at line 132. It can end six ways, each a named status: model-error (line 140),
                failed-verification (154), loop-detected (166), denied-limit (200),
                checkpoint-failed (219) and step-limit (222). A model that says "final" ends it as
                done or done-with-denials (155).
    2 Tools     the Tool contract (line 46); lookup and input check in step 5 (168); the run in step 7
                (203), which is never retried because a repeated write is worse than one failure.
    3 Context   cut() (line 110) caps every result and trace line; view() (line 118) is the history window.
    4 Memory    step 8 (line 213): after any tool that is not a read, the checkpoint hook saves the state.
    5 Gates     step 6 (line 182): only irreversible tools ask a human, and no answer means no.
    6 Verify    step 2 (line 142): when the model says "final", verify(state) checks the real world first.
    7 Trace     log() (line 114) writes one TraceEntry per event; TraceEntry itself is at line 58.
    + Recovery  finish() (line 128) is the one way out of run(), so every early stop gets the hand-over note
                that handover_note() (line 75) writes for a person to pick up.

Model contract:  model(history: list[str]) -> {"tool": name, "args": {...}}  or  {"final": text}
"""
from dataclasses import dataclass
import json
from typing import Any, Callable, Literal

Risk = Literal["read", "write", "irreversible"]
Status = Literal["done", "done-with-denials", "failed-verification", "step-limit", "loop-detected",
                 "denied-limit", "model-error", "checkpoint-failed"]
TraceKind = Literal["decide", "tool", "denied", "error", "stop", "pause"]   # "pause" is only used by the LangGraph engine

Model = Callable[[list[str]], dict[str, Any]]
Approve = Callable[[str, dict[str, Any], str], bool]      # (tool name, args, plain words) -> allowed?
Verify = Callable[[Any], "str | None"]                     # state -> a problem sentence, or None when all is well
Checkpoint = Callable[[Any], None]                         # state -> saved somewhere


@dataclass
class Tool:
    """A tool is a contract: what the model may ask for, how risky it is, and how to check and run it."""
    name: str
    description: str                       # shown to the model in the menu
    params: dict[str, str]                 # parameter name -> type word, shown to the model in the menu
    risk: Risk                             # NOT shown to the model: the harness reads it, a prompt cannot change it
    validate: Callable[[dict[str, Any]], "str | None"]   # a problem sentence, or None when the input is fine
    run: Callable[[dict[str, Any], Any], str]            # (args, state) -> short result text; raises on failure
    describe: "Callable[[dict[str, Any], Any], str] | None" = None   # plain words for the approval prompt


@dataclass
class TraceEntry:
    """One numbered line of the flight recorder."""
    step: int
    kind: TraceKind
    detail: str


@dataclass
class RunResult:
    """What a run returns. `status` is decided by code, never by the model's own claim."""
    status: Status
    answer: str
    denials: int
    trace: list[TraceEntry]
    handover: str = ""     # plain words for a human when the run stopped early; empty when it finished normally


def handover_note(status: str, goal: str, trace: list[TraceEntry]) -> str:
    """Recovery: a note a person can pick the work up from. Empty for runs that finished normally."""
    if status in ("done", "done-with-denials"):
        return ""
    last = trace[-1] if trace else None
    return (f"Stopped with status '{status}'. Goal: '{goal}'. Steps taken: {last.step if last else 0}. "
            f"Last step: {last.detail if last else 'none'}. A person should check the task list and decide whether to retry.")


def _args_text(args: dict[str, Any]) -> str:
    """Args as JSON text. Sorted keys keep the repeat check honest: key order cannot hide a repeat."""
    return json.dumps(args, sort_keys=True, default=str)


def run(
    goal: str,
    *,
    model: Model,
    tools: list[Tool],
    state: Any,
    max_steps: int = 10,
    max_result_chars: int = 300,
    max_denials: int = 3,
    max_history: "int | None" = None,
    approve: "Approve | None" = None,
    verify: "Verify | None" = None,
    checkpoint: "Checkpoint | None" = None,
) -> RunResult:
    """Run the loop: decide, act, observe, stop. Every exit is a named status. One step = one model call."""
    history: list[str] = [f"user: {goal}"]
    trace: list[TraceEntry] = []
    recent: list[str] = []                       # the last calls, for the repeat check
    denials = 0
    tool_map = {t.name: t for t in tools}

    def cut(text: str) -> str:
        """Context: no single result may flood the model or the trace."""
        return text if len(text) <= max_result_chars else text[:max_result_chars] + " [truncated]"

    def log(step: int, kind: TraceKind, detail: str) -> None:
        """Trace: one numbered line per event."""
        trace.append(TraceEntry(step=step, kind=kind, detail=cut(detail)))

    def view() -> list[str]:
        """Context: what the model sees this turn. The goal, denial notes that fell out of the window, the last N lines."""
        if max_history is None or len(history) <= max_history + 1:
            return list(history)                                   # everything fits: show it all
        goal_line = history[0]
        tail = history[-max_history:] if max_history > 0 else []   # history[-0:] would be the WHOLE list
        forgotten = history[1:len(history) - len(tail)]            # the lines that fell out of the window
        old_denials = [line for line in forgotten if line.startswith("denied:")]   # a refusal must never be forgotten
        return [goal_line, *old_denials, *tail]

    def finish(status: Status, answer: str) -> RunResult:
        """Every exit goes through here, so every early stop gets a hand-over note."""
        return RunResult(status, answer, denials, trace, handover_note(status, goal, trace))

    for step in range(1, max_steps + 1):
        # ---- 1. (part 1, Loop) ask the model. A failing or malformed model must never crash the harness. ----
        try:
            decision = model(view())
            if not isinstance(decision, dict) or ("final" not in decision and "tool" not in decision):
                raise ValueError("malformed model output")
        except Exception as err:
            log(step, "stop", f"model error: {err}")
            return finish("model-error", "stopped: the model call failed")

        # ---- 2. (part 6, Verify) "final": do not trust the claim, check the world ----
        if "final" in decision:
            text = str(decision["final"])
            log(step, "decide", f"final: {text}")
            problem = None
            if verify is not None:
                try:
                    problem = verify(state)
                except Exception as err:
                    problem = f"the check itself crashed: {err}"
            if problem:
                log(step, "stop", f"verification failed: {problem}")
                return finish("failed-verification", f"not done: {problem}")
            return finish("done-with-denials" if denials else "done", text)

        # ---- 3. (part 2, Tools) a tool call. Missing or non-dict args mean "no arguments". ----
        name = str(decision["tool"])
        args = decision.get("args") if isinstance(decision.get("args"), dict) else {}
        log(step, "decide", f"{name} {_args_text(args)}")

        # ---- 4. (part 1, Loop) repeat check: the same call 3 times within the last 6 steps ----
        recent.append(f"{name}:{_args_text(args)}")
        if recent[-6:].count(recent[-1]) >= 3:
            log(step, "stop", "same call 3 times in the last 6 steps")
            return finish("loop-detected", "stopped: repeating the same action")

        # ---- 5. (part 2, Tools) look the tool up, validate the input: problems go back to the model as text ----
        tool = tool_map.get(name)
        if tool is None:
            problem = f"unknown tool {name}"
        else:
            try:
                problem = tool.validate(args)
            except Exception as err:
                problem = f"input check crashed: {err}"
        if problem:
            log(step, "error", f"error: {problem}")
            history += [f"assistant wants {name} {_args_text(args)}", cut(f"error: {problem}")]
            continue

        # ---- 6. (part 5, Gates) the gate: only irreversible tools ask a human, and no answer means no ----
        if tool.risk == "irreversible":
            allowed = False                        # default deny: stays False unless a human says yes
            try:
                words = f"{name} {_args_text(args)}"
                if tool.describe:
                    words = tool.describe(args, state)           # plain words, so the human sees the real effect
                if approve:
                    allowed = bool(approve(name, args, words))
            except Exception:
                allowed = False                    # a crash in the approver or describe is a refusal
            if not allowed:
                denials += 1
                log(step, "denied", f"{name} {_args_text(args)}")
                history += [f"assistant wants {name} {_args_text(args)}",
                            f"denied: {name} {_args_text(args)} was not approved. Do not retry it."]
                if denials >= max_denials:         # stop pestering the human
                    log(step, "stop", "too many denied actions")
                    return finish("denied-limit", "stopped: too many actions were denied")
                continue

        # ---- 7. (part 2, Tools) run the tool. Never retried: a repeated write is worse than one failure. ----
        try:
            result = tool.run(args, state)
        except Exception as err:
            log(step, "error", f"error: {err}")
            history += [f"assistant wants {name} {_args_text(args)}", cut(f"error: {err}")]
            continue                               # note: a tool that changes state and THEN raises is not checkpointed
        log(step, "tool", result)
        history += [f"assistant wants {name} {_args_text(args)}", f"tool: {cut(result)}"]   # "tool:" marks it as DATA

        # ---- 8. (part 4, Memory) memory: save progress after anything that changed state ----
        if tool.risk != "read" and checkpoint is not None:
            try:
                checkpoint(state)
            except Exception as err:               # memory failures are loud: better to stop than to lose work silently
                log(step, "stop", f"checkpoint failed: {err}")
                return finish("checkpoint-failed", "stopped: progress could not be saved")

    log(max_steps, "stop", "step limit reached")
    return finish("step-limit", "stopped: step limit reached")
