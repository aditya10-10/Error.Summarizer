"""Rule-based and AI-assisted error summarisation."""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Protocol

from .models import ErrorSummary, FailureGroup
from .parser import clean

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-lite"


class Summarizer(Protocol):
    def summarize(self, group: FailureGroup) -> ErrorSummary | None: ...


def extract_error_message(descriptions: list[str]) -> str:
    for description in descriptions:
        match = re.search(r"Message:\s*(.*?)(?:<br\s*/?>|$)", description, re.I | re.S)
        if not match:
            continue
        message = re.sub(r"\s+", " ", match.group(1))
        message = re.split(
            r"\s+(?:--->|at\s+|ClientConnectionId:|Error Number:|Inner exception)",
            message,
            flags=re.I,
        )[0]
        message = re.sub(r"^Value cannot be null\.\s*\(Parameter\s*['\"]?", "", message, flags=re.I)
        message = re.sub(r"[)'\"]+$", "", message).strip()
        if re.search(r"timeout expired|wait operation timed out|execution timeout", message, re.I):
            return ""
        if message:
            return message[:160]
    return ""


def processing_type(task_type_id: str) -> str:
    return {
        "224": "conversion processing",
        "256": "postback pixel processing",
        "286": "attribution insight processing",
        "379": "app-install processing",
    }.get(task_type_id, "task processing")


class RuleBasedSummarizer:
    def summarize(self, group: FailureGroup) -> ErrorSummary:
        text = " ".join(group.descriptions).lower()
        checks = [
            (("transaction timeout", "state of the transaction"), "database transaction timeouts"),
            (("execution timeout expired", "wait operation timed out"), "SQL execution timeouts"),
            (("physical connection is not usable", "transport-level error", "connection was forcibly closed", "connection is broken"), "SQL connection failures"),
            (("severe error occurred on the current command", "results, if any, should be discarded"), "severe SQL command failures"),
            (("kill state",), "database-side failure — SQL session entered kill state"),
            (("memoryerror", "outofmemory", "out of memory"), "memory errors"),
        ]
        reasons = [reason for terms, reason in checks if any(term in text for term in terms)]
        prefix = ", ".join(reasons) if reasons else "Task failure"
        return ErrorSummary(
            reason=f"{prefix} during {processing_type(group.task_type_id)}",
            message=extract_error_message(group.descriptions),
        )


def ai_context(group: FailureGroup) -> str:
    """Return safe evidence: no traces, paths, task IDs, or agency IDs."""
    messages: list[str] = []
    for description in group.descriptions:
        visible = re.search(r"Message:\s*(.*?)(?:<br\s*/?>|$)", description, re.I | re.S)
        if visible:
            messages.append(visible.group(1))
        messages.extend(re.findall(r'"Message"\s*:\s*"((?:\\.|[^"\\])*)"', description))

    unique: list[str] = []
    for message in messages:
        message = clean(message.replace(r'\"', '"').replace(r"\n", " ").replace(r"\r", " "))
        if message and message not in unique:
            unique.append(message[:500])
    return "\n".join([f"Task type: {group.title or group.task_type_id}", "Error messages:", *[f"- {item}" for item in unique[:8]]])


def normalise_ai_text(value: object, maximum_length: int) -> str:
    value = re.sub(r"\s+", " ", clean(value))
    return re.sub(r"^[-*\"']+|[-*\"']+$", "", value).strip()[:maximum_length].strip()


class GeminiSummarizer:
    """Generate concise summaries using the Gemini Developer API."""

    def __init__(self, api_key: str, model_name: str) -> None:
        from langchain_google_genai import ChatGoogleGenerativeAI

        self.model = ChatGoogleGenerativeAI(
            google_api_key=api_key,
            model=model_name,
            temperature=0,
            max_tokens=180,
            timeout=30,
        )

    def summarize(self, group: FailureGroup) -> ErrorSummary | None:
        from langchain_core.messages import HumanMessage, SystemMessage

        prompt = (
            "You explain application errors for a non-technical operations user. "
            "Use only supplied evidence; do not invent causes, fixes, IDs, or timestamps. "
            "Return ONLY valid JSON with exactly two fields: "
            '{"reason":"likely technical cause in one short sentence","message":"clear, plain-English error message in one short sentence"}'
        )
        try:
            response = self.model.invoke([SystemMessage(content=prompt), HumanMessage(content=ai_context(group))])
            content = re.sub(r"^```(?:json)?\s*|\s*```$", "", str(response.content).strip(), flags=re.I)
            data = json.loads(content)
            result = ErrorSummary(
                reason=normalise_ai_text(data.get("reason"), 160),
                message=normalise_ai_text(data.get("message"), 220),
            )
            return result if result.reason and result.message else None
        except Exception as error:
            print(f"AI analysis skipped for AgencyId {group.agency_id}, TaskTypeId {group.task_type_id}: {error}", file=sys.stderr)
            return None


def build_ai_summarizer(disabled: bool = False) -> GeminiSummarizer | None:
    if disabled:
        return None
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None
    try:
        return GeminiSummarizer(api_key, os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL))
    except ImportError:
        print("AI analysis is unavailable: run 'uv sync'.", file=sys.stderr)
        return None
