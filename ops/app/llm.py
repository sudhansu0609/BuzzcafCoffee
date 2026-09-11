"""Optional Claude pass for the assistant: understand a mail, classify an
unclear document, pull numbers out of a financial PDF.

Everything here is best-effort and off by default: it runs only when
``enabled()`` is true, i.e. Anthropic credentials exist (ANTHROPIC_API_KEY in
ops/.env or the environment, or an `ant auth login` profile) and
BUZZCAF_ASSISTANT_LLM is not set to "0". Every function returns None on any
failure so the rule-based path always completes.

Model: claude-opus-5 with server-side refusal fallbacks enabled.
"""
from __future__ import annotations

import json
import os
from typing import Any

MODEL = "claude-opus-5"
_client = None

COMPANY = (
    "Buzzcaf Private Limited (CIN U15400PN2022PTC209619, GSTIN 27AAKCB6111C1Z3, FSSAI 11522079000056), "
    "a Pune instant-coffee brand restarting in Sep 2026 as a private-label relabeller selling on Amazon FBA and buzzcaf.com. "
    "Directors: Sudhansu (runs it) and Himansu. Indian financial year runs 1 April to 31 March; FY2024-25 means Apr 2024 to Mar 2025."
)


def enabled() -> bool:
    if os.environ.get("BUZZCAF_ASSISTANT_LLM", "1") == "0":
        return False
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return True
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    # an `ant auth login` profile on disk also counts
    from pathlib import Path
    return (Path.home() / ".config" / "anthropic").exists()


def _get_client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic()
    return _client


def _ask_json(system: str, user: str, schema: dict[str, Any], max_tokens: int = 4000) -> dict[str, Any] | None:
    """One structured-output request. None on refusal or any error."""
    try:
        import anthropic
        client = _get_client()
        resp = client.beta.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": schema}},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        if resp.stop_reason == "refusal":
            return None
        text = next((b.text for b in resp.content if b.type == "text"), None)
        return json.loads(text) if text else None
    except (anthropic.APIError, json.JSONDecodeError, StopIteration, ImportError):  # type: ignore[name-defined]
        return None
    except Exception:  # noqa: BLE001 - never let the LLM path break the assistant
        return None


# ------------------------------------------------------------ documents ----
DOC_SCHEMA = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "description": "one of the allowed kinds"},
        "fy": {"type": ["string", "null"], "description": "financial year like 2024-25, or null"},
        "period": {"type": ["string", "null"], "description": "month YYYY-MM for monthly returns/statements, else null"},
        "date": {"type": ["string", "null"], "description": "date on the document, YYYY-MM-DD"},
        "number": {"type": ["string", "null"], "description": "SRN / ARN / UDIN / acknowledgement / licence number"},
        "expiry": {"type": ["string", "null"], "description": "expiry / valid-upto date if the document has one, YYYY-MM-DD"},
        "title": {"type": "string"},
        "confidence": {"type": "number"},
        "why": {"type": "string"},
    },
    "required": ["kind", "fy", "period", "date", "number", "expiry", "title", "confidence", "why"],
    "additionalProperties": False,
}


def classify_document(filename: str, text: str, kinds: list[str]) -> dict[str, Any] | None:
    system = (
        "You file documents for " + COMPANY + " Decide what the document is. "
        "kind must be exactly one of: " + ", ".join(kinds) + ". Use 'other' if none fits. "
        "confidence is 0-1. Be conservative with fy: only state it when the document says so."
    )
    user = f"Filename: {filename}\n\nDocument text (may be truncated):\n{text[:30000]}"
    return _ask_json(system, user, DOC_SCHEMA)


FACTS_SCHEMA = {
    "type": "object",
    "properties": {
        "unit_multiplier": {"type": "number", "description": "1 if amounts are in rupees, 100000 if in lakhs, etc."},
        "facts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string"},
                    "value": {"type": "number", "description": "as printed, before applying unit_multiplier"},
                    "period": {"type": "string", "description": "'FY' or YYYY-MM"},
                    "confidence": {"type": "number"},
                },
                "required": ["metric", "value", "period", "confidence"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["unit_multiplier", "facts"],
    "additionalProperties": False,
}

METRICS = [
    "revenue", "other_income", "total_income", "total_expenses", "pbt", "pat", "total_assets", "equity",
    "total_liabilities", "cash", "share_capital", "borrowings", "gst_taxable_value", "gst_igst", "gst_cgst",
    "gst_sgst", "gst_itc", "gst_tax_paid_cash", "gst_late_fee", "itr_gross_total_income", "itr_total_income",
    "itr_tax_payable", "itr_taxes_paid", "itr_refund", "bank_opening", "bank_closing", "bank_credits", "bank_debits",
]


def extract_facts(kind: str, text: str, fy: str | None) -> list[dict[str, Any]] | None:
    system = (
        "You read Indian company financial documents for " + COMPANY +
        " Extract the current-year figures (not the previous-year comparative column) for these metrics only: "
        + ", ".join(METRICS) + ". Skip metrics that are not in the document. Losses are negative numbers."
    )
    user = f"Document kind: {kind}. Financial year: {fy or 'unknown'}.\n\n{text[:40000]}"
    res = _ask_json(system, user, FACTS_SCHEMA, max_tokens=6000)
    if not res:
        return None
    mult = float(res.get("unit_multiplier") or 1)
    out = []
    for f in res.get("facts", []):
        if f.get("metric") in METRICS:
            out.append({"metric": f["metric"], "value": round(float(f["value"]) * mult, 2),
                        "period": f.get("period") or "FY", "confidence": float(f.get("confidence", 0.7)),
                        "notes": "llm" + (f" ×{mult:g}" if mult != 1 else "")})
    return out


# ----------------------------------------------------------------- mail ----
MAIL_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string"},
        "importance": {"type": "string", "enum": ["urgent", "high", "normal", "low", "ignore"]},
        "summary": {"type": "string", "description": "2-3 plain sentences: what it says and what it means for Buzzcaf"},
        "action_needed": {"type": "string", "description": "the one thing Sudhansu should do, or empty"},
        "due_date": {"type": ["string", "null"], "description": "deadline in the mail, YYYY-MM-DD"},
        "amount": {"type": ["number", "null"], "description": "main rupee amount mentioned"},
        "create_task": {"type": "boolean"},
        "task_title": {"type": "string"},
    },
    "required": ["category", "importance", "summary", "action_needed", "due_date", "amount", "create_task", "task_title"],
    "additionalProperties": False,
}


def understand_mail(sender: str, subject: str, body: str, attachments: list[str], categories: list[str]) -> dict[str, Any] | None:
    system = (
        "You are the personal assistant for the director of " + COMPANY +
        " Read one email and tell the director what it means. category must be one of: " + ", ".join(categories) +
        ". Mark newsletters, promotions and automated noise as importance 'ignore'. Mark government, tax, MCA, bank, "
        "FSSAI, legal notices and anything with a deadline or a penalty as 'high' or 'urgent'. create_task only when a "
        "concrete action by the director is needed."
    )
    user = (f"From: {sender}\nSubject: {subject}\nAttachments: {', '.join(attachments) or 'none'}\n\n"
            f"{body[:20000]}")
    return _ask_json(system, user, MAIL_SCHEMA)


BRIEF_SCHEMA = {
    "type": "object",
    "properties": {"brief": {"type": "string", "description": "the morning brief in plain prose, max 250 words"}},
    "required": ["brief"],
    "additionalProperties": False,
}


def write_brief(context: dict[str, Any]) -> str | None:
    system = (
        "You are the personal assistant for the director of " + COMPANY +
        " Write the morning brief from the JSON context: what is overdue, what arrived in mail, what was filed, "
        "what needs a decision today. Lead with the most consequential item. Plain sentences, no headings, no bullet spam."
    )
    res = _ask_json(system, json.dumps(context, ensure_ascii=False)[:60000], BRIEF_SCHEMA, max_tokens=2000)
    return res.get("brief") if res else None
