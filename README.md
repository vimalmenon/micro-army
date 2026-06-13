# 🪖 micro-army

Microservices army — backend services running on the homelab k3s cluster.

## Services

| Service | Description | Stack |
|---|---|---|
| **dynamo-svc** | Amazon DynamoDB gateway | FastAPI + boto3 |
| **pythia** | Lead oracle — AI-powered lead collection, scoring & enrichment | FastAPI + DeepSeek + DynamoDB |
| **angelos** | Contact form — public message intake | FastAPI + Clio |
| **iris** | Email delivery — transactional messages | FastAPI + SMTP |
| **helios** | Admin dashboard — messages & leads overview | React + Vite |
| **hestia** | Admin backend API — proxies Clio & Pythia for admin dashboard | FastAPI + httpx |

## Structure

```
micro-army/
├── services/
│   └── <service-name>/
│       ├── src/          # Python source code
│       ├── Dockerfile
│       └── requirements.txt
└── common/               # Shared utilities (future)
```

Each service is deployed on the cluster via ArgoCD from the [homelab-army](https://github.com/vimalmenon/homelab-army) repo.
