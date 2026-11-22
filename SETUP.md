# Setup: one page, step by step

Words used here: a **terminal** is a window where you type commands. **Green** means a check passed. A **folder** is this project folder (cloned or unzipped).

## 1. Open a terminal in this folder
- **macOS:** open the Terminal app, type `cd ` (with a space), drag this folder from Finder into the window, press Return.
- **Windows:** open this folder in File Explorer, click the address bar, type `cmd`, press Enter.
- **In an editor** (Cursor, VS Code): open this folder, then Terminal > New Terminal.

## 2. Check Python (3.10 or newer)
In that terminal, run:
- **macOS / Linux:** `python3 --version`
- **Windows:** `py --version` (on Windows use `py` wherever these docs say `python3`)

If it says 3.10 or higher (3.11, 3.12 ...), carry on. If not, install Python from python.org, then reopen the terminal. On a new Mac, the first `python3` may offer to install "command line developer tools": say yes and wait (it can take several minutes), then try again.

## 3. Make your `.env` file
- **macOS / Linux:** `cp .env.example .env`
- **Windows:** `copy .env.example .env`

## 4. Get your free Gemini key
1. Go to **https://aistudio.google.com/apikey** and sign in with a Google account.
2. Click "Create API key" and copy it.
3. Open `.env` in a PLAIN text editor and paste the key after `GEMINI_API_KEY=` (no spaces, no quotes). Save. A file whose name starts with a dot is hidden in Finder, so open it from the terminal: **macOS** `open -e .env` (TextEdit: if it asks, choose plain text), **Windows** `notepad .env` (make sure it saves as `.env`, not `.env.txt`).

Paste your key **only** into `.env`. Never into your coding agent's chat, never into `.env.example`, never into a screenshot.

## 5. Check it works
```
python3 check.py
```
Expected, before you build anything: the first line says the provided files are green, and every phase says **"not built yet"**. That is correct. Nothing is broken.

Then try the model once: `python3 ask.py`. You should see a one-line reply from the model.

## If something goes wrong
| You see | Do this |
|---|---|
| `python3: command not found` | on Windows use `py`; otherwise install Python |
| `No API key` | `.env` is missing or the key line is empty; redo step 3 and 4 |
| an error with `429` | your free quota for that model is used up. Wait 60 seconds, or add `GEMINI_MODEL=gemini-flash-lite-latest` (or another model) to `.env` |
| an error with `503` or "high demand" | the model is busy; wait a minute and retry |
| `403` or `401` | the key is wrong or restricted; make a new one |

Phase 5 only: `pip install -r requirements.txt` (installs LangGraph).
