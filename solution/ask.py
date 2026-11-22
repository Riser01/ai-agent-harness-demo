"""Phase 0, the plain prompt call: the "before" picture of a model that can talk but cannot act.

Before you build a harness, it helps to see what a bare model does with "Add 'pay rent' to my to-do list". It
replies "Done!", and nothing was saved. Nothing in this program can save anything: there are no tools, no loop
and no state, so the only thing the model can produce here is words.

Keep that gap in mind for the rest of the course. Every later file exists to turn "the model said it" into "it
really happened, and we can check".

What to look at
    PROMPT        the one request we send, the same kind of request the later phases handle properly.
    plain_call()  sends it and reports the reply next to the tasks really saved, which is always an empty list.
    main()        prints what was sent and the raw reply (INFO lines), then the reply next to the tasks saved,
                  so the gap is impossible to miss.

Run it live:  python3 ask.py     (needs a model key in .env; see .env.example)
"""
import time
from typing import Callable

PROMPT = "Add 'pay rent' to my to-do list."


def plain_call(chat: Callable[[str], str], prompt: str = PROMPT) -> dict:
    """Send one prompt and report what the model said and what was actually saved (always nothing)."""
    saved_tasks: list[str] = []          # there is nowhere for the model to put a task
    reply = chat(prompt)
    return {"reply": reply, "tasks_after": list(saved_tasks)}


def main() -> None:
    """Call the real model once and show the gap between what it says and what happened."""
    import llm
    from config import load_env

    load_env()
    print(f"INFO  model  sending: {PROMPT}")
    start = time.perf_counter()
    result = plain_call(llm.ask_text)
    usage = llm.last_call.get("usage") or {}
    tokens = f" ({usage['prompt_tokens']} in / {usage['completion_tokens']} out tokens)" if "prompt_tokens" in usage and "completion_tokens" in usage else ""
    raw = str(llm.last_call.get("raw", result["reply"])).replace("\n", " | ")   # the reply exactly as the model wrote it
    print(f"INFO  model  reply in {time.perf_counter() - start:.1f}s{tokens}: {raw}")
    print("model says:      ", result["reply"])
    print("tasks really saved:", result["tasks_after"], " <- nothing: a prompt cannot change anything by itself")


if __name__ == "__main__":
    main()
