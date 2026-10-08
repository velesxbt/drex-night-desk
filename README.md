# Night Desk

**A quant desk that reads the documents behind the market, then gates the trade.**
[Nace Document Intelligence (NDI)](https://www.nace.ai/ndi) reads the filings - 8-Ks, 10-Qs, 10-Ks, earnings PDFs, scans - and grounds every number to its page. [Drex](https://www.nace.ai/drex) reads all of it and decides - fire, size down, or block - in well under a second.

[Live demo](https://night-desk-fvo7.onrender.com/) · [GitHub](https://github.com/velesxbt/drex-night-desk) · [X / @velesxbt](https://x.com/velesxbt) · [Get a Drex key](https://drex.nace.ai/invite/j8697dgz)

![Night Desk - a LULU long signal sized down after Drex reads the full Q2 FY2026 earnings call](docs/desk-full.png)

**▶ Try it live: [night-desk-fvo7.onrender.com](https://night-desk-fvo7.onrender.com/)** - no key needed for the demo. Want to run it on your own text? [Get a free Drex key](https://drex.nace.ai/invite/j8697dgz).

---

## Why

A momentum model sees a headline beat and fires a long. The headline doesn't tell it that the beat came from a one-off tariff refund, or that the CFO cut full-year guidance forty minutes into the Q&A.

Night Desk puts two models between the signal and execution:

1. **Perception - [NDI](https://www.nace.ai/ndi).** Filings are PDFs, scans and spreadsheets, not clean text. NDI parses them, extracts the numbers a trader checks (EPS, revenue, margins, guidance range, one-off items), and **grounds every value to the page and line it came from**.
2. **Decision - [Drex](https://www.nace.ai/drex).** Drex reads the grounded facts, the full parsed filings and anything else the desk has - the whole call, prior quarters - and answers one question: **what should happen to this signal?**

```
 filing (PDF / scan / xlsx)  →  NDI parse → extract → ground  →  Drex gate  →  execution size
                                 markdown    15 fields   p.N + crop   fire / size down / block
```

Drex is built for exactly this. It doesn't write text. You give it a state and a set of options, and one forward pass returns a calibrated probability for every option. No token stream, no JSON to repair, and it can't invent an option you didn't offer.

## A real run

Lululemon, Q2 FY2026 (Sept 3, 2026). Adjusted EPS came in at **$2.92 vs $1.82** consensus - a headline beat. A long signal fires at 1.00x.

Night Desk passes the full earnings call transcript to Drex:

![Gate decision - SIZE DOWN at 67.8%, guidance lowered, beat driven by one-off items](docs/gate-decision.png)

| | |
|---|---|
| **Decision** | **SIZE DOWN** → executes at 0.50x |
| Probabilities | size down 67.8% · block 27.7% · fire 4.5% |
| Forward guidance | **lowered** (99.9%) |
| Beat driven by one-off items | **yes** (98.7%) - $0.86/share came from tariff refunds |
| Management tone | cautious (1.09 / 4) |
| Model time | **143 ms** for 11,326 tokens |

The stock fell more than 17% in pre-market trading the next morning.

> This is a replay of a past call, not a live trade. Drex may have seen public information about the outcome. Treat it as a demo of the workflow, not a backtest.

## What's on the desk

The desk has two tabs: **SIGNAL GATE · DREX** (decisions) and **FILINGS · NDI** (perception).

### Filings · NDI

**Filings** - drop the documents behind the trade: earnings releases, 8-K / 10-Q / 10-K PDFs, scanned pages, spreadsheets (NDI reads 36 file types), or paste a filing URL. Hit **Read filings**.

**Pipeline** - each filing runs through four NDI operations, shown live: **upload → parse → extract → ground**, with page count, OCR, fields found and how many landed on a page.

**Extracted facts** - one schema for any filing: 52 fields in seven groups - filing (company, ticker, document type, period), income statement, cash flow, balance sheet, business metrics (segments, comparable sales, stores, remaining performance obligations, net revenue retention, large customers), guidance, and risk & events (one-offs, tariffs, risk factor changes, legal proceedings, events after the quarter). Every row shows its value, NDI's confidence and a **`p.N` source chip**. Fields a document type doesn't carry (a 10-Q has no guidance) fold into "N not in this filing" instead of being guessed.

**Ticker matching** - the filing's ticker picks the signal it goes to. A company with no signal yet gets **+ Add signal**; sending a filing to another company's signal asks first.

**Document viewer** - the filing itself, page by page (`p. 3 / 14`, `‹ ›` or the arrow keys), each page fitted whole into the panel; **⤢** expands it near full-window (Esc closes). Every extracted value is boxed where NDI read it, and the boxes land live: extract runs in NDI's progressive mode, so values appear while their citations are still being resolved, and the viewer follows each one to its page as it's cited (click anything to take over). Click a fact to jump to its page; click a box to select its fact. **TEXT** shows NDI's parsed text of the same page with each source quote highlighted. Boxes come from NDI's coordinates; when a value has none, the desk finds its source quote in the PDF's own text layer. Word, HTML and email files show as the PDF NDI renders from them; scans show as the image.

**Evidence** - the crop NDI returned for the selected value, its source quote, the match method and confidence.

**Send to signal gate** - attaches the grounded facts and the parsed filings to a signal in the queue.

**Perception log** - every NDI job with operation, result, credits, time and job ID.

### Signal gate · Drex

**Signal queue** - incoming signals with ticker, side, size multiplier and strategy tag. Each one shows its gate status once decided.

**Context** - paste or drop in anything the desk knows about the name: the earnings call, prior calls, notes. Filings attached from the NDI tab show as a chip (`NDI · 1 FILING · 12 FACTS`) and count toward the load meter, which shows how much you've given it against Drex's 128K window, with Jev's 64K request limit marked.

![Context panel with the full earnings call loaded](docs/context.png)

**Gate decision** - one Drex call answers four questions about the same context:

| Key | Type | Question |
|---|---|---|
| `gate` | choice | Fire / size down / block this signal? |
| `guidance` | choice | Did management raise, maintain, lower or skip guidance? |
| `one_off` | yes/no | Was the headline beat driven by one-time items? |
| `tone` | score | How confident did management sound? (very cautious → very confident) |

The desk maps the verdict to an execution size: **fire** = 1.0x, **size down** = 0.5x, **block** = 0x of the signal's size. When filings are attached, the guidance and one-off reads get a **`p.N ↗` evidence chip** that jumps to the page the answer rests on.

**Pre-market tape** - paste headlines and Drex tags each one bullish, bearish or noise for the position. Headlines go 20 per call, each as its own question.

<p align="center"><img src="docs/premarket-tape.png" width="380" alt="Pre-market tape - five LULU headlines tagged bearish, one oil headline tagged noise"></p>

**Blotter** - every decision with time, verdict, confidence, execution size, sources (`1 doc · 14p · 11/12 grounded`), token count, model time and request ID.

## Get a key

One Nace console key runs both NDI (perception) and Drex (decisions), billed from the same credit.

1. Sign up with the invite link: **[drex.nace.ai/invite/j8697dgz](https://drex.nace.ai/invite/j8697dgz)** - free, with signup credit.
2. In the console, open **API Keys** and create a key (it starts with `nace_sk_`).
3. Paste it into Night Desk. The first time you open the desk without a key, it walks you through this:

<p align="center"><img src="docs/key-modal.png" width="520" alt="Key modal - sign up with the invite link, create an API key, paste it here"></p>

Your key is stored only in your browser and sent with each run. The server forwards it to Nace and never stores or logs it. Filings don't pass through the server at all: it asks Nace for a single-use upload grant, and your browser sends the file straight to the document service. No key yet? Hit **Try the demo** - it replays a real recorded run.

## Quick start

You need Python 3.9+ (standard library only - nothing to install). Setting `DREX_API_KEY` is optional - without it, the desk asks for a key in the browser.

**macOS / Linux**

```bash
git clone https://github.com/velesxbt/drex-night-desk.git
cd drex-night-desk
export DREX_API_KEY="nace_sk_..."
python3 server.py
```

Or double-click `run.command` - it asks for the key and starts the desk. (First time: `chmod +x run.command`, then right-click → Open if macOS warns about it.)

**Windows (PowerShell)**

```powershell
git clone https://github.com/velesxbt/drex-night-desk.git
cd drex-night-desk
$env:DREX_API_KEY = "nace_sk_..."
python server.py
```

Or run `.\run.ps1`.

The desk opens at **http://localhost:8765**. The key chip in the top right reads `LIVE` once a key is set - click it any time to change or remove your key.

## Walkthrough

1. **Read the filings.** Open **FILINGS · NDI**, drop the earnings release PDF (or a 10-Q, a scan, a spreadsheet) and hit **Read filings**. Click any fact to check it against its page.
2. **Send to the gate.** Pick the signal and hit **Send to signal gate →**. The desk switches back with the filings attached.
3. **Add more context** (optional). Paste the earnings call transcript into the center panel, or drop `.txt` files onto it - each gets a `=== filename ===` header. A PDF dropped here goes to NDI.
4. **Run Gate** (or `Ctrl/Cmd + Enter`). The verdict, probabilities and risk read fill in; the signal's status updates in the queue and a row lands in the blotter.
5. **Tag the tape** (optional). Paste headlines into the right panel, one per line, and hit **Tag Tape**.

To trade a name that isn't in the queue, add it at the bottom left (`TICKER`, side, size, strategy → **Add**).

Sample headlines for the two reference cases are in [`examples/`](examples/). They were written from the reported numbers, not copied from a wire.

### Getting transcripts

Transcripts aren't included in this repo - they're copyrighted by whoever publishes them. Any public transcript works. For Motley Fool pages, [`tools/extract-transcript.js`](tools/extract-transcript.js) strips the page down to just the call:

1. Open the transcript page and the browser console (`Cmd+Option+J` / `Ctrl+Shift+J`).
2. Paste the script and press Enter. The page becomes one text box with the call already selected.
3. Copy, then paste into Night Desk.

Keep local transcripts in a `transcripts/` folder - it's git-ignored.

### Reference cases

| Case | Why it's interesting |
|---|---|
| **LULU** Q2 FY2026 (Sept 3, 2026) | Headline EPS beat, but it leaned on tariff refunds and guidance was cut. Stock fell 17%+ pre-market. |
| **SNOW** Q2 FY2027 (Sept 2, 2026) | Clean beat-and-raise: EPS $0.62 vs $0.45, product revenue +37%, FY guidance raised. Stock rose ~22% after hours. |
| **LULU**, eight calls (Aug 2024 → Sept 2026) | Around 85K tokens - past Jev's 64K request limit, inside Drex's 128K window. |

## Deploy

Night Desk is one Python file with no dependencies, so it runs on any host that can start `python server.py`. When the platform sets `PORT`, the server binds to `0.0.0.0` and skips opening a browser.

**Render (free tier, one click)**

1. Push this repo to GitHub.
2. On [render.com](https://render.com): **New + → Blueprint**, pick the repo. It reads [`render.yaml`](render.yaml).
3. Deploy. Your desk is live at `https://<name>.onrender.com`.

Free instances sleep when idle - the first visit after a while takes ~30 seconds to wake up.

**Railway / Fly.io / anything else** - start command `python server.py`, no build step. Health check: `/healthz`.

> **Don't set `DREX_API_KEY` on a public deployment.** It becomes the fallback for every visitor without a key, and your credits go with it. Leave it unset and visitors bring their own.

Built-in guardrails for public hosting:

- Per-IP rate limit (`RATE_LIMIT_PER_MIN`, default 30).
- Request size cap (`MAX_BODY_BYTES`, default ~2 MB - roughly Drex's 128K-token window).
- No server-side storage. Nothing about a visitor's key or text is written to disk or logs.

## How it works

```
                      ┌─ POST /api/docs/grant ───▶ server.py ─▶ POST /v1/documents/upload-grants
                      │  POST file + X-Upload-Token ──────────────▶ document service (no key, no proxy)
 browser (desk.html) ─┼─ POST /api/docs/parse|extract|ground ─▶ server.py ─▶ /v1/documents/*   (NDI)
                      │  GET  /api/docs/jobs/{id}[/crop]      ─▶ server.py ─▶ /v1/documents/jobs/*
                      └─ POST /api/decide ────────────────────▶ server.py ─▶ /v1/systemone     (Drex)
```

- `desk.html` is the whole UI - a single file, no build step, no framework.
- `server.py` serves it and forwards requests to Nace with the visitor's key from the `X-Drex-Key` header (or `DREX_API_KEY` as a fallback when running locally).

### Perception (NDI)

Each filing runs through three document jobs. Jobs are async: the server waits up to `DOC_WAIT_SECONDS` inline, then the desk polls `GET /v1/documents/jobs/{id}`.

| Step | Request | What the desk uses |
|---|---|---|
| Parse | `{"source": {"type": "workspace_file", ...}, "output": {"formats": ["markdown"], "include_page_markers": true}}` | page count, OCR flag, markdown with `--- Page N ---` markers |
| Extract | `{"source": {"type": "parse_result", "job_id": ...}, "schema": {...}, "citations": {"enabled": true, "include_source_text": true}}` | per-field value, status (`found` / `not_found` / `ambiguous`), confidence, page and source quote |
| Ground | `{"source": {"type": "parse_result", ...}, "targets": [{"id": "eps_gaap", "text": "<source quote>", "page_hints": [1]}], "options": {"include_previews": true}}` - up to 30 targets per call, so the desk batches | match method, locator confidence, page, crop image |

The facts go to Drex at the top of the state, each one tagged with its page:

```
=== NDI EXTRACTED FACTS · each value grounded to its source page ===
[lulu-q2fy26-ex99.pdf · 14 pages]
- Diluted EPS (GAAP): $2.92 [p.1] "Diluted earnings per share were $2.92 ..."
- Guidance change: lowered [p.3] "... now expects diluted earnings per share in the range of ..."
...
=== FILING · lulu-q2fy26-ex99.pdf · parsed by NDI · 14 pages ===
--- Page 1 --- ...
```

To track different fields (a 10-K's debt covenants, a fund's holdings), edit `FIELDS` in `desk.html`.

### Decision (Drex)

Every gate is a single request to `POST /v1/systemone`:

```json
{
  "model": "drex-v1.5",
  "state": "DESK SIGNAL\nTicker: LULU\nDirection: LONG\nSize: 1.00x\n...\n=== CONTEXT ===\n<full transcript>",
  "questions": {
    "gate": {
      "type": "choice",
      "instructions": "A long signal fired on LULU at 1.00x size. Given everything in the context, what should the desk do with this signal before it goes to execution?",
      "criteria": {
        "fire": "Send the long order at full size. The context supports the trade.",
        "size_down": "Send the long order at reduced size. The context is mixed or adds risk.",
        "block": "Cancel the order. The context contradicts the long thesis."
      }
    },
    "guidance": { "type": "choice", "instructions": "What did management do to forward guidance?", "criteria": { "raised": "...", "maintained": "...", "lowered": "...", "not_given": "..." } },
    "one_off":  { "type": "noul",   "instructions": "Was the headline earnings beat driven mainly by one-time or non-recurring items?" },
    "tone":     { "type": "score",  "instructions": "How confident did management sound about the next quarters?", "criteria": ["Very cautious", "Cautious", "Neutral", "Confident", "Very confident"] }
  }
}
```

The desk reads `answers.<key>.probabilities`, `evaluation_time_ms` and `usage.input_tokens` from the response. See the [Drex API docs](https://drex.nace.ai/docs) for the full schema.

To change what the desk asks, edit the `questions` object in `runGate()` inside `desk.html`.

## Configuration

| Variable | Default | |
|---|---|---|
| `DREX_API_KEY` | - | Optional fallback key. Handy locally - **leave unset when public**. |
| `DREX_MODEL` | `drex-v1.5` | Model name sent with each request. |
| `DREX_BASE` | `https://drex.nace.ai` | API base URL. |
| `PORT` | - | Set by hosting platforms. When present, binds to `0.0.0.0`. |
| `DREX_DESK_PORT` | `8765` | Local port when `PORT` isn't set. |
| `DREX_INVITE_URL` | invite link | Signup link shown in the key modal. |
| `RATE_LIMIT_PER_MIN` | `30` | POST requests per IP per minute (job polling and crops don't count). `0` disables it. |
| `MAX_BODY_BYTES` | `2000000` | Largest request the server accepts. Filings don't count - they go straight to Nace. |
| `DOC_WAIT_SECONDS` | `25` | How long the server waits inline on a document job before the desk polls. |
| `DREX_NO_BROWSER` | - | Set to `1` to skip opening a browser tab on start. |

## Project structure

```
drex-night-desk/
├── desk.html                 the dashboard (single file)
├── server.py                 local server + Drex proxy (stdlib only)
├── run.command               macOS launcher
├── run.ps1                   Windows launcher
├── render.yaml               one-click Render deploy
├── demo/                     recorded NDI + Drex run for the demo (see demo/README.md)
├── examples/                 sample headline tapes
├── tools/
│   └── extract-transcript.js console helper for transcript pages
└── docs/                     screenshots
```

## Notes

- **Drex and NDI** are products of [Nace AI](https://www.nace.ai).
- **Not trading advice.** Night Desk is a demo of a signal-gating workflow. Nothing here places orders, and no output should be read as a recommendation to buy or sell anything.
- **Token counts.** The load meter estimates tokens at ~4 characters each before a run, then switches to the exact count Drex reports.
- **Costs.** Each gate is one request, billed on input tokens. A full earnings call runs roughly 10-15K tokens. Each filing costs three document jobs (parse, extract, ground), billed in credits from the same balance - the perception log shows each one. Check current pricing on [nace.ai/drex](https://www.nace.ai/drex).
- **Long filings.** Drex gets up to ~95K tokens of parsed filing text plus the facts block; anything past that is cut with a `[... truncated ...]` marker. The facts are always sent in full.

## Author

Built by **Veles** - [@velesxbt](https://x.com/velesxbt) on X. Issues and PRs welcome on [GitHub](https://github.com/velesxbt/drex-night-desk).

## License

[MIT](LICENSE)
