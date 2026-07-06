# 🪖 micro-army

Microservices army — backend services running on the homelab k3s cluster.

## Services

| Service | Description | Stack |
|---|---|---|
| **clio** | DynamoDB gateway — single source of truth for all data | FastAPI + boto3 |
| **pythia** | Lead oracle — AI-powered lead collection, scoring & enrichment | FastAPI + DeepSeek + DynamoDB |
| **angelos** | Contact form — public message intake | FastAPI + Clio |
| **iris** | Email delivery — transactional messages | FastAPI + SMTP |
| **helios** | Admin dashboard — messages & leads overview | React + Vite |
| **hestia** | Admin backend API — proxies Clio & Pythia for admin dashboard | FastAPI + httpx |
| **atlas** | S3 storage service — file uploads & retrieval | FastAPI + boto3 |
| **athena** | Wiki service — knowledge base with Markdown support | FastAPI |
| **orpheus** | YouTube service — video metadata & content management | FastAPI |
| **arachne** | Tunnel sync — reconciles k3s ingresses with Cloudflare Tunnel | Python |
| **arch** | Landing page — static marketing site | Static HTML |
| **azure-quiz** | AZ-104 quiz app — Azure certification practice | React |

## Structure

```
micro-army/
├── services/
│   └── <service-name>/
│       ├── src/          # Python source code (where applicable)
│       ├── public/       # Static assets (where applicable)
│       ├── Dockerfile
│       └── requirements.txt
└── README.md
```

Each service is deployed on the cluster via ArgoCD from the [homelab-army](https://github.com/vimalmenon/homelab-army) repo.
