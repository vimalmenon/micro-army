"""Telegram digest formatter — turns scored leads into a daily report with enrichment."""
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

            # Enrichment block
            enrich_parts = []
            if lead.website:
                enrich_parts.append(f"\U0001f310 {lead.website}")
            if lead.linkedin:
                enrich_parts.append(f"\U0001f4bc {lead.linkedin}")
            if lead.contact_name:
                enrich_parts.append(f"\U0001f464 {lead.contact_name}")
            if lead.contact_email:
                enrich_parts.append(f"\U0001f4e7 {lead.contact_email}")
            if lead.funding:
                enrich_parts.append(f"\U0001f4b0 {lead.funding}")
            if lead.recent_news:
                for news in lead.recent_news[:2]:
                    enrich_parts.append(f"\U0001f4f0 {news}")
            if lead.budget_min is not None or lead.budget_max is not None:
                budget_str = f"Budget: ${lead.budget_min:,}-${lead.budget_max:,}" if lead.budget_min and lead.budget_max else f"Budget: ~${(lead.budget_max or lead.budget_min or 0):,}"
                if lead.budget_confidence:
                    budget_str += f" ({lead.budget_confidence})"
                enrich_parts.append(f"\U0001f4b8 {budget_str}")

            if enrich_parts:
                lines.append(f"   {'  '.join(enrich_parts[:4])}")

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
            if lead.website:
                lines.append(f"   \U0001f310 {lead.website}")
            if lead.contact_email:
                lines.append(f"   \U0001f4e7 {lead.contact_email}")
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
