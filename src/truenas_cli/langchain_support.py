"""LangChain-based helpers for human-friendly CLI output."""

from __future__ import annotations

from typing import Any

try:
    from langchain.prompts import PromptTemplate
except Exception:  # pragma: no cover - optional dependency fallback
    PromptTemplate = None  # type: ignore[assignment]


def render_system_summary(info: dict[str, Any]) -> str:
    """Generate a concise system summary using LangChain if available."""

    if PromptTemplate is None:
        hostname = info.get("hostname", "unknown")
        version = info.get("version", "unknown")
        model = info.get("model", "unknown hardware")
        cores = info.get("cores", "?")
        physical = info.get("physical_cores", "?")
        return (
            "System summary: Host "
            f"{hostname} runs TrueNAS version {version} on {model}. "
            f"CPU cores: {cores} total ({physical} physical)."
        )

    template = PromptTemplate(
        input_variables=[
            "hostname",
            "version",
            "model",
            "cores",
            "physical_cores",
        ],
        template=(
            "System summary: Host {hostname} runs TrueNAS version {version} "
            "on {model}. CPU cores: {cores} total ({physical_cores} physical)."
        ),
    )
    return template.format(
        hostname=info.get("hostname", "unknown"),
        version=info.get("version", "unknown"),
        model=info.get("model", "unknown hardware"),
        cores=info.get("cores", "?"),
        physical_cores=info.get("physical_cores", "?"),
    )
