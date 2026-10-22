"""Command-line entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from .parser import load_groups
from .reporting import render_group, write_report
from .summarizer import RuleBasedSummarizer, build_ai_summarizer


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create concise summaries from a task failure TSV export.")
    parser.add_argument("--input", type=Path, default=Path("failures.txt"), help="Input TSV file (default: failures.txt)")
    parser.add_argument("--output", type=Path, default=Path("output.txt"), help="Report file to write (default: output.txt)")
    parser.add_argument("--no-ai", action="store_true", help="Use only deterministic rule-based summaries.")
    return parser.parse_args()


def main() -> None:
    args = arguments()
    load_dotenv()
    try:
        groups = load_groups(args.input)
    except (FileNotFoundError, ValueError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from error

    fallback = RuleBasedSummarizer()
    ai_summarizer = build_ai_summarizer(args.no_ai)
    print("AI analysis enabled." if ai_summarizer else "AI analysis disabled; using rule-based summaries.")
    blocks = []
    for group in groups:
        summary = ai_summarizer.summarize(group) if ai_summarizer else None
        blocks.append(render_group(group, summary or fallback.summarize(group)))

    write_report(args.output, blocks)
    print("Done.")
    print(f"Input : {args.input}")
    print(f"Output: {args.output}")
    print(f"Groups: {len(groups)}")


if __name__ == "__main__":
    main()
