"""Shared output shaping helpers for gateway JSON responses."""

from __future__ import annotations

from typing import Any

DEFAULT_TRUNCATE_KEYS = (
    "text",
    "match_snippet",
    "last_message",
    "message_preview",
    "conversation_text",
)


def parse_fields(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        return items or None
    if isinstance(value, str):
        items = [part.strip() for part in value.split(",")]
        items = [part for part in items if part]
        return items or None
    return None


def truncate_text(value: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(value) <= max_chars:
        return value
    return value[:max_chars].rstrip() + "..."


def apply_output_controls(
    data: Any,
    *,
    fields: list[str] | None,
    max_text_chars: int | None,
    compact: bool,
    minimal: bool,
    default_fields: list[str] | None = None,
    truncate_keys: tuple[str, ...] = DEFAULT_TRUNCATE_KEYS,
) -> Any:
    """Filter/truncate JSON output to reduce LLM token overhead."""
    if (compact or minimal) and max_text_chars is None:
        max_text_chars = 200 if compact else 120

    if minimal:
        base_fields = ["date", "phone", "is_from_me", "text"]
        if default_fields and "match_snippet" in default_fields:
            base_fields.append("match_snippet")
        if fields is None:
            fields = base_fields

    effective_fields = fields or (default_fields if compact else None)

    def transform_record(rec: dict[str, Any]) -> dict[str, Any]:
        if effective_fields:
            out = {key: rec.get(key) for key in effective_fields if key in rec}
        else:
            out = dict(rec)

        if max_text_chars is not None:
            for key in truncate_keys:
                value = out.get(key)
                if isinstance(value, str):
                    out[key] = truncate_text(value, max_text_chars)
        return out

    if isinstance(data, list):
        return [transform_record(item) if isinstance(item, dict) else item for item in data]
    if isinstance(data, dict):
        if effective_fields or any(key in data for key in truncate_keys):
            return transform_record(data)  # type: ignore[arg-type]
        return data
    return data
