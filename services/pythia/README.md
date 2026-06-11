# Pythia — Lead Oracle

**Prophetess of Apollo**

Pythia (Πυθία) was the oracle of Delphi in ancient Greek mythology — the high priestess who spoke prophecies inspired by Apollo, delivering foresight and wisdom to those who sought it.

**Why Pythia?**

This microservice is the lead oracle for Complete Automate — it scours the web for potential leads, scores them with an LLM, enriches them with web research, and delivers daily intelligence. Like Pythia peering into the future, this service gazes across the web to identify who needs automation help and when to reach out.

**Domain:** Lead collection, scoring, enrichment, and management
**Dependencies:** Clio (DynamoDB), DeepSeek/OpenRouter (LLM scoring), Google CSE (enrichment)

## Pipeline

```
Collect (6 sources) → Dedup → Score (LLM, parallel 10×) → Enrich (4-round loop, hot only) → Store (DynamoDB)
```

### Sources

| Source | Feed Type | What It Fetches |
|---|---|---|
| Reddit | RSS | Posts from r/automation, r/smallbusiness, r/entrepreneur, etc. |
| Hacker News | Algolia API | Ask HN / Show HN posts + automation keyword hits |
| Google News | RSS | News articles matching automation/workflow/AI queries |
| Indeed | Google News RSS (proxy) | Job-market news for automation/hiring signals |
| Crunchbase | Google News RSS (proxy) | Startup funding rounds and capital-raising news |
| Product Hunt | RSS | Launches filtered for tech/automation relevance |

### Scoring

Each raw item is sent to DeepSeek (via OpenRouter) with a structured prompt scoring 1–10:
- **8–10 (Hot):** Actively seeking help, has budget, clear pain point
- **5–7 (Warm):** Exploring options, likely need, positive signals
- **1–4 (Cold):** Not relevant / no action needed

Parallel execution via `asyncio.Semaphore(10)` — ~4 min for 1300 items.

### Enrichment

Hot leads (score 8+) go through a 4-round web research loop via Google CSE:
1. Company overview search
2. Contact info search
3. Funding / tech stack search
4. Targeted gap search

Each round: identify gaps → web search → LLM extract → fill fields. Stops early when all fields populated.

### State Workflow

Leads start in `discovery` and transition freely via PATCH API:
```
discovery → contacted → qualified → won
                                      → not_interested
```

State history is recorded as an array `[{state, at}]` on each lead record.

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/run` | Manually trigger the full pipeline |
| GET | `/leads` | List all leads (newest first, ?limit=N) |
| GET | `/leads/{id}` | Get single lead with enrichment + history |
| PATCH | `/leads/{id}` | Update lead state (body: `{"state": "..."}`) |

All API endpoints are proxied through Angelos and gated by Authelia at the ingress.

## Deployments

| Component | Type | Schedule/Duration |
|---|---|---|
| **pythia-api** | Deployment (long-lived) | Serves API endpoints for Helios UI |
| **pythia-cron** | CronJob | Daily at 12:00 HKT (04:00 UTC) |

Both deployed via ArgoCD from `homelab-army`.

## Tech Stack

- **Python 3.11+** — asyncio, httpx, Pydantic v2, FastAPI
- **DynamoDB** — single `vimal` table, `CA#Lead` partition
- **LLM** — DeepSeek via OpenRouter (configurable)
- **Search** — Google Custom Search API (optional)
- **Kubernetes** — k3s, ArgoCD, CronJob + Deployment
