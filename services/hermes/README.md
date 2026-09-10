# Hermes 🪶

Telegram messaging microservice for the Complete Automate army.

Hermes sends text messages to a Telegram chat via the Bot API. It's the army's
herald — one `POST /send`, one message, delivered.

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness/readiness probe |
| `POST` | `/send` | Send a plain-text (or parsed) message |
| `POST` | `/send-html` | Send an HTML-formatted message |
| `GET` | `/metrics` | Prometheus metrics |

### Request body (`/send`, `/send-html`)

```json
{
  "text": "Hello from Hermes",
  "chat_id": "optional-override"
}
```

`chat_id` is optional — if omitted, the configured default chat is used.
`/send` also accepts an optional `parse_mode` (`"HTML"` or `"MarkdownV2"`).

## Configuration

| Env var | Purpose |
|---------|---------|
| `TELEGRAM_BOT_TOKEN` | Bot token (from `telegram-bot-creds` secret) |
| `TELEGRAM_CHAT_ID` | Default target chat (from `telegram-bot-creds` secret) |
| `TELEGRAM_API_BASE` | Bot API base URL (default `https://api.telegram.org`) |
| `SERVICE_PORT` | Port (default `8000`) |

## Run locally

```bash
pip install -r requirements.txt
TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... \
  uvicorn src.main:app --host 0.0.0.0 --port 8000
```

## Test

```bash
PYTHONPATH=src:.. pytest tests/ -v
```
