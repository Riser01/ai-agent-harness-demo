"""Load your own keys from a `.env` file into the environment, so no key ever appears in code.

WHY THIS FILE EXISTS
    The demo needs a few secrets (a Gemini key, optionally Langfuse keys). Secrets in source code get committed and
    shared by accident. A git-ignored `.env` file keeps them on your machine only; this tiny loader reads it.

RULES
    * Standard library only (no python-dotenv).
    * A variable already set in your shell wins over the file (setdefault), so `export GEMINI_API_KEY=...` still works.
    * Blank values are ignored, so an unfilled `.env` is the same as no keys.
    * Call load_env() once at the start of a script (agent.py and try_it.py do). Library code reads os.environ only, so tests
      never depend on whatever `.env` happens to be on disk.
"""
import os
from pathlib import Path


def load_env(path: str | Path | None = None) -> list[str]:
    """Read KEY=VALUE lines from `.env` (next to this file by default). Returns the names it set, never the values."""
    env_path = Path(path) if path else Path(__file__).with_name(".env")
    if not env_path.is_file():
        return []
    loaded: list[str] = []
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip("\"'")
        if key and value and key not in os.environ:
            os.environ[key] = value
            loaded.append(key)
    # Langfuse's newer name is LANGFUSE_BASE_URL, older SDK versions read LANGFUSE_HOST: make either one work.
    if os.environ.get("LANGFUSE_BASE_URL") and not os.environ.get("LANGFUSE_HOST"):
        os.environ["LANGFUSE_HOST"] = os.environ["LANGFUSE_BASE_URL"]
    return loaded
