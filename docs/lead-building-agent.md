# Lead Building Agent — Pythia (πυθία)

> **Design Document** — Automated pipeline that discovers, scores, and surfaces business leads for Complete Automate.

---

## 1. Purpose

Find people and companies actively seeking automation services — not automation *companies* (competitors), but **potential customers** expressing intent signals online. Deliver a curated shortlist daily so outreach happens while the need is fresh.

## 2. Target Profile

| Profile | Signal | Example |
|---|---|---|
| Founder / CTO of a SaaS or service business | Asking "how do I automate X?" on HN or Reddit | Direct lead, pain point clear |
| Growing company (raised funding, hiring) | Job postings for "Automation Engineer" | Budget + need confirmed |
| Small business owner | Complaining about manual processes online | Pain point, low-tech solution |
| Agency / consultancy | Looking for automation partner | Outsourcing need |

## 3. Data Sources (All Free)

| Source | Method | What We Look For |
|---|---|---|
| **Reddit** (r/automation, r/smallbusiness, r/entrepreneur, r/webdev, r/SaaS, r/startups) | RSS feed + API | Posts/comments asking for help automating, looking for recommendations |
| **Hacker News** (Ask HN / Show HN comments) | Algolia API | Founders discussing problems, looking for tools/services |
| **Google News / Web Search** | web_search API | Intent keywords: "automation consultant", "need workflow automation help", "looking for AI integration" |
| **Crunchbase** | RSS / API | Companies that just raised Seed/Series A (need to scale ops) |
| **Indeed / LinkedIn** | Web search | Job postings for "Automation Engineer", "Workflow Automation Lead" |
| **Product Hunt** | RSS feed | New launches + commenters saying "I wish this existed for my business" |

## 4. Pipeline

```
                 ┌──────────────────┐
                 │  Seen Items Cache │
                 │  (DynamoDB)       │
                 └────────┬─────────┘
                          │ (dedup)
┌──────────┐    ┌────────▼─────────┐    ┌──────────────────┐    ┌──────────────────┐
│ Reddit   │───▶│                  │    │                  │    │                  │
│ HN       │───▶│   COLLECTOR      │───▶│   LLM SCORER     │───▶│   LEAD STORE     │
│ Google   │───▶│   (daily cron)   │    │   (per item)     │    │   (DynamoDB)     │
│ Indeed   │───▶│                  │    │                  │    │   CA#Lead        │
└──────────┘    └──────────────────┘    └──────────────────┘    └────────┬─────────┘
                                                                        │
                                                                        ▼
                                                                ┌──────────────────┐
                                                                │  TELEGRAM DIGEST │
                                                                │  (daily @ 8 AM)  │
                                                                └──────────────────┘
```

### Step 1: Collect
- For each source, fetch new items since last run
- Deduplicate against already-seen items (keyed by URL hash)
- Store raw items temporarily

### Step 2: Score
- Each new item sent to an LLM with structured scoring prompt
- Returns: score (1-10), company/person name, pain point, fit reasoning, suggested outreach angle, urgency
- Items scoring 5+ are stored as leads
- Items scoring 1-4 are discarded (noise)

### Step 3: Store
- DynamoDB `vimal` table, `CA#Lead` partition
- Status lifecycle: `new` → `contacted` → `qualified` → `converted` → `discarded`

### Step 4: Deliver
- Telegram message with 🔥 Hot (8+), 🟡 Warm (5-7)
- Shows: score, pain point, fit angle, source link
- Stats: items scanned, hot/warm/cold counts

## 5. LLM Scoring Prompt

```
You are a lead qualification AI for Complete Automate, a business 
automation consultancy. Given a post/comment from the web, evaluate 
it as a potential sales lead.

Score 1-10 where:
- 10 = Actively seeking automation help, has budget, clear pain point
- 7-9 = Exploring options, likely need, some signals
- 4-6 = Vague mention, might be worth monitoring
- 1-3 = Not relevant / no action needed

Return JSON:
{
  "score": <int>,
  "company": "<company or person name, or null>",
  "pain_point": "<what they need automated>",
  "fit_reason": "<why Complete Automate could help>",
  "angle": "<suggested outreach message angle>",
  "urgency": "<high|medium|low>"
}

Post: {title}\n{body}
```

## 6. Data Model (DynamoDB)

**Partition:** `CA#Lead`
**Sort key:** `id` (MD5 hash of source URL for dedup)

| Field | Type | Description |
|---|---|---|
| `app` | String | `CA#Lead` |
| `id` | String | MD5 of source URL (deterministic) |
| `source` | String | Origin: reddit, hn, google, indeed, crunchbase, producthunt |
| `url` | String | Original post URL |
| `title` | String | Post title |
| `body` | String | Post content / snippet |
| `company` | String or null | Extracted company/person name |
| `score` | Integer | LLM score 1-10 |
| `pain_point` | String | What they need automated |
| `fit_reason` | String | Why Complete Automate fits |
| `angle` | String | Suggested outreach angle |
| `urgency` | String | high / medium / low |
| `status` | String | new / contacted / qualified / converted / discarded |
| `seen_at` | String | ISO timestamp when first seen |

## 7. Delivery Format (Telegram)

```
🔥 Daily Lead Report — Jun 12

━━━━━━━━━━━━━━━━━━━━
🟢 HOT

1. Acme Corp — Invoice automation
   Score: 9 | Need: Manual invoicing for 20-person team
   Angle: Show AI-powered invoice extraction
   Reddit → r/smallbusiness

━━━━━━━━━━━━━━━━━━━━
🟡 WARM

2. Jane (Taskly.io founder)
   Score: 7 | Need: Building automation features
   Angle: Consulting for custom automation build
   Hacker News

━━━━━━━━━━━━━━━━━━━━
📊 23 scanned → 1 hot, 3 warm, 19 cold
```

## 8. Service Structure

### Service Name: Pythia (πυθία — "the oracle")

```
services/pythia/
├── src/
│   ├── __init__.py
│   ├── main.py              # FastAPI app (for health + manual trigger)
│   ├── config.py            # Settings
│   ├── models.py            # Pydantic models
│   ├── collectors/
│   │   ├── __init__.py
│   │   ├── base.py          # Base collector interface
│   │   ├── reddit.py        # Reddit RSS collector
│   │   ├── hackernews.py    # HN Algolia API collector
│   │   ├── google_news.py   # Google News web search collector
│   │   ├── indeed.py        # Indeed web search collector
│   │   ├── crunchbase.py    # Crunchbase RSS collector
│   │   └── producthunt.py   # Product Hunt RSS collector
│   ├── scorer.py            # LLM scoring logic
│   ├── store.py             # DynamoDB CRUD via Clio
│   ├── digest.py            # Telegram digest formatting
│   └── runner.py            # Orchestrator: collect → score → store → deliver
├── tests/
│   ├── __init__.py
│   ├── test_collectors.py
│   ├── test_scorer.py
│   ├── test_store.py
│   ├── test_digest.py
│   └── test_runner.py
├── requirements.txt
├── Dockerfile
└── pytest.ini
```

## 9. Deployment

| Resource | Detail |
|---|---|
| Runtime | k8s CronJob (`schedule: "0 8 * * *"`) |
| Image | `ghcr.io/vimalmenon/micro-army/pythia:latest` |
| ImagePullPolicy | Always |
| Env vars | `DYNAMO_SVC_URL`, `LLM_API_KEY`, `TELEGRAM_BOT_TOKEN` |
| Resources | requests: 100m CPU / 128Mi, limits: 500m / 512Mi |
| Service (for health) | ClusterIP on port 8000 |
| Ingress | Not exposed publicly (internal only) |
| ArgoCD | Application in homelab-army |

## 10. Phase 2 — Future

- Admin dashboard at `admin.completeautomate.com/leads`
- Status tracking (contacted, qualified, converted)
- Notes and follow-up reminders
- Multi-channel monitoring (Twitter/X, LinkedIn posts)
- CRM integration (HubSpot, etc.)

## 11. Cost Estimate

| Item | Cost |
|---|---|
| Reddit RSS | Free |
| HN Algolia API | Free (60 req/min) |
| Google Web Search | Free (low volume) |
| Indeed / LinkedIn search | Free |
| Crunchbase API | Free tier |
| Product Hunt RSS | Free |
| LLM scoring (50 items/run) | ~$0.02 |
| DynamoDB writes | Micro (free tier) |
| **Daily total** | **~$0.02** |
| **Monthly total** | **~$0.60** |
