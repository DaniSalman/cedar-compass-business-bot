---
title: Cedar & Compass Travel
emoji: 🧭
colorFrom: green
colorTo: blue
sdk: gradio
sdk_version: 5.50.0
app_file: app.py
python_version: "3.12"
pinned: false
---

# Cedar & Compass Travel — Chat with Layla

**EECE 503P/798S — C3: Agent-Powered Business Assistant** · Dani Salman

Layla is the virtual concierge of Cedar & Compass Travel, a **fictional** boutique
travel agency in Hamra, Beirut. She answers questions from the business PDF and
summary, routes every message to one of three handling paths, records leads and
feedback through real model function calls, and reviews each reply before
sending it. It runs on Google Gemini (free tier), model `gemini-3.5-flash-lite`.

- **Demo video:** https://docs.google.com/videos/d/1rYcEJidBaimUFH6_-aVCb4fBgGtG-sn1INwCS1R7zXI/play?usp=sharing

## Project structure

```text
.
├── me/
│   ├── about_business.pdf      # three-page business profile
│   └── business_summary.txt    # four-paragraph summary
├── business_agent.ipynb        # main notebook: persona, instructions, router, tools, demos, UI
├── agent.py                    # shared agent code used by the notebook and app.py
├── app.py                      # Gradio app (python app.py, also used on HF Spaces)
├── budget.py                   # persistent API spending guard
├── demo_checks.py              # live demo cases and acceptance checks
├── build_profile.py            # regenerates the PDF and summary (no API needed)
├── deploy_space.py             # optional Hugging Face Spaces deployment
├── tests/test_agent.py         # offline tests (no API calls)
├── evidence/                   # saved results from the notebook and tests
├── requirements.txt
├── .env.example                # copy to .env and add your key (.env is never committed)
└── .gitignore
```

The notebook and `app.py` share `agent.py`, so the notebook demo and the deployed
app behave the same way.

## Assignment checklist

| Requirement | Where |
| --- | --- |
| `business_summary.txt` and `about_business.pdf` (name, mission, services, team, unique value proposition) | `me/` |
| `business_agent.ipynb` | repo root |
| Clearly labeled persona and instructions | notebook sections 2 and 3 (`PERSONA`, `INSTRUCTIONS`) |
| Router with three intents | notebook section 6; `BusinessAgent.route` |
| Two tools: `record_customer_interest(email, name, message)`, `record_feedback(question)` | notebook section 4; `ToolRecorder` |
| MCP-style tool schemas (name, parameters, expected output) | notebook section 4 |
| System prompt, chat history, tool-call loop | notebook section 7; `BusinessAgent.respond_with_trace` |
| Gradio `ChatInterface` | notebook section 10; `app.py` |
| API key in `.env`, not uploaded | `.env.example`, `.gitignore` |
| Bonus: reflection with logged draft and revision | notebook section 8; `reflection_log.jsonl` |
| Bonus: Hugging Face Spaces | see [Hugging Face Spaces](#hugging-face-spaces) |

## Run locally

Python 3.10 or newer (tested on 3.12 and 3.14). From this folder:

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Open `.env` and set `GEMINI_API_KEY` (a free key from
[Google AI Studio](https://aistudio.google.com/apikey)). Leave the HF fields empty
unless deploying.
Then start the app:

```bash
python app.py
```

Open the address Gradio prints (normally `http://127.0.0.1:7860`). The UI starts
without a key; the chat then explains that the key is missing. Use made-up contact
details in the demo, never real passport, card or password details.

## Notebook (local or Colab)

Locally: open `business_agent.ipynb` and choose **Restart Kernel → Run All**.
With a key, Run All makes about 35 API calls (within the free daily quota) and
saves the results to `evidence/live_results.json`. Without a key the live demos are skipped
with a clear message.

In Colab:

1. Open `business_agent.ipynb` in Colab.
2. Add `GEMINI_API_KEY` under **Secrets** (key icon) and enable notebook access.
3. In the first cell, set `REPO_URL` to this repository's URL, or upload a ZIP
   of this folder named `business_bot.zip` to `/content`.
4. Run all cells. The first cell clones or extracts the project and installs the
   requirements.
5. To open the chat, set `LAUNCH_UI = True` in the last code cell and run it.
   In Colab this creates a temporary public `share=True` link.

## How the agent works

The brief names `google.generativeai` or `openai.ChatCompletion`. Google has since
deprecated `google.generativeai`, so this project uses the current `openai` Python
client (`client.chat.completions.create`) pointed at
[Gemini's OpenAI-compatible endpoint](https://ai.google.dev/gemini-api/docs/openai)
with a Gemini key.

1. **Knowledge:** at startup `pypdf` extracts all three PDF pages and the summary
   is loaded. Both go into the system prompt. The sources are small, so no vector
   database is needed.
2. **Persona and instructions:** separate `PERSONA` and `INSTRUCTIONS` variables
   in separate labeled notebook cells, combined by `make_system_prompt`.
3. **Router:** one cheap model call with a strict JSON schema that only allows the
   three labels `general_question`, `lead_collection` and `feedback_unanswered`.
   The label is also validated in Python; anything invalid falls back to
   `general_question`. Each label adds a different handling instruction before the
   main agent runs, and every decision is logged.
4. **Tools:** two short strict JSON schemas, documented MCP-style in the notebook
   and converted into OpenAI-format function declarations, which Gemini accepts.
   Gemini 3 attaches a "thought signature" to each tool call; the agent sends it
   back with the tool results, as Gemini requires. The model chooses when to call
   them (`tool_choice="auto"`). On the feedback path the first generation is
   required to call `record_feedback`, so unknown questions are always logged.
   Python validates each call, runs it, and returns the result to the model by
   `tool_call_id`. Several calls per turn and several rounds are supported, and a
   duplicate call in the same turn is not executed twice.
5. **Memory:** the last ten user/assistant turns are passed to the router and the
   agent. Each browser session keeps its own history.
6. **Reflection (bonus):** a separate model call checks the draft against the
   instructions, the source facts and the actual tool results, and returns `OK` or
   a revised reply. The original draft, the verdict and the revision are logged.
   Turn it off with `REFLECTION_ENABLED=false`.
7. **Input safety:** long messages are rejected, and messages containing API keys,
   Luhn-valid card numbers or labelled passport/password values are refused before
   they reach the model or any log. A lead is only saved if the name and email
   appear in what the user actually wrote. CSV fields starting with formula
   characters are escaped.

The model is still probabilistic. Routing, forced feedback logging and reflection
reduce mistakes but cannot guarantee every reply is correct. The sensitive-data
checks are basic classroom safeguards, not a full data-loss-prevention system.

## Model, free-tier quota and budget guard

The default model is `gemini-3.5-flash-lite` with the lightest thinking level
(`minimal`). Set `GEMINI_MODEL` in `.env` to change it. Free-tier quotas are per
model and per day (reset at midnight Pacific time). `gemini-3.8-flash` is smarter
but allows only **20 free requests per day**, fewer than one notebook Run All
(about 35 calls). If a model's daily quota runs out, the app says so instead of
retrying. Per-minute limits are handled by waiting for the delay Gemini returns
(up to three retries).

Gemini's thinking tokens count toward each call's output limit, so every call
gets 2,048 tokens of extra room. Without this, the router's JSON answer was cut
off and every message fell back to `general_question`.

The free tier costs nothing, but the budget guard stays as a safety net in case
billing is ever enabled on the Google project. `budget.py` prices calls at
Gemini 3.5 Flash-Lite's paid rates ($0.30 per million input tokens, $2.50 per
million output tokens, checked on 2026-10-18). Before every API call, the guard
reserves the maximum possible cost of that call in a local SQLite ledger
(`.api_budget.sqlite3`) and refuses the call if the total would pass the cap.
After the call it records the real usage; requests rejected with HTTP 429 are
released, since they are not billed. The default cap is **$1.00**
(`API_BUDGET_USD` in `.env`, maximum $10). If you hit the cap, raise
`API_BUDGET_USD` or delete `.api_budget.sqlite3` to start a new ledger.

Check spending without making an API call:

```bash
python -c "from agent import BusinessAgent; print(BusinessAgent().budget.summary())"
```

The guard only counts calls made through this project and this ledger. It is not
an account-wide billing limit.

## Logs and evidence

Runtime files are written to this folder (change with `BUSINESS_BOT_LOG_DIR`) and
are ignored by Git:

| File | Content |
| --- | --- |
| `leads.csv` | timestamp, name, email, trip note |
| `feedback.log` | timestamp and the unanswered question or feedback |
| `router_log.jsonl` | each message and its intent |
| `tool_log.jsonl` | each model tool call, its arguments and result |
| `reflection_log.jsonl` | original draft, verdict, revised reply |
| `.api_budget.sqlite3` | token usage per call (no key, no prompts) |

`evidence/live_results.json` is written by the notebook's live demo (router
predictions, conversations, tool results, the reflection example and pass/fail
checks). `evidence/offline_results.json` records the last offline test run. All
contacts in the evidence are made up (`example.com` addresses).

The reflection section includes a clearly labeled **fault-injection example**: a
deliberately bad draft (fake discount, confirmed booking, asking for a card
number) is sent to the real reviewer, which rewrites it. This makes the
self-correction visible even when the normal drafts are already fine.

## Tests

```bash
python -m pytest -q
python demo_checks.py
```

The first command runs the offline tests (a scripted fake client, no API calls).
The second runs the live demo cases with your key and rewrites
`evidence/live_results.json`.

To rebuild the PDF and summary after editing the business details:

```bash
python build_profile.py
```

## Hugging Face Spaces

Gradio Spaces on the default CPU Basic hardware now need a paid (PRO) account.
Free accounts with a verified email that are older than 30 days can host up to
two Gradio Spaces on **ZeroGPU** hardware. This app is CPU-only; `app.py` includes
an unused `@spaces.GPU` placeholder that ZeroGPU expects. Deployment to Spaces has
not been tested yet.

Manual steps:

1. Create a new Space: SDK **Gradio**, hardware **ZeroGPU** (or CPU Basic with PRO).
2. Upload `README.md`, `app.py`, `agent.py`, `budget.py`, `requirements.txt` and
   the `me/` folder. Do not upload `.env`, logs or the budget ledger.
3. In **Settings → Variables and secrets**, add the secret `GEMINI_API_KEY` and
   the variable `API_BUDGET_USD=1.00`.
4. Wait until the Space shows **Running**, then ask "What are your office hours?".

Or set `HF_TOKEN` (write access) and `HF_SPACE_ID=username/space-name` in `.env`
next to `GEMINI_API_KEY`, then run `python deploy_space.py`. It uploads only the app
files, stores the key as a Space secret, waits for the build and sends a test
message. It never writes either token to disk. Options: `HF_SPACE_HARDWARE`
(default `zero-a10g`, i.e. ZeroGPU) and `HF_SPACE_PUBLIC=true`.

A **private** Space can only be opened by you, so a grader can't open it. A
**public** Space lets anyone chat with it using your Gemini key. On the free tier
that costs nothing, but every visitor uses up the same daily quota. Make it public
only for grading, then switch it back to private.

## Video demo outline (about 80 seconds)

| Time | Action |
| --- | --- |
| 0–10s | Show the notebook's `PERSONA` and `INSTRUCTIONS` cells and the business PDF. |
| 10–22s | In Gradio ask "What's included in the Istanbul package?". Show the grounded answer and the `general_question` route. |
| 22–36s | Type "I want a quote for 4 people to Barcelona in June." Show `lead_collection` and Layla asking for name and email. |
| 36–48s | Type "I'm Sara, sara@example.com. Please save that quote request." Show the `record_customer_interest` output and the new row in `leads.csv`. |
| 48–60s | Ask "Do you sell travel insurance?". Show `feedback_unanswered`, the honest "not in our materials" reply and the `feedback.log` entry. |
| 60–73s | In the notebook show the reflection example: the injected bad draft, the reviewer's revision and the log entry. |
| 73–83s | Show the router accuracy table, the acceptance checks and the budget summary. |

## Lessons from testing

- An early version sent unknown questions and complaints down the general path,
  and once claimed the agency does not sell insurance (the documents simply don't
  mention it). Three changes fixed this: the router now uses a strict enum schema,
  the feedback path must call `record_feedback`, and the instructions treat an
  unlisted service as unknown rather than unavailable.
- Moving to Gemini, the router scored 5/9 at first: thinking tokens used up its
  55-token output limit, so the JSON was cut off and fell back to
  `general_question`. Adding thinking room brought it back to 9/9.
- `gemini-3.8-flash` ran out of its 20 free daily requests during testing, so the
  default became `gemini-3.5-flash-lite`, which also answers about three times faster.

## References

- [Gemini OpenAI compatibility](https://ai.google.dev/gemini-api/docs/openai)
- [Gemini pricing and free tier](https://ai.google.dev/gemini-api/docs/pricing)
- [Gemini rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- [Gemini function calling](https://ai.google.dev/gemini-api/docs/function-calling)
- [Gradio ChatInterface](https://www.gradio.app/docs/gradio/chatinterface)
- [Gradio Spaces configuration](https://huggingface.co/docs/hub/spaces-sdks-gradio)
- [Spaces overview and hardware](https://huggingface.co/docs/hub/spaces-overview)
- [ZeroGPU Spaces](https://huggingface.co/docs/hub/spaces-zerogpu)
