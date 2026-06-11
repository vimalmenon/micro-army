"""Telegram digest formatter — turns scored leads into a daily report."""
from __future__ import annotations

from models import ScoredLead


def format_telegram_digest(
    hot: list[ScoredLead],
    warm: list[ScoredLead],
    total_scanned: int,
    cold_count: int,
) -> str:
    """Format leads into a Telegram markdown message."""
    lines: list[str] = []
    lines.append("\U0001f525 Daily Lead Report")
    lines.append("")

    # Hot leads
    if hot:
        lines.append("\U0001f7e2 HOT (score 8+)")
        lines.append("")
        for i, lead in enumerate(hot, 1):
            lines.append(f"*{i}. {lead.company or 'Unknown'}*")
            lines.append(f"   Score: {lead.score} | Urgency: {lead.urgency.upper()}")
            if lead.pain_point:
                lines.append(f"   Pain: {lead.pain_point}")
            if lead.angle:
                lines.append(f"   Angle: {lead.angle}")
            lines.append(f"   [{lead.source}]({lead.url})")
            lines.append("")
    else:
        lines.append("\U0001f7e2 HOT (score 8+) — *None today*")
        lines.append("")

    # Warm leads
    if warm:
        lines.append("\U0001f7e1 WARM (score 5-7)")
        lines.append("")
        for i, lead in enumerate(warm, 1):
            lines.append(f"*{i}. {lead.company or 'Unknown'}*")
            lines.append(f"   Score: {lead.score} | Pain: {lead.pain_point or 'N/A'}")
            lines.append(f"   [{lead.source}]({lead.url})")
            lines.append("")
    else:
        lines.append("\U0001f7e1 WARM (score 5-7) — *None today*")
        lines.append("")

    # Stats
    lines.append("")
    lines.append(f"\U0001f4ca Stats: {total_scanned} scanned \u2192 {len(hot)} hot, {len(warm)} warm, {cold_count} cold")

    return "\n".join(lines)


def categorize_leads(leads: list[ScoredLead]) -> tuple[list[ScoredLead], list[ScoredLead]]:
    """Split leads into hot (8+) and warm (5-7)."""
    hot: list[ScoredLead] = []
    warm: list[ScoredLead] = []
    for lead in leads:
        if lead.score >= 8:
            hot.append(lead)
        else:
            warm.append(lead)
    return hot, warm
