# Error report summariser

Python-only CLI for turning a task-failure TSV export into a concise report. It uses `uv` for dependency and virtual-environment management.

## Project layout

```
src/error_summarizer/
  cli.py          Command-line application
  parser.py       TSV validation and grouping
  summarizer.py   Rule-based and Gemini AI summaries
  reporting.py    Report status calculation and rendering
  models.py       Domain data structures
```

## Setup

Install [uv](https://docs.astral.sh/uv/) and Python 3.11 or newer, then run:

```powershell
uv sync
Copy-Item .env.example .env
```

Create a Gemini API key in [Google AI Studio](https://aistudio.google.com/app/apikey), then set `GOOGLE_API_KEY` in `.env`. You may optionally change `GEMINI_MODEL` there. The default, `gemini-2.5-flash-lite`, has a free tier suitable for short summaries.

## Run

```powershell
uv run error-summarizer
```

Useful options:

```powershell
uv run error-summarizer --no-ai
uv run error-summarizer --input another-failures.txt --output report.txt
```

Without `GOOGLE_API_KEY` (or with `--no-ai`), the CLI uses deterministic rule-based summaries. With an API key, LangChain calls the selected Gemini model. Only extracted error messages are sent to the model; stack traces, paths, task IDs, and agency IDs are excluded.
