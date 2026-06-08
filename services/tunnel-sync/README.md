# tunnel-sync

Reconciles k3s Ingress hostnames with Cloudflare tunnel ingress rules.

Detects hostnames deployed in k8s but missing from the Cloudflare tunnel
config and adds them automatically — so new services behind Traefik are
accessible without manual tunnel config updates.

## How it works

1. **Discover** — runs `kubectl get ingress -A` and collects hostnames
   ending in `.completeautomate.com`
2. **Compare** — fetches the current tunnel ingress config from Cloudflare
3. **Reconcile** — adds any missing hostnames (pointing to the k3s LB)
4. **Report** — outputs a summary of what changed

## Usage

```bash
# Preview changes
CLOUDFLARE_API_TOKEN="..." python src/tunnel_sync.py --dry-run

# Apply changes
CLOUDFLARE_API_TOKEN="..." python src/tunnel_sync.py

# Machine-readable JSON output
CLOUDFLARE_API_TOKEN="..." python src/tunnel_sync.py --json
```

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `CLOUDFLARE_API_TOKEN` | **Yes** | — | Cloudflare API token with DNS + tunnel read/write |
| `CF_ACCOUNT_ID` | No | `3fffdd2b...` | Cloudflare account ID |
| `CF_TUNNEL_ID` | No | `011a9625...` | Tunnel UUID |
| `TUNNEL_BACKEND` | No | `http://192.168.128.200` | Backend URL for new ingress rules |
| `HOST_SUFFIX` | No | `.completeautomate.com` | Only reconcile hostnames with this suffix |

## Deployment

### As a cron job (Hermes Agent)

```bash
hermes cron create \
  --schedule "every 15m" \
  --prompt "Run tunnel-sync to reconcile k3s ingresses with the Cloudflare tunnel config" \
  --workdir /home/hermes/micro-army/services/tunnel-sync
```

### As a Kubernetes CronJob

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: tunnel-sync
  namespace: default
spec:
  schedule: "*/15 * * * *"
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: tunnel-sync
          containers:
          - name: tunnel-sync
            image: tunnel-sync:latest
            env:
            - name: CLOUDFLARE_API_TOKEN
              valueFrom:
                secretKeyRef:
                  name: cloudflare-token
                  key: token
          restartPolicy: OnFailure
```

## Development

```bash
# Install deps
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Test against real cluster (dry-run)
CLOUDFLARE_API_TOKEN="..." python src/tunnel_sync.py --dry-run --verbose
```
